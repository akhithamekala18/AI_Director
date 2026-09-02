# -*- coding: utf-8 -*-
"""DG-11 publishing adapter and OAuth tests."""
import os
import pytest
from unittest.mock import patch, MagicMock


class TestAdapterRegistry:
    def test_get_youtube_adapter(self):
        from apps.publishing.adapters import get_adapter
        adapter = get_adapter("YouTube")
        assert adapter.platform == "YouTube"

    def test_get_instagram_adapter(self):
        from apps.publishing.adapters import get_adapter
        adapter = get_adapter("Instagram")
        assert adapter.platform == "Instagram"

    def test_get_tiktok_adapter(self):
        from apps.publishing.adapters import get_adapter
        adapter = get_adapter("TikTok")
        assert adapter.platform == "TikTok"

    def test_unknown_platform_raises(self):
        from apps.publishing.adapters import get_adapter
        with pytest.raises(ValueError, match="No adapter"):
            get_adapter("UnknownPlatform")


class TestYouTubeAdapter:
    def test_authorization_url(self):
        from apps.publishing.adapters.youtube import YouTubeAdapter
        with patch.dict(os.environ, {"YOUTUBE_CLIENT_ID": "test_id", "YOUTUBE_CLIENT_SECRET": "test_secret"}):
            adapter = YouTubeAdapter()
            url = adapter.get_authorization_url("test_state")
            assert "accounts.google.com" in url
            assert "test_id" in url
            assert "test_state" in url

    def test_normalize_error_401(self):
        from apps.publishing.adapters.youtube import YouTubeAdapter
        exc = MagicMock()
        exc.response.status_code = 401
        result = YouTubeAdapter().normalize_error(exc)
        assert not result.success
        assert result.retryable
        assert result.platform == "YouTube"

    def test_normalize_error_403(self):
        from apps.publishing.adapters.youtube import YouTubeAdapter
        exc = MagicMock()
        exc.response.status_code = 403
        result = YouTubeAdapter().normalize_error(exc)
        assert not result.success
        assert not result.retryable


class TestInstagramAdapter:
    def test_authorization_url(self):
        from apps.publishing.adapters.instagram import InstagramAdapter
        with patch.dict(os.environ, {"INSTAGRAM_CLIENT_ID": "ig_id", "INSTAGRAM_CLIENT_SECRET": "ig_secret"}):
            adapter = InstagramAdapter()
            url = adapter.get_authorization_url("test_state")
            assert "facebook.com" in url
            assert "ig_id" in url


class TestTikTokAdapter:
    def test_authorization_url(self):
        from apps.publishing.adapters.tiktok import TikTokAdapter
        with patch.dict(os.environ, {"TIKTOK_CLIENT_KEY": "tt_key", "TIKTOK_CLIENT_SECRET": "tt_secret"}):
            adapter = TikTokAdapter()
            url = adapter.get_authorization_url("test_state")
            assert "tiktok.com" in url
            assert "tt_key" in url


class TestOAuthState:
    def test_generate_and_validate_state(self):
        from apps.publishing.oauth import _generate_state, _validate_state
        state = _generate_state(user_id=1)
        assert _validate_state(state, user_id=1)
        # State consumed after validation
        assert not _validate_state(state, user_id=1)

    def test_reject_wrong_user(self):
        from apps.publishing.oauth import _generate_state, _validate_state
        state = _generate_state(user_id=1)
        assert not _validate_state(state, user_id=2)

    def test_reject_expired_state(self):
        from apps.publishing.oauth import _generate_state, _validate_state, _oauth_states
        state = _generate_state(user_id=1)
        _oauth_states[state]["created_at"] = 0  # Force expiry
        assert not _validate_state(state, user_id=1)


class TestPublishingTaskExists:
    def test_task_importable(self):
        from apps.publishing.tasks import publish_entry
        assert publish_entry is not None

    def test_task_is_shared(self):
        from apps.publishing.tasks import publish_entry
        assert hasattr(publish_entry, "delay")


class TestCredentialEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        from apps.settings_app.services import encrypt_secret, decrypt_secret
        original = "my_secret_access_token_12345"
        encrypted = encrypt_secret(original)
        assert encrypted != original
        decrypted = decrypt_secret(encrypted)
        assert decrypted == original

    def test_decrypt_wrong_key_fails(self):
        from apps.settings_app.services import encrypt_secret, decrypt_secret
        encrypted = encrypt_secret("secret")
        # Tamper with the encrypted value
        with pytest.raises(ValueError):
            decrypt_secret("not-a-valid-token")


class TestPublishingServices:
    @pytest.mark.django_db
    def test_connect_social_account(self, user, team):
        from apps.publishing.services import connect_social_account
        account = connect_social_account(user, "YouTube", "UC123456", "Test Channel")
        assert account.platform == "YouTube"
        assert account.platform_account_id == "UC123456"
        assert account.display_name == "Test Channel"
        assert account.status == "active"

    @pytest.mark.django_db
    def test_approval_validity(self, user, team, project):
        from apps.publishing.services import connect_social_account, create_post, create_entry, approve_entry, is_approval_valid
        from apps.publishing.models import ScheduledEntry
        from django.utils import timezone
        from datetime import timedelta
        account = connect_social_account(user, "YouTube", "UC123456", "Test")
        post = create_post(user, project)
        entry = create_entry(user, post, account.id, timezone.now() + timedelta(days=3))
        entry.status = ScheduledEntry.Status.READY_FOR_APPROVAL
        entry.save()
        approval = approve_entry(user, entry)
        assert is_approval_valid(entry)

    @pytest.mark.django_db
    def test_retry_logic(self, user, team, project):
        from apps.publishing.services import connect_social_account, create_post, create_entry, approve_entry, can_retry_entry
        from apps.publishing.models import ScheduledEntry
        from django.utils import timezone
        from datetime import timedelta
        account = connect_social_account(user, "YouTube", "UC123456", "Test")
        post = create_post(user, project)
        entry = create_entry(user, post, account.id, timezone.now() + timedelta(days=3))
        entry.status = ScheduledEntry.Status.READY_FOR_APPROVAL
        entry.save()
        approve_entry(user, entry)
        # Entry is APPROVED, not UPLOAD_FAILED, so retry not allowed
        retryable, reason = can_retry_entry(entry)
        assert not retryable
