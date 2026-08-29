import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function Register() {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const { register, error, clearError } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLocalError(null);

    if (password !== confirm) {
      setLocalError("Passwords do not match");
      return;
    }
    if (!username.trim()) return;
    if (!password) return;

    setSubmitting(true);
    try {
      await register(username.trim(), email.trim(), password);
      navigate("/");
    } catch {
      // error is set by context
    } finally {
      setSubmitting(false);
    }
  };

  const displayError = localError || error;

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>AI Director</h1>
        <h2>Create Account</h2>

        {displayError && (
          <div className="error-banner" role="alert">
            {displayError}
            <button
              type="button"
              onClick={() => {
                setLocalError(null);
                clearError();
              }}
              aria-label="Dismiss"
            >
              ×
            </button>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <label htmlFor="reg-username">Username</label>
          <input
            id="reg-username"
            type="text"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            disabled={submitting}
          />

          <label htmlFor="reg-email">Email (optional)</label>
          <input
            id="reg-email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={submitting}
          />

          <label htmlFor="reg-password">Password</label>
          <input
            id="reg-password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={submitting}
          />

          <label htmlFor="reg-confirm">Confirm Password</label>
          <input
            id="reg-confirm"
            type="password"
            autoComplete="new-password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            required
            disabled={submitting}
          />

          <button type="submit" disabled={submitting}>
            {submitting ? "Creating account…" : "Create Account"}
          </button>
        </form>

        <p className="auth-alt">
          Already have an account? <Link to="/login">Sign In</Link>
        </p>
      </div>
    </div>
  );
}
