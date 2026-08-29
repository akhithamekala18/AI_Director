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
