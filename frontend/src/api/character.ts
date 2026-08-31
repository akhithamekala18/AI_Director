import { api } from "./client";

// ---------------------------------------------------------------------------
// Character set (detected characters for a project, Gate 3)
// ---------------------------------------------------------------------------

export interface CharacterEntry {
  id: string;
  name: string;
  age: string;
  gender: string;
  appearance: Record<string, unknown>;
  clothing: Record<string, unknown>;
  accessories: unknown[];
  style: Record<string, unknown>;
}

export interface CharacterSet {
  id: number;
  project: number;
  team: number;
  script: number | null;
  characters: CharacterEntry[];
  gate_state: string;
  version: number;
  rejection_reason: string | null;
  approval_actor_username: string | null;
  approval_at: string | null;
  character_count: number;
  created_at: string;
  updated_at: string;
}

export interface CharacterDetailResponse {
  character: CharacterSet;
}

// ---------------------------------------------------------------------------
// Library (persistent, reusable characters)
// ---------------------------------------------------------------------------

export interface LibraryCharacter {
  id: number;
  character_id: string;
  name: string;
  age: string;
  gender: string;
  appearance: Record<string, unknown>;
  clothing: Record<string, unknown>;
  accessories: unknown[];
  style: Record<string, unknown>;
  version: number;
  origin_project: number | null;
  created_at: string;
  updated_at: string;
}

export interface CharacterLibraryResponse {
  library: LibraryCharacter[];
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function getCharacter(projectId: number): Promise<CharacterDetailResponse> {
  return api.get<CharacterDetailResponse>(`/projects/${projectId}/character/`);
}

export async function generateCharacter(projectId: number): Promise<CharacterDetailResponse> {
  return api.post<CharacterDetailResponse>(`/projects/${projectId}/character/generate/`);
}

export async function approveCharacter(projectId: number): Promise<CharacterDetailResponse> {
  return api.post<CharacterDetailResponse>(`/projects/${projectId}/character/approve/`);
}

export async function requestCharacterChanges(
  projectId: number,
  reason: string,
): Promise<CharacterDetailResponse> {
  return api.post<CharacterDetailResponse>(
    `/projects/${projectId}/character/request-changes/`,
    { reason },
  );
}

export async function getCharacterLibrary(projectId: number): Promise<CharacterLibraryResponse> {
  return api.get<CharacterLibraryResponse>(`/projects/${projectId}/character/library/`);
}

export async function reuseCharacter(
  projectId: number,
  libraryEntryId: number,
): Promise<CharacterDetailResponse> {
  return api.post<CharacterDetailResponse>(`/projects/${projectId}/character/reuse/`, {
    library_entry_id: libraryEntryId,
  });
}
