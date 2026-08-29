# -*- coding: utf-8 -*-
def record_audit(actor, action, target_type="", target_id="", reason=""):
    """Create an append-only audit record. Safe to call from any service."""
    from apps.audit.models import AuditLog

    return AuditLog.objects.create(
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=str(target_id)[:64],
        reason=reason[:255],
    )
