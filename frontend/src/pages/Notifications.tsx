import { useEffect, useState, useCallback } from "react";
import {
  listNotifications,
  markNotificationRead,
  type Notification,
} from "../api/notifications";
import { ApiError } from "../api/client";

// ---------------------------------------------------------------------------
// Complete notifications center (Task 48). Renders every backend notification
// type (status, approval_request, reminder, publish_outcome, publish_failure,
// team_assignment) with a friendly label, read/unread state, and mark-read.
// ---------------------------------------------------------------------------

const TYPE_LABELS: Record<string, string> = {
  status: "Status",
  approval_request: "Approval Request",
  reminder: "Reminder",
  publish_outcome: "Publish Outcome",
  publish_failure: "Publish Failure",
  team_assignment: "Team Assignment",
};

function typeLabel(type: string): string {
  return TYPE_LABELS[type] ?? type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function typeClass(type: string): string {
  if (type === "approval_request") return "notif-approval";
  if (type === "publish_failure") return "notif-failure";
  if (type === "publish_outcome") return "notif-success";
  if (type === "reminder") return "notif-reminder";
  if (type === "team_assignment") return "notif-team";
  return "notif-status";
}

export function Notifications() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listNotifications();
      setNotifications(res.notifications);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? "Failed to load notifications"
          : "Failed to load notifications",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleMarkRead = async (pk: number) => {
    setBusyId(pk);
    setError(null);
    try {
      const res = await markNotificationRead(pk);
      setNotifications((prev) =>
        prev.map((n) => (n.id === pk ? { ...n, ...res.notification } : n)),
      );
    } catch (err) {
      setError(
        err instanceof ApiError
          ? "Failed to mark notification as read"
          : "Failed to mark notification as read",
      );
    } finally {
      setBusyId(null);
    }
  };

  if (loading) return <div className="page-loading">Loading notifications…</div>;

  const unread = notifications.filter((n) => !n.read).length;
  const read = notifications.filter((n) => n.read).length;

  return (
    <div className="page">
      <h1>Notifications</h1>
      <p className="text-muted">
        {unread} unread · {read} read
      </p>

      {error && <div className="page-error">{error}</div>}

      {notifications.length === 0 ? (
        <div className="empty-state">
          <p>No notifications yet.</p>
        </div>
      ) : (
        <ul className="notification-list full">
          {notifications.map((n) => (
            <li
              key={n.id}
              className={`notification-item ${n.read ? "read" : "unread"} ${typeClass(n.type)}`}
            >
              <div className="notification-content">
                <div className="notification-header">
                  <span className="notification-type">{typeLabel(n.type)}</span>
                  <strong>{n.title}</strong>
                  <span className="notification-date">
                    {new Date(n.created_at).toLocaleString()}
                  </span>
                </div>
                {n.message && <p>{n.message}</p>}
                {n.artifact_type && n.artifact_id && (
                  <span className="notification-artifact">
                    {n.artifact_type} #{n.artifact_id}
                  </span>
                )}
              </div>
              {!n.read && (
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick={() => handleMarkRead(n.id)}
                  disabled={busyId === n.id}
                >
                  {busyId === n.id ? "Saving…" : "Mark read"}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
