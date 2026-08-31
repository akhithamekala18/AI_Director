import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  listVideos,
  generateVideo,
  type VideoAsset,
} from "../api/video";
import {
  listThumbnails,
  generateThumbnail,
  type ThumbnailAsset,
} from "../api/thumbnail";
import { ApiError } from "../api/client";

// ---------------------------------------------------------------------------
// Status presentation helpers (backend states, do not invent)
// VideoAsset.status: pending | generating | ready | failed
// ThumbnailAsset.status: pending | generating | ready | failed
// ---------------------------------------------------------------------------

function statusClass(status: string): string {
  if (status === "ready") return "state-approved";
  if (status === "failed") return "state-revision";
  if (status === "generating" || status === "pending") return "state-generating";
  return "state-review";
}

function formatStatus(status: string): string {
  return status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function durationLabel(seconds: number): string {
  if (!seconds) return "—";
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s}s`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function VideoStatus() {
  const { id } = useParams<{ id: string }>();
  const projectId = Number(id);

  const [videos, setVideos] = useState<VideoAsset[]>([]);
  const [thumbnails, setThumbnails] = useState<ThumbnailAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [generating, setGenerating] = useState(false);
  const [thumbGenerating, setThumbGenerating] = useState(false);
  const [platform, setPlatform] = useState("YouTube");

  // ---- Data loading ----

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [vRes, tRes] = await Promise.all([
        listVideos(projectId),
        listThumbnails(projectId),
      ]);
      setVideos(vRes.videos);
      setThumbnails(tRes.thumbnails);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setVideos([]);
        setThumbnails([]);
      } else {
        setError("Failed to load video status");
      }
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (projectId) loadData();
  }, [projectId, loadData]);

  // ---- Actions ----

  const handleGenerateVideo = async () => {
    setGenerating(true);
    setError(null);
    try {
      await generateVideo(projectId, platform);
      await loadData();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? `Video generation failed: ${err.message}`
          : "Video generation failed",
      );
    } finally {
      setGenerating(false);
    }
  };

  const handleGenerateThumbnail = async () => {
    setThumbGenerating(true);
    setError(null);
    try {
      await generateThumbnail(projectId, platform);
      await loadData();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? `Thumbnail generation failed: ${err.message}`
          : "Thumbnail generation failed",
      );
    } finally {
      setThumbGenerating(false);
    }
  };

  if (loading) return <div className="page-loading">Loading video status…</div>;

  const hasVideo = videos.length > 0;
  const readyVideo = videos.filter((v) => v.status === "ready");
  const hasReadyVideo = readyVideo.length > 0;

  return (
    <div className="page">
      <h1>Video Status</h1>
      <p>
        <Link to={`/projects/${projectId}`}>&larr; Back to Project</Link>
      </p>

      {error && <div className="page-error">{error}</div>}

      {/* ---- Generate control ---- */}
      <div className="detail-section">
        <h2>Generate Video</h2>
        <div className="action-buttons">
          <label htmlFor="video-platform">Platform Target</label>
          <select
            id="video-platform"
            value={platform}
            onChange={(e) => setPlatform(e.target.value)}
          >
            <option value="YouTube">YouTube</option>
            <option value="TikTok">TikTok</option>
            <option value="Instagram Reels">Instagram Reels</option>
            <option value="Instagram Feed">Instagram Feed</option>
            <option value="Twitter">Twitter</option>
            <option value="LinkedIn">LinkedIn</option>
          </select>
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleGenerateVideo}
            disabled={generating}
          >
            {generating ? "Generating…" : "Generate Video"}
          </button>
          <button
            type="button"
            className="btn"
            onClick={handleGenerateThumbnail}
            disabled={thumbGenerating}
          >
            {thumbGenerating ? "Generating…" : "Generate Thumbnail"}
          </button>
        </div>
      </div>

      {/* ---- Video status ---- */}
      <div className="detail-section">
        <h2>Video Assets ({videos.length})</h2>
        {!hasVideo ? (
          <p className="text-muted">
            No video generated yet. Generate a video above. A video requires an
            approved scene package (Gate 4).
          </p>
        ) : (
          <div className="media-list">
            {videos.map((video) => (
              <div key={video.id} className="source-card">
                <div className="source-header">
                  <span className="job-type">
                    {video.platform_target || "Default"}
                  </span>
                  <span className={`state-badge ${statusClass(video.status)}`}>
                    {formatStatus(video.status)}
                  </span>
                </div>
                <div className="media-asset-ref">
                  Asset: {video.asset_ref || "—"}
                </div>
                <div className="media-asset-ref">
                  Provider: {video.provider || "—"}
                </div>
                <div className="media-asset-ref">
                  Version: {video.version} · Resolution: {video.resolution_width}
                  ×{video.resolution_height} ({video.aspect_ratio})
                </div>
                <div className="media-asset-ref">
                  Duration: {durationLabel(video.duration_seconds)} · Scenes:{" "}
                  {video.scene_count}
                </div>
                {video.error_message && (
                  <div className="media-error">Error: {video.error_message}</div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ---- Thumbnail status / variations ---- */}
      <div className="detail-section">
        <h2>Thumbnails ({thumbnails.length})</h2>
        {thumbnails.length === 0 ? (
          <p className="text-muted">
            No thumbnail generated yet. Generate a thumbnail above to see
            variations.
          </p>
        ) : (
          <div className="media-list">
            {thumbnails.map((thumb) => (
              <div key={thumb.id} className="source-card">
                <div className="source-header">
                  <span className="job-type">
                    {thumb.platform_target || "Default"}
                  </span>
                  <span className={`state-badge ${statusClass(thumb.status)}`}>
                    {formatStatus(thumb.status)}
                  </span>
                </div>
                <div className="media-asset-ref">
                  Resolution: {thumb.width}×{thumb.height}
                </div>
                {thumb.title_text && (
                  <div className="media-asset-ref">
                    Title: {thumb.title_text}
                  </div>
                )}
                {thumb.error_message && (
                  <div className="media-error">Error: {thumb.error_message}</div>
                )}
                {Array.isArray(thumb.variations) && thumb.variations.length > 0 && (
                  <div className="variation-list">
                    {thumb.variations.map((v, i) => (
                      <span key={v} className="variation-chip">
                        Variation {i + 1}: {v}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ---- Preview access ---- */}
      <div className="detail-section">
        <h2>Preview</h2>
        {hasReadyVideo ? (
          <p>
            A ready video is available.{" "}
            <Link className="btn btn-primary" to={`/projects/${projectId}/preview`}>
              Open Preview
            </Link>
          </p>
        ) : (
          <p className="text-muted">
            Preview is available once a video has been generated and is{" "}
            <strong>ready</strong>. Video status: {formatStatus(videos[0]?.status ?? "none")}.
          </p>
        )}
      </div>
    </div>
  );
}
