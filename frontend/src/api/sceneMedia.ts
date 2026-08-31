import { api } from "./client";

// ---------------------------------------------------------------------------
// Scene Media asset
// ---------------------------------------------------------------------------

export interface SceneMediaAsset {
  id: number;
  project: number;
  team: number;
  scene_builder: number | null;
  scene_id: string;
  scene_order: number;
  media_type: string;
  status: string;
  asset_ref: string;
  provider: string;
  provider_metadata: Record<string, unknown>;
  direction: string;
  narration: string;
  characters: unknown[];
  duration_seconds: number;
  pacing: string;
  transition: string;
  voice: Record<string, unknown>;
  music: Record<string, unknown>;
  caption: Record<string, unknown>;
  error_message: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface SceneMediaListResponse {
  media: SceneMediaAsset[];
}

export interface SceneMediaDetailResponse {
  media: SceneMediaAsset;
}

// ---------------------------------------------------------------------------
// Regeneration request
// ---------------------------------------------------------------------------

export interface RegenerationRequest {
  id: number;
  project: number;
  scene_id: string | null;
  media_types: string[];
  full: boolean;
  status: string;
  error_message: string;
  created_at: string;
  updated_at: string;
}

export interface RegenerationListResponse {
  regeneration: RegenerationRequest[];
}

// ---------------------------------------------------------------------------
// Job (for async generation/regeneration)
// ---------------------------------------------------------------------------

export interface AsyncJob {
  id: number;
  job_type: string;
  status: string;
  progress: number;
  result: Record<string, unknown> | null;
  error_message: string;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// API functions — Scene Media
// ---------------------------------------------------------------------------

export async function listSceneMedia(projectId: number): Promise<SceneMediaListResponse> {
  return api.get<SceneMediaListResponse>(`/projects/${projectId}/scene-media/`);
}

export async function getSceneMedia(
  projectId: number,
  mediaId: number,
): Promise<SceneMediaDetailResponse> {
  return api.get<SceneMediaDetailResponse>(`/projects/${projectId}/scene-media/${mediaId}/`);
}

export async function generateSceneMedia(
  projectId: number,
  mediaTypes?: string[],
): Promise<{ job: AsyncJob }> {
  return api.post<{ job: AsyncJob }>(`/projects/${projectId}/scene-media/generate/`, {
    media_types: mediaTypes,
  });
}

// ---------------------------------------------------------------------------
// API functions — Regeneration
// ---------------------------------------------------------------------------

export async function requestRegeneration(
  projectId: number,
  options: { scene_id?: string; media_types?: string[]; full?: boolean },
): Promise<{ job: AsyncJob; regeneration: RegenerationRequest | null }> {
  return api.post<{ job: AsyncJob; regeneration: RegenerationRequest | null }>(
    `/projects/${projectId}/regenerate/regenerate/`,
    options,
  );
}

export async function listRegenerations(
  projectId: number,
): Promise<RegenerationListResponse> {
  return api.get<RegenerationListResponse>(`/projects/${projectId}/regenerate/`);
}
