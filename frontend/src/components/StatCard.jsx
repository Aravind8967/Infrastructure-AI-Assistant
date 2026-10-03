import React from 'react';
import { ArrowUpRight } from 'lucide-react';

export default function StatCard({ title, count, stateKey, type, icon: Icon, onClick }) {
  return (
    <div className={`stat-card ${type}`} onClick={() => onClick(stateKey, title)}>
      <div className="stat-header">
        <span className="stat-title">{title}</span>
        <div className="stat-icon-box">
          <Icon size={20} />
        </div>
      </div>

      <div className="stat-body">
        <span className="stat-count">{count}</span>
        <span className="stat-action-hint">
          View Incidents <ArrowUpRight size={14} />
        </span>
      </div>
    </div>
  );
}
