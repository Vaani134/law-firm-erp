import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchMatterDetail, fetchCaseBrainTimeline } from '../services/api';
import type { MatterDetailResponse, CaseBrainTimelineResponse, MatterParticipant, MatterEmail, MatterCaseBrainEntry } from '../types';
import './MatterDetail.css';

export function MatterDetail() {
  const { matterKey } = useParams<{ matterKey: string | undefined }>();
  const [matter, setMatter] = useState<MatterDetailResponse | null>(null);
  const [timeline, setTimeline] = useState<CaseBrainTimelineResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!matterKey) return;

    let cancelled = false;

    async function load() {
      try {
        const [matterData, timelineData] = await Promise.all([
          fetchMatterDetail(matterKey),
          fetchCaseBrainTimeline(matterKey),
        ]);
        if (!cancelled) {
          setMatter(matterData);
          setTimeline(timelineData);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load matter');
          setLoading(false);
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [matterKey]);

  if (!matterKey) {
    return <div className="matter-detail">No matter selected.</div>;
  }

  if (loading) {
    return <div className="matter-detail">Loading...</div>;
  }

  if (error || !matter) {
    return (
      <div className="matter-detail">
        <div className="alert alert-error">
          {error || 'Matter not found.'}
        </div>
      </div>
    );
  }

  return (
    <div className="matter-detail">
      <h2>Matter Detail</h2>

      <div className="panel">
        <div className="panel-header">
          <h3>{matter.matter.matter_name}</h3>
          <span className="badge badge-info">{matter.matter.matter_status}</span>
        </div>
        <div className="panel-body">
          <div className="detail-grid">
            <div className="detail-item">
              <span className="detail-label">Matter Key</span>
              <span className="detail-value">{matter.matter.matter_key}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Client</span>
              <span className="detail-value">{matter.matter.client_name}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Practice Area</span>
              <span className="detail-value">{matter.matter.practice_area || '—'}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Primary Attorney</span>
              <span className="detail-value">{matter.matter.primary_attorney || '—'}</span>
            </div>
          </div>
          <p className="matter-description">{matter.matter.matter_description}</p>
        </div>
      </div>

      <div className="section">
        <h3>Participants ({matter.participants.length})</h3>
        {matter.participants.length === 0 && <p>No participants.</p>}
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Organization</th>
              <th>Role</th>
              <th>Active</th>
            </tr>
          </thead>
          <tbody>
            {matter.participants.map((p: MatterParticipant) => (
              <tr key={p.participant_id}>
                <td>{p.participant_name}</td>
                <td>{p.email_address || '—'}</td>
                <td>{p.organization || '—'}</td>
                <td>{p.role_relationship || '—'}</td>
                <td>{p.is_active ? 'Yes' : 'No'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="section">
        <h3>Emails ({matter.emails.length})</h3>
        {matter.emails.length === 0 && <p>No emails.</p>}
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
            {matter.emails.map((e: MatterEmail) => (
              <tr key={e.email_id}>
                <td>
                  <Link to={`/email/${e.email_id}`} className="link">
                    {e.subject || '(no subject)'}
                  </Link>
                </td>
                <td>{e.sender}</td>
                <td>{e.received_at ? new Date(e.received_at).toLocaleString() : '—'}</td>
                <td>
                  <span className="badge badge-info">{e.processing_status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="section">
        <h3>Case Brain ({timeline?.total ?? 0})</h3>
        {!timeline || timeline.entries.length === 0 ? (
          <p>No case brain entries.</p>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Occurred</th>
                <th>Source</th>
                <th>Source Reference</th>
                <th>Actor</th>
                <th>Summary</th>
              </tr>
            </thead>
            <tbody>
              {timeline.entries.map((entry: MatterCaseBrainEntry) => (
                <tr key={entry.brain_entry_id}>
                  <td>{new Date(entry.occurred_at).toLocaleString()}</td>
                  <td>{entry.source_type}</td>
                  <td>{entry.source_reference || '—'}</td>
                  <td>{entry.source_actor || '—'}</td>
                  <td>{entry.update_summary}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
