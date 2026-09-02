import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { fetchEmailDetail } from '../services/api';
import type { EmailDetail } from '../types/emailDetail';
import './EmailDetail.css';

export function EmailDetail() {
  const { emailId } = useParams<{ emailId: string | undefined }>();
  const [email, setEmail] = useState<EmailDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!emailId) return;

    let cancelled = false;

    async function load() {
      try {
        const data = await fetchEmailDetail(emailId);
        if (!cancelled) {
          setEmail(data);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load email');
          setLoading(false);
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [emailId]);

  if (!emailId) {
    return <div className="email-detail">No email selected.</div>;
  }

  if (loading) {
    return <div className="email-detail">Loading...</div>;
  }

  if (error || !email) {
    return (
      <div className="email-detail">
        <div className="alert alert-error">
          {error || 'Email not found.'}
        </div>
        <Link to="/review-queue" className="link">Back to Review Queue</Link>
      </div>
    );
  }

  return (
    <div className="email-detail">
      <div className="breadcrumb">
        <Link to="/review-queue" className="link">Review Queue</Link>
        <span className="breadcrumb-sep">/</span>
        <span>Email Detail</span>
      </div>

      <h2>{email.subject || '(no subject)'}</h2>

      <div className="panel">
        <div className="panel-header">
          <h3>Email Information</h3>
          <span className="badge badge-info">{email.processing_status}</span>
        </div>
        <div className="panel-body">
          <div className="detail-grid">
            <div className="detail-item">
              <span className="detail-label">Email ID</span>
              <span className="detail-value mono">{email.email_id}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Message ID</span>
              <span className="detail-value mono">{email.message_id || '—'}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Sender</span>
              <span className="detail-value">{email.sender}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Matter</span>
              <span className="detail-value">
                {email.matter_key ? (
                  <Link to={`/matters/${email.matter_key}`} className="link">
                    {email.matter_key}
                  </Link>
                ) : (
                  '—'
                )}
              </span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Received</span>
              <span className="detail-value">
                {email.received_at ? new Date(email.received_at).toLocaleString() : '—'}
              </span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Raw File</span>
              <span className="detail-value mono">{email.raw_file_path}</span>
            </div>
          </div>

          <div className="section">
            <h4>Body</h4>
            <pre className="body-text">{email.body_text || '(no body)'}</pre>
          </div>
        </div>
      </div>
    </div>
  );
}
