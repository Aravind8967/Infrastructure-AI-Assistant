import React, { useEffect, useState } from 'react';
import { X, ExternalLink, RefreshCw } from 'lucide-react';

export default function IncidentsListModal({ stateKey, title, onClose, onSelectIncident }) {
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchIncidents();
  }, [stateKey]);

  const fetchIncidents = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/incidents?state=${encodeURIComponent(stateKey)}`);
      if (!res.ok) throw new Error('Failed to load incidents');
      const data = await res.json();
      setIncidents(data.incidents || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getCriticalityBadge = (crit) => {
    switch (crit) {
      case 1: return <span style={{ color: '#ef4444', fontWeight: 600 }}>P1 - Critical</span>;
      case 2: return <span style={{ color: '#f59e0b', fontWeight: 600 }}>P2 - High</span>;
      case 3: return <span style={{ color: '#3b82f6', fontWeight: 600 }}>P3 - Medium</span>;
      default: return <span style={{ color: '#9ca3af' }}>P4 - Low</span>;
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">
            <span>{title}</span>
            <span style={{ fontSize: '0.85rem', color: '#9ca3af', fontWeight: 400 }}>
              ({incidents.length} total)
            </span>
          </div>
          <button className="btn-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px', color: '#9ca3af' }}>
              <RefreshCw size={24} className="spin" style={{ marginBottom: '12px' }} />
              <p>Loading {title}...</p>
            </div>
          ) : error ? (
            <div className="error-banner">{error}</div>
          ) : incidents.length === 0 ? (
            <p style={{ textAlign: 'center', color: '#9ca3af', padding: '40px' }}>
              No incidents found in state '{stateKey}'.
            </p>
          ) : (
            <table className="incidents-table">
              <thead>
                <tr>
                  <th>Incident ID</th>
                  <th>Problem Summary</th>
                  <th>Category</th>
                  <th>Assigned To</th>
                  <th>Criticality</th>
                </tr>
              </thead>
              <tbody>
                {incidents.map((inc) => (
                  <tr key={inc.incident_id}>
                    <td>
                      <a
                        href="#detail"
                        className="incident-link"
                        onClick={(e) => {
                          e.preventDefault();
                          onSelectIncident(inc.incident_id);
                        }}
                      >
                        {inc.incident_id} <ExternalLink size={12} style={{ display: 'inline', marginLeft: '2px' }} />
                      </a>
                    </td>
                    <td style={{ maxWidth: '280px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {inc.short_description}
                    </td>
                    <td>{inc.category || 'N/A'}</td>
                    <td>{inc.assigned_to || 'Unassigned'}</td>
                    <td>{getCriticalityBadge(inc.criticality)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
