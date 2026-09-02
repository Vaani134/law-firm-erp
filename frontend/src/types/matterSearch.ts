export interface MatterSummary {
  matter_key: string;
  client_name: string;
  matter_name: string;
  practice_area: string | null;
  matter_type: string | null;
  matter_status: string;
  primary_attorney: string | null;
}

export interface MatterSearchResponse {
  total: number;
  limit: number;
  offset: number;
  matters: MatterSummary[];
}

export interface MatterAssignmentResponse {
  email_id: string;
  status: 'assigned' | 'already_assigned';
  matter_key: string | null;
  processing_status: string;
}
