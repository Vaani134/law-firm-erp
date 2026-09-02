export interface CaseBrainLogEntry {
  brain_entry_id: number;
  email_id: string | null;
  occurred_at: string;
  source_type: string;
  source_reference: string | null;
  source_actor: string | null;
  update_summary: string;
  logged_by: string | null;
}

export interface CaseBrainTimelineResponse {
  matter_key: string;
  total: number;
  entries: CaseBrainLogEntry[];
}
