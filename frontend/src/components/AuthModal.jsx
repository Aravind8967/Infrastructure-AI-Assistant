import React, { useState } from 'react';
import { ShieldAlert, User, Lock, Briefcase } from 'lucide-react';

export default function AuthModal({ onLogin }) {
  const [isSignUp, setIsSignUp] = useState(false);
  const [userName, setUserName] = useState('');
  const [password, setPassword] = useState('');
  const [userRole, setUserRole] = useState('Engineer');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!userName.trim() || !password.trim()) {
      setError('Please fill in all required fields.');
      return;
    }

    setLoading(true);

    try {
      const endpoint = isSignUp ? '/api/auth/signup' : '/api/auth/login';
      const bodyData = isSignUp 
        ? { user_name: userName.trim(), user_role: userRole, user_pass: password }
        : { user_name: userName.trim(), password: password };

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(bodyData),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Authentication failed');
      }

      onLogin(data.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '16px' }}>
          <div className="brand-logo" style={{ width: '48px', height: '48px' }}>
            <ShieldAlert size={28} />
          </div>
        </div>

        <h1 className="auth-title">SwarmOps</h1>
        <p className="auth-subtitle">
          {isSignUp ? 'Create an account for Incident AI' : 'Sign in to Incident Manager Assistant'}
        </p>

        {error && <div className="error-banner">{error}</div>}

        <form onSubmit={handleSubmit} className="auth-form" style={{ marginTop: '16px' }}>
          <div className="form-group">
            <label className="form-label">Username</label>
            <div style={{ position: 'relative' }}>
              <input
                type="text"
                className="form-input"
                style={{ width: '100%', paddingLeft: '40px' }}
                placeholder="Enter your username"
                value={userName}
                onChange={(e) => setUserName(e.target.value)}
                required
              />
              <User size={18} style={{ position: 'absolute', left: '12px', top: '12px', color: '#9ca3af' }} />
            </div>
          </div>

          {isSignUp && (
            <div className="form-group">
              <label className="form-label">Role</label>
              <div style={{ position: 'relative' }}>
                <input
                  type="text"
                  className="form-input"
                  style={{ width: '100%', paddingLeft: '40px' }}
                  placeholder="e.g. DevOps Engineer, Admin"
                  value={userRole}
                  onChange={(e) => setUserRole(e.target.value)}
                />
                <Briefcase size={18} style={{ position: 'absolute', left: '12px', top: '12px', color: '#9ca3af' }} />
              </div>
            </div>
          )}

          <div className="form-group">
            <label className="form-label">Password</label>
            <div style={{ position: 'relative' }}>
              <input
                type="password"
                className="form-input"
                style={{ width: '100%', paddingLeft: '40px' }}
                placeholder="Enter password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <Lock size={18} style={{ position: 'absolute', left: '12px', top: '12px', color: '#9ca3af' }} />
            </div>
          </div>

          <button type="submit" className="btn-auth" disabled={loading}>
            {loading ? 'Processing...' : isSignUp ? 'Sign Up' : 'Log In'}
          </button>
        </form>

        <div className="auth-toggle">
          {isSignUp ? 'Already have an account?' : "Don't have an account?"}
          <span className="auth-toggle-link" onClick={() => { setIsSignUp(!isSignUp); setError(''); }}>
            {isSignUp ? 'Log In' : 'Sign Up'}
          </span>
        </div>
      </div>
    </div>
  );
}
