export interface MatterParticipant {
  participant_id: number;
  matter_key: string;
  participant_name: string;
  email_address: string | null;
  organization: string | null;
  role_relationship: string | null;
  is_active: boolean;
}

export interface MatterEmail {
  email_id: string;
  message_id: string | null;
  matter_key: string | null;
  sender: string;
  to_recipients: Array<Record<string, unknown>> | null;
  cc_recipients: Array<Record<string, unknown>> | null;
  subject: string | null;
  body_text: string | null;
  received_at: string | null;
  raw_file_path: string;
  content_hash: string;
  processing_status: string;
  created_at: string;
  updated_at: string;
}

export interface MatterCaseBrainEntry {
  brain_entry_id: number;
  email_id: string | null;
  occurred_at: string;
  source_type: string;
  source_reference: string | null;
  source_actor: string | null;
  update_summary: string;
  logged_by: string | null;
}

export interface MatterResponse {
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
}

export interface MatterDetailResponse {
  matter: MatterResponse;
  participants: MatterParticipant[];
  emails: MatterEmail[];
  case_brain: MatterCaseBrainEntry[];
}
