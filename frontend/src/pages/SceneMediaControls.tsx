import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import {
  listSceneMedia,
  generateSceneMedia,
  requestRegeneration,
  type SceneMediaAsset,
} from "../api/sceneMedia";
import { ApiError } from "../api/client";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function statusClass(status: string): string {
  if (status === "ready") return "state-approved";
  if (status === "failed") return "state-revision";
  if (status === "generating") return "state-generating";
  return "state-draft";
}

function formatStatus(status: string): string {
  return status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function mediaTypeLabel(t: string): string {
  const labels: Record<string, string> = {
    visual: "Visual",
    voice: "Voice / Narration",
    music: "Music / Audio",
    subtitle: "Subtitles / Captions",
  };
  return labels[t] || t;
}

// ---------------------------------------------------------------------------
// Grouped scene media
// ---------------------------------------------------------------------------

interface SceneGroup {
  sceneId: string;
  sceneOrder: number;
  assets: SceneMediaAsset[];
}

function groupByScene(media: SceneMediaAsset[]): SceneGroup[] {
  const map = new Map<string, SceneGroup>();
  for (const m of media) {
    if (!map.has(m.scene_id)) {
      map.set(m.scene_id, {
        sceneId: m.scene_id,
        sceneOrder: m.scene_order,
        assets: [],
      });
    }
    map.get(m.scene_id)!.assets.push(m);
  }
  return Array.from(map.values()).sort((a, b) => a.sceneOrder - b.sceneOrder);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function SceneMediaControls() {
  const { id } = useParams<{ id: string }>();
  const projectId = Number(id);

  const [media, setMedia] = useState<SceneMediaAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Generation state
  const [generatingAll, setGeneratingAll] = useState(false);
  const [regeneratingScene, setRegeneratingScene] = useState<string | null>(null);
  const [regeneratingType, setRegeneratingType] = useState<string | null>(null);

  // Expanded scene
  const [expandedScene, setExpandedScene] = useState<string | null>(null);

  // ---- Data loading ----

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await listSceneMedia(projectId);
      setMedia(res.media);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setMedia([]);
      } else {
        setError("Failed to load scene media");
      }
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    if (projectId) loadData();
  }, [projectId, loadData]);

  // ---- Actions ----

  const handleGenerateAll = async () => {
    setGeneratingAll(true);
    setError(null);
    try {
      await generateSceneMedia(projectId);
      // Reload after a short delay to pick up newly created media
      setTimeout(() => loadData(), 1000);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Generation failed");
    } finally {
      setGeneratingAll(false);
    }
  };

  const handleRegenerateScene = async (sceneId: string, mediaTypes: string[]) => {
    setRegeneratingScene(sceneId);
    setError(null);
    try {
      await requestRegeneration(projectId, { scene_id: sceneId, media_types: mediaTypes });
      setTimeout(() => loadData(), 1000);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Regeneration failed");
    } finally {
      setRegeneratingScene(null);
    }
  };

  const handleRegenerateType = async (sceneId: string, mediaType: string) => {
    setRegeneratingType(`${sceneId}-${mediaType}`);
    setError(null);
    try {
      await requestRegeneration(projectId, {
        scene_id: sceneId,
        media_types: [mediaType],
      });
      setTimeout(() => loadData(), 1000);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Regeneration failed");
    } finally {
      setRegeneratingType(null);
    }
  };

  // ---- Loading / empty ----

  if (loading) return <div className="page-loading">Loading scene media…</div>;

  const sceneGroups = groupByScene(media);

  return (
    <div className="page">
      <h1>Scene Media Controls</h1>
      <p>
        <Link to={`/projects/${projectId}`}>&larr; Back to Project</Link>
      </p>

      {error && <div className="page-error">{error}</div>}

      {media.length === 0 ? (
        <div className="detail-section">
          <p>No scene media found. Generate media for all scenes or build scenes first.</p>
          <div className="action-buttons">
            <button className="btn" onClick={handleGenerateAll} disabled={generatingAll}>
              {generatingAll ? "Generating…" : "Generate All Media"}
            </button>
          </div>
        </div>
      ) : (
        <>
          {/* ---- Summary ---- */}
          <div className="detail-section">
            <h2>Media Overview</h2>
            <div className="media-summary">
              <span className="media-summary-item">
                {sceneGroups.length} scene{sceneGroups.length !== 1 ? "s" : ""}
              </span>
              <span className="media-summary-item">
                {media.filter((m) => m.status === "ready").length} ready
              </span>
              <span className="media-summary-item">
                {media.filter((m) => m.status === "generating").length} generating
              </span>
              <span className="media-summary-item">
                {media.filter((m) => m.status === "failed").length} failed
              </span>
              <span className="media-summary-item">
                {media.filter((m) => m.status === "pending").length} pending
              </span>
            </div>
          </div>

          {/* ---- Per-Scene Media ---- */}
          <div className="detail-section">
            <h2>Per-Scene Media</h2>
            <div className="media-scene-list">
              {sceneGroups.map((group) => {
                const isExpanded = expandedScene === group.sceneId;
                const readyCount = group.assets.filter((a) => a.status === "ready").length;
                const totalCount = group.assets.length;
                const isWorking = regeneratingScene === group.sceneId;

                return (
                  <div key={group.sceneId} className="media-scene-card">
                    <div
                      className="media-scene-header"
                      onClick={() => setExpandedScene(isExpanded ? null : group.sceneId)}
                    >
                      <div className="media-scene-title">
                        <span className="media-scene-order">#{group.sceneOrder}</span>
                        <span className="media-scene-id">Scene {group.sceneId}</span>
                        <span className="media-scene-status">
                          {readyCount}/{totalCount} ready
                        </span>
                      </div>
                      <span className="media-expand">{isExpanded ? "▲" : "▼"}</span>
                    </div>

                    {isExpanded && (
                      <div className="media-scene-detail">
                        {/* Media type cards */}
                        <div className="media-type-grid">
                          {group.assets.map((asset) => (
                            <div key={asset.id} className="media-type-card">
                              <div className="media-type-header">
                                <span className="media-type-name">
                                  {mediaTypeLabel(asset.media_type)}
                                </span>
                                <span className={`badge ${statusClass(asset.status)}`}>
                                  {formatStatus(asset.status)}
                                </span>
                              </div>
                              {asset.status === "failed" && asset.error_message && (
                                <p className="media-error">{asset.error_message}</p>
                              )}
                              {asset.status === "ready" && asset.asset_ref && (
                                <p className="media-asset-ref">Asset: {asset.asset_ref}</p>
                              )}
                              {asset.voice && Object.keys(asset.voice).length > 0 && (
                                <div className="media-detail-row">
                                  <strong>Voice:</strong> {JSON.stringify(asset.voice)}
                                </div>
                              )}
                              {asset.music && Object.keys(asset.music).length > 0 && (
                                <div className="media-detail-row">
                                  <strong>Music:</strong> {JSON.stringify(asset.music)}
                                </div>
                              )}
                              {asset.caption && Object.keys(asset.caption).length > 0 && (
                                <div className="media-detail-row">
                                  <strong>Caption:</strong> {JSON.stringify(asset.caption)}
                                </div>
                              )}
                              <div className="media-type-actions">
                                <button
                                  className="btn btn-sm"
                                  onClick={() =>
                                    handleRegenerateType(group.sceneId, asset.media_type)
                                  }
                                  disabled={
                                    regeneratingType === `${group.sceneId}-${asset.media_type}` ||
                                    isWorking
                                  }
                                >
                                  {regeneratingType === `${group.sceneId}-${asset.media_type}`
                                    ? "Regenerating…"
                                    : `Re-render ${mediaTypeLabel(asset.media_type).split(" ")[0]}`}
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>

                        {/* Scene-level actions */}
                        <div className="media-scene-actions">
                          <button
                            className="btn"
                            onClick={() =>
                              handleRegenerateScene(group.sceneId, [
                                "visual",
                                "voice",
                                "music",
                                "subtitle",
                              ])
                            }
                            disabled={isWorking}
                          >
                            {regeneratingScene === group.sceneId
                              ? "Regenerating…"
                              : "Regenerate Entire Scene"}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* ---- Global Actions ---- */}
          <div className="detail-section">
            <h2>Actions</h2>
            <div className="action-buttons">
              <button className="btn" onClick={handleGenerateAll} disabled={generatingAll}>
                {generatingAll ? "Generating…" : "Generate All Media"}
              </button>
              <button className="btn" onClick={loadData}>
                Refresh
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
