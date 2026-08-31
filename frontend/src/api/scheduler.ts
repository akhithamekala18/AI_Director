import { api } from "./client";

// ---------------------------------------------------------------------------
// Schedule entry (backend: apps.scheduler.models.ScheduleEntry)
//
// Status values (do not invent): scheduled | rescheduled | cancelled |
// published | failed
// ---------------------------------------------------------------------------

export interface ScheduleEntry {
  id: number;
  project: number;
  platform: string;
  scheduled_local_datetime: string;
  timezone: string;
  scheduled_utc_datetime: string;
  status: string;
  best_time_suggestion: {
    best_days?: string[];
    best_hours_utc?: number[];
    reasoning?: string;
  };
  reminder_sent: boolean;
  reminder_scheduled_at: string | null;
  cancelled_at: string | null;
  cancellation_reason: string;
  published_at: string | null;
  version: number;
  previous_scheduled_utc: string | null;
  created_at: string;
  updated_at: string;
}

export interface ScheduleListResponse {
  entries: ScheduleEntry[];
}

export interface ScheduleCalendarResponse {
  calendar: ScheduleEntry[];
}

export interface ScheduleDetailResponse {
  entry: ScheduleEntry;
}

export interface BestTimeSuggestion {
  best_days: string[];
  best_hours_utc: number[];
  reasoning: string;
}

export interface BestTimeResponse {
  suggestion: BestTimeSuggestion;
}

// ---------------------------------------------------------------------------
// Scheduler API
// ---------------------------------------------------------------------------

export async function listSchedules(
  projectId: number,
): Promise<ScheduleListResponse> {
  return api.get<ScheduleListResponse>(`/projects/${projectId}/schedule/`);
}

export async function getSchedule(
  projectId: number,
  entryId: number,
): Promise<ScheduleDetailResponse> {
  return api.get<ScheduleDetailResponse>(
    `/projects/${projectId}/schedule/${entryId}/`,
  );
}

export async function createSchedule(
  projectId: number,
  payload: {
    platform: string;
    scheduled_local_datetime: string;
    timezone?: string;
  },
): Promise<ScheduleDetailResponse> {
  return api.post<ScheduleDetailResponse>(
    `/projects/${projectId}/schedule/create/`,
    {
      platform: payload.platform,
      scheduled_local_datetime: payload.scheduled_local_datetime,
      timezone: payload.timezone ?? "UTC",
    },
  );
}

export async function rescheduleEntry(
  projectId: number,
  entryId: number,
  payload: { scheduled_local_datetime: string; timezone?: string },
): Promise<ScheduleDetailResponse> {
  return api.post<ScheduleDetailResponse>(
    `/projects/${projectId}/schedule/${entryId}/reschedule/`,
    {
      scheduled_local_datetime: payload.scheduled_local_datetime,
      timezone: payload.timezone ?? undefined,
    },
  );
}

export async function cancelEntry(
  projectId: number,
  entryId: number,
  reason = "",
): Promise<ScheduleDetailResponse> {
  return api.post<ScheduleDetailResponse>(
    `/projects/${projectId}/schedule/${entryId}/cancel/`,
    { reason },
  );
}

export async function getCalendar(
  projectId: number,
): Promise<ScheduleCalendarResponse> {
  return api.get<ScheduleCalendarResponse>(
    `/projects/${projectId}/schedule/calendar/`,
  );
}

export async function getBestTime(
  projectId: number,
  platform: string,
): Promise<BestTimeResponse> {
  return api.get<BestTimeResponse>(
    `/projects/${projectId}/schedule/best-time/?platform=${encodeURIComponent(platform)}`,
  );
}
