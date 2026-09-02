export interface ReviewQueueEmail {
  email_id: string;
  message_id: string | null;
  sender: string;
  to_recipients: Array<Record<string, unknown>> | null;
  cc_recipients: Array<Record<string, unknown>> | null;
  subject: string | null;
  received_at: string | null;
  processing_status: string;
  matter_key: string | null;
}

export interface ReviewQueueResponse {
  total: number;
  emails: ReviewQueueEmail[];
}
