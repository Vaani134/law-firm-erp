import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  fetchReviewQueue,
  searchCaseBrain,
  searchMatters,
  fetchTasks,
} from '../services/api';
import type {
  CaseBrainSearchEntry,
  ReviewQueueEmail,
  TaskResponse,
} from '../types';
import './Dashboard.css';

function getStartOfTodayIso(): string {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return start.toISOString();
}

function getEndOfTodayIso(): string {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const end = new Date(start);
  end.setDate(end.getDate() + 1);
  return end.toISOString();
}

function getNowIso(): string {
  return new Date().toISOString();
}

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString();
}

function getStatusBadgeClass(status: string): string {
  switch (status) {
    case 'OPEN':
      return 'badge-task-open';
    case 'IN_PROGRESS':
      return 'badge-task-in-progress';
    case 'WAITING':
      return 'badge-task-waiting';
    case 'COMPLETED':
      return 'badge-task-completed';
    case 'CANCELLED':
      return 'badge-task-cancelled';
    default:
      return 'badge-info';
  }
}

function getPriorityBadgeClass(priority: string): string {
  switch (priority) {
    case 'LOW':
      return 'badge-task-low';
    case 'MEDIUM':
      return 'badge-task-medium';
    case 'HIGH':
      return 'badge-task-high';
    case 'URGENT':
      return 'badge-task-urgent';
    default:
      return 'badge-info';
  }
}

function filterActionable(tasks: TaskResponse[]): TaskResponse[] {
  return tasks.filter(
    (t) => t.status !== 'COMPLETED' && t.status !== 'CANCELLED',
  );
}

export function Dashboard() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [refreshing, setRefreshing] = useState(false);

  const [matterCounts, setMatterCounts] = useState({
    total: 0,
    open: 0,
    closed: 0,
    pending: 0,
    suspended: 0,
  });
  const [matterLoading, setMatterLoading] = useState(true);
  const [matterError, setMatterError] = useState<string | null>(null);

  const [taskCounts, setTaskCounts] = useState({
    dueToday: 0,
    overdue: 0,
    waiting: 0,
  });
  const [taskLoading, setTaskLoading] = useState(true);
  const [taskError, setTaskError] = useState<string | null>(null);

  const [reviewQueue, setReviewQueue] = useState<ReviewQueueEmail[]>([]);
  const [reviewLoading, setReviewLoading] = useState(true);
  const [reviewError, setReviewError] = useState<string | null>(null);

  const [recentCaseBrain, setRecentCaseBrain] = useState<CaseBrainSearchEntry[]>([]);
  const [caseBrainLoading, setCaseBrainLoading] = useState(true);
  const [caseBrainError, setCaseBrainError] = useState<string | null>(null);

  const [attentionTasks, setAttentionTasks] = useState<TaskResponse[]>([]);
  const [attentionLoading, setAttentionLoading] = useState(true);
  const [attentionError, setAttentionError] = useState<string | null>(null);

  const loadDashboard = useCallback(async () => {
    const nowISO = getNowIso();
    const todayStart = getStartOfTodayIso();
    const todayEnd = getEndOfTodayIso();

    const [
      totalMatters,
      openMatters,
      closedMatters,
      pendingMatters,
      suspendedMatters,
      dueTodayTasksPage,
      overdueTasksPage,
      waitingTasksPage,
      reviewData,
      recentCaseBrainData,
      overdueAttention,
      todayAttention,
      waitingAttention,
    ] = await Promise.all([
      searchMatters('', '', '', 1, 0),
      searchMatters('', 'open', '', 1, 0),
      searchMatters('', 'closed', '', 1, 0),
      searchMatters('', 'pending', '', 1, 0),
      searchMatters('', 'suspended', '', 1, 0),
      fetchTasks({ dueFrom: todayStart, dueTo: todayEnd, limit: 100, offset: 0 }),
      fetchTasks({ dueTo: nowISO, limit: 100, offset: 0 }),
      fetchTasks({ status: 'WAITING', limit: 100, offset: 0 }),
      fetchReviewQueue(),
      searchCaseBrain({ limit: 5, offset: 0 }),
      fetchTasks({ dueTo: nowISO, limit: 5, offset: 0 }),
      fetchTasks({ dueFrom: todayStart, dueTo: todayEnd, limit: 5, offset: 0 }),
      fetchTasks({ status: 'WAITING', limit: 5, offset: 0 }),
    ]);

    const actionableOverdue = filterActionable(overdueTasksPage.tasks);
    const actionableToday = filterActionable(dueTodayTasksPage.tasks);
    const actionableWaiting = filterActionable(waitingTasksPage.tasks);

    setMatterCounts({
      total: totalMatters.total,
      open: openMatters.total,
      closed: closedMatters.total,
      pending: pendingMatters.total,
      suspended: suspendedMatters.total,
    });
    setMatterLoading(false);
    setMatterError(null);

    setTaskCounts({
      dueToday: actionableToday.length,
      overdue: actionableOverdue.length,
      waiting: actionableWaiting.length,
    });
    setTaskLoading(false);
    setTaskError(null);

    setReviewQueue(reviewData.emails.slice(0, 5));
    setReviewLoading(false);
    setReviewError(null);

    setRecentCaseBrain(recentCaseBrainData.entries);
    setCaseBrainLoading(false);
    setCaseBrainError(null);

    const attentionOverdue = filterActionable(overdueAttention.tasks);
    const attentionToday = filterActionable(todayAttention.tasks);
    const attentionWaiting = filterActionable(waitingAttention.tasks);

    const combined = [
      ...attentionOverdue.map((t) => ({ ...t, _category: 'overdue' as const })),
      ...attentionToday.map((t) => ({ ...t, _category: 'today' as const })),
      ...attentionWaiting.map((t) => ({ ...t, _category: 'waiting' as const })),
    ];

    const seen = new Set<string>();
    const unique = combined.filter((t) => {
      if (seen.has(t.task_id)) return false;
      seen.add(t.task_id);
      return true;
    });

    const categoryOrder = { overdue: 0, today: 1, waiting: 2 };
    unique.sort((a, b) => {
      const catDiff = categoryOrder[a._category] - categoryOrder[b._category];
      if (catDiff !== 0) return catDiff;

      if (a.due_at && b.due_at) {
        return new Date(a.due_at).getTime() - new Date(b.due_at).getTime();
      }
      if (a.due_at) return -1;
      if (b.due_at) return 1;

      const priorityOrder = { URGENT: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
      return priorityOrder[a.priority] - priorityOrder[b.priority];
    });

    setAttentionTasks(unique.slice(0, 10));
    setAttentionLoading(false);
    setAttentionError(null);
  }, []);

  useEffect(() => {
    let cancelled = false;
    setMatterLoading(true);
    setTaskLoading(true);
    setReviewLoading(true);
    setCaseBrainLoading(true);
    setAttentionLoading(true);

    loadDashboard().then(() => {
      if (!cancelled) {
        setRefreshing(false);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [refreshKey, loadDashboard]);

  const handleRefresh = () => {
    setRefreshing(true);
    setRefreshKey((k) => k + 1);
  };

  const todayLabel = new Date().toLocaleDateString(undefined, {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div className="dashboard-header-text">
          <h2>Dashboard</h2>
          <p className="dashboard-subtitle">Firm-wide overview of work requiring attention.</p>
          <p className="dashboard-date">{todayLabel}</p>
        </div>
        <button
          type="button"
          className="btn btn-secondary dashboard-refresh"
          onClick={handleRefresh}
          disabled={refreshing}
        >
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {(matterError || taskError || reviewError || caseBrainError || attentionError) && (
        <div className="alert alert-error">
          One or more dashboard sections failed to load. Details are shown within each section.
        </div>
      )}

      <div className="dashboard-stats">
        <div className="stat-card">
          <div className="stat-label">Open Matters</div>
          <div className="stat-value">
            {matterLoading ? '—' : matterError ? '!' : matterCounts.open}
          </div>
          {!matterLoading && !matterError && (
            <Link to="/matters" className="link">View matters</Link>
          )}
        </div>

        <div className="stat-card">
          <div className="stat-label">Tasks Due Today</div>
          <div className="stat-value">
            {taskLoading ? '—' : taskError ? '!' : taskCounts.dueToday}
          </div>
          {!taskLoading && !taskError && (
            <Link to="/tasks" className="link">View tasks</Link>
          )}
        </div>

        <div className="stat-card">
          <div className="stat-label">Overdue Tasks</div>
          <div className="stat-value">
            {taskLoading ? '—' : taskError ? '!' : taskCounts.overdue}
          </div>
          {!taskLoading && !taskError && (
            <Link to="/tasks" className="link">View tasks</Link>
          )}
        </div>

        <div className="stat-card">
          <div className="stat-label">Waiting Tasks</div>
          <div className="stat-value">
            {taskLoading ? '—' : taskError ? '!' : taskCounts.waiting}
          </div>
          {!taskLoading && !taskError && (
            <Link to="/tasks" className="link">View tasks</Link>
          )}
        </div>

        <div className="stat-card">
          <div className="stat-label">Review Required</div>
          <div className="stat-value">
            {reviewLoading ? '—' : reviewError ? '!' : reviewQueue.length}
          </div>
          {!reviewLoading && !reviewError && reviewQueue.length > 0 && (
            <Link to="/review-queue" className="link">Review now</Link>
          )}
        </div>
      </div>

      <div className="dashboard-section">
        <div className="panel">
          <div className="panel-header">
            <h3>Tasks Requiring Attention</h3>
            <Link to="/tasks" className="link">View all tasks</Link>
          </div>
          <div className="panel-body">
            {attentionLoading && <p>Loading tasks...</p>}
            {!attentionLoading && attentionError && (
              <div className="alert alert-error">
                Unable to load tasks: {attentionError}
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setRefreshKey((k) => k + 1)}
                >
                  Retry
                </button>
              </div>
            )}
            {!attentionLoading && !attentionError && attentionTasks.length === 0 && (
              <p className="empty-state-text">You're clear — no tasks require immediate attention.</p>
            )}
            {!attentionLoading && !attentionError && attentionTasks.length > 0 && (
              <div className="dashboard-table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Task</th>
                      <th>Matter</th>
                      <th>Status</th>
                      <th>Priority</th>
                      <th>Due</th>
                      <th>Next Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {attentionTasks.map((task) => (
                      <tr key={task.task_id}>
                        <td>
                          <Link to={`/tasks/${encodeURIComponent(task.task_id)}`} className="link">
                            {task.title}
                          </Link>
                        </td>
                        <td>
                          <Link to={`/matters/${encodeURIComponent(task.matter_key)}`} className="link">
                            {task.matter_key}
                          </Link>
                        </td>
                        <td>
                          <span className={`badge ${getStatusBadgeClass(task.status)}`}>
                            {task.status.replace('_', ' ')}
                          </span>
                        </td>
                        <td>
                          <span className={`badge ${getPriorityBadgeClass(task.priority)}`}>
                            {task.priority}
                          </span>
                        </td>
                        <td>{formatDate(task.due_at)}</td>
                        <td>{formatDate(task.next_action_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="dashboard-grid">
        <div className="dashboard-section">
          <div className="panel">
            <div className="panel-header">
              <h3>Review Required</h3>
              <Link to="/review-queue" className="link">View review queue</Link>
            </div>
            <div className="panel-body">
              {reviewLoading && <p>Loading...</p>}
              {!reviewLoading && reviewError && (
                <div className="alert alert-error">
                  Unable to load review queue: {reviewError}
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => setRefreshKey((k) => k + 1)}
                  >
                    Retry
                  </button>
                </div>
              )}
              {!reviewLoading && !reviewError && reviewQueue.length === 0 && (
                <p className="empty-state-text">No emails currently require review.</p>
              )}
              {!reviewLoading && !reviewError && reviewQueue.length > 0 && (
                <div className="dashboard-table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Subject</th>
                        <th>Sender</th>
                        <th>Received</th>
                      </tr>
                    </thead>
                    <tbody>
                      {reviewQueue.map((email) => (
                        <tr key={email.email_id}>
                          <td>
                            <Link to={`/email/${email.email_id}`} className="link">
                              {email.subject || '(no subject)'}
                            </Link>
                          </td>
                          <td>{email.sender}</td>
                          <td>{formatDate(email.received_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="dashboard-section">
          <div className="panel">
            <div className="panel-header">
              <h3>Recent Case Brain Activity</h3>
              <Link to="/case-brain" className="link">View Case Brain</Link>
            </div>
            <div className="panel-body">
              {caseBrainLoading && <p>Loading...</p>}
              {!caseBrainLoading && caseBrainError && (
                <div className="alert alert-error">
                  Unable to load Case Brain: {caseBrainError}
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => setRefreshKey((k) => k + 1)}
                  >
                    Retry
                  </button>
                </div>
              )}
              {!caseBrainLoading && !caseBrainError && recentCaseBrain.length === 0 && (
                <p className="empty-state-text">No recent Case Brain activity.</p>
              )}
              {!caseBrainLoading && !caseBrainError && recentCaseBrain.length > 0 && (
                <div className="case-brain-timeline">
                  {recentCaseBrain.map((entry) => (
                    <div key={entry.brain_entry_id} className="case-brain-timeline-entry">
                      <div className="case-brain-timeline-header">
                        <span className={`badge badge-source badge-source-${entry.source_type.toLowerCase()}`}>
                          {entry.source_type}
                        </span>
                        <span className="case-brain-timeline-time">
                          {formatDate(entry.occurred_at)}
                        </span>
                      </div>
                      <div className="case-brain-timeline-body">
                        <Link to={`/matters/${encodeURIComponent(entry.matter_key)}`} className="link case-brain-timeline-matter">
                          {entry.matter_key}
                        </Link>
                        <p className="case-brain-timeline-summary">{entry.update_summary}</p>
                        {entry.email_id && (
                          <Link to={`/email/${entry.email_id}`} className="link case-brain-timeline-email">
                            Email {entry.email_id}
                          </Link>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="dashboard-section">
        <div className="panel">
          <div className="panel-header">
            <h3>Matter Overview</h3>
            <Link to="/matters" className="link">View all matters</Link>
          </div>
          <div className="panel-body">
            {matterLoading && <p>Loading matters...</p>}
            {!matterLoading && matterError && (
              <div className="alert alert-error">
                Unable to load matters: {matterError}
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setRefreshKey((k) => k + 1)}
                >
                  Retry
                </button>
              </div>
            )}
            {!matterLoading && !matterError && (
              <div className="matter-overview-grid">
                <div className="matter-overview-item">
                  <span className="matter-overview-label">Total</span>
                  <span className="matter-overview-value">{matterCounts.total}</span>
                </div>
                <div className="matter-overview-item">
                  <span className="matter-overview-label">Open</span>
                  <span className="matter-overview-value matter-overview-open">{matterCounts.open}</span>
                </div>
                <div className="matter-overview-item">
                  <span className="matter-overview-label">Closed</span>
                  <span className="matter-overview-value matter-overview-closed">{matterCounts.closed}</span>
                </div>
                <div className="matter-overview-item">
                  <span className="matter-overview-label">Pending</span>
                  <span className="matter-overview-value matter-overview-pending">{matterCounts.pending}</span>
                </div>
                <div className="matter-overview-item">
                  <span className="matter-overview-label">Suspended</span>
                  <span className="matter-overview-value matter-overview-suspended">{matterCounts.suspended}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
