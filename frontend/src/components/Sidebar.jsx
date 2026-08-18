import React from 'react';
import './Sidebar.css';

export default function Sidebar({ currentView, setCurrentView }) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: '⊞' },
    { id: 'new-request', label: 'New Prior Authorization', icon: '📄' },
    { id: 'requests', label: 'Authorization Requests', icon: '📋' },
    { id: 'results', label: 'Decision Results', icon: '✅' },
    { id: 'policy', label: 'Policy Explorer', icon: '🏛️' },
    { id: 'analytics', label: 'Analytics', icon: '📊' },
    { id: 'audit', label: 'Audit Trail', icon: '📉' },
    { id: 'settings', label: 'Settings', icon: '⚙️' }
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo-shield">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.956 11.956 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
        </div>
        <div className="brand-text">
          <h2>CMS PA Intelligence</h2>
          <span className="brand-sub">Decision support</span>
        </div>
      </div>
      
      <nav className="sidebar-nav">
        {navItems.map(item => (
          <button 
            key={item.id}
            className={`nav-item ${currentView === item.id ? 'active' : ''}`}
            onClick={() => setCurrentView(item.id)}
          >
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-label">{item.label}</span>
          </button>
        ))}
      </nav>
      
      <div className="sidebar-footer">
        <button className="collapse-btn">
          <span>⟨</span> Collapse
        </button>
      </div>
    </aside>
  );
}
