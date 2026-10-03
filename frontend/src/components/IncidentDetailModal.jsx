import React, { useEffect, useState } from 'react';
import { X, Bot, Calendar, User, Tag, AlertTriangle, CheckCircle2, Clock } from 'lucide-react';

export default function IncidentDetailModal({ incidentId, onClose, onAskAI }) {
  const [incident, setIncident] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (incidentId) fetchDetail();
  }, [incidentId]);

  const fetchDetail = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/incidents/${encodeURIComponent(incidentId)}`);
      if (!res.ok) throw new Error(`Could not fetch details for ${incidentId}`);
      const data = await res.json();
      setIncident(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '850px' }}>
        <div className="modal-header">
          <div className="modal-title">
            <Tag size={20} color="#6366f1" />
            <span>Incident Details: {incidentId}</span>
          </div>
          <button className="btn-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px', color: '#9ca3af' }}>
              Loading details for {incidentId}...
            </div>
          ) : error ? (
            <div className="error-banner">{error}</div>
          ) : incident ? (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px' }}>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>{incident.short_description}</h2>
                <button
                  className="btn-send"
                  style={{ padding: '8px 16px', fontSize: '0.85rem' }}
                  onClick={() => {
                    onAskAI(`Tell me details and resolution summary for ${incident.incident_id}`);
                    onClose();
                  }}
                >
                  <Bot size={16} />
                  Ask AI About This
                </button>
              </div>

              <div className="detail-grid">
                <div className="detail-item">
                  <div className="detail-label">Status & State</div>
                  <div className="detail-value">{incident.state}</div>
                </div>

                <div className="detail-item">
                  <div className="detail-label">Criticality</div>
                  <div className="detail-value">{incident.criticality_description || `Level ${incident.criticality}`}</div>
                </div>

                <div className="detail-item">
                  <div className="detail-label">Category / Subcategory</div>
                  <div className="detail-value">{incident.category} &rsaquo; {incident.subcategory}</div>
                </div>

                <div className="detail-item">
                  <div className="detail-label">Assigned To</div>
                  <div className="detail-value">{incident.assigned_to || 'Unassigned'} ({incident.assignment_group})</div>
                </div>

                <div className="detail-item">
                  <div className="detail-label">Opened At & By</div>
                  <div className="detail-value">{incident.opened_at || 'N/A'} ({incident.opened_by || 'Unknown'})</div>
                </div>

                <div className="detail-item">
                  <div className="detail-label">Service Affected</div>
                  <div className="detail-value">{incident.service || 'N/A'}</div>
                </div>
              </div>

              <div className="detail-block">
                <div className="detail-label">Full Problem Description</div>
                <p style={{ marginTop: '6px', fontSize: '0.95rem', color: '#e5e7eb' }}>
                  {incident.description || 'No detailed description available.'}
                </p>
              </div>

              {incident.root_cause_analysis && (
                <div className="detail-block" style={{ borderColor: 'rgba(245, 158, 11, 0.3)' }}>
                  <div className="detail-label" style={{ color: '#fbbf24' }}>Root Cause Analysis (RCA)</div>
                  <p style={{ marginTop: '6px', fontSize: '0.95rem', color: '#fef08a' }}>
                    {incident.root_cause_analysis}
                  </p>
                </div>
              )}

              {incident.resolution && (
                <div className="detail-block" style={{ borderColor: 'rgba(16, 185, 129, 0.3)' }}>
                  <div className="detail-label" style={{ color: '#6ee7b7' }}>Resolution</div>
                  <p style={{ marginTop: '6px', fontSize: '0.95rem', color: '#d1fae5' }}>
                    {incident.resolution}
                  </p>
                </div>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
