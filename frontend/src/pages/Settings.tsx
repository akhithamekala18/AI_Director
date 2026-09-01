import { useEffect, useState, type FormEvent } from "react";
import {
  getSettings,
  updateSettings,
  listCredentials,
  createCredential,
  revokeCredential,
  getPublishingPreferences,
  updatePublishingPreferences,
  getNotificationPreferences,
  updateNotificationPreferences,
  type UserSettings,
  type StoredCredential,
  type PublishingPreferences,
  type NotificationPreferences,
} from "../api/settings";
import { ApiError } from "../api/client";

export function Settings() {
  const [, setSettings] = useState<UserSettings | null>(null);
  const [credentials, setCredentials] = useState<StoredCredential[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Settings form
  const [emailNotif, setEmailNotif] = useState(true);
  const [inAppNotif, setInAppNotif] = useState(true);
  const [voiceStyle, setVoiceStyle] = useState("");
  const [captionStyle, setCaptionStyle] = useState("");
  const [musicMood, setMusicMood] = useState("");
  const [savingSettings, setSavingSettings] = useState(false);

  // Credential form
  const [credProvider, setCredProvider] = useState("");
  const [credLabel, setCredLabel] = useState("");
  const [credSecret, setCredSecret] = useState("");
  const [creatingCred, setCreatingCred] = useState(false);

  // Publishing prefs
  const [pubPrefs, setPubPrefs] = useState<PublishingPreferences | null>(null);
  const [autoApprove, setAutoApprove] = useState(false);
  const [defaultPostingTime, setDefaultPostingTime] = useState("");
  const [crossPost, setCrossPost] = useState(false);
  const [savingPub, setSavingPub] = useState(false);

  // Notification prefs
  const [notifPrefs, setNotifPrefs] = useState<NotificationPreferences | null>(null);
  const [prefApprovalRequests, setPrefApprovalRequests] = useState(true);
  const [prefReminders, setPrefReminders] = useState(true);
  const [prefPublishOutcomes, setPrefPublishOutcomes] = useState(true);
  const [prefPublishFailures, setPrefPublishFailures] = useState(true);
  const [prefTeamAssignments, setPrefTeamAssignments] = useState(true);
  const [savingNotifPrefs, setSavingNotifPrefs] = useState(false);

  const [notifPrefsChanged, setNotifPrefsChanged] = useState(false);
  const [pubPrefsChanged, setPubPrefsChanged] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const s = await getSettings();
        const c = await listCredentials();
        const pub = await getPublishingPreferences();
        const notif = await getNotificationPreferences();
        if (cancelled) return;
        setSettings(s.settings);
        setEmailNotif(s.settings.email_notifications_enabled);
        setInAppNotif(s.settings.in_app_notifications_enabled);
        setVoiceStyle(s.settings.default_voice_style);
        setCaptionStyle(s.settings.default_caption_style);
        setMusicMood(s.settings.default_music_mood);
        setCredentials(c.credentials);
        setPubPrefs(pub.publishing_preferences);
        setAutoApprove(pub.publishing_preferences.auto_approve_enabled);
        setDefaultPostingTime(
          pub.publishing_preferences.default_posting_time
            ? pub.publishing_preferences.default_posting_time.slice(0, 5)
            : "",
        );
        setCrossPost(pub.publishing_preferences.cross_post_by_default);
        setNotifPrefs(notif.notification_preferences);
        setPrefApprovalRequests(notif.notification_preferences.approval_requests);
        setPrefReminders(notif.notification_preferences.reminders);
        setPrefPublishOutcomes(notif.notification_preferences.publish_outcomes);
        setPrefPublishFailures(notif.notification_preferences.publish_failures);
        setPrefTeamAssignments(notif.notification_preferences.team_assignments);
      } catch (err) {
        if (err instanceof ApiError) {
          setError(`Failed to load settings (${err.status})`);
        } else {
          setError("Failed to load settings");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSaveSettings = async (e: FormEvent) => {
    e.preventDefault();
    setSavingSettings(true);
    setError(null);
    try {
      const res = await updateSettings({
        email_notifications_enabled: emailNotif,
        in_app_notifications_enabled: inAppNotif,
        default_voice_style: voiceStyle,
        default_caption_style: captionStyle,
        default_music_mood: musicMood,
      });
      setSettings(res.settings);
    } catch {
      setError("Failed to save settings");
    } finally {
      setSavingSettings(false);
    }
  };

  const handleCreateCredential = async (e: FormEvent) => {
    e.preventDefault();
    if (!credProvider.trim() || !credLabel.trim() || !credSecret) return;
    setCreatingCred(true);
    setError(null);
    try {
      const res = await createCredential({
        provider: credProvider.trim(),
        label: credLabel.trim(),
        secret: credSecret,
      });
      setCredentials((prev) => [...prev, res.credential]);
      setCredProvider("");
      setCredLabel("");
      setCredSecret("");
    } catch {
      setError("Failed to create credential");
    } finally {
      setCreatingCred(false);
    }
  };

  const handleSavePublishingPrefs = async (e: FormEvent) => {
    e.preventDefault();
    setSavingPub(true);
    setError(null);
    try {
      const data: {
        auto_approve_enabled: boolean;
        default_posting_time: string | null;
        cross_post_by_default: boolean;
      } = {
        auto_approve_enabled: autoApprove,
        default_posting_time: defaultPostingTime
          ? `${defaultPostingTime}:00`
          : null,
        cross_post_by_default: crossPost,
      };
      const res = await updatePublishingPreferences(data);
      setPubPrefs(res.publishing_preferences);
      setPubPrefsChanged(false);
    } catch {
      setError("Failed to save publishing preferences");
    } finally {
      setSavingPub(false);
    }
  };

  const handleSaveNotifPrefs = async (e: FormEvent) => {
    e.preventDefault();
    setSavingNotifPrefs(true);
    setError(null);
    try {
      const res = await updateNotificationPreferences({
        approval_requests: prefApprovalRequests,
        reminders: prefReminders,
        publish_outcomes: prefPublishOutcomes,
        publish_failures: prefPublishFailures,
        team_assignments: prefTeamAssignments,
      });
      setNotifPrefs(res.notification_preferences);
      setNotifPrefsChanged(false);
    } catch {
      setError("Failed to save notification preferences");
    } finally {
      setSavingNotifPrefs(false);
    }
  };

  const handleRevoke = async (pk: number) => {
    if (!confirm("Revoke this credential?")) return;
    setError(null);
    try {
      await revokeCredential(pk);
      setCredentials((prev) => prev.filter((c) => c.id !== pk));
    } catch {
      setError("Failed to revoke credential");
    }
  };

  if (loading) return <div className="page-loading">Loading settings…</div>;

  return (
    <div className="page">
      <h1>Settings</h1>
      {error && <div className="page-error">{error}</div>}

      {/* Notification Settings */}
      <section className="detail-section">
        <h2>Notifications</h2>
        <form onSubmit={handleSaveSettings} className="form-card">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={emailNotif}
              onChange={(e) => setEmailNotif(e.target.checked)}
            />
            Email notifications
          </label>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={inAppNotif}
              onChange={(e) => setInAppNotif(e.target.checked)}
            />
            In-app notifications
          </label>

          <h3>Default Content Styles</h3>
          <label htmlFor="voice-style">Voice Style</label>
          <input
            id="voice-style"
            type="text"
            value={voiceStyle}
            onChange={(e) => setVoiceStyle(e.target.value)}
            placeholder="e.g. Professional, Casual"
          />
          <label htmlFor="caption-style">Caption Style</label>
          <input
            id="caption-style"
            type="text"
            value={captionStyle}
            onChange={(e) => setCaptionStyle(e.target.value)}
            placeholder="e.g. Bold, Minimal"
          />
          <label htmlFor="music-mood">Music Mood</label>
          <input
            id="music-mood"
            type="text"
            value={musicMood}
            onChange={(e) => setMusicMood(e.target.value)}
            placeholder="e.g. Upbeat, Calm"
          />

          <button
            type="submit"
            disabled={savingSettings}
            className="btn btn-primary"
          >
            {savingSettings ? "Saving…" : "Save Settings"}
          </button>
        </form>
      </section>

      {/* Credentials */}
      <section className="detail-section">
        <h2>Platform Credentials</h2>
        {credentials.length > 0 ? (
          <table className="project-table">
            <thead>
              <tr>
                <th>Provider</th>
                <th>Label</th>
                <th>Created</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {credentials.map((c) => (
                <tr key={c.id}>
                  <td>{c.provider}</td>
                  <td>{c.label}</td>
                  <td>{new Date(c.created_at).toLocaleDateString()}</td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-danger btn-sm"
                      onClick={() => handleRevoke(c.id)}
                    >
                      Revoke
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="empty-text">No credentials stored.</p>
        )}

        <h3>Add Credential</h3>
        <form onSubmit={handleCreateCredential} className="form-card">
          <label htmlFor="cred-provider">Provider *</label>
          <input
            id="cred-provider"
            type="text"
            value={credProvider}
            onChange={(e) => setCredProvider(e.target.value)}
            placeholder="e.g. YouTube, TikTok"
            required
            disabled={creatingCred}
          />
          <label htmlFor="cred-label">Label *</label>
          <input
            id="cred-label"
            type="text"
            value={credLabel}
            onChange={(e) => setCredLabel(e.target.value)}
            placeholder="e.g. My YouTube Account"
            required
            disabled={creatingCred}
          />
          <label htmlFor="cred-secret">Secret / API Key *</label>
          <input
            id="cred-secret"
            type="password"
            value={credSecret}
            onChange={(e) => setCredSecret(e.target.value)}
            required
            disabled={creatingCred}
          />
          <button
            type="submit"
            disabled={creatingCred}
            className="btn btn-primary"
          >
            {creatingCred ? "Adding…" : "Add Credential"}
          </button>
        </form>
      </section>

      {/* Publishing Preferences */}
      <section className="detail-section">
        <h2>Publishing Preferences</h2>
        {pubPrefs ? (
          <form onSubmit={handleSavePublishingPrefs} className="form-card">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={autoApprove}
                onChange={(e) => {
                  setAutoApprove(e.target.checked);
                  setPubPrefsChanged(true);
                }}
              />
              Auto-approve prepared publications
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={crossPost}
                onChange={(e) => {
                  setCrossPost(e.target.checked);
                  setPubPrefsChanged(true);
                }}
              />
              Cross-post to connected platforms by default
            </label>
            <label htmlFor="default-posting-time">Default Posting Time</label>
            <input
              id="default-posting-time"
              type="time"
              value={defaultPostingTime}
              onChange={(e) => {
                setDefaultPostingTime(e.target.value);
                setPubPrefsChanged(true);
              }}
            />
            <button
              type="submit"
              disabled={savingPub || !pubPrefsChanged}
              className="btn btn-primary"
            >
              {savingPub ? "Saving…" : "Save Publishing Preferences"}
            </button>
          </form>
        ) : (
          <p className="empty-text">No publishing preferences available.</p>
        )}
      </section>

      {/* Notification Preferences */}
      <section className="detail-section">
        <h2>Notification Preferences</h2>
        {notifPrefs ? (
          <form onSubmit={handleSaveNotifPrefs} className="form-card">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={prefApprovalRequests}
                onChange={(e) => {
                  setPrefApprovalRequests(e.target.checked);
                  setNotifPrefsChanged(true);
                }}
              />
              Approval requests
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={prefReminders}
                onChange={(e) => {
                  setPrefReminders(e.target.checked);
                  setNotifPrefsChanged(true);
                }}
              />
              Reminders
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={prefPublishOutcomes}
                onChange={(e) => {
                  setPrefPublishOutcomes(e.target.checked);
                  setNotifPrefsChanged(true);
                }}
              />
              Publish outcomes
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={prefPublishFailures}
                onChange={(e) => {
                  setPrefPublishFailures(e.target.checked);
                  setNotifPrefsChanged(true);
                }}
              />
              Publish failures
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={prefTeamAssignments}
                onChange={(e) => {
                  setPrefTeamAssignments(e.target.checked);
                  setNotifPrefsChanged(true);
                }}
              />
              Team assignments
            </label>
            <button
              type="submit"
              disabled={savingNotifPrefs || !notifPrefsChanged}
              className="btn btn-primary"
            >
              {savingNotifPrefs ? "Saving…" : "Save Notification Preferences"}
            </button>
          </form>
        ) : (
          <p className="empty-text">No notification preferences available.</p>
        )}
      </section>
    </div>
  );
}
