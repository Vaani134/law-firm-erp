import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { createMatter } from '../services/api';
import type {
  MatterCreateRequest,
  MatterParticipantCreate,
  IntakeNarrative,
} from '../types/matterCreation';
import './MatterCreate.css';

interface ParticipantForm extends MatterParticipantCreate {
  id: string; // Local ID for React key
}

const EMPTY_PARTICIPANT: Omit<ParticipantForm, 'id'> = {
  participant_name: '',
  email_address: '',
  organization: '',
  role_relationship: '',
  is_active: true,
};

function toIsoOrNull(localValue: string): string | null {
  if (!localValue) return null;
  const parsed = new Date(localValue);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toISOString();
}

export function MatterCreate() {
  const navigate = useNavigate();

  // Matter fields
  const [matterKey, setMatterKey] = useState('');
  const [clientId, setClientId] = useState('');
  const [matterId, setMatterId] = useState('');
  const [clientName, setClientName] = useState('');
  const [matterName, setMatterName] = useState('');
  const [matterDescription, setMatterDescription] = useState('');
  const [matterStatus, setMatterStatus] = useState<'open' | 'closed' | 'pending' | 'suspended'>('open');
  const [practiceArea, setPracticeArea] = useState('');
  const [matterType, setMatterType] = useState('');
  const [matterAliases, setMatterAliases] = useState('');
  const [primaryAttorney, setPrimaryAttorney] = useState('');

  // Participants
  const [participants, setParticipants] = useState<ParticipantForm[]>([]);

  // Intake narrative
  const [intakeSummary, setIntakeSummary] = useState('');
  const [intakeActor, setIntakeActor] = useState('');
  const [intakeReference, setIntakeReference] = useState('');
  const [intakeOccurredAt, setIntakeOccurredAt] = useState('');
  const [intakeLoggedBy, setIntakeLoggedBy] = useState('');

  // UI state
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  function addParticipant() {
    const newParticipant: ParticipantForm = {
      ...EMPTY_PARTICIPANT,
      id: `participant-${Date.now()}-${Math.random()}`,
    };
    setParticipants([...participants, newParticipant]);
  }

  function removeParticipant(id: string) {
    setParticipants(participants.filter((p) => p.id !== id));
  }

  function updateParticipant(id: string, field: keyof ParticipantForm, value: string | boolean) {
    setParticipants(
      participants.map((p) =>
        p.id === id ? { ...p, [field]: value } : p
      )
    );
  }

  function validateForm(): boolean {
    const errors: Record<string, string> = {};

    if (!matterKey.trim()) errors.matter_key = 'Matter Key is required';
    if (!clientId.trim()) errors.client_id = 'Client ID is required';
    if (!matterId.trim()) errors.matter_id = 'Matter ID is required';
    if (!clientName.trim()) errors.client_name = 'Client Name is required';
    if (!matterName.trim()) errors.matter_name = 'Matter Name is required';
    if (!matterDescription.trim()) errors.matter_description = 'Matter Description is required';

    // Validate participants
    participants.forEach((p, index) => {
      if (!p.participant_name.trim()) {
        errors[`participant_${index}_name`] = `Participant ${index + 1} name is required`;
      }
    });

    // Validate intake if any field is filled
    const hasIntake = intakeSummary.trim() || intakeActor.trim() || intakeReference.trim() || intakeOccurredAt || intakeLoggedBy.trim();
    if (hasIntake && !intakeSummary.trim()) {
      errors.intake_summary = 'Update Summary is required if filling Intake section';
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    
    if (submitting) return;
    if (!validateForm()) return;

    setSubmitting(true);
    setError(null);

    try {
      // Build participants array
      const participantsPayload: MatterParticipantCreate[] | undefined =
        participants.length > 0
          ? participants.map((p) => ({
              participant_name: p.participant_name.trim(),
              email_address: p.email_address?.trim() || null,
              organization: p.organization?.trim() || null,
              role_relationship: p.role_relationship?.trim() || null,
              is_active: p.is_active,
            }))
          : undefined;

      // Build intake narrative
      const intakePayload: IntakeNarrative | null =
        intakeSummary.trim()
          ? {
              update_summary: intakeSummary.trim(),
              source_actor: intakeActor.trim() || null,
              source_reference: intakeReference.trim() || null,
              occurred_at: toIsoOrNull(intakeOccurredAt),
              logged_by: intakeLoggedBy.trim() || null,
            }
          : null;

      const payload: MatterCreateRequest = {
        matter_key: matterKey.trim(),
        client_id: clientId.trim(),
        matter_id: matterId.trim(),
        client_name: clientName.trim(),
        matter_name: matterName.trim(),
        matter_description: matterDescription.trim(),
        matter_status: matterStatus,
        practice_area: practiceArea.trim() || null,
        matter_type: matterType.trim() || null,
        matter_aliases_identifiers: matterAliases.trim() || null,
        primary_attorney: primaryAttorney.trim() || null,
        participants: participantsPayload,
        intake_narrative: intakePayload,
      };

      const response = await createMatter(payload);
      
      // Navigate to the newly created matter
      navigate(`/matters/${encodeURIComponent(response.matter_key)}`);
    } catch (err) {
      if (err instanceof Error) {
        const message = err.message;
        // Check for 409 Conflict (duplicate matter_key)
        if (message.includes('HTTP 409') || message.toLowerCase().includes('already exists')) {
          setError(`Matter Key "${matterKey}" already exists. Please use a different Matter Key.`);
        } else if (message.includes('HTTP 422')) {
          setError(`Validation error: ${message}`);
        } else {
          setError(message || 'Failed to create matter. Please try again.');
        }
      } else {
        setError('An unexpected error occurred. Please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="matter-create">
      <h2>Create Matter</h2>

      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate>
        {/* Matter Information */}
        <div className="panel">
          <div className="panel-header">
            <h3>Matter Information</h3>
          </div>
          <div className="panel-body">
            <div className="create-form-grid">
              <div className="create-form-field">
                <label htmlFor="matter-key">
                  Matter Key <span className="required-mark">*</span>
                </label>
                <input
                  id="matter-key"
                  type="text"
                  value={matterKey}
                  onChange={(e) => setMatterKey(e.target.value)}
                  disabled={submitting}
                  maxLength={50}
                  placeholder="e.g., 10001-001"
                />
                {fieldErrors.matter_key && (
                  <span className="field-error">{fieldErrors.matter_key}</span>
                )}
              </div>

              <div className="create-form-field">
                <label htmlFor="client-id">
                  Client ID <span className="required-mark">*</span>
                </label>
                <input
                  id="client-id"
                  type="text"
                  value={clientId}
                  onChange={(e) => setClientId(e.target.value)}
                  disabled={submitting}
                  maxLength={30}
                  placeholder="e.g., 10001"
                />
                {fieldErrors.client_id && (
                  <span className="field-error">{fieldErrors.client_id}</span>
                )}
              </div>

              <div className="create-form-field">
                <label htmlFor="matter-id">
                  Matter ID <span className="required-mark">*</span>
                </label>
                <input
                  id="matter-id"
                  type="text"
                  value={matterId}
                  onChange={(e) => setMatterId(e.target.value)}
                  disabled={submitting}
                  maxLength={30}
                  placeholder="e.g., 001"
                />
                {fieldErrors.matter_id && (
                  <span className="field-error">{fieldErrors.matter_id}</span>
                )}
              </div>

              <div className="create-form-field">
                <label htmlFor="matter-status">
                  Matter Status <span className="required-mark">*</span>
                </label>
                <select
                  id="matter-status"
                  value={matterStatus}
                  onChange={(e) => setMatterStatus(e.target.value as typeof matterStatus)}
                  disabled={submitting}
                >
                  <option value="open">Open</option>
                  <option value="closed">Closed</option>
                  <option value="pending">Pending</option>
                  <option value="suspended">Suspended</option>
                </select>
              </div>

              <div className="create-form-field create-form-field-wide">
                <label htmlFor="client-name">
                  Client Name <span className="required-mark">*</span>
                </label>
                <input
                  id="client-name"
                  type="text"
                  value={clientName}
                  onChange={(e) => setClientName(e.target.value)}
                  disabled={submitting}
                  maxLength={200}
                />
                {fieldErrors.client_name && (
                  <span className="field-error">{fieldErrors.client_name}</span>
                )}
              </div>

              <div className="create-form-field create-form-field-wide">
                <label htmlFor="matter-name">
                  Matter Name <span className="required-mark">*</span>
                </label>
                <input
                  id="matter-name"
                  type="text"
                  value={matterName}
                  onChange={(e) => setMatterName(e.target.value)}
                  disabled={submitting}
                  maxLength={200}
                />
                {fieldErrors.matter_name && (
                  <span className="field-error">{fieldErrors.matter_name}</span>
                )}
              </div>

              <div className="create-form-field create-form-field-wide">
                <label htmlFor="matter-description">
                  Matter Description <span className="required-mark">*</span>
                </label>
                <textarea
                  id="matter-description"
                  value={matterDescription}
                  onChange={(e) => setMatterDescription(e.target.value)}
                  disabled={submitting}
                  maxLength={500}
                  rows={3}
                />
                {fieldErrors.matter_description && (
                  <span className="field-error">{fieldErrors.matter_description}</span>
                )}
              </div>

              <div className="create-form-field">
                <label htmlFor="practice-area">Practice Area</label>
                <input
                  id="practice-area"
                  type="text"
                  value={practiceArea}
                  onChange={(e) => setPracticeArea(e.target.value)}
                  disabled={submitting}
                  maxLength={100}
                />
              </div>

              <div className="create-form-field">
                <label htmlFor="matter-type">Matter Type</label>
                <input
                  id="matter-type"
                  type="text"
                  value={matterType}
                  onChange={(e) => setMatterType(e.target.value)}
                  disabled={submitting}
                  maxLength={100}
                />
              </div>

              <div className="create-form-field">
                <label htmlFor="primary-attorney">Primary Attorney</label>
                <input
                  id="primary-attorney"
                  type="text"
                  value={primaryAttorney}
                  onChange={(e) => setPrimaryAttorney(e.target.value)}
                  disabled={submitting}
                  maxLength={200}
                />
              </div>

              <div className="create-form-field create-form-field-wide">
                <label htmlFor="matter-aliases">Matter Aliases / Identifiers</label>
                <textarea
                  id="matter-aliases"
                  value={matterAliases}
                  onChange={(e) => setMatterAliases(e.target.value)}
                  disabled={submitting}
                  rows={2}
                  placeholder="Alternative names or identifiers"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Participants */}
        <div className="panel">
          <div className="panel-header">
            <h3>Participants</h3>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={addParticipant}
              disabled={submitting}
            >
              Add Participant
            </button>
          </div>
          <div className="panel-body">
            {participants.length === 0 && (
              <p className="empty-hint">No participants added yet.</p>
            )}

            {participants.map((participant, index) => (
              <div key={participant.id} className="participant-group">
                <div className="participant-header">
                  <h4>Participant {index + 1}</h4>
                  <button
                    type="button"
                    className="btn-remove"
                    onClick={() => removeParticipant(participant.id)}
                    disabled={submitting}
                    aria-label={`Remove participant ${index + 1}`}
                  >
                    ×
                  </button>
                </div>

                <div className="create-form-grid">
                  <div className="create-form-field create-form-field-wide">
                    <label htmlFor={`participant-name-${participant.id}`}>
                      Name <span className="required-mark">*</span>
                    </label>
                    <input
                      id={`participant-name-${participant.id}`}
                      type="text"
                      value={participant.participant_name}
                      onChange={(e) => updateParticipant(participant.id, 'participant_name', e.target.value)}
                      disabled={submitting}
                    />
                    {fieldErrors[`participant_${index}_name`] && (
                      <span className="field-error">{fieldErrors[`participant_${index}_name`]}</span>
                    )}
                  </div>

                  <div className="create-form-field">
                    <label htmlFor={`participant-email-${participant.id}`}>
                      Email Address
                    </label>
                    <input
                      id={`participant-email-${participant.id}`}
                      type="email"
                      value={participant.email_address || ''}
                      onChange={(e) => updateParticipant(participant.id, 'email_address', e.target.value)}
                      disabled={submitting}
                    />
                  </div>

                  <div className="create-form-field">
                    <label htmlFor={`participant-organization-${participant.id}`}>
                      Organization
                    </label>
                    <input
                      id={`participant-organization-${participant.id}`}
                      type="text"
                      value={participant.organization || ''}
                      onChange={(e) => updateParticipant(participant.id, 'organization', e.target.value)}
                      disabled={submitting}
                    />
                  </div>

                  <div className="create-form-field">
                    <label htmlFor={`participant-role-${participant.id}`}>
                      Role / Relationship
                    </label>
                    <input
                      id={`participant-role-${participant.id}`}
                      type="text"
                      value={participant.role_relationship || ''}
                      onChange={(e) => updateParticipant(participant.id, 'role_relationship', e.target.value)}
                      disabled={submitting}
                    />
                  </div>

                  <div className="create-form-field">
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={participant.is_active}
                        onChange={(e) => updateParticipant(participant.id, 'is_active', e.target.checked)}
                        disabled={submitting}
                      />
                      <span>Active</span>
                    </label>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Initial Intake */}
        <div className="panel">
          <div className="panel-header">
            <h3>Initial Intake (Optional)</h3>
          </div>
          <div className="panel-body">
            <div className="create-form-grid">
              <div className="create-form-field create-form-field-wide">
                <label htmlFor="intake-summary">
                  Update Summary
                  {intakeSummary.trim() && <span className="required-mark">*</span>}
                </label>
                <textarea
                  id="intake-summary"
                  value={intakeSummary}
                  onChange={(e) => setIntakeSummary(e.target.value)}
                  disabled={submitting}
                  rows={3}
                  placeholder="Describe the initial intake event or conversation"
                />
                {fieldErrors.intake_summary && (
                  <span className="field-error">{fieldErrors.intake_summary}</span>
                )}
              </div>

              <div className="create-form-field">
                <label htmlFor="intake-actor">Source Actor</label>
                <input
                  id="intake-actor"
                  type="text"
                  value={intakeActor}
                  onChange={(e) => setIntakeActor(e.target.value)}
                  disabled={submitting}
                  placeholder="Person or system"
                />
              </div>

              <div className="create-form-field">
                <label htmlFor="intake-reference">Source Reference</label>
                <input
                  id="intake-reference"
                  type="text"
                  value={intakeReference}
                  onChange={(e) => setIntakeReference(e.target.value)}
                  disabled={submitting}
                  placeholder="Optional identifier"
                />
              </div>

              <div className="create-form-field">
                <label htmlFor="intake-occurred-at">Occurred At</label>
                <input
                  id="intake-occurred-at"
                  type="datetime-local"
                  value={intakeOccurredAt}
                  onChange={(e) => setIntakeOccurredAt(e.target.value)}
                  disabled={submitting}
                />
              </div>

              <div className="create-form-field">
                <label htmlFor="intake-logged-by">Logged By</label>
                <input
                  id="intake-logged-by"
                  type="text"
                  value={intakeLoggedBy}
                  onChange={(e) => setIntakeLoggedBy(e.target.value)}
                  disabled={submitting}
                  placeholder="Initials or name"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Form Actions */}
        <div className="create-form-actions">
          <Link to="/matters" className="btn btn-secondary">
            Cancel
          </Link>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={submitting}
          >
            {submitting ? 'Creating Matter...' : 'Create Matter'}
          </button>
        </div>
      </form>
    </div>
  );
}
