import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  addCaseBrainEntry,
  fetchCaseBrainTimeline,
  fetchMatterDetail,
} from '../services/api';
import type {
  CaseBrainEntryCreate,
  CaseBrainSourceType,
  MatterCaseBrainEntry,
  MatterDetailResponse,
  CaseBrainTimelineResponse,
  MatterEmail,
  MatterParticipant,
} from '../types';
import './MatterDetail.css';

const SOURCE_TYPE_OPTIONS: { value: CaseBrainSourceType; label: string }[] = [
  { value: 'manual', label: 'Manual' },
  { value: 'intake', label: 'Intake' },
  { value: 'system', label: 'System' },
  { value: 'import', label: 'Import' },
];

const EMPTY_FORM = {
  source_type: 'manual' as CaseBrainSourceType,
  update_summary: '',
  source_reference: '',
  source_actor: '',
  occurred_at: '',
  logged_by: '',
};

type FormState = typeof EMPTY_FORM;

function toIsoOrNull(localValue: string): string | null {
  if (!localValue) return null;
  // datetime-local gives "YYYY-MM-DDTHH:mm" without timezone.
  // Treat it as local time and convert to ISO with UTC offset.
  const parsed = new Date(localValue);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toISOString();
}

export function MatterDetail() {
  const { matterKey } = useParams<{ matterKey: string | undefined }>();
  const [matter, setMatter] = useState<MatterDetailResponse | null>(null);
  const [timeline, setTimeline] = useState<CaseBrainTimelineResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showEntryForm, setShowEntryForm] = useState(false);
  const [entryForm, setEntryForm] = useState<FormState>(EMPTY_FORM);
  const [entrySaving, setEntrySaving] = useState(false);
  const [entryError, setEntryError] = useState<string | null>(null);
  const [entryFieldError, setEntryFieldError] = useState<string | null>(null);
  const [entrySuccess, setEntrySuccess] = useState<string | null>(null);

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

  function openEntryForm() {
    setEntryForm(EMPTY_FORM);
    setEntryError(null);
    setEntryFieldError(null);
    setEntrySuccess(null);
    setShowEntryForm(true);
  }

  function closeEntryForm() {
    if (entrySaving) return;
    setShowEntryForm(false);
  }

  async function reloadTimeline() {
    if (!matterKey) return;
    const timelineData = await fetchCaseBrainTimeline(matterKey);
    setTimeline(timelineData);
  }

  async function handleEntrySubmit(e: React.FormEvent) {
    e.preventDefault();
    if (entrySaving || !matterKey) return;

    const summary = entryForm.update_summary.trim();
    if (!summary) {
      setEntryFieldError('Update summary is required and cannot be blank.');
      return;
    }

    const payload: CaseBrainEntryCreate = {
      source_type: entryForm.source_type,
      update_summary: summary,
      source_reference: entryForm.source_reference.trim() || null,
      source_actor: entryForm.source_actor.trim() || null,
      occurred_at: toIsoOrNull(entryForm.occurred_at),
      logged_by: entryForm.logged_by.trim() || null,
    };

    setEntrySaving(true);
    setEntryError(null);
    setEntryFieldError(null);
    setEntrySuccess(null);

    try {
      await addCaseBrainEntry(matterKey, payload);
      setShowEntryForm(false);
      setEntryForm(EMPTY_FORM);
      setEntrySuccess('Case Brain entry added.');
      await reloadTimeline();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to add entry.';
      setEntryError(message);
    } finally {
      setEntrySaving(false);
    }
  }

  return (
    <div className="matter-detail">
      <h2>Matter Detail</h2>

      {entrySuccess && (
        <div className="alert alert-success" role="status">
          {entrySuccess}
        </div>
      )}

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
        <div className="section-header">
          <h3>Case Brain ({timeline?.total ?? 0})</h3>
          {!showEntryForm && (
            <button type="button" className="btn btn-primary" onClick={openEntryForm}>
              Add Entry
            </button>
          )}
        </div>

        {showEntryForm && (
          <form className="entry-form" onSubmit={handleEntrySubmit} noValidate>
            {entryError && (
              <div className="alert alert-error entry-form-alert">{entryError}</div>
            )}

            <div className="entry-form-grid">
              <div className="entry-form-field">
                <label htmlFor="cbe-source-type">Source Type</label>
                <select
                  id="cbe-source-type"
                  value={entryForm.source_type}
                  onChange={(e) =>
                    setEntryForm({ ...entryForm, source_type: e.target.value as CaseBrainSourceType })
                  }
                  disabled={entrySaving}
                >
                  {SOURCE_TYPE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="entry-form-field">
                <label htmlFor="cbe-occurred-at">Occurred At</label>
                <input
                  id="cbe-occurred-at"
                  type="datetime-local"
                  value={entryForm.occurred_at}
                  onChange={(e) => setEntryForm({ ...entryForm, occurred_at: e.target.value })}
                  disabled={entrySaving}
                />
              </div>

              <div className="entry-form-field entry-form-field-wide">
                <label htmlFor="cbe-summary">
                  Update Summary <span className="required-mark">*</span>
                </label>
                <textarea
                  id="cbe-summary"
                  rows={3}
                  value={entryForm.update_summary}
                  onChange={(e) => {
                    setEntryForm({ ...entryForm, update_summary: e.target.value });
                    if (entryFieldError) setEntryFieldError(null);
                  }}
                  disabled={entrySaving}
                  placeholder="Describe the event, call, or note."
                />
                {entryFieldError && (
                  <span className="field-error">{entryFieldError}</span>
                )}
              </div>

              <div className="entry-form-field">
                <label htmlFor="cbe-source-ref">Source Reference</label>
                <input
                  id="cbe-source-ref"
                  type="text"
                  value={entryForm.source_reference}
                  onChange={(e) => setEntryForm({ ...entryForm, source_reference: e.target.value })}
                  disabled={entrySaving}
                  placeholder="Optional identifier"
                />
              </div>

              <div className="entry-form-field">
                <label htmlFor="cbe-source-actor">Source Actor</label>
                <input
                  id="cbe-source-actor"
                  type="text"
                  value={entryForm.source_actor}
                  onChange={(e) => setEntryForm({ ...entryForm, source_actor: e.target.value })}
                  disabled={entrySaving}
                  placeholder="Optional person/system"
                />
              </div>

              <div className="entry-form-field">
                <label htmlFor="cbe-logged-by">Logged By</label>
                <input
                  id="cbe-logged-by"
                  type="text"
                  value={entryForm.logged_by}
                  onChange={(e) => setEntryForm({ ...entryForm, logged_by: e.target.value })}
                  disabled={entrySaving}
                  placeholder="Optional initials or name"
                />
              </div>
            </div>

            <div className="entry-form-actions">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={closeEntryForm}
                disabled={entrySaving}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={entrySaving}
              >
                {entrySaving ? 'Saving...' : 'Add Entry'}
              </button>
            </div>
          </form>
        )}

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
                  <td>
                    <span className={`badge badge-source badge-source-${entry.source_type.toLowerCase()}`}>
                      {entry.source_type}
                    </span>
                  </td>
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
