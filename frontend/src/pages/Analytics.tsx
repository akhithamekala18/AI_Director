import { useEffect, useState, useCallback } from "react";
import {
  getAnalyticsSummary,
  getAnalyticsByPlatform,
  getAnalyticsByTopic,
  type AnalyticsSummary,
  type PlatformAnalytics,
  type TopicAnalytics,
} from "../api/analytics";
import { ApiError } from "../api/client";

// ---------------------------------------------------------------------------
// Analytics dashboard (Task 49). Read-only performance tracking for published
// entries. The backend enforces that only published content is measured and
// scopes results to the user's teams. Aggregates by platform and topic.
// ---------------------------------------------------------------------------

function formatNumber(value: number | null | undefined): string {
  if (value == null) return "—";
  return value.toLocaleString();
}

function formatPercent(value: number | null | undefined): string {
  if (value == null) return "—";
  return `${value.toFixed(2)}%`;
}

function SummaryCard({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="analytics-card">
      <span className="analytics-card-label">{label}</span>
      <span className="analytics-card-value">{value}</span>
    </div>
  );
}

export function Analytics() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [platforms, setPlatforms] = useState<PlatformAnalytics[]>([]);
  const [topics, setTopics] = useState<TopicAnalytics[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, p, t] = await Promise.all([
        getAnalyticsSummary(),
        getAnalyticsByPlatform(),
        getAnalyticsByTopic(),
      ]);
      setSummary(s.summary);
      setPlatforms(p.platforms);
      setTopics(t.topics);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? "Failed to load analytics"
          : "Failed to load analytics",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) return <div className="page-loading">Loading analytics…</div>;

  const hasData =
    summary != null &&
    (summary.entry_count > 0 || platforms.length > 0 || topics.length > 0);

  return (
    <div className="page">
      <h1>Analytics</h1>
      <p className="text-muted">
        Published-content performance only. Views and engagement are measured
        for entries that have actually been published.
      </p>

      {error && <div className="page-error">{error}</div>}

      {!hasData ? (
        <div className="empty-state">
          <p>No analytics yet. Performance appears after content is published.</p>
        </div>
      ) : (
        <>
          {summary && (
            <section className="detail-section">
              <h2>Summary</h2>
              <div className="analytics-grid">
                <SummaryCard label="Total Views" value={formatNumber(summary.total_views)} />
                <SummaryCard label="Total Likes" value={formatNumber(summary.total_likes)} />
                <SummaryCard label="Total Comments" value={formatNumber(summary.total_comments)} />
                <SummaryCard label="Total Shares" value={formatNumber(summary.total_shares)} />
                <SummaryCard label="Avg Engagement" value={formatPercent(summary.avg_engagement)} />
                <SummaryCard label="Published Entries" value={formatNumber(summary.entry_count)} />
              </div>
            </section>
          )}

          <section className="detail-section">
            <h2>By Platform</h2>
            {platforms.length === 0 ? (
              <p className="empty-text">No platform breakdown available.</p>
            ) : (
              <table className="project-table">
                <thead>
                  <tr>
                    <th>Platform</th>
                    <th>Views</th>
                    <th>Likes</th>
                    <th>Comments</th>
                    <th>Shares</th>
                    <th>Engagement</th>
                    <th>Entries</th>
                  </tr>
                </thead>
                <tbody>
                  {platforms.map((p) => (
                    <tr key={p.platform}>
                      <td>{p.platform}</td>
                      <td>{formatNumber(p.total_views)}</td>
                      <td>{formatNumber(p.total_likes)}</td>
                      <td>{formatNumber(p.total_comments)}</td>
                      <td>{formatNumber(p.total_shares)}</td>
                      <td>{formatPercent(p.avg_engagement)}</td>
                      <td>{formatNumber(p.entry_count)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>

          <section className="detail-section">
            <h2>By Topic</h2>
            {topics.length === 0 ? (
              <p className="empty-text">No topic breakdown available.</p>
            ) : (
              <table className="project-table">
                <thead>
                  <tr>
                    <th>Topic</th>
                    <th>Views</th>
                    <th>Likes</th>
                    <th>Engagement</th>
                    <th>Entries</th>
                  </tr>
                </thead>
                <tbody>
                  {topics.map((t) => (
                    <tr key={t.topic}>
                      <td>{t.topic}</td>
                      <td>{formatNumber(t.total_views)}</td>
                      <td>{formatNumber(t.total_likes)}</td>
                      <td>{formatPercent(t.avg_engagement)}</td>
                      <td>{formatNumber(t.entry_count)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </>
      )}
    </div>
  );
}
