import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  addCaseBrainEntry,
  fetchCaseBrainTimeline,
  fetchMatterDetail,
  fetchMatterTasks,
  createTask,
  updateTask,
} from '../services/api';
import type {
  CaseBrainEntryCreate,
  CaseBrainSourceType,
  MatterCaseBrainEntry,
  MatterDetailResponse,
  CaseBrainTimelineResponse,
  MatterEmail,
  MatterParticipant,
  TaskResponse,
  TaskCreate,
  TaskUpdate,
  TaskType,
  TaskStatus,
  TaskPriority,
  ActionOwnerType,
  WaitingOn,
} from '../types';
import './MatterDetail.css';

const SOURCE_TYPE_OPTIONS: { value: CaseBrainSourceType; label: string }[] = [
  { value: 'manual', label: 'Manual' },
  { value: 'intake', label: 'Intake' },
  { value: 'system', label: 'System' },
  { value: 'import', label: 'Import' },
];

const EMPTY_CASE_BRAIN_FORM = {
  source_type: 'manual' as CaseBrainSourceType,
  update_summary: '',
  source_reference: '',
  source_actor: '',
  occurred_at: '',
  logged_by: '',
};

type CaseBrainFormState = typeof EMPTY_CASE_BRAIN_FORM;

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

export function MatterDetail() {
  const { matterKey } = useParams<{ matterKey: string | undefined }>();
  const [matter, setMatter] = useState<MatterDetailResponse | null>(null);
  const [timeline, setTimeline] = useState<CaseBrainTimelineResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [tasks, setTasks] = useState<TaskResponse[]>([]);
  const [tasksTotal, setTasksTotal] = useState(0);
  const [tasksLoading, setTasksLoading] = useState(true);
  const [tasksError, setTasksError] = useState<string | null>(null);
  const [taskStatusFilter, setTaskStatusFilter] = useState<TaskStatus | ''>('');
  const [taskPriorityFilter, setTaskPriorityFilter] = useState<TaskPriority | ''>('');
  const [taskOffset, setTaskOffset] = useState(0);

  const [showEntryForm, setShowEntryForm] = useState(false);
  const [entryForm, setEntryForm] = useState<CaseBrainFormState>(EMPTY_CASE_BRAIN_FORM);
  const [entrySaving, setEntrySaving] = useState(false);
  const [entryError, setEntryError] = useState<string | null>(null);
  const [entryFieldError, setEntryFieldError] = useState<string | null>(null);
  const [entrySuccess, setEntrySuccess] = useState<string | null>(null);

  const [showTaskForm, setShowTaskForm] = useState(false);
  const [taskForm, setTaskForm] = useState<TaskFormState>(EMPTY_TASK_FORM);
  const [taskSaving, setTaskSaving] = useState(false);
  const [taskError, setTaskError] = useState<string | null>(null);
  const [taskFieldError, setTaskFieldError] = useState<string | null>(null);
  const [taskSuccess, setTaskSuccess] = useState<string | null>(null);
  const [editingTaskId, setEditingTaskId] = useState<string | null>(null);

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

  useEffect(() => {
    if (!matterKey) return;

    let cancelled = false;
    setTasksLoading(true);
    setTasksError(null);

    async function loadTasks() {
      try {
        const data = await fetchMatterTasks(matterKey, 50, taskOffset);
        let filtered = data.tasks;
        if (taskStatusFilter) {
          filtered = filtered.filter((t) => t.status === taskStatusFilter);
        }
        if (taskPriorityFilter) {
          filtered = filtered.filter((t) => t.priority === taskPriorityFilter);
        }
        if (!cancelled) {
          setTasks(filtered);
          setTasksTotal(data.total);
          setTasksLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setTasksError(err instanceof Error ? err.message : 'Failed to load tasks');
          setTasksLoading(false);
        }
      }
    }

    loadTasks();
    return () => {
      cancelled = true;
    };
  }, [matterKey, taskStatusFilter, taskPriorityFilter, taskOffset]);

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

  function openCaseBrainEntryForm() {
    setEntryForm(EMPTY_CASE_BRAIN_FORM);
    setEntryError(null);
    setEntryFieldError(null);
    setEntrySuccess(null);
    setShowEntryForm(true);
  }

  function closeCaseBrainEntryForm() {
    if (entrySaving) return;
    setShowEntryForm(false);
  }

  async function reloadTimeline() {
    if (!matterKey) return;
    const timelineData = await fetchCaseBrainTimeline(matterKey);
    setTimeline(timelineData);
  }

  async function handleCaseBrainEntrySubmit(e: React.FormEvent) {
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
      setEntryForm(EMPTY_CASE_BRAIN_FORM);
      setEntrySuccess('Case Brain entry added.');
      await reloadTimeline();
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to add entry.';
      setEntryError(message);
    } finally {
      setEntrySaving(false);
    }
  }

  function openTaskForm() {
    setTaskForm(EMPTY_TASK_FORM);
    setTaskError(null);
    setTaskFieldError(null);
    setTaskSuccess(null);
    setEditingTaskId(null);
    setShowTaskForm(true);
  }

  function openEditTaskForm(task: TaskResponse) {
    setTaskForm({
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
    setShowTaskForm(true);
  }

  function closeTaskForm() {
    if (taskSaving) return;
    setShowTaskForm(false);
    setEditingTaskId(null);
  }

  async function reloadTasks() {
    if (!matterKey) return;
    setTasksLoading(true);
    setTasksError(null);
    try {
      const data = await fetchMatterTasks(matterKey, 50, taskOffset);
      let filtered = data.tasks;
      if (taskStatusFilter) {
        filtered = filtered.filter((t) => t.status === taskStatusFilter);
      }
      if (taskPriorityFilter) {
        filtered = filtered.filter((t) => t.priority === taskPriorityFilter);
      }
      setTasks(filtered);
      setTasksTotal(data.total);
      setTasksLoading(false);
    } catch (err) {
      setTasksError(err instanceof Error ? err.message : 'Failed to load tasks');
      setTasksLoading(false);
    }
  }

  async function handleTaskSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (taskSaving || !matterKey) return;

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

    const payload: TaskCreate = {
      matter_key: matterKey,
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
        await createTask(payload);
        setTaskSuccess('Task created.');
      }
      setShowTaskForm(false);
      setTaskForm(EMPTY_TASK_FORM);
      setEditingTaskId(null);
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

  return (
    <div className="matter-detail">
      <h2>Matter Detail</h2>

      {entrySuccess && (
        <div className="alert alert-success" role="status">
          {entrySuccess}
        </div>
      )}

      {taskSuccess && (
        <div className="alert alert-success" role="status">
          {taskSuccess}
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
          <h3>Tasks ({tasksTotal})</h3>
          {!showTaskForm && (
            <button type="button" className="btn btn-primary" onClick={openTaskForm}>
              Add Task
            </button>
          )}
        </div>

        <div className="task-filters">
          <div className="task-filter-field">
            <label htmlFor="task-status-filter">Status</label>
            <select
              id="task-status-filter"
              value={taskStatusFilter}
              onChange={(e) => {
                setTaskStatusFilter(e.target.value as TaskStatus | '');
                setTaskOffset(0);
              }}
            >
              <option value="">All</option>
              {TASK_STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          <div className="task-filter-field">
            <label htmlFor="task-priority-filter">Priority</label>
            <select
              id="task-priority-filter"
              value={taskPriorityFilter}
              onChange={(e) => {
                setTaskPriorityFilter(e.target.value as TaskPriority | '');
                setTaskOffset(0);
              }}
            >
              <option value="">All</option>
              {TASK_PRIORITY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {showTaskForm && (
          <form className="entry-form task-form" onSubmit={handleTaskSubmit} noValidate>
            {taskError && (
              <div className="alert alert-error entry-form-alert">{taskError}</div>
            )}

            <div className="entry-form-grid">
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
                {taskFieldError && (
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

        {tasksError && (
          <div className="alert alert-error">
            {tasksError}
          </div>
        )}

        {tasksLoading ? (
          <p>Loading tasks...</p>
        ) : tasks.length === 0 ? (
          <p className="empty-state">No tasks match the current filters.</p>
        ) : (
          <div className="task-table-wrap">
            <table className="data-table task-table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Priority</th>
                  <th>Assigned To</th>
                  <th>Action Owner</th>
                  <th>Waiting On</th>
                  <th>Due</th>
                  <th>Next Action</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((task) => (
                  <tr key={task.task_id}>
                    <td>
                      <div className="task-title-cell">
                        <span className="task-title-text">{task.title}</span>
                        {task.description && (
                          <span className="task-description-hint" title={task.description}>
                            💬
                          </span>
                        )}
                      </div>
                    </td>
                    <td>{task.task_type.replace('_', ' ')}</td>
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
                    <td>{task.assigned_to || '—'}</td>
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
        )}
      </div>

      <div className="section">
        <div className="section-header">
          <h3>Case Brain ({timeline?.total ?? 0})</h3>
          {!showEntryForm && (
            <button type="button" className="btn btn-primary" onClick={openCaseBrainEntryForm}>
              Add Entry
            </button>
          )}
        </div>

        {showEntryForm && (
          <form className="entry-form" onSubmit={handleCaseBrainEntrySubmit} noValidate>
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
                onClick={closeCaseBrainEntryForm}
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
