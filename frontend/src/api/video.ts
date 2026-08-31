import { api } from "./client";

// ---------------------------------------------------------------------------
// Video asset (backend: apps.video.models.VideoAsset)
// ---------------------------------------------------------------------------

export interface VideoAsset {
  id: number;
  project: number;
  team: number;
  scene_builder: number | null;
  platform_target: string;
  aspect_ratio: string;
  resolution_width: number;
  resolution_height: number;
  status: string;
  asset_ref: string;
  provider: string;
  provider_metadata: Record<string, unknown>;
  duration_seconds: number;
  scene_count: number;
  version: number;
  error_message: string;
  retry_count: number;
  max_retries: number;
  created_at: string;
  updated_at: string;
}

export interface VideoListResponse {
  videos: VideoAsset[];
}

export interface VideoDetailResponse {
  video: VideoAsset;
}

// ---------------------------------------------------------------------------
// Video API
// ---------------------------------------------------------------------------

export async function listVideos(projectId: number): Promise<VideoListResponse> {
  return api.get<VideoListResponse>(`/projects/${projectId}/video/`);
}

export async function getVideo(
  projectId: number,
  videoId: number,
): Promise<VideoDetailResponse> {
  return api.get<VideoDetailResponse>(`/projects/${projectId}/video/${videoId}/`);
}

export async function generateVideo(
  projectId: number,
  platformTarget = "YouTube",
): Promise<VideoDetailResponse> {
  return api.post<VideoDetailResponse>(`/projects/${projectId}/video/generate/`, {
    platform_target: platformTarget,
  });
}
