import React from 'react';
import Sidebar from './Sidebar';
import './Layout.css';

export default function Layout({ children, currentView, setCurrentView }) {
  return (
    <div className="app-layout">
      <Sidebar currentView={currentView} setCurrentView={setCurrentView} />
      <div className="main-wrapper">
        <header className="top-header">
          <div className="search-bar">
            <span className="search-icon">🔍</span>
            <input type="text" placeholder="Search authorization ID, patient or request..." />
          </div>
          <div className="header-actions">
            <div className="status-indicator">
              <span className="status-dot"></span> Systems healthy
            </div>
            <button className="notification-btn">
              <span className="bell-icon">🔔</span>
              <span className="badge">4</span>
            </button>
            <div className="user-profile-top">
              <div className="avatar-sm">JM</div>
              <div className="user-info-top">
                <span className="user-name-top">Joanna Mercer, RN</span>
                <span className="user-role-top">Utilization Management</span>
              </div>
            </div>
          </div>
        </header>
        <main className="main-content">
          {children}
        </main>
      </div>
    </div>
  );
}
