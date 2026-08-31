import { api } from "./client";

// ---------------------------------------------------------------------------
// Thumbnail asset (backend: apps.thumbnail.models.ThumbnailAsset)
// ---------------------------------------------------------------------------

export interface ThumbnailAsset {
  id: number;
  project: number;
  team: number;
  scene_builder: number | null;
  platform_target: string;
  width: number;
  height: number;
  status: string;
  asset_ref: string;
  provider: string;
  provider_metadata: Record<string, unknown>;
  title_text: string;
  variations: string[];
  version: number;
  error_message: string;
  created_at: string;
  updated_at: string;
}

export interface ThumbnailListResponse {
  thumbnails: ThumbnailAsset[];
}

export interface ThumbnailDetailResponse {
  thumbnail: ThumbnailAsset;
}

// ---------------------------------------------------------------------------
// Thumbnail API
// ---------------------------------------------------------------------------

export async function listThumbnails(
  projectId: number,
): Promise<ThumbnailListResponse> {
  return api.get<ThumbnailListResponse>(`/projects/${projectId}/thumbnail/`);
}

export async function getThumbnail(
  projectId: number,
  thumbnailId: number,
): Promise<ThumbnailDetailResponse> {
  return api.get<ThumbnailDetailResponse>(
    `/projects/${projectId}/thumbnail/${thumbnailId}/`,
  );
}

export async function generateThumbnail(
  projectId: number,
  platformTarget = "YouTube",
  titleText = "",
): Promise<ThumbnailDetailResponse> {
  return api.post<ThumbnailDetailResponse>(
    `/projects/${projectId}/thumbnail/generate/`,
    { platform_target: platformTarget, title_text: titleText },
  );
}
