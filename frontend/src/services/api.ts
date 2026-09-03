import type { ReviewQueueEmail } from '../types/reviewQueue';
import type { EmailDetail } from '../types/emailDetail';
import type { MatterDetailResponse } from '../types/matterDetail';
import type { CaseBrainTimelineResponse } from '../types/caseBrain';
import type { MatterAssignmentResponse, MatterSearchResponse } from '../types/matterSearch';
import type { CaseBrainEntryCreate, CaseBrainEntryResponse } from '../types/caseBrainEntry';

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

export async function searchMatters(query: string): Promise<MatterSearchResponse> {
  const trimmed = query.trim();
  const params = new URLSearchParams({ limit: '20', offset: '0' });
  if (trimmed.length > 0) {
    params.set('q', trimmed);
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
