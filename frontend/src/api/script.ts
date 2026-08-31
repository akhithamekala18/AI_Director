import { api } from "./client";

export interface Script {
  id: number;
  project: number;
  team: number;
  research: number | null;
  title: string;
  outline: string;
  script: string;
  narration: string;
  scenes: string[];
  captions: string[];
  hashtags: string[];
  gate_state: string;
  version: number;
  rejection_reason: string | null;
  approval_actor_username: string | null;
  approval_at: string | null;
  scene_count: number;
  created_at: string;
  updated_at: string;
}

export interface ScriptDetailResponse {
  script: Script;
}

export async function getScript(projectId: number): Promise<ScriptDetailResponse> {
  return api.get<ScriptDetailResponse>(`/projects/${projectId}/script/`);
}

export async function generateScript(projectId: number): Promise<ScriptDetailResponse> {
  return api.post<ScriptDetailResponse>(`/projects/${projectId}/script/generate/`);
}

export async function approveScript(projectId: number): Promise<ScriptDetailResponse> {
  return api.post<ScriptDetailResponse>(`/projects/${projectId}/script/approve/`);
}

export async function requestScriptChanges(
  projectId: number,
  reason: string,
): Promise<ScriptDetailResponse> {
  return api.post<ScriptDetailResponse>(
    `/projects/${projectId}/script/request-changes/`,
    { reason },
  );
}
