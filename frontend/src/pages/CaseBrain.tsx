import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { searchCaseBrain, addCaseBrainEntry } from '../services/api';
import type { CaseBrainSearchEntry } from '../types';
import type { CaseBrainEntryCreate, CaseBrainSourceType } from '../types/caseBrainEntry';
import './CaseBrain.css';

const PAGE_SIZE = 50;
const SEARCH_DEBOUNCE_MS = 300;

const SOURCE_TYPE_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All sources' },
  { value: 'email', label: 'Email' },
  { value: 'manual', label: 'Manual' },
  { value: 'intake', label: 'Intake' },
  { value: 'system', label: 'System' },
  { value: 'import', label: 'Import' },
];

const EMPTY_FORM = {
  matter_key: '',
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
  const parsed = new Date(localValue);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toISOString();
}

export function CaseBrain() {
  const [query, setQuery] = useState('');
  const [sourceType, setSourceType] = useState('');
  const [matterKey, setMatterKey] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const [page, setPage] = useState(0);
  const [results, setResults] = useState<CaseBrainSearchEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showEntryForm, setShowEntryForm] = useState(false);
  const [entryForm, setEntryForm] = useState<FormState>(EMPTY_FORM);
  const [entrySaving, setEntrySaving] = useState(false);
  const [entryError, setEntryError] = useState<string | null>(null);
  const [entryFieldError, setEntryFieldError] = useState<string | null>(null);
  const [entrySuccess, setEntrySuccess] = useState<string | null>(null);

  const seqRef = useRef(0);
  const debounceRef = useRef<number | null>(null);
  const cancelledRef = useRef(false);

  const fetchPage = useCallback(
    async (
      q: string,
      st: string,
      mk: string,
      df: string,
      dt: string,
      pageIndex: number,
    ) => {
      const seq = ++seqRef.current;
      setLoading(true);
      setError(null);
      try {
        const resp = await searchCaseBrain({
          q: q || undefined,
          sourceType: st || undefined,
          matterKey: mk || undefined,
          dateFrom: df || undefined,
          dateTo: dt || undefined,
          limit: PAGE_SIZE,
          offset: pageIndex * PAGE_SIZE,
        });
        if (cancelledRef.current || seq !== seqRef.current) return;
        setResults(resp.entries);
        setTotal(resp.total);
        setLoading(false);
      } catch (err) {
        if (cancelledRef.current || seq !== seqRef.current) return;
        setError(err instanceof Error ? err.message : 'Failed to load Case Brain entries.');
        setResults([]);
        setTotal(0);
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (debounceRef.current !== null) {
      window.clearTimeout(debounceRef.current);
    }
    setPage(0);
    debounceRef.current = window.setTimeout(() => {
      void fetchPage(query, sourceType, matterKey, dateFrom, dateTo, 0);
    }, SEARCH_DEBOUNCE_MS);

    return () => {
      if (debounceRef.current !== null) {
        window.clearTimeout(debounceRef.current);
      }
    };
  }, [query, sourceType, matterKey, dateFrom, dateTo, fetchPage]);

  useEffect(() => {
    if (page === 0) return;
    void fetchPage(query, sourceType, matterKey, dateFrom, dateTo, page);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  useEffect(() => {
    cancelledRef.current = false;
    return () => {
      cancelledRef.current = true;
      if (debounceRef.current !== null) {
        window.clearTimeout(debounceRef.current);
      }
    };
  }, []);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const isFirstPage = page === 0;
  const isLastPage = page >= totalPages - 1;
  const filtersActive =
    query.trim().length > 0 ||
    sourceType !== '' ||
    matterKey.trim().length > 0 ||
    dateFrom.trim().length > 0 ||
    dateTo.trim().length > 0;

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
    await fetchPage(query, sourceType, matterKey, dateFrom, dateTo, page);
  }

  async function handleEntrySubmit(e: React.FormEvent) {
    e.preventDefault();
    if (entrySaving) return;

    const mk = entryForm.matter_key.trim();
    if (!mk) {
      setEntryFieldError('Matter key is required.');
      return;
    }

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
      await addCaseBrainEntry(mk, payload);
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

  const matterHref = (mk: string) => `/matters/${encodeURIComponent(mk)}`;
  const emailHref = (eid: string | null) => (eid ? `/email/${encodeURIComponent(eid)}` : null);

  return (
    <div className="case-brain-page">
      <div className="page-header">
        <h2>Case Brain</h2>
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
              <label htmlFor="cb-matter-key">Matter Key <span className="required-mark">*</span></label>
              <input
                id="cb-matter-key"
                type="text"
                value={entryForm.matter_key}
                onChange={(e) => {
                  setEntryForm({ ...entryForm, matter_key: e.target.value });
                  if (entryFieldError) setEntryFieldError(null);
                }}
                disabled={entrySaving}
                placeholder="e.g. MAT-001"
              />
              {entryFieldError && entryFieldError.toLowerCase().includes('matter') && (
                <span className="field-error">{entryFieldError}</span>
              )}
            </div>

            <div className="entry-form-field">
              <label htmlFor="cb-source-type">Source Type</label>
              <select
                id="cb-source-type"
                value={entryForm.source_type}
                onChange={(e) =>
                  setEntryForm({ ...entryForm, source_type: e.target.value as CaseBrainSourceType })
                }
                disabled={entrySaving}
              >
                <option value="manual">Manual</option>
                <option value="intake">Intake</option>
                <option value="system">System</option>
                <option value="import">Import</option>
              </select>
            </div>

            <div className="entry-form-field">
              <label htmlFor="cb-occurred-at">Occurred At</label>
              <input
                id="cb-occurred-at"
                type="datetime-local"
                value={entryForm.occurred_at}
                onChange={(e) => setEntryForm({ ...entryForm, occurred_at: e.target.value })}
                disabled={entrySaving}
              />
            </div>

            <div className="entry-form-field entry-form-field-wide">
              <label htmlFor="cb-summary">
                Update Summary <span className="required-mark">*</span>
              </label>
              <textarea
                id="cb-summary"
                rows={3}
                value={entryForm.update_summary}
                onChange={(e) => {
                  setEntryForm({ ...entryForm, update_summary: e.target.value });
                  if (entryFieldError) setEntryFieldError(null);
                }}
                disabled={entrySaving}
                placeholder="Describe the event, call, or note."
              />
              {entryFieldError && entryFieldError.toLowerCase().includes('summary') && (
                <span className="field-error">{entryFieldError}</span>
              )}
            </div>

            <div className="entry-form-field">
              <label htmlFor="cb-source-ref">Source Reference</label>
              <input
                id="cb-source-ref"
                type="text"
                value={entryForm.source_reference}
                onChange={(e) => setEntryForm({ ...entryForm, source_reference: e.target.value })}
                disabled={entrySaving}
                placeholder="Optional identifier"
              />
            </div>

            <div className="entry-form-field">
              <label htmlFor="cb-source-actor">Source Actor</label>
              <input
                id="cb-source-actor"
                type="text"
                value={entryForm.source_actor}
                onChange={(e) => setEntryForm({ ...entryForm, source_actor: e.target.value })}
                disabled={entrySaving}
                placeholder="Optional person/system"
              />
            </div>

            <div className="entry-form-field">
              <label htmlFor="cb-logged-by">Logged By</label>
              <input
                id="cb-logged-by"
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

      {entrySuccess && !showEntryForm && (
        <div className="alert alert-success" role="status">
          {entrySuccess}
        </div>
      )}

      <div className="panel">
        <div className="panel-body">
          <div className="case-brain-filters">
            <div className="case-brain-filter-field case-brain-filter-field-grow">
              <label htmlFor="cb-q">Search</label>
              <input
                id="cb-q"
                type="text"
                placeholder="Search summary, reference, actor, or matter key"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>

            <div className="case-brain-filter-field">
              <label htmlFor="cb-matter">Matter Key</label>
              <input
                id="cb-matter"
                type="text"
                placeholder="e.g. MAT-001"
                value={matterKey}
                onChange={(e) => setMatterKey(e.target.value)}
              />
            </div>

            <div className="case-brain-filter-field">
              <label htmlFor="cb-source">Source</label>
              <select
                id="cb-source"
                value={sourceType}
                onChange={(e) => setSourceType(e.target.value)}
              >
                {SOURCE_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value || 'all'} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="case-brain-filter-field">
              <label htmlFor="cb-date-from">Date From</label>
              <input
                id="cb-date-from"
                type="datetime-local"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
              />
            </div>

            <div className="case-brain-filter-field">
              <label htmlFor="cb-date-to">Date To</label>
              <input
                id="cb-date-to"
                type="datetime-local"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
              />
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="alert alert-error case-brain-alert">
          <span>Unable to load Case Brain entries: {error}</span>
          <button
            type="button"
            className="btn btn-secondary case-brain-retry"
            onClick={() => {
              void fetchPage(query, sourceType, matterKey, dateFrom, dateTo, page);
            }}
          >
            Retry
          </button>
        </div>
      )}

      <div className="case-brain-meta">
        {loading ? (
          <span className="case-brain-meta-text">Loading...</span>
        ) : (
          <span className="case-brain-meta-text">
            {total === 0
              ? 'No entries found.'
              : `Showing ${page * PAGE_SIZE + 1}–${Math.min((page + 1) * PAGE_SIZE, total)} of ${total}`}
          </span>
        )}
      </div>

      {!loading && !error && total === 0 && filtersActive && (
        <div className="empty-state">
          No Case Brain entries match the current filters.
        </div>
      )}

      {!loading && !error && total > 0 && (
        <div className="case-brain-table-wrap">
          <table className="data-table case-brain-table">
            <thead>
              <tr>
                <th>Occurred</th>
                <th>Matter</th>
                <th>Email</th>
                <th>Source</th>
                <th>Reference</th>
                <th>Actor</th>
                <th>Summary</th>
              </tr>
            </thead>
            <tbody>
              {results.map((entry) => {
                const matterLink = matterHref(entry.matter_key);
                const emailLink = emailHref(entry.email_id);
                return (
                  <tr key={entry.brain_entry_id}>
                    <td>{new Date(entry.occurred_at).toLocaleString()}</td>
                    <td>
                      <Link to={matterLink} className="link">
                        {entry.matter_key}
                      </Link>
                    </td>
                    <td>
                      {emailLink ? (
                        <Link to={emailLink} className="link">
                          {entry.email_id}
                        </Link>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td>
                      <span className={`badge badge-source badge-source-${entry.source_type.toLowerCase()}`}>
                        {entry.source_type}
                      </span>
                    </td>
                    <td>{entry.source_reference || '—'}</td>
                    <td>{entry.source_actor || '—'}</td>
                    <td>{entry.update_summary}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {!loading && !error && total > 0 && (
        <div className="case-brain-pagination">
          <button
            type="button"
            className="btn btn-secondary"
            disabled={isFirstPage}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
          >
            Previous
          </button>
          <span className="case-brain-pagination-label">
            Page {page + 1} of {totalPages}
          </span>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={isLastPage}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </button>
        </div>
      )}

      <p className="case-brain-help">
        <Link to="/" className="link">← Back to Dashboard</Link>
      </p>
    </div>
  );
}
