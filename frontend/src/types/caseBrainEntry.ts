export type CaseBrainSourceType = 'manual' | 'intake' | 'system' | 'import';

export interface CaseBrainEntryCreate {
  source_type: CaseBrainSourceType;
  source_reference: string | null;
  source_actor: string | null;
  update_summary: string;
  occurred_at: string | null;
  logged_by: string | null;
}

export interface CaseBrainEntryResponse {
  brain_entry_id: number;
  matter_key: string;
  email_id: string | null;
  occurred_at: string;
  logged_at: string;
  source_type: string;
  source_reference: string | null;
  source_actor: string | null;
  update_summary: string;
  logged_by: string | null;
}
