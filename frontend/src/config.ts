// In development, Vite's proxy forwards /api to the backend.
// In production, set VITE_API_BASE_URL to the full backend URL.
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "";
