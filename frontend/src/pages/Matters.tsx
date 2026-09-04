import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { searchMatters } from '../services/api';
import type { MatterSummary } from '../types/matterSearch';
import './Matters.css';

const PAGE_SIZE = 20;
const SEARCH_DEBOUNCE_MS = 300;

// Mirror the statuses the existing backend / data use today.
const STATUS_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'All statuses' },
  { value: 'open', label: 'Open' },
  { value: 'pending', label: 'Pending' },
  { value: 'suspended', label: 'Suspended' },
  { value: 'closed', label: 'Closed' },
];

function statusBadgeClass(status: string): string {
  switch (status.toLowerCase()) {
    case 'open':
      return 'badge badge-status-open';
    case 'closed':
      return 'badge badge-status-closed';
    case 'pending':
      return 'badge badge-status-pending';
    case 'suspended':
      return 'badge badge-status-suspended';
    default:
      return 'badge badge-info';
  }
}

export function Matters() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [practiceArea, setPracticeArea] = useState('');

  const [page, setPage] = useState(0);
  const [results, setResults] = useState<MatterSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Request sequence id — guarantees that an older in-flight request
  // cannot overwrite a newer result set.
  const seqRef = useRef(0);
  const debounceRef = useRef<number | null>(null);
  const cancelledRef = useRef(false);

  // Build the practice-area options from results we have already seen,
  // plus the currently-typed value (so a filter whose results have not
  // arrived yet is still selectable).
  const practiceAreaOptions = useMemo(() => {
    const set = new Set<string>();
    if (practiceArea.trim().length > 0) set.add(practiceArea.trim());
    for (const m of results) {
      if (m.practice_area) set.add(m.practice_area);
    }
    return Array.from(set).sort((a, b) => a.localeCompare(b));
  }, [results, practiceArea]);

  const fetchPage = useCallback(
    async (q: string, status: string, pa: string, pageIndex: number) => {
      const seq = ++seqRef.current;
      setLoading(true);
      setError(null);
      try {
        const resp = await searchMatters(q, status, pa, PAGE_SIZE, pageIndex * PAGE_SIZE);
        if (cancelledRef.current || seq !== seqRef.current) return;
        setResults(resp.matters);
        setTotal(resp.total);
        setLoading(false);
      } catch (err) {
        if (cancelledRef.current || seq !== seqRef.current) return;
        setError(err instanceof Error ? err.message : 'Failed to load matters.');
        setResults([]);
        setTotal(0);
        setLoading(false);
      }
    },
    [],
  );

  // Debounced search: re-fetch when any filter changes. Resets page to 0
  // so the filtered request is for page 0 only — no stale page->N fetch.
  useEffect(() => {
    if (debounceRef.current !== null) {
      window.clearTimeout(debounceRef.current);
    }
    setPage(0);
    debounceRef.current = window.setTimeout(() => {
      void fetchPage(query, statusFilter, practiceArea, 0);
    }, SEARCH_DEBOUNCE_MS);

    return () => {
      if (debounceRef.current !== null) {
        window.clearTimeout(debounceRef.current);
      }
    };
  }, [query, statusFilter, practiceArea, fetchPage]);

  // Page-change fetch (no debounce — direct). Only fires when the user
  // actually changes the page; not when filters change.
  useEffect(() => {
    void fetchPage(query, statusFilter, practiceArea, page);
    // Intentionally only depend on `page` so filter changes do not
    // re-trigger this effect.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  // Cleanup on unmount: invalidate any pending response.
  useEffect(() => {
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
    query.trim().length > 0 || statusFilter !== '' || practiceArea.trim().length > 0;

  return (
    <div className="matters-page">
      <h2>Matters</h2>

      <div className="panel">
        <div className="panel-body">
          <div className="matters-filters">
            <div className="matters-filter-field matters-filter-field-grow">
              <label htmlFor="matters-q">Search</label>
              <input
                id="matters-q"
                type="text"
                placeholder="Search by matter key, client, or matter name"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>

            <div className="matters-filter-field">
              <label htmlFor="matters-status">Status</label>
              <select
                id="matters-status"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                {STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value || 'all'} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="matters-filter-field">
              <label htmlFor="matters-practice-area">Practice Area</label>
              <select
                id="matters-practice-area"
                value={practiceArea}
                onChange={(e) => setPracticeArea(e.target.value)}
              >
                <option value="">All practice areas</option>
                {practiceAreaOptions.map((pa) => (
                  <option key={pa} value={pa}>
                    {pa}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="alert alert-error matters-alert">
          <span>Unable to load matters: {error}</span>
          <button
            type="button"
            className="btn btn-secondary matters-retry"
            onClick={() => {
              void fetchPage(query, statusFilter, practiceArea, page);
            }}
          >
            Retry
          </button>
        </div>
      )}

      <div className="matters-meta">
        {loading ? (
          <span className="matters-meta-text">Loading...</span>
        ) : (
          <span className="matters-meta-text">
            {total === 0
              ? 'No matters found.'
              : `Showing ${page * PAGE_SIZE + 1}–${Math.min((page + 1) * PAGE_SIZE, total)} of ${total}`}
          </span>
        )}
      </div>

      {!loading && !error && total === 0 && filtersActive && (
        <div className="empty-state">
          No matters match the current filters.
        </div>
      )}

      {!loading && !error && total > 0 && (
        <div className="matters-table-wrap">
          <table className="data-table matters-table">
            <thead>
              <tr>
                <th>Matter Key</th>
                <th>Client</th>
                <th>Matter Name</th>
                <th>Practice Area</th>
                <th>Matter Type</th>
                <th>Status</th>
                <th>Primary Attorney</th>
              </tr>
            </thead>
            <tbody>
              {results.map((m) => (
                <tr
                  key={m.matter_key}
                  className="matters-row"
                  onClick={() => navigate(`/matters/${encodeURIComponent(m.matter_key)}`)}
                >
                  <td className="matters-cell-key">{m.matter_key}</td>
                  <td>{m.client_name}</td>
                  <td>{m.matter_name}</td>
                  <td>{m.practice_area || '—'}</td>
                  <td>{m.matter_type || '—'}</td>
                  <td>
                    <span className={statusBadgeClass(m.matter_status)}>
                      {m.matter_status}
                    </span>
                  </td>
                  <td>{m.primary_attorney || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!loading && !error && total > 0 && (
        <div className="matters-pagination">
          <button
            type="button"
            className="btn btn-secondary"
            disabled={isFirstPage}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
          >
            Previous
          </button>
          <span className="matters-pagination-label">
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

      <p className="matters-help">
        <Link to="/" className="link">← Back to Dashboard</Link>
      </p>
    </div>
  );
}
