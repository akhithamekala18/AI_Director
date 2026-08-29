import { api } from "./client";

// ---------------------------------------------------------------------------
// Types matching the backend serializers
// ---------------------------------------------------------------------------

export interface Project {
  id: number;
  topic: string;
  platform_target: string;
  format: string;
  lifecycle_state: string;
  next_required_action: string;
  is_template: boolean;
  owner_username: string;
  team_name: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectListResponse {
  projects: Project[];
}

export interface ProjectDetailResponse {
  project: Project;
}

// ---------------------------------------------------------------------------
// Projects API
// ---------------------------------------------------------------------------

export async function listProjects(
  includeArchived = false,
): Promise<ProjectListResponse> {
  const qs = includeArchived ? "?archived=1" : "";
  return api.get<ProjectListResponse>(`/projects/${qs}`);
}

export async function getProject(
  pk: number,
): Promise<ProjectDetailResponse> {
  return api.get<ProjectDetailResponse>(`/projects/${pk}/`);
}

export async function createProject(data: {
  topic: string;
  platform_target?: string;
  format?: string;
  is_template?: boolean;
}): Promise<ProjectDetailResponse> {
  return api.post<ProjectDetailResponse>("/projects/", data);
}

export async function patchProject(
  pk: number,
  data: { topic?: string; platform_target?: string; format?: string },
): Promise<ProjectDetailResponse> {
  return api.patch<ProjectDetailResponse>(`/projects/${pk}/`, data);
}

export async function archiveProject(
  pk: number,
): Promise<ProjectDetailResponse> {
  return api.post<ProjectDetailResponse>(`/projects/${pk}/archive/`);
}

export async function duplicateProject(
  pk: number,
): Promise<ProjectDetailResponse> {
  return api.post<ProjectDetailResponse>(`/projects/${pk}/duplicate/`);
}

export async function transitionProject(
  pk: number,
  target_state: string,
): Promise<ProjectDetailResponse> {
  return api.post<ProjectDetailResponse>(`/projects/${pk}/transition/`, {
    target_state,
  });
}
