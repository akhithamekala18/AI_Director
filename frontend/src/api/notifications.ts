import { api } from "./client";

// ---------------------------------------------------------------------------
// Types matching the backend serializers
// ---------------------------------------------------------------------------

export interface Notification {
  id: number;
  type: string;
  title: string;
  message: string;
  artifact_type: string;
  artifact_id: number | null;
  read: boolean;
  created_at: string;
}

export interface NotificationListResponse {
  notifications: Notification[];
}

// ---------------------------------------------------------------------------
// Notifications API
// ---------------------------------------------------------------------------

export async function listNotifications(): Promise<NotificationListResponse> {
  return api.get<NotificationListResponse>("/notifications/");
}

export async function markNotificationRead(
  pk: number,
): Promise<{ notification: Notification }> {
  return api.post<{ notification: Notification }>(
    `/notifications/${pk}/read/`,
  );
}
