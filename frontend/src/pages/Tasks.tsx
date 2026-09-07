import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchTasks, createTask, updateTask, searchMatters } from '../services/api';
import type {
  TaskResponse,
  TaskCreate,
  TaskUpdate,
  TaskType,
  TaskStatus,
  TaskPriority,
  ActionOwnerType,
  WaitingOn,
  MatterSummary,
} from '../types';
import './Tasks.css';

const PAGE_SIZE = 50;
const SEARCH_DEBOUNCE_MS = 300;
const MATTER_SEARCH_DEBOUNCE_MS = 300;

const TASK_TYPE_OPTIONS: { value: TaskType; label: string }[] = [
  { value: 'LEGAL', label: 'Legal' },
  { value: 'CLIENT', label: 'Client' },
  { value: 'DOCUMENT', label: 'Document' },
  { value: 'COMMUNICATION', label: 'Communication' },
  { value: 'FOLLOW_UP', label: 'Follow-up' },
  { value: 'FINANCIAL', label: 'Financial' },
  { value: 'ADMINISTRATIVE', label: 'Administrative' },
  { value: 'OTHER', label: 'Other' },
];

const TASK_STATUS_OPTIONS: { value: TaskStatus; label: string }[] = [
  { value: 'OPEN', label: 'Open' },
  { value: 'IN_PROGRESS', label: 'In Progress' },
  { value: 'WAITING', label: 'Waiting' },
  { value: 'COMPLETED', label: 'Completed' },
  { value: 'CANCELLED', label: 'Cancelled' },
];

const TASK_PRIORITY_OPTIONS: { value: TaskPriority; label: string }[] = [
  { value: 'LOW', label: 'Low' },
  { value: 'MEDIUM', label: 'Medium' },
  { value: 'HIGH', label: 'High' },
  { value: 'URGENT', label: 'Urgent' },
];

const ACTION_OWNER_OPTIONS: { value: ActionOwnerType; label: string }[] = [
  { value: 'INTERNAL', label: 'Internal' },
  { value: 'CLIENT', label: 'Client' },
  { value: 'EXTERNAL', label: 'External' },
];

const WAITING_ON_OPTIONS: { value: WaitingOn; label: string }[] = [
  { value: 'CLIENT', label: 'Client' },
  { value: 'OPPOSING_COUNSEL', label: 'Opposing Counsel' },
  { value: 'COURT', label: 'Court' },
  { value: 'GOVERNMENT', label: 'Government' },
  { value: 'PAYMENT', label: 'Payment' },
  { value: 'SIGNATURE', label: 'Signature' },
  { value: 'DOCUMENT', label: 'Document' },
  { value: 'INTERNAL_APPROVAL', label: 'Internal Approval' },
  { value: 'OTHER', label: 'Other' },
];

const QUICK_FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'open', label: 'Open' },
  { key: 'in_progress', label: 'In Progress' },
  { key: 'waiting', label: 'Waiting' },
  { key: 'completed', label: 'Completed' },
  { key: 'overdue', label: 'Overdue' },
  { key: 'due_today', label: 'Due Today' },
] as const;

type QuickFilter = (typeof QUICK_FILTERS)[number]['key'];

const EMPTY_TASK_FORM = {
  matter_key: '',
  title: '',
  description: '',
  task_type: 'LEGAL' as TaskType,
  status: 'OPEN' as TaskStatus,
  priority: 'MEDIUM' as TaskPriority,
  assigned_to: '',
  action_owner_type: 'INTERNAL' as ActionOwnerType,
  waiting_on: '',
  waiting_reason: '',
  due_at: '',
  next_action_at: '',
};

type TaskFormState = typeof EMPTY_TASK_FORM;

function toIsoOrNull(localValue: string): string | null {
  if (!localValue) return null;
  const parsed = new Date(localValue);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toISOString();
}

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString();
}

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

export function Tasks() {
  const [query, setQuery] = useState('');
  const [quickFilter, setQuickFilter] = useState<QuickFilter>('all');
  const [matterFilter, setMatterFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState<TaskStatus | ''>('');
  const [priorityFilter, setPriorityFilter] = useState<TaskPriority | ''>('');
  const [taskTypeFilter, setTaskTypeFilter] = useState<TaskType | ''>('');
  const [actionOwnerFilter, setActionOwnerFilter] = useState<ActionOwnerType | ''>('');
  const [waitingOnFilter, setWaitingOnFilter] = useState<WaitingOn | ''>('');

  const [page, setPage] = useState(0);
  const [results, setResults] = useState<TaskResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showTaskForm, setShowTaskForm] = useState(false);
  const [taskForm, setTaskForm] = useState<TaskFormState>(EMPTY_TASK_FORM);
  const [taskSaving, setTaskSaving] = useState(false);
  const [taskError, setTaskError] = useState<string | null>(null);
  const [taskFieldError, setTaskFieldError] = useState<string | null>(null);
  const [taskSuccess, setTaskSuccess] = useState<string | null>(null);
  const [editingTaskId, setEditingTaskId] = useState<string | null>(null);

  const [matterSearchQuery, setMatterSearchQuery] = useState('');
  const [matterSearchResults, setMatterSearchResults] = useState<MatterSummary[]>([]);
  const [showMatterDropdown, setShowMatterDropdown] = useState(false);
  const [selectedMatterLabel, setSelectedMatterLabel] = useState('');

  const seqRef = useRef(0);
  const debounceRef = useRef<number | null>(null);
  const cancelledRef = useRef(false);
  const matterDebounceRef = useRef<number | null>(null);

  const fetchPage = useCallback(
    async (
      q: string,
      qf: QuickFilter,
      mk: string,
      sf: string,
      pf: string,
      tf: string,
      ao: string,
      wo: string,
      pageIndex: number,
    ) => {
      const seq = ++seqRef.current;
      setLoading(true);
      setError(null);

      let dueFrom: string | undefined;
      let dueTo: string | undefined;

      if (qf === 'overdue') {
        dueTo = getNowIso();
      } else if (qf === 'due_today') {
        dueFrom = getStartOfTodayIso();
        dueTo = getEndOfTodayIso();
      }

      try {
        const resp = await fetchTasks({
          q: q || undefined,
          matterKey: mk || undefined,
          taskType: tf || undefined,
          status: sf || undefined,
          priority: pf || undefined,
          actionOwnerType: ao || undefined,
          waitingOn: wo || undefined,
          dueFrom,
          dueTo,
          limit: PAGE_SIZE,
          offset: pageIndex * PAGE_SIZE,
        });

        let filtered = resp.tasks;
        if (qf === 'overdue') {
          filtered = filtered.filter(
            (t) => t.status !== 'COMPLETED' && t.status !== 'CANCELLED',
          );
        }

        if (cancelledRef.current || seq !== seqRef.current) return;
        setResults(filtered);
        setTotal(resp.total);
        setLoading(false);
      } catch (err) {
        if (cancelledRef.current || seq !== seqRef.current) return;
        setError(err instanceof Error ? err.message : 'Failed to load tasks.');
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
      void fetchPage(
        query,
        quickFilter,
        matterFilter,
        statusFilter,
        priorityFilter,
        taskTypeFilter,
        actionOwnerFilter,
        waitingOnFilter,
        0,
      );
    }, SEARCH_DEBOUNCE_MS);

    return () => {
      if (debounceRef.current !== null) {
        window.clearTimeout(debounceRef.current);
      }
    };
  }, [
    query,
    quickFilter,
    matterFilter,
    statusFilter,
    priorityFilter,
    taskTypeFilter,
    actionOwnerFilter,
    waitingOnFilter,
    fetchPage,
  ]);

  useEffect(() => {
    if (page === 0) return;
    void fetchPage(
      query,
      quickFilter,
      matterFilter,
      statusFilter,
      priorityFilter,
      taskTypeFilter,
      actionOwnerFilter,
      waitingOnFilter,
      page,
    );
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

  useEffect(() => {
    if (matterDebounceRef.current !== null) {
      window.clearTimeout(matterDebounceRef.current);
    }
    const trimmed = matterSearchQuery.trim();
    if (trimmed.length === 0) {
      setMatterSearchResults([]);
      return;
    }

    matterDebounceRef.current = window.setTimeout(async () => {
      try {
        const resp = await searchMatters(trimmed, undefined, undefined, 10, 0);
        setMatterSearchResults(resp.matters);
      } catch {
        setMatterSearchResults([]);
      }
    }, MATTER_SEARCH_DEBOUNCE_MS);

    return () => {
      if (matterDebounceRef.current !== null) {
        window.clearTimeout(matterDebounceRef.current);
      }
    };
  }, [matterSearchQuery]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const isFirstPage = page === 0;
  const isLastPage = page >= totalPages - 1;

  function openTaskForm() {
    setTaskForm(EMPTY_TASK_FORM);
    setTaskError(null);
    setTaskFieldError(null);
    setTaskSuccess(null);
    setEditingTaskId(null);
    setSelectedMatterLabel('');
    setMatterSearchQuery('');
    setMatterSearchResults([]);
    setShowMatterDropdown(false);
    setShowTaskForm(true);
  }

  function openEditTaskForm(task: TaskResponse) {
    setTaskForm({
      matter_key: task.matter_key,
      title: task.title,
      description: task.description || '',
      task_type: task.task_type,
      status: task.status,
      priority: task.priority,
      assigned_to: task.assigned_to || '',
      action_owner_type: task.action_owner_type,
      waiting_on: task.waiting_on || '',
      waiting_reason: task.waiting_reason || '',
      due_at: task.due_at ? task.due_at.slice(0, 16) : '',
      next_action_at: task.next_action_at ? task.next_action_at.slice(0, 16) : '',
    });
    setTaskError(null);
    setTaskFieldError(null);
    setTaskSuccess(null);
    setEditingTaskId(task.task_id);
    setSelectedMatterLabel(task.matter_key);
    setMatterSearchQuery(task.matter_key);
    setShowTaskForm(true);
  }

  function closeTaskForm() {
    if (taskSaving) return;
    setShowTaskForm(false);
    setEditingTaskId(null);
  }

  function selectMatter(matter: MatterSummary) {
    setTaskForm({ ...taskForm, matter_key: matter.matter_key });
    setSelectedMatterLabel(`${matter.matter_key} — ${matter.client_name} / ${matter.matter_name}`);
    setMatterSearchQuery(matter.matter_key);
    setMatterSearchResults([]);
    setShowMatterDropdown(false);
  }

  async function reloadTasks() {
    setPage(0);
    setQuickFilter((prev) => prev);
  }

  async function handleTaskSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (taskSaving) return;

    const title = taskForm.title.trim();
    if (!title) {
      setTaskFieldError('Title is required.');
      return;
    }

    if (!taskForm.matter_key.trim()) {
      setTaskFieldError('Matter key is required.');
      return;
    }

    if (taskForm.status === 'WAITING' && !taskForm.waiting_on) {
      setTaskFieldError('waiting_on is required when status is WAITING.');
      return;
    }

    const waitingOnValue = taskForm.waiting_on || null;

    setTaskSaving(true);
    setTaskError(null);
    setTaskFieldError(null);
    setTaskSuccess(null);

    try {
      if (editingTaskId) {
        const updatePayload: TaskUpdate = {
          title,
          description: taskForm.description.trim() || null,
          task_type: taskForm.task_type,
          status: taskForm.status,
          priority: taskForm.priority,
          assigned_to: taskForm.assigned_to || null,
          action_owner_type: taskForm.action_owner_type,
          waiting_on: waitingOnValue as WaitingOn | null,
          waiting_reason: taskForm.waiting_reason.trim() || null,
          due_at: toIsoOrNull(taskForm.due_at),
          next_action_at: toIsoOrNull(taskForm.next_action_at),
        };
        await updateTask(editingTaskId, updatePayload);
        setTaskSuccess('Task updated.');
      } else {
        const payload: TaskCreate = {
          matter_key: taskForm.matter_key.trim(),
          title,
          description: taskForm.description.trim() || null,
          task_type: taskForm.task_type,
          status: taskForm.status,
          priority: taskForm.priority,
          assigned_to: taskForm.assigned_to || null,
          action_owner_type: taskForm.action_owner_type,
          waiting_on: waitingOnValue as WaitingOn | null,
          waiting_reason: taskForm.waiting_reason.trim() || null,
          waiting_since: null,
          due_at: toIsoOrNull(taskForm.due_at),
          next_action_at: toIsoOrNull(taskForm.next_action_at),
        };
        await createTask(payload);
        setTaskSuccess('Task created.');
      }
      setShowTaskForm(false);
      setTaskForm(EMPTY_TASK_FORM);
      setEditingTaskId(null);
      setSelectedMatterLabel('');
      setMatterSearchQuery('');
      await reloadTasks();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to save task.';
      setTaskError(message);
    } finally {
      setTaskSaving(false);
    }
  }

  function getStatusBadgeClass(status: TaskStatus): string {
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

  function getPriorityBadgeClass(priority: TaskPriority): string {
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

  function getEmptyMessage(): string {
    if (quickFilter === 'overdue') return 'No overdue tasks.';
    if (quickFilter === 'due_today') return 'No tasks due today.';
    if (quickFilter === 'completed') return 'No completed tasks.';
    if (quickFilter === 'waiting') return 'No waiting tasks.';
    if (quickFilter === 'in_progress') return 'No in-progress tasks.';
    if (quickFilter === 'open') return 'No open tasks.';
    return 'No tasks found.';
  }

  return (
    <div className="tasks-page">
      <div className="page-header">
        <h2>Tasks</h2>
        {!showTaskForm && (
          <button type="button" className="btn btn-primary" onClick={openTaskForm}>
            Add Task
          </button>
        )}
      </div>

      {taskSuccess && !showTaskForm && (
        <div className="alert alert-success" role="status">
          {taskSuccess}
        </div>
      )}

      <div className="quick-filters">
        {QUICK_FILTERS.map((qf) => (
          <button
            key={qf.key}
            type="button"
            className={`quick-filter-btn ${quickFilter === qf.key ? 'active' : ''}`}
            onClick={() => setQuickFilter(qf.key)}
          >
            {qf.label}
          </button>
        ))}
      </div>

      <div className="panel">
        <div className="panel-body">
          <div className="tasks-filters">
            <div className="tasks-filter-field tasks-filter-field-grow">
              <label htmlFor="tasks-q">Search</label>
              <input
                id="tasks-q"
                type="text"
                placeholder="Search tasks..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>

            <div className="tasks-filter-field">
              <label htmlFor="tasks-matter">Matter</label>
              <input
                id="tasks-matter"
                type="text"
                placeholder="Filter by matter key"
                value={matterFilter}
                onChange={(e) => setMatterFilter(e.target.value)}
              />
            </div>

            <div className="tasks-filter-field">
              <label htmlFor="tasks-status">Status</label>
              <select
                id="tasks-status"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as TaskStatus | '')}
              >
                <option value="">All</option>
                {TASK_STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="tasks-filter-field">
              <label htmlFor="tasks-priority">Priority</label>
              <select
                id="tasks-priority"
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value as TaskPriority | '')}
              >
                <option value="">All</option>
                {TASK_PRIORITY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="tasks-filter-field">
              <label htmlFor="tasks-type">Type</label>
              <select
                id="tasks-type"
                value={taskTypeFilter}
                onChange={(e) => setTaskTypeFilter(e.target.value as TaskType | '')}
              >
                <option value="">All</option>
                {TASK_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="tasks-filter-field">
              <label htmlFor="tasks-owner">Action Owner</label>
              <select
                id="tasks-owner"
                value={actionOwnerFilter}
                onChange={(e) => setActionOwnerFilter(e.target.value as ActionOwnerType | '')}
              >
                <option value="">All</option>
                {ACTION_OWNER_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="tasks-filter-field">
              <label htmlFor="tasks-waiting">Waiting On</label>
              <select
                id="tasks-waiting"
                value={waitingOnFilter}
                onChange={(e) => setWaitingOnFilter(e.target.value as WaitingOn | '')}
              >
                <option value="">All</option>
                {WAITING_ON_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {showTaskForm && (
        <form className="entry-form task-form" onSubmit={handleTaskSubmit} noValidate>
          {taskError && (
            <div className="alert alert-error entry-form-alert">{taskError}</div>
          )}

          <div className="entry-form-grid">
            <div className="entry-form-field entry-form-field-wide">
              <label htmlFor="task-matter-search">
                Matter <span className="required-mark">*</span>
              </label>
              <input
                id="task-matter-search"
                type="text"
                value={matterSearchQuery}
                onChange={(e) => {
                  setMatterSearchQuery(e.target.value);
                  setShowMatterDropdown(true);
                }}
                onFocus={() => {
                  if (matterSearchResults.length > 0) setShowMatterDropdown(true);
                }}
                disabled={taskSaving || editingTaskId !== null}
                placeholder="Search matters by key, client, or name"
                autoComplete="off"
              />
              {taskFieldError && taskFieldError.toLowerCase().includes('matter') && (
                <span className="field-error">{taskFieldError}</span>
              )}
              {showMatterDropdown && matterSearchResults.length > 0 && (
                <div className="matter-dropdown">
                  {matterSearchResults.map((m) => (
                    <div
                      key={m.matter_key}
                      className="matter-dropdown-item"
                      onMouseDown={() => selectMatter(m)}
                    >
                      <span className="matter-dropdown-key">{m.matter_key}</span>
                      <span className="matter-dropdown-name">
                        {m.client_name} / {m.matter_name}
                      </span>
                    </div>
                  ))}
                </div>
              )}
              {selectedMatterLabel && (
                <span className="matter-selected-label">Selected: {selectedMatterLabel}</span>
              )}
            </div>

            <div className="entry-form-field entry-form-field-wide">
              <label htmlFor="task-title">
                Title <span className="required-mark">*</span>
              </label>
              <input
                id="task-title"
                type="text"
                value={taskForm.title}
                onChange={(e) => {
                  setTaskForm({ ...taskForm, title: e.target.value });
                  if (taskFieldError) setTaskFieldError(null);
                }}
                disabled={taskSaving}
                placeholder="e.g. Review draft agreement"
              />
              {taskFieldError && taskFieldError.toLowerCase().includes('title') && (
                <span className="field-error">{taskFieldError}</span>
              )}
            </div>

            <div className="entry-form-field">
              <label htmlFor="task-type">Type</label>
              <select
                id="task-type"
                value={taskForm.task_type}
                onChange={(e) => setTaskForm({ ...taskForm, task_type: e.target.value as TaskType })}
                disabled={taskSaving}
              >
                {TASK_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="entry-form-field">
              <label htmlFor="task-status">Status</label>
              <select
                id="task-status"
                value={taskForm.status}
                onChange={(e) => {
                  const newStatus = e.target.value as TaskStatus;
                  setTaskForm({ ...taskForm, status: newStatus });
                  if (newStatus !== 'WAITING') {
                    setTaskForm((prev) => ({ ...prev, status: newStatus, waiting_on: '' }));
                  }
                  if (taskFieldError) setTaskFieldError(null);
                }}
                disabled={taskSaving}
              >
                {TASK_STATUS_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="entry-form-field">
              <label htmlFor="task-priority">Priority</label>
              <select
                id="task-priority"
                value={taskForm.priority}
                onChange={(e) => setTaskForm({ ...taskForm, priority: e.target.value as TaskPriority })}
                disabled={taskSaving}
              >
                {TASK_PRIORITY_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="entry-form-field">
              <label htmlFor="task-assigned">Assigned To (UUID)</label>
              <input
                id="task-assigned"
                type="text"
                value={taskForm.assigned_to}
                onChange={(e) => setTaskForm({ ...taskForm, assigned_to: e.target.value })}
                disabled={taskSaving}
                placeholder="Optional UUID"
              />
            </div>

            <div className="entry-form-field">
              <label htmlFor="task-action-owner">Action Owner</label>
              <select
                id="task-action-owner"
                value={taskForm.action_owner_type}
                onChange={(e) => setTaskForm({ ...taskForm, action_owner_type: e.target.value as ActionOwnerType })}
                disabled={taskSaving}
              >
                {ACTION_OWNER_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="entry-form-field">
              <label htmlFor="task-waiting-on">Waiting On</label>
              <select
                id="task-waiting-on"
                value={taskForm.waiting_on}
                onChange={(e) => setTaskForm({ ...taskForm, waiting_on: e.target.value as WaitingOn | '' })}
                disabled={taskSaving}
              >
                <option value="">—</option>
                {WAITING_ON_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="entry-form-field">
              <label htmlFor="task-due">Due At</label>
              <input
                id="task-due"
                type="datetime-local"
                value={taskForm.due_at}
                onChange={(e) => setTaskForm({ ...taskForm, due_at: e.target.value })}
                disabled={taskSaving}
              />
            </div>

            <div className="entry-form-field">
              <label htmlFor="task-next-action">Next Action At</label>
              <input
                id="task-next-action"
                type="datetime-local"
                value={taskForm.next_action_at}
                onChange={(e) => setTaskForm({ ...taskForm, next_action_at: e.target.value })}
                disabled={taskSaving}
              />
            </div>

            <div className="entry-form-field entry-form-field-wide">
              <label htmlFor="task-description">Description</label>
              <textarea
                id="task-description"
                rows={3}
                value={taskForm.description}
                onChange={(e) => setTaskForm({ ...taskForm, description: e.target.value })}
                disabled={taskSaving}
                placeholder="Optional details..."
              />
            </div>
          </div>

          <div className="entry-form-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={closeTaskForm}
              disabled={taskSaving}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={taskSaving}
            >
              {taskSaving ? 'Saving...' : editingTaskId ? 'Update Task' : 'Add Task'}
            </button>
          </div>
        </form>
      )}

      {error && (
        <div className="alert alert-error">
          <span>{error}</span>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() =>
              fetchPage(
                query,
                quickFilter,
                matterFilter,
                statusFilter,
                priorityFilter,
                taskTypeFilter,
                actionOwnerFilter,
                waitingOnFilter,
                page,
              )
            }
          >
            Retry
          </button>
        </div>
      )}

      {loading ? (
        <p>Loading tasks...</p>
      ) : results.length === 0 ? (
        <p className="empty-state">{getEmptyMessage()}</p>
      ) : (
        <>
          <div className="task-table-wrap">
            <table className="data-table task-table">
              <thead>
                <tr>
                  <th>Task</th>
                  <th>Matter</th>
                  <th>Status</th>
                  <th>Priority</th>
                  <th>Type</th>
                  <th>Owner</th>
                  <th>Waiting On</th>
                  <th>Due</th>
                  <th>Next Action</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {results.map((task) => (
                  <tr key={task.task_id}>
                  <td>
                    <Link to={`/tasks/${encodeURIComponent(task.task_id)}`} className="link task-title-link">
                      {task.title}
                    </Link>
                    {task.description && (
                      <span className="task-description-hint" title={task.description}>
                        💬
                      </span>
                    )}
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
                    <td>{task.task_type.replace('_', ' ')}</td>
                    <td>{task.action_owner_type}</td>
                    <td>
                      {task.status === 'WAITING' && task.waiting_on ? (
                        <span className="task-waiting-badge">{task.waiting_on.replace('_', ' ')}</span>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td>{formatDate(task.due_at)}</td>
                    <td>{formatDate(task.next_action_at)}</td>
                    <td>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={() => openEditTaskForm(task)}
                      >
                        Edit
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="tasks-pagination">
            <button
              type="button"
              className="btn btn-secondary"
              disabled={isFirstPage}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
            >
              Previous
            </button>
            <span className="tasks-pagination-label">
              {total === 0
                ? 'No tasks'
                : `Showing ${page * PAGE_SIZE + 1}–${Math.min((page + 1) * PAGE_SIZE, total)} of ${total}`}
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
        </>
      )}
    </div>
  );
}
