import { api } from "./client";

export interface ResearchSource {
  id: number;
  url: string;
  title: string;
  snippet: string;
  credibility_score: number;
  accessed_at: string;
  created_at: string;
}

export interface ResearchGap {
  id: number;
  gap_type: string;
  description: string;
  source_a: number | null;
  source_b: number | null;
  status: string;
  created_at: string;
}

export interface Research {
  id: number;
  project: number;
  team: number;
  summary: string;
  gate_state: string;
  version: number;
  rejection_reason: string | null;
  approval_actor_username: string | null;
  approval_at: string | null;
  source_count: number;
  gap_count: number;
  created_at: string;
  updated_at: string;
}

export interface ResearchDetailResponse {
  research: Research;
}

export interface ResearchSourcesResponse {
  sources: ResearchSource[];
}

export interface ResearchGapsResponse {
  gaps: ResearchGap[];
}

export async function getResearch(projectId: number): Promise<ResearchDetailResponse> {
  return api.get<ResearchDetailResponse>(`/projects/${projectId}/research/`);
}

export async function generateResearch(projectId: number): Promise<ResearchDetailResponse> {
  return api.post<ResearchDetailResponse>(`/projects/${projectId}/research/generate/`);
}

export async function getResearchSources(projectId: number): Promise<ResearchSourcesResponse> {
  return api.get<ResearchSourcesResponse>(`/projects/${projectId}/research/sources/`);
}

export async function getResearchGaps(projectId: number): Promise<ResearchGapsResponse> {
  return api.get<ResearchGapsResponse>(`/projects/${projectId}/research/gaps/`);
}

export async function approveResearch(projectId: number): Promise<ResearchDetailResponse> {
  return api.post<ResearchDetailResponse>(`/projects/${projectId}/research/approve/`);
}

export async function requestResearchChanges(projectId: number, reason: string): Promise<ResearchDetailResponse> {
  return api.post<ResearchDetailResponse>(`/projects/${projectId}/research/request-changes/`, { reason });
}
