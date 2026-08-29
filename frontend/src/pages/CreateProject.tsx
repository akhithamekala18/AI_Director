import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { createProject } from "../api/projects";
import { ApiError } from "../api/client";

export function CreateProject() {
  const [topic, setTopic] = useState("");
  const [platformTarget, setPlatformTarget] = useState("");
  const [format, setFormat] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await createProject({
        topic: topic.trim(),
        platform_target: platformTarget || undefined,
        format: format || undefined,
      });
      navigate(`/projects/${res.project.id}`);
    } catch (err) {
      if (err instanceof ApiError) {
        const data = err.data as Record<string, unknown>;
        const msg = typeof data.detail === "string" ? data.detail : "Failed to create project";
        setError(msg);
      } else {
        setError("Failed to create project");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page">
      <h1>Create Project</h1>

      {error && <div className="page-error">{error}</div>}

      <form onSubmit={handleSubmit} className="form-card">
        <label htmlFor="topic">Topic *</label>
        <input
          id="topic"
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="e.g. Climate change solutions"
          required
          disabled={submitting}
        />

        <label htmlFor="platform">Platform Target</label>
        <select
          id="platform"
          value={platformTarget}
          onChange={(e) => setPlatformTarget(e.target.value)}
          disabled={submitting}
        >
          <option value="">— Select —</option>
          <option value="YouTube">YouTube</option>
          <option value="TikTok">TikTok</option>
          <option value="Instagram Reels">Instagram Reels</option>
          <option value="Facebook">Facebook</option>
          <option value="LinkedIn">LinkedIn</option>
          <option value="X (Twitter)">X (Twitter)</option>
          <option value="Other">Other</option>
        </select>

        <label htmlFor="format">Format</label>
        <select
          id="format"
          value={format}
          onChange={(e) => setFormat(e.target.value)}
          disabled={submitting}
        >
          <option value="">— Select —</option>
          <option value="Short (15-60s)">Short (15-60s)</option>
          <option value="Medium (1-3min)">Medium (1-3min)</option>
          <option value="Long (3-10min)">Long (3-10min)</option>
        </select>

        <button type="submit" disabled={submitting} className="btn btn-primary">
          {submitting ? "Creating…" : "Create Project"}
        </button>
      </form>
    </div>
  );
}
