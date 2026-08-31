import { api } from "./client";

// ---------------------------------------------------------------------------
// Async Job
// ---------------------------------------------------------------------------

export interface AsyncJob {
  id: number;
  team: number;
  team_name: string;
  project: number;
  project_topic: string;
  owner: number;
  owner_username: string;
  job_type: string;
  status: string;
  progress: number;
  result: Record<string, unknown> | null;
  error_message: string;
  retry_count: number;
  max_retries: number;
  cost: string;
  cost_currency: string;
  provider: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface JobListResponse {
  jobs: AsyncJob[];
}

export interface JobDetailResponse {
  job: AsyncJob;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function listJobs(projectId?: number): Promise<JobListResponse> {
  const path = projectId ? `/jobs/?project=${projectId}` : "/jobs/";
  return api.get<JobListResponse>(path);
}

export async function getJob(jobId: number): Promise<JobDetailResponse> {
  return api.get<JobDetailResponse>(`/jobs/${jobId}/`);
}

export async function cancelJob(jobId: number): Promise<JobDetailResponse> {
  return api.post<JobDetailResponse>(`/jobs/${jobId}/cancel/`);
}

export async function retryJob(jobId: number): Promise<JobDetailResponse> {
  return api.post<JobDetailResponse>(`/jobs/${jobId}/retry/`);
}
