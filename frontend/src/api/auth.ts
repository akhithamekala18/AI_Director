import { api } from "./client";

// ---------------------------------------------------------------------------
// Types matching the backend serializers
// ---------------------------------------------------------------------------

export interface User {
  id: number;
  username: string;
  email: string;
  role: string;
  mfa_enabled: boolean;
  date_joined: string;
}

export interface AuthResponse {
  token: string;
  user: User;
}

export interface MeResponse {
  user: User;
}

// ---------------------------------------------------------------------------
// Auth API
// ---------------------------------------------------------------------------

export async function register(
  username: string,
  email: string,
  password: string,
): Promise<AuthResponse> {
  return api.post<AuthResponse>("/accounts/register/", {
    username,
    email: email || undefined,
    password,
  });
}

export async function login(
  username: string,
  password: string,
): Promise<AuthResponse> {
  return api.post<AuthResponse>("/accounts/login/", { username, password });
}

export async function logout(): Promise<{ message: string }> {
  return api.post<{ message: string }>("/accounts/logout/");
}

export async function getMe(): Promise<MeResponse> {
  return api.get<MeResponse>("/accounts/me/");
}
