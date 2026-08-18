import React from 'react';
import KPICard from '../components/KPICard';
import './Dashboard.css';

export default function Dashboard({ setCurrentView }) {
  return (
    <div className="dashboard animate-fade-in">
      <header className="dashboard-header flex-between align-start mb-6">
        <div>
          <h1>Operations dashboard</h1>
          <p className="text-subtle">Live view of prior authorization throughput, decision mix and pipeline health.</p>
        </div>
        <button 
          className="glass-button primary new-auth-btn"
          onClick={() => setCurrentView('new-request')}
        >
          New prior authorization
        </button>
      </header>

      <section className="kpi-grid">
        <KPICard title="Total PA requests" value="10" subtitle="Active queue today" type="primary" />
        <KPICard title="Approved" value="4" subtitle="Auto-decided ≥ 0.85" type="approve" />
        <KPICard title="Denied" value="2" subtitle="Policy exclusion or failed criteria" type="deny" />
        <KPICard title="Pending" value="2" subtitle="Awaiting data or lookup" type="pend" />
        <KPICard title="Nurse Review" value="2" subtitle="Routed for human adjudication" type="nurse_review" />
        <KPICard title="Average Confidence" value="0.80" subtitle="Weighted across 5 factors" type="nurse_review" />
        <KPICard title="Avg Processing Time" value="34.5s" subtitle="Upload to explanation" type="nurse_review" />
      </section>

      <div className="dashboard-main-grid">
        <section className="glass-panel p-6">
          <h3 className="mb-2">Decision distribution</h3>
          <p className="text-subtle mb-6">Current queue by decision class</p>
          
          <div className="chart-layout">
            <div className="mock-donut-chart">
              {/* CSS Donut Chart */}
              <div className="donut-hole"></div>
            </div>
            
            <div className="chart-legend">
              <div className="legend-item">
                <div className="legend-label">
                  <span className="dot dot-approve"></span> Approve
                </div>
                <div className="legend-stats">
                  <span className="count">4</span>
                  <span className="pct">40%</span>
                </div>
              </div>
              <div className="legend-item">
                <div className="legend-label">
                  <span className="dot dot-deny"></span> Deny
                </div>
                <div className="legend-stats">
                  <span className="count">2</span>
                  <span className="pct">20%</span>
                </div>
              </div>
              <div className="legend-item">
                <div className="legend-label">
                  <span className="dot dot-pend"></span> Pend
                </div>
                <div className="legend-stats">
                  <span className="count">2</span>
                  <span className="pct">20%</span>
                </div>
              </div>
              <div className="legend-item">
                <div className="legend-label">
                  <span className="dot dot-review"></span> Nurse review
                </div>
                <div className="legend-stats">
                  <span className="count">2</span>
                  <span className="pct">20%</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="glass-panel p-6">
          <div className="flex-between mb-4">
            <div>
              <h3 className="mb-2">Pipeline health</h3>
              <p className="text-subtle">8-phase evaluation engine</p>
            </div>
            <div className="actions flex gap-4">
              <button className="glass-button primary flex gap-2"><span className="icon">🚀</span> Browse</button>
              <button className="glass-button flex gap-2"><span className="icon">💬</span> Comment</button>
            </div>
          </div>
          
          <div className="health-grid mt-6">
            <div className="health-stat">
              <div className="health-val">96.2%</div>
              <div className="health-lbl">Auto-coding accuracy</div>
            </div>
            <div className="health-stat">
              <div className="health-val">0.91</div>
              <div className="health-lbl">RAG retrieval precision</div>
            </div>
            <div className="health-stat">
              <div className="health-val">88.4%</div>
              <div className="health-lbl">Deterministic rule pass rate</div>
            </div>
            <div className="health-stat">
              <div className="health-val">71.5%</div>
              <div className="health-lbl">Auto-decision rate</div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
