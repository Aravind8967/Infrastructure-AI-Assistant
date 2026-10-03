import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import AuthModal from './components/AuthModal';
import StatCard from './components/StatCard';
import IncidentsListModal from './components/IncidentsListModal';
import IncidentDetailModal from './components/IncidentDetailModal';
import AIChatInterface from './components/AIChatInterface';
import { AlertCircle, Clock, AlertTriangle, CheckCircle } from 'lucide-react';

export default function App() {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('swarmops_user');
    return saved ? JSON.parse(saved) : null;
  });

  const [stats, setStats] = useState({
    total: 0,
    open: 0,
    in_progress: 0,
    pending: 0,
    closed: 0,
  });

  const [selectedState, setSelectedState] = useState(null);
  const [selectedStateTitle, setSelectedStateTitle] = useState('');
  const [selectedIncidentId, setSelectedIncidentId] = useState(null);
  const [injectedPrompt, setInjectedPrompt] = useState(null);

  useEffect(() => {
    if (user) {
      fetchStats();
    }
  }, [user]);

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/incidents/stats');
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Error fetching incident stats:', err);
    }
  };

  const handleLogin = (userData) => {
    setUser(userData);
    localStorage.setItem('swarmops_user', JSON.stringify(userData));
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('swarmops_user');
  };

  const handleStatCardClick = (stateKey, title) => {
    setSelectedState(stateKey);
    setSelectedStateTitle(title);
  };

  const handleAskAIFromDetail = (promptText) => {
    setInjectedPrompt(promptText);
  };

  if (!user) {
    return <AuthModal onLogin={handleLogin} />;
  }

  return (
    <div className="app-container">
      <Header user={user} onLogout={handleLogout} />

      <main className="dashboard-content">
        {/* Top 4 Stat Cards matching user wireframe */}
        <div className="stats-grid">
          <StatCard
            title="In - Progress Incidents"
            count={stats.in_progress}
            stateKey="In Progress"
            type="in-progress"
            icon={Clock}
            onClick={handleStatCardClick}
          />
          <StatCard
            title="Open Incidents"
            count={stats.open}
            stateKey="Open"
            type="open"
            icon={AlertCircle}
            onClick={handleStatCardClick}
          />
          <StatCard
            title="Pending Incidents"
            count={stats.pending}
            stateKey="Pending"
            type="pending"
            icon={AlertTriangle}
            onClick={handleStatCardClick}
          />
          <StatCard
            title="Closed Incidents"
            count={stats.closed}
            stateKey="Closed"
            type="closed"
            icon={CheckCircle}
            onClick={handleStatCardClick}
          />
        </div>

        {/* AI Interface spanning the main workspace below stat cards */}
        <AIChatInterface user={user} promptInject={injectedPrompt} />
      </main>

      {/* Incidents List Modal when Stat Card is clicked */}
      {selectedState && (
        <IncidentsListModal
          stateKey={selectedState}
          title={selectedStateTitle}
          onClose={() => setSelectedState(null)}
          onSelectIncident={(id) => setSelectedIncidentId(id)}
        />
      )}

      {/* Incident Detail Modal when Incident Anchor Link is clicked */}
      {selectedIncidentId && (
        <IncidentDetailModal
          incidentId={selectedIncidentId}
          onClose={() => setSelectedIncidentId(null)}
          onAskAI={handleAskAIFromDetail}
        />
      )}
    </div>
  );
}
