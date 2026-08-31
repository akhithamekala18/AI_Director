import { api } from "./client";

// ---------------------------------------------------------------------------
// Scene entry (within a SceneBuilder's scenes JSON array)
// ---------------------------------------------------------------------------

export interface SceneEntry {
  id: string;
  order: number;
  heading: string;
  narration: string;
  visual_direction: string;
  characters: string[];
  pacing: string;
  transition: string;
  duration_seconds: number;
  metadata: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// SceneBuilder (project's assembled scene package, Gate 4)
// ---------------------------------------------------------------------------

export interface SceneBuilder {
  id: number;
  project: number;
  team: number;
  script: number | null;
  character_set: number | null;
  scenes: SceneEntry[];
  gate_state: string;
  version: number;
  rejection_reason: string | null;
  approval_actor_username: string | null;
  approval_at: string | null;
  scene_count: number;
  created_at: string;
  updated_at: string;
}

export interface SceneDetailResponse {
  scene: SceneBuilder;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function getScene(projectId: number): Promise<SceneDetailResponse> {
  return api.get<SceneDetailResponse>(`/projects/${projectId}/scene/`);
}

export async function buildScenes(projectId: number): Promise<SceneDetailResponse> {
  return api.post<SceneDetailResponse>(`/projects/${projectId}/scene/build/`);
}

export async function approveScene(projectId: number): Promise<SceneDetailResponse> {
  return api.post<SceneDetailResponse>(`/projects/${projectId}/scene/approve/`);
}

export async function requestSceneChanges(
  projectId: number,
  reason: string,
): Promise<SceneDetailResponse> {
  return api.post<SceneDetailResponse>(
    `/projects/${projectId}/scene/request-changes/`,
    { reason },
  );
}
