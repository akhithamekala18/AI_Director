import { api } from "./client";

// ---------------------------------------------------------------------------
// Preview asset (backend: apps.preview.models.PreviewAsset)
// ---------------------------------------------------------------------------

export interface PreviewAsset {
  id: number;
  project: number;
  video: number;
  platform_target: string;
  aspect_ratio: string;
  resolution_width: number;
  resolution_height: number;
  status: string;
  asset_ref: string;
  provider: string;
  duration_seconds: number;
  scene_count: number;
  version: number;
  approval_state: string;
  approved_by: string | null;
  approved_at: string | null;
  rejection_reason: string;
  error_message: string;
  created_at: string;
  updated_at: string;
}

export interface PreviewListResponse {
  previews: PreviewAsset[];
}

export interface PreviewDetailResponse {
  preview: PreviewAsset;
}

// ---------------------------------------------------------------------------
// Preview API
// ---------------------------------------------------------------------------

export async function listPreviews(
  projectId: number,
): Promise<PreviewListResponse> {
  return api.get<PreviewListResponse>(`/projects/${projectId}/preview/`);
}

export async function getPreview(
  projectId: number,
  previewId: number,
): Promise<PreviewDetailResponse> {
  return api.get<PreviewDetailResponse>(
    `/projects/${projectId}/preview/${previewId}/`,
  );
}

export async function generatePreview(
  projectId: number,
  platformTarget = "YouTube",
): Promise<PreviewDetailResponse> {
  return api.post<PreviewDetailResponse>(`/projects/${projectId}/preview/generate/`, {
    platform_target: platformTarget,
  });
}

export async function approvePreview(
  projectId: number,
  previewId: number,
): Promise<PreviewDetailResponse> {
  return api.post<PreviewDetailResponse>(
    `/projects/${projectId}/preview/${previewId}/approve/`,
    {},
  );
}

export async function rejectPreview(
  projectId: number,
  previewId: number,
  reason: string,
): Promise<PreviewDetailResponse> {
  return api.post<PreviewDetailResponse>(
    `/projects/${projectId}/preview/${previewId}/reject/`,
    { reason },
  );
}
