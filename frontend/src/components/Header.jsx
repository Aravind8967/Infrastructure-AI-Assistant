import React from 'react';
import { ShieldAlert, LogOut, UserCheck } from 'lucide-react';

export default function Header({ user, onLogout }) {
  return (
    <header className="app-header">
      <div className="brand-section">
        <div className="brand-logo">
          <ShieldAlert size={22} />
        </div>
        <div className="brand-name">SwarmOps Incident AI</div>
      </div>

      <div className="header-actions">
        <div className="status-pill">
          <div className="status-dot"></div>
          <span>Backend Live</span>
        </div>

        {user && (
          <div className="user-badge">
            <div className="user-avatar">
              {user.user_name ? user.user_name[0].toUpperCase() : 'U'}
            </div>
            <div>
              <span style={{ fontWeight: 600 }}>{user.user_name}</span>
              <span style={{ fontSize: '0.75rem', color: '#9ca3af', marginLeft: '6px' }}>
                ({user.user_role || 'User'})
              </span>
            </div>
          </div>
        )}

        <button className="btn-logout" onClick={onLogout} title="Log out of session">
          <LogOut size={16} />
          <span>Logout</span>
        </button>
      </div>
    </header>
  );
}
