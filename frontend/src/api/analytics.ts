import { api } from "./client";

// ---------------------------------------------------------------------------
// Analytics (backend: apps.analytics). Read-only published-performance
// tracking. The backend enforces the published-only boundary invariant and
// team isolation via memberships. All query results aggregate over the user's
// teams; an optional team_id narrows to a single team the user belongs to.
// ---------------------------------------------------------------------------

export interface AnalyticsSummary {
  total_views: number | null;
  total_likes: number | null;
  total_comments: number | null;
  total_shares: number | null;
  avg_engagement: number | null;
  entry_count: number;
}

export interface PlatformAnalytics {
  platform: string;
  total_views: number;
  total_likes: number;
  total_comments: number;
  total_shares: number;
  avg_engagement: number;
  entry_count: number;
}

export interface TopicAnalytics {
  topic: string;
  total_views: number;
  total_likes: number;
  avg_engagement: number;
  entry_count: number;
}

export interface SummaryResponse {
  summary: AnalyticsSummary;
}

export interface ByPlatformResponse {
  platforms: PlatformAnalytics[];
}

export interface ByTopicResponse {
  topics: TopicAnalytics[];
}

// ---------------------------------------------------------------------------
// Analytics API
// ---------------------------------------------------------------------------

export async function getAnalyticsSummary(
  teamId?: number,
): Promise<SummaryResponse> {
  const q = teamId ? `?team_id=${teamId}` : "";
  return api.get<SummaryResponse>(`/analytics/summary/${q}`);
}

export async function getAnalyticsByPlatform(
  teamId?: number,
): Promise<ByPlatformResponse> {
  const q = teamId ? `?team_id=${teamId}` : "";
  return api.get<ByPlatformResponse>(`/analytics/by-platform/${q}`);
}

export async function getAnalyticsByTopic(
  teamId?: number,
): Promise<ByTopicResponse> {
  const q = teamId ? `?team_id=${teamId}` : "";
  return api.get<ByTopicResponse>(`/analytics/by-topic/${q}`);
}
