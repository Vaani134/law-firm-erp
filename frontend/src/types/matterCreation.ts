/**
 * Types for Matter Creation (Intake) - POST /api/matters
 */

export interface MatterParticipantCreate {
  participant_name: string;
  email_address?: string | null;
  organization?: string | null;
  role_relationship?: string | null;
  is_active: boolean;
}

export interface IntakeNarrative {
  update_summary: string;
  source_actor?: string | null;
  source_reference?: string | null;
  occurred_at?: string | null;  // ISO datetime string
  logged_by?: string | null;
}

export interface MatterCreateRequest {
  matter_key: string;
  client_id: string;
  matter_id: string;
  client_name: string;
  matter_name: string;
  matter_description: string;
  matter_status: 'open' | 'closed' | 'pending' | 'suspended';
  practice_area?: string | null;
  matter_type?: string | null;
  matter_aliases_identifiers?: string | null;
  primary_attorney?: string | null;
  participants?: MatterParticipantCreate[];
  intake_narrative?: IntakeNarrative | null;
}

export interface MatterParticipantSummary {
  participant_id: number;
  matter_key: string;
  participant_name: string;
  email_address: string | null;
  organization: string | null;
  role_relationship: string | null;
  is_active: boolean;
}

export interface MatterCaseBrainSummary {
  brain_entry_id: number;
  email_id: string | null;
  occurred_at: string;
  source_type: string;
  source_reference: string | null;
  source_actor: string | null;
  update_summary: string;
  logged_by: string | null;
}

export interface MatterCreateResponse {
  matter_key: string;
  client_id: string;
  matter_id: string;
  client_name: string;
  matter_name: string;
  practice_area: string | null;
  matter_type: string | null;
  matter_description: string;
  matter_aliases_identifiers: string | null;
  matter_status: string;
  primary_attorney: string | null;
  last_brain_update: string | null;
  created_at: string;
  updated_at: string;
  participants: MatterParticipantSummary[];
  case_brain_entries: MatterCaseBrainSummary[];
}
