import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import {
  getMe,
  login as apiLogin,
  register as apiRegister,
  logout as apiLogout,
  setToken,
  clearToken,
  getToken,
  ApiError,
  type User,
} from "../api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (
    username: string,
    email: string,
    password: string,
  ) => Promise<void>;
  logout: () => Promise<void>;
  error: string | null;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/** Extract a user-friendly error message from backend error envelope. */
function extractErrorMessage(data: unknown, fallback: string): string {
  if (typeof data === "object" && data !== null) {
    const d = data as Record<string, unknown>;
    // Backend error envelope: { success: false, error: { message, details } }
    if ("error" in d && typeof d.error === "object" && d.error !== null) {
      const err = d.error as Record<string, unknown>;
      if (typeof err.message === "string") return err.message;
    }
    // DRF default: { detail: "..." }
    if (typeof d.detail === "string") return d.detail;
    // Field-level errors: { field: ["error"] }
    const msgs: string[] = [];
    for (const [key, val] of Object.entries(d)) {
      if (Array.isArray(val)) msgs.push(`${key}: ${val.join(", ")}`);
    }
    if (msgs.length) return msgs.join("; ");
  }
  return fallback;
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // On mount, try to restore session
  useEffect(() => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    getMe()
      .then((res) => setUser(res.user))
      .catch(() => clearToken())
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (username: string, password: string) => {      try {
        setError(null);
        const res = await apiLogin(username, password);
        setToken(res.token);
        setUser(res.user);
      } catch (err) {
        if (err instanceof ApiError) {
          setError(extractErrorMessage(err.data, "Login failed"));
        } else {
          setError("Login failed");
        }
      throw err;
    }
  }, []);

  const register = useCallback(
    async (username: string, email: string, password: string) => {
      try {
        setError(null);
        const res = await apiRegister(username, email, password);
        setToken(res.token);
        setUser(res.user);
      } catch (err) {
        if (err instanceof ApiError) {
          setError(extractErrorMessage(err.data, "Registration failed"));
        } else {
          setError("Registration failed");
        }
        throw err;
      }
    },
    [],
  );

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } catch {
      // Ignore logout errors — clear local state regardless
    } finally {
      clearToken();
      setUser(null);
    }
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return (
    <AuthContext.Provider
      value={{ user, loading, login, register, logout, error, clearError }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}
