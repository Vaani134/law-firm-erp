import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  assignEmailToMatter,
  fetchReviewQueue,
  searchMatters,
} from '../services/api';
import type { MatterSummary } from '../types/matterSearch';
import type { ReviewQueueEmail } from '../types/reviewQueue';
import './ReviewQueue.css';

const STATUS_LABEL: Record<string, string> = {
  open: 'Open',
  closed: 'Closed',
  pending: 'Pending',
  suspended: 'Suspended',
};

function mapAssignmentError(status: number, fallback: string): string {
  if (status === 409) {
    return 'The email is already assigned to a different matter.';
  }
  if (status === 404) {
    return 'The email or matter could not be found.';
  }
  if (status === 422) {
    return 'Invalid assignment data.';
  }
  return fallback || 'Unable to assign matter. Please try again.';
}

export function ReviewQueue() {
  const [emails, setEmails] = useState<ReviewQueueEmail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [assignTarget, setAssignTarget] = useState<ReviewQueueEmail | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [results, setResults] = useState<MatterSummary[]>([]);
  const [selectedMatter, setSelectedMatter] = useState<MatterSummary | null>(null);
  const [assigning, setAssigning] = useState(false);
  const [assignError, setAssignError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const searchSeq = useRef(0);
  const debounceRef = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const data = await fetchReviewQueue();
        if (!cancelled) {
          setEmails(data.emails);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load review queue');
          setLoading(false);
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!assignTarget) return;

    if (debounceRef.current !== null) {
      window.clearTimeout(debounceRef.current);
    }
    const trimmed = searchTerm.trim();

    if (trimmed.length === 0) {
      setResults([]);
      setSearching(false);
      setSearchError(null);
      return;
    }

    const seq = ++searchSeq.current;
    setSearching(true);
    setSearchError(null);

    debounceRef.current = window.setTimeout(async () => {
      try {
        const resp = await searchMatters(trimmed);
        if (seq !== searchSeq.current) return;
        setResults(resp.matters);
        setSearching(false);
      } catch (err) {
        if (seq !== searchSeq.current) return;
        setSearchError(
          err instanceof Error ? err.message : 'Failed to search matters.',
        );
        setSearching(false);
      }
    }, 250);

    return () => {
      if (debounceRef.current !== null) {
        window.clearTimeout(debounceRef.current);
      }
    };
  }, [searchTerm, assignTarget]);

  function openAssignModal(email: ReviewQueueEmail) {
    setAssignTarget(email);
    setSearchTerm('');
    setResults([]);
    setSelectedMatter(null);
    setSearchError(null);
    setAssignError(null);
  }

  function closeAssignModal() {
    if (assigning) return;
    setAssignTarget(null);
  }

  async function handleAssign() {
    if (!assignTarget || !selectedMatter || assigning) return;
    setAssigning(true);
    setAssignError(null);

    try {
      await assignEmailToMatter(assignTarget.email_id, selectedMatter.matter_key);
      const assignedKey = selectedMatter.matter_key;
      setEmails((prev) => prev.filter((e) => e.email_id !== assignTarget.email_id));
      setAssignTarget(null);
      setSelectedMatter(null);
      setSearchTerm('');
      setResults([]);
      setSuccessMessage(`Email assigned to matter ${assignedKey}.`);
    } catch (err) {
      const message = err instanceof Error ? err.message : '';
      const statusMatch = message.match(/HTTP\s+(\d{3})/);
      const status = statusMatch ? parseInt(statusMatch[1], 10) : 0;
      setAssignError(mapAssignmentError(status, message));
    } finally {
      setAssigning(false);
    }
  }

  const totalLabel = useMemo(() => `${emails.length} email${emails.length === 1 ? '' : 's'}`, [emails.length]);

  return (
    <div className="review-queue">
      <h2>Review Queue</h2>

      {successMessage && (
        <div className="alert alert-success" role="status">
          {successMessage}
        </div>
      )}

      {error && (
        <div className="alert alert-error">
          Unable to load review queue: {error}
        </div>
      )}

      {loading && <p>Loading...</p>}

      {!loading && !error && emails.length === 0 && (
        <div className="empty-state">No emails require review.</div>
      )}

      {!loading && !error && emails.length > 0 && (
        <>
          <p className="review-queue-meta">{totalLabel} awaiting review</p>
          <table className="data-table">
            <thead>
              <tr>
                <th>Subject</th>
                <th>Sender</th>
                <th>To</th>
                <th>Received</th>
                <th>Matter</th>
                <th>Status</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {emails.map((email) => (
                <tr key={email.email_id}>
                  <td>
                    <Link to={`/email/${email.email_id}`} className="link">
                      {email.subject || '(no subject)'}
                    </Link>
                  </td>
                  <td>{email.sender}</td>
                  <td>
                    {email.to_recipients && email.to_recipients.length > 0
                      ? email.to_recipients.map((r: Record<string, unknown>) => r.email as string).join(', ')
                      : '—'}
                  </td>
                  <td>{email.received_at ? new Date(email.received_at).toLocaleString() : '—'}</td>
                  <td>{email.matter_key || '—'}</td>
                  <td>
                    <span className="badge badge-warning">{email.processing_status}</span>
                  </td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={() => openAssignModal(email)}
                    >
                      Assign Matter
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {assignTarget && (
        <div className="modal-backdrop" onClick={closeAssignModal}>
          <div
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="assign-modal-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <h3 id="assign-modal-title">Assign Matter</h3>
              <button
                type="button"
                className="modal-close"
                onClick={closeAssignModal}
                disabled={assigning}
                aria-label="Close"
              >
                ×
              </button>
            </div>

            <div className="modal-body">
              <section className="modal-email-summary">
                <div className="modal-email-row">
                  <span className="modal-label">Subject</span>
                  <span>{assignTarget.subject || '(no subject)'}</span>
                </div>
                <div className="modal-email-row">
                  <span className="modal-label">From</span>
                  <span>{assignTarget.sender}</span>
                </div>
                <div className="modal-email-row">
                  <span className="modal-label">Received</span>
                  <span>
                    {assignTarget.received_at
                      ? new Date(assignTarget.received_at).toLocaleString()
                      : '—'}
                  </span>
                </div>
                <div className="modal-email-row">
                  <span className="modal-label">Status</span>
                  <span>{assignTarget.processing_status}</span>
                </div>
              </section>

              <label className="modal-label" htmlFor="matter-search-input">
                Search matters
              </label>
              <input
                id="matter-search-input"
                type="text"
                className="modal-input"
                placeholder="Search by matter key, client, or matter name"
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value);
                  setSelectedMatter(null);
                }}
                autoFocus
                disabled={assigning}
              />

              {searchError && (
                <div className="alert alert-error modal-alert">
                  Search failed: {searchError}
                </div>
              )}

              <div className="modal-results">
                {searchTerm.trim().length === 0 && (
                  <p className="modal-hint">Type to search for a matter.</p>
                )}

                {searchTerm.trim().length > 0 && searching && (
                  <p className="modal-hint">Searching...</p>
                )}

                {searchTerm.trim().length > 0 && !searching && !searchError && results.length === 0 && (
                  <p className="modal-hint">No matters match your search.</p>
                )}

                {results.length > 0 && (
                  <ul className="modal-result-list">
                    {results.map((m) => {
                      const isSelected = selectedMatter?.matter_key === m.matter_key;
                      return (
                        <li
                          key={m.matter_key}
                          className={`modal-result-item${isSelected ? ' is-selected' : ''}`}
                        >
                          <button
                            type="button"
                            className="modal-result-button"
                            onClick={() => setSelectedMatter(m)}
                            disabled={assigning}
                          >
                            <div className="modal-result-line-1">
                              <span className="modal-result-key">{m.matter_key}</span>
                              <span className="modal-result-client">{m.client_name}</span>
                            </div>
                            <div className="modal-result-line-2">
                              <span>{m.matter_name}</span>
                            </div>
                            <div className="modal-result-line-3">
                              <span
                                className={`badge badge-status badge-${m.matter_status}`}
                              >
                                {STATUS_LABEL[m.matter_status] || m.matter_status}
                              </span>
                              {m.practice_area && (
                                <span className="modal-result-tag">{m.practice_area}</span>
                              )}
                              {m.primary_attorney && (
                                <span className="modal-result-tag">Lead: {m.primary_attorney}</span>
                              )}
                            </div>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>

              {assignError && (
                <div className="alert alert-error modal-alert">{assignError}</div>
              )}
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={closeAssignModal}
                disabled={assigning}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={handleAssign}
                disabled={!selectedMatter || assigning}
              >
                {assigning ? 'Assigning...' : 'Assign'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
