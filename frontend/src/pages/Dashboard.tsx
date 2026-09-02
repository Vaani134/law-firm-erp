import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchReviewQueue } from '../services/api';
import type { ReviewQueueEmail } from '../types/reviewQueue';
import './Dashboard.css';

export function Dashboard() {
  const [reviewQueue, setReviewQueue] = useState<ReviewQueueEmail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const data = await fetchReviewQueue();
        if (!cancelled) {
          setReviewQueue(data.emails);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load dashboard');
          setLoading(false);
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const reviewRequiredCount = reviewQueue.length;

  return (
    <div className="dashboard">
      <h2>Dashboard</h2>

      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-label">Review Required</div>
          <div className="stat-value">{loading ? '—' : reviewRequiredCount}</div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <h3>Review Queue</h3>
          <Link to="/review-queue" className="link">View all</Link>
        </div>
        <div className="panel-body">
          {loading && <p>Loading...</p>}
          {!loading && error && <p className="error-text">Unable to load review queue.</p>}
          {!loading && !error && reviewRequiredCount === 0 && (
            <p>No emails require review.</p>
          )}
          {!loading && !error && reviewRequiredCount > 0 && (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Subject</th>
                  <th>Sender</th>
                  <th>Received</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {reviewQueue.slice(0, 5).map((email) => (
                  <tr key={email.email_id}>
                    <td>
                      <Link to={`/email/${email.email_id}`} className="link">
                        {email.subject || '(no subject)'}
                      </Link>
                    </td>
                    <td>{email.sender}</td>
                    <td>{email.received_at ? new Date(email.received_at).toLocaleString() : '—'}</td>
                    <td>
                      <span className="badge badge-warning">{email.processing_status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
