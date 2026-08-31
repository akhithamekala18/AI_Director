from datetime import timedelta
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone as dj_tz
from .models import Approval, PublishingAuditLog, ScheduledEntry, ScheduledPost, SocialAccount, UploadAttempt

_VALIDITY_HOURS = 24

def _is_member(user, team_id):
    return user.memberships.filter(team_id=team_id).exists()

def _team_of(user):
    m = user.memberships.select_related("team").order_by("id").first()
    if not m:
        raise DjangoValidationError("user has no team")
    return m.team

def _audit(user, action, entry=None, approval=None, attempt=None, reason=""):
    PublishingAuditLog.objects.create(actor=user, action=action, entry=entry, approval=approval, attempt=attempt, reason=reason)

def connect_social_account(user, platform, platform_account_id, display_name=""):
    team = _team_of(user)
    account, created = SocialAccount.objects.get_or_create(owner=user, platform=platform, platform_account_id=platform_account_id, defaults={"team": team, "display_name": display_name})
    if not created and account.status != SocialAccount.Status.ACTIVE:
        account.status = SocialAccount.Status.ACTIVE
        account.save()
    _audit(user, "social_account_connected", reason=f"{platform}:{platform_account_id}")
    return account

def disconnect_social_account(user, account_id):
    account = _get_social_account(user, account_id)
    account.status = SocialAccount.Status.REVOKED
    account.save()
    ScheduledEntry.objects.filter(social_account=account, status=ScheduledEntry.Status.UPLOADING).update(status=ScheduledEntry.Status.FAILED)
    _audit(user, "social_account_disconnected", reason=f"account:{account_id}")
    return account

def list_social_accounts(user):
    team_ids = user.memberships.values_list("team_id", flat=True)
    return SocialAccount.objects.filter(team_id__in=team_ids, status=SocialAccount.Status.ACTIVE)

def _get_social_account(user, account_id):
    team_ids = user.memberships.values_list("team_id", flat=True)
    account = SocialAccount.objects.filter(id=account_id, team_id__in=team_ids).first()
    if not account:
        raise DjangoValidationError("social account not found")
    return account

def create_post(user, project, video=None):
    team = _team_of(user)
    post = ScheduledPost.objects.create(project=project, team=team, owner=user, video=video, status=ScheduledPost.Status.DRAFT)
    _audit(user, "post_created", reason=f"post:{post.id}")
    return post

def get_post(user, post_id):
    team_ids = user.memberships.values_list("team_id", flat=True)
    return ScheduledPost.objects.filter(id=post_id, team_id__in=team_ids).first()

def list_posts(user, project):
    team_ids = user.memberships.values_list("team_id", flat=True)
    return ScheduledPost.objects.filter(project=project, team_id__in=team_ids)

def create_entry(user, post, social_account_id, scheduled_utc, tz_name="UTC"):
    team = _team_of(user)
    social_account = _get_social_account(user, social_account_id)
    if social_account.team_id != team.id:
        raise DjangoValidationError("social account does not belong to this team")
    entry = ScheduledEntry.objects.create(post=post, social_account=social_account, platform=social_account.platform, team=team, status=ScheduledEntry.Status.SCHEDULED, scheduled_utc=scheduled_utc, timezone=tz_name)
    _audit(user, "entry_created", entry=entry, reason=f"platform:{social_account.platform}")
    return entry

def get_entry(user, entry_id):
    team_ids = user.memberships.values_list("team_id", flat=True)
    return ScheduledEntry.objects.filter(id=entry_id, team_id__in=team_ids).first()

def list_entries(user, post):
    team_ids = user.memberships.values_list("team_id", flat=True)
    return ScheduledEntry.objects.filter(post=post, team_id__in=team_ids)

def cancel_entry(user, entry):
    if entry.status in (ScheduledEntry.Status.UPLOADING, ScheduledEntry.Status.PUBLISHED):
        raise DjangoValidationError(f"cannot cancel entry in '{entry.status}' state")
    entry.status = ScheduledEntry.Status.CANCELED
    entry.save()
    _audit(user, "entry_canceled", entry=entry)
    return entry

def _compute_expires_at(scheduled_utc):
    return scheduled_utc - timedelta(hours=_VALIDITY_HOURS)

def approve_entry(user, entry, reason=""):
    if entry.status not in (ScheduledEntry.Status.READY_FOR_APPROVAL, ScheduledEntry.Status.APPROVAL_INVALIDATED, ScheduledEntry.Status.REJECTED):
        raise DjangoValidationError(f"cannot approve entry in '{entry.status}' state")
    Approval.objects.filter(entry=entry, invalidated=False, decision=Approval.Decision.APPROVE).update(invalidated=True, invalidated_at=dj_tz.now())
    expires_at = _compute_expires_at(entry.scheduled_utc)
    approval = Approval.objects.create(entry=entry, actor=user, decision=Approval.Decision.APPROVE, reason=reason.strip() if reason else "", expires_at=expires_at)
    entry.status = ScheduledEntry.Status.APPROVED
    entry.save()
    _audit(user, "entry_approved", entry=entry, approval=approval, reason=reason)
    return approval

def reject_entry(user, entry, reason=""):
    if entry.status not in (ScheduledEntry.Status.READY_FOR_APPROVAL, ScheduledEntry.Status.APPROVAL_INVALIDATED):
        raise DjangoValidationError(f"cannot reject entry in '{entry.status}' state")
    approval = Approval.objects.create(entry=entry, actor=user, decision=Approval.Decision.REJECT, reason=reason.strip() if reason else "")
    entry.status = ScheduledEntry.Status.REJECTED
    entry.save()
    _audit(user, "entry_rejected", entry=entry, approval=approval, reason=reason)
    return approval

def is_approval_valid(entry):
    from django.db.models import Q
    now = dj_tz.now()
    return Approval.objects.filter(entry=entry, decision=Approval.Decision.APPROVE, invalidated=False).filter(Q(expires_at__isnull=True) | Q(expires_at__gte=now)).exists()

def list_approvals(user, entry):
    team_ids = user.memberships.values_list("team_id", flat=True)
    return Approval.objects.filter(entry=entry, entry__team_id__in=team_ids)

def invalidate_approvals_for_entry(entry, reason="schedule_or_platform_changed"):
    count = Approval.objects.filter(entry=entry, invalidated=False).update(invalidated=True, invalidated_at=dj_tz.now())
    if count > 0:
        entry.status = ScheduledEntry.Status.APPROVAL_INVALIDATED
        entry.save()
    return count

def create_upload_attempt(user, entry):
    if entry.status != ScheduledEntry.Status.APPROVED:
        raise DjangoValidationError(f"upload requires APPROVED status, current: '{entry.status}'")
    if not is_approval_valid(entry):
        raise DjangoValidationError("upload requires a valid, unexpired approval")
    attempt_no = entry.upload_attempts.count() + 1
    if attempt_no > 4:
        raise DjangoValidationError("maximum upload attempts (4) exceeded")
    attempt = UploadAttempt.objects.create(entry=entry, attempt_no=attempt_no, status=UploadAttempt.Status.PENDING)
    entry.status = ScheduledEntry.Status.UPLOADING
    entry.save()
    _audit(user, "upload_attempt_created", entry=entry, attempt=attempt)
    return attempt

def complete_upload_attempt(attempt, success, failure_kind=UploadAttempt.FailureKind.NONE, error=""):
    attempt.finished_at = dj_tz.now()
    if success:
        attempt.status = UploadAttempt.Status.SUCCESS
        attempt.entry.status = ScheduledEntry.Status.PUBLISHED
        attempt.entry.save()
    else:
        attempt.status = UploadAttempt.Status.FAILED
        attempt.failure_kind = failure_kind
        attempt.error_message = error
        entry = attempt.entry
        total = entry.upload_attempts.count()  # noqa: F841
        successful = entry.upload_attempts.filter(status=UploadAttempt.Status.SUCCESS).count()
        if successful > 0:
            entry.status = ScheduledEntry.Status.FAILED
            entry.save()
    attempt.save()
    return attempt

def get_publishing_history(user, project):
    team_ids = user.memberships.values_list("team_id", flat=True)
    return ScheduledEntry.objects.filter(post__project=project, team_id__in=team_ids).select_related("post", "social_account").order_by("-created_at")

def get_pending_approvals(user):
    team_ids = user.memberships.values_list("team_id", flat=True)
    return ScheduledEntry.objects.filter(team_id__in=team_ids, status__in=[ScheduledEntry.Status.READY_FOR_APPROVAL, ScheduledEntry.Status.APPROVAL_INVALIDATED]).select_related("post", "social_account")


# --- Task 40: Approval validity & invalidation ---

def reschedule_entry(user, entry, new_scheduled_utc, new_tz_name=None):
    """Reschedule an entry. Invalidates all existing approvals (PRD Decision 5)."""
    if entry.status in (ScheduledEntry.Status.UPLOADING, ScheduledEntry.Status.PUBLISHED, ScheduledEntry.Status.CANCELED):
        raise DjangoValidationError(f"cannot reschedule entry in '{entry.status}' state")
    entry.scheduled_utc = new_scheduled_utc
    if new_tz_name:
        entry.timezone = new_tz_name
    entry.save()
    count = invalidate_approvals_for_entry(entry, reason="reschedule")
    entry.status = ScheduledEntry.Status.READY_FOR_APPROVAL
    entry.save()
    _audit(user, "entry_rescheduled", entry=entry, reason=f"invalidated:{count}_approvals")
    return entry, count


def change_entry_platform(user, entry, new_platform, new_social_account_id=None):
    """Change the platform for an entry. Invalidates all approvals (PRD Decision 5)."""
    if entry.status in (ScheduledEntry.Status.UPLOADING, ScheduledEntry.Status.PUBLISHED, ScheduledEntry.Status.CANCELED):
        raise DjangoValidationError(f"cannot change platform for entry in '{entry.status}' state")
    old_platform = entry.platform
    entry.platform = new_platform
    if new_social_account_id:
        social_account = _get_social_account(user, new_social_account_id)
        entry.social_account = social_account
    entry.save()
    count = invalidate_approvals_for_entry(entry, reason=f"platform_change_{old_platform}_to_{new_platform}")
    entry.status = ScheduledEntry.Status.READY_FOR_APPROVAL
    entry.save()
    _audit(user, "entry_platform_changed", entry=entry, reason=f"invalidated:{count}_approvals")
    return entry, count


def recheck_expired_approvals(user=None):
    """Re-check all APPROVED entries for expired approvals.

    If an entry's approval has expired, move it back to READY_FOR_APPROVAL.
    This is the expiry enforcement from PRD Decision 2.
    """
    from django.db.models import Q
    now = dj_tz.now()
    # Find APPROVED entries where the latest valid approval has expired
    approved_entries = ScheduledEntry.objects.filter(status=ScheduledEntry.Status.APPROVED)
    expired_count = 0
    for entry in approved_entries:
        valid_approval = Approval.objects.filter(
            entry=entry, decision=Approval.Decision.APPROVE, invalidated=False
        ).filter(Q(expires_at__isnull=True) | Q(expires_at__gte=now)).order_by("-granted_at").first()
        if valid_approval is None:
            # All approvals expired or invalidated
            entry.status = ScheduledEntry.Status.READY_FOR_APPROVAL
            entry.save()
            _audit(user or entry.post.owner, "approval_expired", entry=entry, reason="all_approvals_expired")
            expired_count += 1
    return expired_count


def approve_entry_with_payload(user, entry, reason="", payload=None):
    """Approve an entry with a payload snapshot (PRD: approval bound to payload).

    Stores the payload snapshot on both the approval and the entry.
    """
    if entry.status not in (
        ScheduledEntry.Status.READY_FOR_APPROVAL,
        ScheduledEntry.Status.APPROVAL_INVALIDATED,
        ScheduledEntry.Status.REJECTED,
    ):
        raise DjangoValidationError(f"cannot approve entry in '{entry.status}' state")
    # Invalidate previous approvals
    Approval.objects.filter(
        entry=entry, invalidated=False, decision=Approval.Decision.APPROVE
    ).update(invalidated=True, invalidated_at=dj_tz.now())
    expires_at = _compute_expires_at(entry.scheduled_utc)
    approval = Approval.objects.create(
        entry=entry, actor=user, decision=Approval.Decision.APPROVE,
        reason=reason.strip() if reason else "", expires_at=expires_at,
    )
    entry.status = ScheduledEntry.Status.APPROVED
    if payload:
        entry.payload_snapshot = payload
    entry.save()
    _audit(user, "entry_approved", entry=entry, approval=approval, reason=reason)
    return approval
