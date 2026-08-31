import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  listSchedules,
  createSchedule,
  rescheduleEntry,
  cancelEntry,
  getCalendar,
  getBestTime,
  type ScheduleEntry,
  type BestTimeSuggestion,
} from "../api/scheduler";
import { ApiError } from "../api/client";

// ---------------------------------------------------------------------------
// Schedule states (backend: apps.scheduler.models.ScheduleEntry — do not invent)
// status: scheduled | rescheduled | cancelled | published | failed
// ---------------------------------------------------------------------------

function statusClass(status: string): string {
  if (status === "scheduled" || status === "rescheduled") return "state-generating";
  if (status === "published") return "state-approved";
  if (status === "cancelled") return "state-draft";
  if (status === "failed") return "state-revision";
  return "state-review";
}

function formatStatus(status: string): string {
  return status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

const PLATFORMS = [
  "YouTube",
  "TikTok",
  "Instagram",
  "Instagram Reels",
  "Instagram Feed",
  "Twitter",
  "LinkedIn",
];

const TIMEZONES = [
  "UTC",
  "Asia/Kolkata",
  "America/New_York",
  "America/Los_Angeles",
  "Europe/London",
  "Europe/Paris",
  "Asia/Shanghai",
  "Asia/Tokyo",
  "Australia/Sydney",
];

// ---------------------------------------------------------------------------
// Helpers to build the ISO local datetime string the backend expects.
// backend: datetime.fromisoformat(local_dt) — naive local datetime + timezone.
// ---------------------------------------------------------------------------

function buildLocalIso(date: string, time: string): string {
  if (!date || !time) return "";
  return `${date}T${time}:00`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function Scheduler() {
  const { id } = useParams<{ id: string }>();
  const projectId = Number(id);

  const [entries, setEntries] = useState<ScheduleEntry[]>([]);
  const [calendar, setCalendar] = useState<ScheduleEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create form
  const [newPlatform, setNewPlatform] = useState("YouTube");
  const [newDate, setNewDate] = useState("");
  const [newTime, setNewTime] = useState("");
  const [newTimezone, setNewTimezone] = useState("UTC");
  const [creating, setCreating] = useState(false);

  // Best-time guidance
  const [suggestion, setSuggestion] = useState<BestTimeSuggestion | null>(null);
  const [suggestionLoading, setSuggestionLoading] = useState(false);

  // Reschedule state (per entry)
  const [rescheduleId, setRescheduleId] = useState<number | null>(null);
  const [resDate, setResDate] = useState("");
  const [resTime, setResTime] = useState("");
  const [resTimezone, setResTimezone] = useState("");
  const [reschedulingId, setReschedulingId] = useState<number | null>(null);

  // Cancel state
  const [cancelId, setCancelId] = useState<number | null>(null);
  const [cancelReason, setCancelReason] = useState("");
  const [cancellingId, setCancellingId] = useState<number | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [listRes, calRes] = await Promise.all([
        listSchedules(projectId),
        getCalendar(projectId),
      ]);
      setEntries(listRes.entries);
      setCalendar(calRes.calendar);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setEntries([]);
        setCalendar([]);
      } else {
        setError("Failed to load schedule data");
      }
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (projectId) loadData();
  }, [projectId, loadData]);

  const loadSuggestion = useCallback(
    async (platform: string) => {
      setSuggestionLoading(true);
      setSuggestion(null);
      try {
      const res = await getBestTime(projectId, platform);
      setSuggestion(res.suggestion);
    } catch {
      setSuggestion(null);
    } finally {
        setSuggestionLoading(false);
      }
    },
    [projectId],
  );

  useEffect(() => {
    if (projectId && newPlatform) loadSuggestion(newPlatform);
  }, [projectId, newPlatform, loadSuggestion]);

  // ---- Create ----

  const handleCreate = async () => {
    const localIso = buildLocalIso(newDate, newTime);
    if (!localIso) {
      setError("Please select a publication date and time.");
      return;
    }
    setCreating(true);
    setError(null);
    try {
      const res = await createSchedule(projectId, {
        platform: newPlatform,
        scheduled_local_datetime: localIso,
        timezone: newTimezone,
      });
      setEntries((prev) => [...prev.filter((e) => e.id !== res.entry.id), res.entry]);
      await loadData();
      setNewDate("");
      setNewTime("");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? `Schedule creation failed: ${err.message}`
          : "Schedule creation failed",
      );
    } finally {
      setCreating(false);
    }
  };

  // ---- Reschedule ----

  const handleStartReschedule = (entry: ScheduleEntry) => {
    setRescheduleId(entry.id);
    setResTimezone(entry.timezone || "UTC");
    const dt = entry.scheduled_local_datetime;
    if (dt) {
      const match = dt.match(/^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})/);
      if (match) {
        setResDate(match[1]);
        setResTime(match[2]);
      } else {
        setResDate("");
        setResTime("");
      }
    }
  };

  const handleReschedule = async () => {
    const localIso = buildLocalIso(resDate, resTime);
    if (!localIso) {
      setError("Please select a new publication date and time.");
      return;
    }
    if (rescheduleId === null) return;
    setReschedulingId(rescheduleId);
    setError(null);
    try {
      const res = await rescheduleEntry(projectId, rescheduleId, {
        scheduled_local_datetime: localIso,
        timezone: resTimezone,
      });
      setEntries((prev) => prev.map((e) => (e.id === res.entry.id ? res.entry : e)));
      await loadData();
      setRescheduleId(null);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? `Reschedule failed: ${err.message}`
          : "Reschedule failed",
      );
    } finally {
      setReschedulingId(null);
    }
  };

  // ---- Cancel ----

  const handleStartCancel = (entry: ScheduleEntry) => {
    setCancelId(entry.id);
    setCancelReason("");
  };

  const handleCancel = async () => {
    if (cancelId === null) return;
    if (!confirm("Cancel this schedule entry? This cannot be undone.")) return;
    setCancellingId(cancelId);
    setError(null);
    try {
      const res = await cancelEntry(projectId, cancelId, cancelReason.trim());
      setEntries((prev) => prev.map((e) => (e.id === res.entry.id ? res.entry : e)));
      await loadData();
      setCancelId(null);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? `Cancel failed: ${err.message}`
          : "Cancel failed",
      );
    } finally {
      setCancellingId(null);
    }
  };

  if (loading) return <div className="page-loading">Loading scheduler…</div>;

  return (
    <div className="page">
      <h1>Scheduler</h1>
      <p>
        <Link to={`/projects/${projectId}`}>&larr; Back to Project</Link>
      </p>

      {error && <div className="page-error">{error}</div>}

      {/* ---- Create schedule ---- */}
      <div className="detail-section">
        <h2>Schedule Content</h2>
        <p className="text-muted">
          Schedule requires an <strong>approved preview</strong> for the selected
          platform (preview-before-schedule invariant). One entry per platform.
        </p>
        <div className="action-buttons">
          <label htmlFor="sched-platform">Platform</label>
          <select
            id="sched-platform"
            value={newPlatform}
            onChange={(e) => setNewPlatform(e.target.value)}
          >
            {PLATFORMS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          <label htmlFor="sched-date">Publication Date</label>
          <input
            id="sched-date"
            type="date"
            value={newDate}
            onChange={(e) => setNewDate(e.target.value)}
          />
          <label htmlFor="sched-time">Time</label>
          <input
            id="sched-time"
            type="time"
            value={newTime}
            onChange={(e) => setNewTime(e.target.value)}
          />
          <label htmlFor="sched-tz">Timezone</label>
          <select
            id="sched-tz"
            value={newTimezone}
            onChange={(e) => setNewTimezone(e.target.value)}
          >
            {TIMEZONES.map((tz) => (
              <option key={tz} value={tz}>
                {tz}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleCreate}
            disabled={creating}
          >
            {creating ? "Scheduling…" : "Create Schedule"}
          </button>
        </div>

        {/* Best-time guidance */}
        <div className="detail-section-sub">
          <h3>Best-Time Guidance ({newPlatform})</h3>
          {suggestionLoading ? (
            <p className="text-muted">Loading guidance…</p>
          ) : suggestion ? (
            <div className="best-time-card">
              <p className="media-asset-ref">
                <strong>Best days:</strong> {suggestion.best_days.join(", ")}
              </p>
              <p className="media-asset-ref">
                <strong>Best hours (UTC):</strong>{" "}
                {suggestion.best_hours_utc.join(", ")}
              </p>
              <p className="media-asset-ref">{suggestion.reasoning}</p>
            </div>
          ) : (
            <p className="text-muted">
              Best-time guidance loads for the selected platform.
            </p>
          )}
        </div>
      </div>

      {/* ---- Schedule entries ---- */}
      <div className="detail-section">
        <h2>Schedule Entries ({entries.length})</h2>
        {entries.length === 0 ? (
          <p className="text-muted">
            No schedule entries yet. Create one above. Scheduling is blocked
            until an approved preview exists for the platform.
          </p>
        ) : (
          <div className="media-list">
            {entries.map((entry) => (
              <div key={entry.id} className="source-card">
                <div className="source-header">
                  <span className="job-type">{entry.platform}</span>
                  <span className={`state-badge ${statusClass(entry.status)}`}>
                    {formatStatus(entry.status)}
                  </span>
                </div>
                <div className="media-asset-ref">
                  Local: {new Date(entry.scheduled_local_datetime).toLocaleString()}{" "}
                  ({entry.timezone})
                </div>
                <div className="media-asset-ref">
                  UTC: {entry.scheduled_utc_datetime || "—"}
                </div>
                <div className="media-asset-ref">
                  Version: {entry.version} · Reminder sent:{" "}
                  {entry.reminder_sent ? "Yes" : "No"}
                </div>
                {entry.reminder_scheduled_at && (
                  <div className="media-asset-ref">
                    Reminder at (UTC): {entry.reminder_scheduled_at}
                  </div>
                )}
                {entry.cancellation_reason && (
                  <div className="media-error">
                    Cancellation reason: {entry.cancellation_reason}
                  </div>
                )}

                {/* Actions: reschedule + cancel for scheduled/rescheduled */}
                {(entry.status === "scheduled" || entry.status === "rescheduled") && (
                  <div className="action-buttons">
                    {rescheduleId === entry.id ? (
                      <div className="reschedule-form">
                        <label htmlFor={`res-date-${entry.id}`}>New Date</label>
                        <input
                          id={`res-date-${entry.id}`}
                          type="date"
                          value={resDate}
                          onChange={(e) => setResDate(e.target.value)}
                        />
                        <label htmlFor={`res-time-${entry.id}`}>New Time</label>
                        <input
                          id={`res-time-${entry.id}`}
                          type="time"
                          value={resTime}
                          onChange={(e) => setResTime(e.target.value)}
                        />
                        <label htmlFor={`res-tz-${entry.id}`}>Timezone</label>
                        <select
                          id={`res-tz-${entry.id}`}
                          value={resTimezone}
                          onChange={(e) => setResTimezone(e.target.value)}
                        >
                          {TIMEZONES.map((tz) => (
                            <option key={tz} value={tz}>
                              {tz}
                            </option>
                          ))}
                        </select>
                        <button
                          type="button"
                          className="btn btn-primary btn-sm"
                          onClick={handleReschedule}
                          disabled={reschedulingId === entry.id}
                        >
                          {reschedulingId === entry.id ? "Saving…" : "Save"}
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm"
                          onClick={() => {
                            setRescheduleId(null);
                          }}
                        >
                          Cancel
                        </button>
                      </div>
                    ) : cancelId === entry.id ? (
                      <div className="reschedule-form">
                        <label htmlFor={`cancel-reason-${entry.id}`}>
                          Cancel reason
                        </label>
                        <input
                          id={`cancel-reason-${entry.id}`}
                          type="text"
                          value={cancelReason}
                          onChange={(e) => setCancelReason(e.target.value)}
                          placeholder="Optional"
                        />
                        <button
                          type="button"
                          className="btn btn-danger btn-sm"
                          onClick={handleCancel}
                          disabled={cancellingId === entry.id}
                        >
                          {cancellingId === entry.id ? "Cancelling…" : "Confirm Cancel"}
                        </button>
                        <button
                          type="button"
                          className="btn btn-sm"
                          onClick={() => setCancelId(null)}
                        >
                          Back
                        </button>
                      </div>
                    ) : (
                      <>
                        <button
                          type="button"
                          className="btn btn-sm"
                          onClick={() => handleStartReschedule(entry)}
                        >
                          Reschedule
                        </button>
                        <button
                          type="button"
                          className="btn btn-danger btn-sm"
                          onClick={() => handleStartCancel(entry)}
                        >
                          Cancel
                        </button>
                      </>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ---- Content calendar ---- */}
      <div className="detail-section">
        <h2>Content Calendar ({calendar.length})</h2>
        {calendar.length === 0 ? (
          <p className="text-muted">
            No active scheduled content. Created schedule entries will appear
            here (cancelled entries are excluded by the calendar API).
          </p>
        ) : (
          <div className="calendar-list">
            {calendar.map((entry) => (
              <div key={entry.id} className="calendar-item">
                <span className="job-type">{entry.platform}</span>
                <span className="calendar-datetime">
                  {new Date(entry.scheduled_utc_datetime).toLocaleString()} (UTC)
                </span>
                <span className={`state-badge ${statusClass(entry.status)}`}>
                  {formatStatus(entry.status)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
