import { useEffect, useState, type FormEvent } from "react";
import {
  getSettings,
  updateSettings,
  listCredentials,
  createCredential,
  revokeCredential,
  type UserSettings,
  type StoredCredential,
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

  useEffect(() => {
    Promise.all([getSettings(), listCredentials()])
      .then(([s, c]) => {
        setSettings(s.settings);
        setEmailNotif(s.settings.email_notifications_enabled);
        setInAppNotif(s.settings.in_app_notifications_enabled);
        setVoiceStyle(s.settings.default_voice_style);
        setCaptionStyle(s.settings.default_caption_style);
        setMusicMood(s.settings.default_music_mood);
        setCredentials(c.credentials);
      })
      .catch((err) => {
        if (err instanceof ApiError) {
          setError(`Failed to load settings (${err.status})`);
        } else {
          setError("Failed to load settings");
        }
      })
      .finally(() => setLoading(false));
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
    </div>
  );
}
