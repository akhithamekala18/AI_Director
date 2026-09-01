import { api } from "./client";

// ---------------------------------------------------------------------------
// Types matching the backend serializers
// ---------------------------------------------------------------------------

export interface UserSettings {
  id: number;
  email_notifications_enabled: boolean;
  in_app_notifications_enabled: boolean;
  default_voice_style: string;
  default_caption_style: string;
  default_music_mood: string;
  created_at: string;
  updated_at: string;
}

export interface StoredCredential {
  id: number;
  provider: string;
  label: string;
  revoked: boolean;
  created_at: string;
}

export interface SettingsResponse {
  settings: UserSettings;
}

export interface CredentialListResponse {
  credentials: StoredCredential[];
}

export interface CredentialDetailResponse {
  credential: StoredCredential;
}

export interface PublishingPreferences {
  id: number;
  auto_approve_enabled: boolean;
  default_posting_time: string | null;
  cross_post_by_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface NotificationPreferences {
  id: number;
  approval_requests: boolean;
  reminders: boolean;
  publish_outcomes: boolean;
  publish_failures: boolean;
  team_assignments: boolean;
  created_at: string;
  updated_at: string;
}

export interface PublishingPreferencesResponse {
  publishing_preferences: PublishingPreferences;
}

export interface NotificationPreferencesResponse {
  notification_preferences: NotificationPreferences;
}

// ---------------------------------------------------------------------------
// Settings API
// ---------------------------------------------------------------------------

export async function getSettings(): Promise<SettingsResponse> {
  return api.get<SettingsResponse>("/settings/");
}

export async function updateSettings(
  data: Partial<Omit<UserSettings, "id" | "created_at" | "updated_at">>,
): Promise<SettingsResponse> {
  return api.patch<SettingsResponse>("/settings/", data);
}

export async function listCredentials(): Promise<CredentialListResponse> {
  return api.get<CredentialListResponse>("/settings/credentials/");
}

export async function createCredential(data: {
  provider: string;
  label: string;
  secret: string;
}): Promise<CredentialDetailResponse> {
  return api.post<CredentialDetailResponse>(
    "/settings/credentials/create/",
    data,
  );
}

export async function revokeCredential(
  pk: number,
): Promise<CredentialDetailResponse> {
  return api.post<CredentialDetailResponse>(
    `/settings/credentials/${pk}/revoke/`,
  );
}

export async function getPublishingPreferences(): Promise<PublishingPreferencesResponse> {
  return api.get<PublishingPreferencesResponse>("/settings/publishing-preferences/");
}

export async function updatePublishingPreferences(
  data: Partial<Omit<PublishingPreferences, "id" | "created_at" | "updated_at">>,
): Promise<PublishingPreferencesResponse> {
  return api.patch<PublishingPreferencesResponse>(
    "/settings/publishing-preferences/",
    data,
  );
}

export async function getNotificationPreferences(): Promise<NotificationPreferencesResponse> {
  return api.get<NotificationPreferencesResponse>("/settings/notification-preferences/");
}

export async function updateNotificationPreferences(
  data: Partial<Omit<NotificationPreferences, "id" | "created_at" | "updated_at">>,
): Promise<NotificationPreferencesResponse> {
  return api.patch<NotificationPreferencesResponse>(
    "/settings/notification-preferences/",
    data,
  );
}
