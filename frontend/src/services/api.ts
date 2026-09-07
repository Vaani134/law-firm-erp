import type { ReviewQueueEmail } from '../types/reviewQueue';
import type { EmailDetail } from '../types/emailDetail';
import type { MatterDetailResponse } from '../types/matterDetail';
import type { CaseBrainTimelineResponse } from '../types/caseBrain';
import type { CaseBrainSearchResponse } from '../types/caseBrainSearch';
import type { MatterAssignmentResponse, MatterSearchResponse } from '../types/matterSearch';
import type { CaseBrainEntryCreate, CaseBrainEntryResponse } from '../types/caseBrainEntry';
import type { MatterCreateRequest, MatterCreateResponse } from '../types/matterCreation';
import type { TaskCreate, TaskListResponse, TaskResponse, TaskUpdate } from '../types/task';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function fetchReviewQueue(): Promise<{ total: number; emails: ReviewQueueEmail[] }> {
  const response = await fetch(`${API_BASE_URL}/api/emails/review-required`);
  return handleResponse<{ total: number; emails: ReviewQueueEmail[] }>(response);
}

export async function fetchEmailDetail(emailId: string | undefined): Promise<EmailDetail> {
  if (!emailId) throw new Error('Missing emailId');
  const response = await fetch(`${API_BASE_URL}/api/emails/${encodeURIComponent(emailId)}`);
  return handleResponse<EmailDetail>(response);
}

export async function fetchMatterDetail(matterKey: string | undefined): Promise<MatterDetailResponse> {
  if (!matterKey) throw new Error('Missing matterKey');
  const response = await fetch(`${API_BASE_URL}/api/matters/${encodeURIComponent(matterKey)}`);
  return handleResponse<MatterDetailResponse>(response);
}

export async function fetchCaseBrainTimeline(matterKey: string | undefined): Promise<CaseBrainTimelineResponse> {
  if (!matterKey) throw new Error('Missing matterKey');
  const response = await fetch(`${API_BASE_URL}/api/matters/${encodeURIComponent(matterKey)}/case-brain`);
  return handleResponse<CaseBrainTimelineResponse>(response);
}

export async function searchCaseBrain({
  q,
  sourceType,
  matterKey,
  dateFrom,
  dateTo,
  limit = 50,
  offset = 0,
}: {
  q?: string;
  sourceType?: string;
  matterKey?: string;
  dateFrom?: string;
  dateTo?: string;
  limit?: number;
  offset?: number;
}): Promise<CaseBrainSearchResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  const trimmedQuery = (q ?? '').trim();
  if (trimmedQuery.length > 0) {
    params.set('q', trimmedQuery);
  }
  const trimmedSource = (sourceType ?? '').trim();
  if (trimmedSource.length > 0) {
    params.set('source_type', trimmedSource);
  }
  const trimmedMatter = (matterKey ?? '').trim();
  if (trimmedMatter.length > 0) {
    params.set('matter_key', trimmedMatter);
  }
  const trimmedFrom = (dateFrom ?? '').trim();
  if (trimmedFrom.length > 0) {
    params.set('date_from', trimmedFrom);
  }
  const trimmedTo = (dateTo ?? '').trim();
  if (trimmedTo.length > 0) {
    params.set('date_to', trimmedTo);
  }
  const response = await fetch(`${API_BASE_URL}/api/case-brain?${params.toString()}`);
  return handleResponse<CaseBrainSearchResponse>(response);
}

export async function addCaseBrainEntry(
  matterKey: string | undefined,
  payload: CaseBrainEntryCreate,
): Promise<CaseBrainEntryResponse> {
  if (!matterKey) throw new Error('Missing matterKey');
  const response = await fetch(
    `${API_BASE_URL}/api/matters/${encodeURIComponent(matterKey)}/case-brain`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
  );
  return handleResponse<CaseBrainEntryResponse>(response);
}

export async function searchMatters(
  query?: string,
  status?: string,
  practiceArea?: string,
  limit: number = 20,
  offset: number = 0,
): Promise<MatterSearchResponse> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  const trimmed = (query ?? '').trim();
  if (trimmed.length > 0) {
    params.set('q', trimmed);
  }
  if (status && status.trim().length > 0) {
    params.set('status', status.trim());
  }
  if (practiceArea && practiceArea.trim().length > 0) {
    params.set('practice_area', practiceArea.trim());
  }
  const response = await fetch(`${API_BASE_URL}/api/matters?${params.toString()}`);
  return handleResponse<MatterSearchResponse>(response);
}

export async function assignEmailToMatter(
  emailId: string,
  matterKey: string,
): Promise<MatterAssignmentResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/emails/${encodeURIComponent(emailId)}/assign-matter`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ matter_key: matterKey }),
    },
  );
  return handleResponse<MatterAssignmentResponse>(response);
}

export async function createMatter(
  payload: MatterCreateRequest,
): Promise<MatterCreateResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/matters`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
  );
  return handleResponse<MatterCreateResponse>(response);
}

export async function fetchMatterTasks(
  matterKey: string | undefined,
  limit = 50,
  offset = 0,
): Promise<TaskListResponse> {
  if (!matterKey) throw new Error('Missing matterKey');
  const params = new URLSearchParams({
    matter_key: matterKey,
    limit: String(limit),
    offset: String(offset),
  });
  const response = await fetch(`${API_BASE_URL}/api/tasks?${params.toString()}`);
  return handleResponse<TaskListResponse>(response);
}

export async function fetchTasks({
  q,
  matterKey,
  assignedTo,
  taskType,
  status,
  priority,
  actionOwnerType,
  waitingOn,
  dueFrom,
  dueTo,
  nextActionFrom,
  nextActionTo,
  limit = 50,
  offset = 0,
}: {
  q?: string;
  matterKey?: string;
  assignedTo?: string;
  taskType?: string;
  status?: string;
  priority?: string;
  actionOwnerType?: string;
  waitingOn?: string;
  dueFrom?: string;
  dueTo?: string;
  nextActionFrom?: string;
  nextActionTo?: string;
  limit?: number;
  offset?: number;
}): Promise<TaskListResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  const trimmedQuery = (q ?? '').trim();
  if (trimmedQuery.length > 0) {
    params.set('q', trimmedQuery);
  }
  const trimmedMatter = (matterKey ?? '').trim();
  if (trimmedMatter.length > 0) {
    params.set('matter_key', trimmedMatter);
  }
  const trimmedAssigned = (assignedTo ?? '').trim();
  if (trimmedAssigned.length > 0) {
    params.set('assigned_to', trimmedAssigned);
  }
  const trimmedType = (taskType ?? '').trim();
  if (trimmedType.length > 0) {
    params.set('task_type', trimmedType);
  }
  const trimmedStatus = (status ?? '').trim();
  if (trimmedStatus.length > 0) {
    params.set('status', trimmedStatus);
  }
  const trimmedPriority = (priority ?? '').trim();
  if (trimmedPriority.length > 0) {
    params.set('priority', trimmedPriority);
  }
  const trimmedOwner = (actionOwnerType ?? '').trim();
  if (trimmedOwner.length > 0) {
    params.set('action_owner_type', trimmedOwner);
  }
  const trimmedWaiting = (waitingOn ?? '').trim();
  if (trimmedWaiting.length > 0) {
    params.set('waiting_on', trimmedWaiting);
  }
  const trimmedDueFrom = (dueFrom ?? '').trim();
  if (trimmedDueFrom.length > 0) {
    params.set('due_from', trimmedDueFrom);
  }
  const trimmedDueTo = (dueTo ?? '').trim();
  if (trimmedDueTo.length > 0) {
    params.set('due_to', trimmedDueTo);
  }
  const trimmedNextFrom = (nextActionFrom ?? '').trim();
  if (trimmedNextFrom.length > 0) {
    params.set('next_action_from', trimmedNextFrom);
  }
  const trimmedNextTo = (nextActionTo ?? '').trim();
  if (trimmedNextTo.length > 0) {
    params.set('next_action_to', trimmedNextTo);
  }
  const response = await fetch(`${API_BASE_URL}/api/tasks?${params.toString()}`);
  return handleResponse<TaskListResponse>(response);
}

export async function createTask(
  payload: TaskCreate,
): Promise<TaskResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/tasks`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
  );
  return handleResponse<TaskResponse>(response);
}

export async function updateTask(
  taskId: string,
  payload: TaskUpdate,
): Promise<TaskResponse> {
  if (!taskId) throw new Error('Missing taskId');
  const response = await fetch(
    `${API_BASE_URL}/api/tasks/${encodeURIComponent(taskId)}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
  );
  return handleResponse<TaskResponse>(response);
}

export async function fetchTask(
  taskId: string | undefined,
): Promise<TaskResponse> {
  if (!taskId) throw new Error('Missing taskId');
  const response = await fetch(`${API_BASE_URL}/api/tasks/${encodeURIComponent(taskId)}`);
  return handleResponse<TaskResponse>(response);
}
