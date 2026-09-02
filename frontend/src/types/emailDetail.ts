export interface EmailDetail {
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
