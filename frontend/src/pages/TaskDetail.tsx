import { useEffect, useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { fetchTask, updateTask, searchMatters } from '../services/api';
import type {
  TaskResponse,
  TaskUpdate,
  TaskType,
  TaskStatus,
  TaskPriority,
  ActionOwnerType,
  WaitingOn,
  MatterSummary,
} from '../types';
import './TaskDetail.css';

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

export function TaskDetail() {
  const { taskId } = useParams<{ taskId: string | undefined }>();
  const navigate = useNavigate();
  const [task, setTask] = useState<TaskResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  const [showEditForm, setShowEditForm] = useState(false);
  const [taskForm, setTaskForm] = useState<TaskFormState>(EMPTY_TASK_FORM);
  const [taskSaving, setTaskSaving] = useState(false);
  const [taskError, setTaskError] = useState<string | null>(null);
  const [taskFieldError, setTaskFieldError] = useState<string | null>(null);
  const [taskSuccess, setTaskSuccess] = useState<string | null>(null);

  const [showWaitingForm, setShowWaitingForm] = useState(false);
  const [waitingForm, setWaitingForm] = useState({ waiting_on: '', waiting_reason: '' });
  const [waitingSaving, setWaitingSaving] = useState(false);
  const [waitingError, setWaitingError] = useState<string | null>(null);

  const [matterSearchQuery, setMatterSearchQuery] = useState('');
  const [matterSearchResults, setMatterSearchResults] = useState<MatterSummary[]>([]);
  const [showMatterDropdown, setShowMatterDropdown] = useState(false);
  const [selectedMatterLabel, setSelectedMatterLabel] = useState('');

  useEffect(() => {
    if (!taskId) return;

    let cancelled = false;
    setLoading(true);
    setError(null);
    setNotFound(false);

    async function load() {
      try {
        const data = await fetchTask(taskId);
        if (!cancelled) {
          setTask(data);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : 'Failed to load task.';
          if (message.includes('404') || message.toLowerCase().includes('not found')) {
            setNotFound(true);
          } else {
            setError(message);
          }
          setLoading(false);
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [taskId]);

  useEffect(() => {
    const trimmed = matterSearchQuery.trim();
    if (trimmed.length === 0) {
      setMatterSearchResults([]);
      return;
    }

    const timeout = setTimeout(async () => {
      try {
        const resp = await searchMatters(trimmed, undefined, undefined, 10, 0);
        setMatterSearchResults(resp.matters);
      } catch {
        setMatterSearchResults([]);
      }
    }, 300);

    return () => clearTimeout(timeout);
  }, [matterSearchQuery]);

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

  function openEditForm() {
    if (!task) return;
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
    setSelectedMatterLabel(task.matter_key);
    setMatterSearchQuery(task.matter_key);
    setTaskError(null);
    setTaskFieldError(null);
    setTaskSuccess(null);
    setShowEditForm(true);
    setShowWaitingForm(false);
  }

  function closeEditForm() {
    if (taskSaving) return;
    setShowEditForm(false);
  }

  function openWaitingForm() {
    if (!task) return;
    setWaitingForm({
      waiting_on: task.waiting_on || '',
      waiting_reason: task.waiting_reason || '',
    });
    setWaitingError(null);
    setShowWaitingForm(true);
    setShowEditForm(false);
  }

  function closeWaitingForm() {
    if (waitingSaving) return;
    setShowWaitingForm(false);
  }

  async function handleEditSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (taskSaving || !task) return;

    const title = taskForm.title.trim();
    if (!title) {
      setTaskFieldError('Title is required.');
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
      const payload: TaskUpdate = {
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
      const updated = await updateTask(task.task_id, payload);
      setTask(updated);
      setTaskSuccess('Task updated.');
      setShowEditForm(false);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update task.';
      setTaskError(message);
    } finally {
      setTaskSaving(false);
    }
  }

  async function handleWaitingSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (waitingSaving || !task) return;

    if (!waitingForm.waiting_on) {
      setWaitingError('waiting_on is required.');
      return;
    }

    setWaitingSaving(true);
    setWaitingError(null);

    try {
      const payload: TaskUpdate = {
        status: 'WAITING',
        waiting_on: waitingForm.waiting_on as WaitingOn,
        waiting_reason: waitingForm.waiting_reason.trim() || null,
      };
      const updated = await updateTask(task.task_id, payload);
      setTask(updated);
      setShowWaitingForm(false);
      setTaskSuccess('Task marked as waiting.');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update task.';
      setWaitingError(message);
    } finally {
      setWaitingSaving(false);
    }
  }

  async function handleStatusTransition(newStatus: TaskStatus) {
    if (waitingSaving || taskSaving || !task) return;

    const payload: TaskUpdate = { status: newStatus };
    if (newStatus !== 'WAITING') {
      payload.waiting_on = null;
      payload.waiting_reason = null;
    }

    setTaskSaving(true);
    setTaskError(null);
    setTaskSuccess(null);

    try {
      const updated = await updateTask(task.task_id, payload);
      setTask(updated);
      setTaskSuccess(`Task marked as ${newStatus.replace('_', ' ').toLowerCase()}.`);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update task.';
      setTaskError(message);
    } finally {
      setTaskSaving(false);
    }
  }

  function selectMatter(matter: MatterSummary) {
    setTaskForm({ ...taskForm, matter_key: matter.matter_key });
    setSelectedMatterLabel(`${matter.matter_key} — ${matter.client_name} / ${matter.matter_name}`);
    setMatterSearchQuery(matter.matter_key);
    setMatterSearchResults([]);
    setShowMatterDropdown(false);
  }

  if (!taskId) {
    return (
      <div className="task-detail-page">
        <div className="alert alert-error">Missing task ID.</div>
      </div>
    );
  }

  if (loading) {
    return <div className="task-detail-page">Loading task...</div>;
  }

  if (notFound || !task) {
    return (
      <div className="task-detail-page">
        <div className="alert alert-error">
          {notFound ? 'Task not found.' : error || 'Failed to load task.'}
        </div>
        <Link to="/tasks" className="link">← Back to Tasks</Link>
      </div>
    );
  }

  const breadcrumb = (
    <div className="task-detail-breadcrumb">
      <Link to="/tasks" className="link">Tasks</Link>
      {task.matter_key && (
        <>
          <span className="breadcrumb-separator">/</span>
          <Link to={`/matters/${encodeURIComponent(task.matter_key)}`} className="link">
            Matter {task.matter_key}
          </Link>
        </>
      )}
      <span className="breadcrumb-separator">/</span>
      <span className="breadcrumb-current">{task.title}</span>
    </div>
  );

  const isWaiting = task.status === 'WAITING';
  const isCompleted = task.status === 'COMPLETED';
  const isCancelled = task.status === 'CANCELLED';
  const isOpen = task.status === 'OPEN';
  const isInProgress = task.status === 'IN_PROGRESS';

  return (
    <div className="task-detail-page">
      {breadcrumb}

      {taskSuccess && !showEditForm && !showWaitingForm && (
        <div className="alert alert-success" role="status">
          {taskSuccess}
        </div>
      )}

      {error && !showEditForm && !showWaitingForm && (
        <div className="alert alert-error">
          <span>{error}</span>
        </div>
      )}

      <div className="task-detail-header">
        <div className="task-detail-title-row">
          <h2 className="task-detail-title">{task.title}</h2>
          <div className="task-detail-badges">
            <span className={`badge ${getStatusBadgeClass(task.status)}`}>
              {task.status.replace('_', ' ')}
            </span>
            <span className={`badge ${getPriorityBadgeClass(task.priority)}`}>
              {task.priority}
            </span>
          </div>
        </div>
        <div className="task-detail-meta">
          <span>{task.task_type.replace('_', ' ')}</span>
          <span className="task-detail-meta-separator">•</span>
          <Link to={`/matters/${encodeURIComponent(task.matter_key)}`} className="link">
            {task.matter_key}
          </Link>
          <span className="task-detail-meta-separator">•</span>
          <span>Owner: {task.action_owner_type}</span>
          {task.assigned_to && (
            <>
              <span className="task-detail-meta-separator">•</span>
              <span>Assigned: {task.assigned_to}</span>
            </>
          )}
        </div>
      </div>

      {isWaiting && (
        <div className="task-detail-waiting-banner">
          <div className="task-detail-waiting-label">Waiting</div>
          <div className="task-detail-waiting-info">
            <span className="task-waiting-badge">{task.waiting_on?.replace('_', ' ')}</span>
            {task.waiting_reason && <span className="task-detail-waiting-reason">— {task.waiting_reason}</span>}
            {task.waiting_since && (
              <span className="task-detail-waiting-since">since {formatDate(task.waiting_since)}</span>
            )}
          </div>
        </div>
      )}

      <div className="task-detail-grid">
        <div className="task-detail-section">
          <h3>Work Details</h3>
          <div className="task-detail-fields">
            <div className="task-detail-field">
              <span className="task-detail-label">Description</span>
              <span className="task-detail-value">{task.description || '—'}</span>
            </div>
            <div className="task-detail-field">
              <span className="task-detail-label">Task Type</span>
              <span className="task-detail-value">{task.task_type.replace('_', ' ')}</span>
            </div>
            <div className="task-detail-field">
              <span className="task-detail-label">Priority</span>
              <span className="task-detail-value">{task.priority}</span>
            </div>
            <div className="task-detail-field">
              <span className="task-detail-label">Status</span>
              <span className="task-detail-value">{task.status.replace('_', ' ')}</span>
            </div>
            <div className="task-detail-field">
              <span className="task-detail-label">Action Owner</span>
              <span className="task-detail-value">{task.action_owner_type}</span>
            </div>
            <div className="task-detail-field">
              <span className="task-detail-label">Assigned To</span>
              <span className="task-detail-value">{task.assigned_to || '—'}</span>
            </div>
            <div className="task-detail-field">
              <span className="task-detail-label">Created By</span>
              <span className="task-detail-value">{task.created_by || '—'}</span>
            </div>
            <div className="task-detail-field">
              <span className="task-detail-label">Created At</span>
              <span className="task-detail-value">{formatDate(task.created_at)}</span>
            </div>
            <div className="task-detail-field">
              <span className="task-detail-label">Updated At</span>
              <span className="task-detail-value">{formatDate(task.updated_at)}</span>
            </div>
          </div>
        </div>

        <div className="task-detail-section">
          <h3>Timing</h3>
          <div className="task-detail-fields">
            <div className="task-detail-field">
              <span className="task-detail-label">Due</span>
              <span className="task-detail-value">{formatDate(task.due_at)}</span>
            </div>
            <div className="task-detail-field">
              <span className="task-detail-label">Next Action</span>
              <span className="task-detail-value">{formatDate(task.next_action_at)}</span>
            </div>
            <div className="task-detail-field">
              <span className="task-detail-label">Completed At</span>
              <span className="task-detail-value">{formatDate(task.completed_at)}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="task-detail-actions">
        <button type="button" className="btn btn-secondary" onClick={() => navigate('/tasks')}>
          ← Back to Tasks
        </button>
        <div className="task-detail-lifecycle">
          {isOpen && (
            <>
              <button type="button" className="btn btn-primary" onClick={() => handleStatusTransition('IN_PROGRESS')} disabled={taskSaving}>
                Start Task
              </button>
              <button type="button" className="btn btn-secondary" onClick={openWaitingForm} disabled={taskSaving || waitingSaving}>
                Mark Waiting
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => handleStatusTransition('COMPLETED')} disabled={taskSaving}>
                Complete
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => handleStatusTransition('CANCELLED')} disabled={taskSaving}>
                Cancel
              </button>
            </>
          )}
          {isInProgress && (
            <>
              <button type="button" className="btn btn-secondary" onClick={openWaitingForm} disabled={taskSaving || waitingSaving}>
                Mark Waiting
              </button>
              <button type="button" className="btn btn-primary" onClick={() => handleStatusTransition('COMPLETED')} disabled={taskSaving}>
                Complete
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => handleStatusTransition('CANCELLED')} disabled={taskSaving}>
                Cancel
              </button>
            </>
          )}
          {isWaiting && (
            <>
              <button type="button" className="btn btn-primary" onClick={() => handleStatusTransition('IN_PROGRESS')} disabled={taskSaving || waitingSaving}>
                Resume Work
              </button>
              <button type="button" className="btn btn-primary" onClick={() => handleStatusTransition('COMPLETED')} disabled={taskSaving || waitingSaving}>
                Complete
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => handleStatusTransition('CANCELLED')} disabled={taskSaving || waitingSaving}>
                Cancel
              </button>
            </>
          )}
          {isCompleted && (
            <button type="button" className="btn btn-primary" onClick={() => handleStatusTransition('OPEN')} disabled={taskSaving}>
              Reopen
            </button>
          )}
          {isCancelled && (
            <button type="button" className="btn btn-primary" onClick={() => handleStatusTransition('OPEN')} disabled={taskSaving}>
              Reopen
            </button>
          )}
          <button type="button" className="btn btn-secondary" onClick={openEditForm} disabled={taskSaving || waitingSaving}>
            Edit Task
          </button>
        </div>
      </div>

      {showWaitingForm && (
        <div className="task-detail-modal-overlay">
          <form className="task-detail-modal" onSubmit={handleWaitingSubmit} noValidate>
            <h3>Mark as Waiting</h3>
            {waitingError && (
              <div className="alert alert-error">{waitingError}</div>
            )}
            <div className="entry-form-grid">
              <div className="entry-form-field">
                <label htmlFor="waiting-on">Waiting On <span className="required-mark">*</span></label>
                <select
                  id="waiting-on"
                  value={waitingForm.waiting_on}
                  onChange={(e) => setWaitingForm({ ...waitingForm, waiting_on: e.target.value })}
                  disabled={waitingSaving}
                >
                  <option value="">—</option>
                  {WAITING_ON_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="entry-form-field entry-form-field-wide">
                <label htmlFor="waiting-reason">Reason</label>
                <input
                  id="waiting-reason"
                  type="text"
                  value={waitingForm.waiting_reason}
                  onChange={(e) => setWaitingForm({ ...waitingForm, waiting_reason: e.target.value })}
                  disabled={waitingSaving}
                  placeholder="Optional reason"
                />
              </div>
            </div>
            <div className="entry-form-actions">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={closeWaitingForm}
                disabled={waitingSaving}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={waitingSaving}
              >
                {waitingSaving ? 'Saving...' : 'Mark Waiting'}
              </button>
            </div>
          </form>
        </div>
      )}

      {showEditForm && (
        <div className="task-detail-modal-overlay">
          <form className="task-detail-modal" onSubmit={handleEditSubmit} noValidate>
            <h3>Edit Task</h3>
            {taskError && (
              <div className="alert alert-error entry-form-alert">{taskError}</div>
            )}

            <div className="entry-form-grid">
              <div className="entry-form-field entry-form-field-wide">
                <label htmlFor="edit-task-matter-search">
                  Matter <span className="required-mark">*</span>
                </label>
                <input
                  id="edit-task-matter-search"
                  type="text"
                  value={matterSearchQuery}
                  onChange={(e) => {
                    setMatterSearchQuery(e.target.value);
                    setShowMatterDropdown(true);
                  }}
                  onFocus={() => {
                    if (matterSearchResults.length > 0) setShowMatterDropdown(true);
                  }}
                  disabled={taskSaving}
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
                <label htmlFor="edit-task-title">
                  Title <span className="required-mark">*</span>
                </label>
                <input
                  id="edit-task-title"
                  type="text"
                  value={taskForm.title}
                  onChange={(e) => {
                    setTaskForm({ ...taskForm, title: e.target.value });
                    if (taskFieldError) setTaskFieldError(null);
                  }}
                  disabled={taskSaving}
                />
                {taskFieldError && taskFieldError.toLowerCase().includes('title') && (
                  <span className="field-error">{taskFieldError}</span>
                )}
              </div>

              <div className="entry-form-field">
                <label htmlFor="edit-task-type">Type</label>
                <select
                  id="edit-task-type"
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
                <label htmlFor="edit-task-status">Status</label>
                <select
                  id="edit-task-status"
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
                <label htmlFor="edit-task-priority">Priority</label>
                <select
                  id="edit-task-priority"
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
                <label htmlFor="edit-task-assigned">Assigned To (UUID)</label>
                <input
                  id="edit-task-assigned"
                  type="text"
                  value={taskForm.assigned_to}
                  onChange={(e) => setTaskForm({ ...taskForm, assigned_to: e.target.value })}
                  disabled={taskSaving}
                  placeholder="Optional UUID"
                />
              </div>

              <div className="entry-form-field">
                <label htmlFor="edit-task-action-owner">Action Owner</label>
                <select
                  id="edit-task-action-owner"
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
                <label htmlFor="edit-task-waiting-on">Waiting On</label>
                <select
                  id="edit-task-waiting-on"
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
                <label htmlFor="edit-task-due">Due At</label>
                <input
                  id="edit-task-due"
                  type="datetime-local"
                  value={taskForm.due_at}
                  onChange={(e) => setTaskForm({ ...taskForm, due_at: e.target.value })}
                  disabled={taskSaving}
                />
              </div>

              <div className="entry-form-field">
                <label htmlFor="edit-task-next-action">Next Action At</label>
                <input
                  id="edit-task-next-action"
                  type="datetime-local"
                  value={taskForm.next_action_at}
                  onChange={(e) => setTaskForm({ ...taskForm, next_action_at: e.target.value })}
                  disabled={taskSaving}
                />
              </div>

              <div className="entry-form-field entry-form-field-wide">
                <label htmlFor="edit-task-description">Description</label>
                <textarea
                  id="edit-task-description"
                  rows={3}
                  value={taskForm.description}
                  onChange={(e) => setTaskForm({ ...taskForm, description: e.target.value })}
                  disabled={taskSaving}
                />
              </div>
            </div>

            <div className="entry-form-actions">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={closeEditForm}
                disabled={taskSaving}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={taskSaving}
              >
                {taskSaving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
