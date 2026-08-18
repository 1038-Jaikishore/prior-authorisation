import React, { useState } from 'react';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import NewRequest from './pages/NewRequest';
import AuditTrail from './pages/AuditTrail';
import PolicyExplorer from './pages/PolicyExplorer';
import './index.css';

function App() {
  const [currentView, setCurrentView] = useState('dashboard');
  const [latestAuditData, setLatestAuditData] = useState(null);

  const renderView = () => {
    switch(currentView) {
      case 'dashboard':
        return <Dashboard />;
      case 'new-request':
        return <NewRequest setLatestAuditData={setLatestAuditData} setCurrentView={setCurrentView} />;
      case 'audit':
        return <AuditTrail data={latestAuditData} />;
      case 'policy':
        return <PolicyExplorer />;
      default:
        return (
          <div className="glass-panel p-6 animate-fade-in text-center mt-10">
            <h2>Coming Soon</h2>
            <p className="text-subtle">This module is under development.</p>
          </div>
        );
    }
  };

  return (
    <Layout currentView={currentView} setCurrentView={setCurrentView}>
      {renderView()}
    </Layout>
  );
}

export default App;
