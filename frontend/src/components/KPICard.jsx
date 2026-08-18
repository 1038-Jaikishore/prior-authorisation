import React from 'react';
import './KPICard.css';

export default function KPICard({ title, value, subtitle, type }) {
  return (
    <div className={`kpi-card glass-panel ${type || 'default'}`}>
      <div className="kpi-title">{title}</div>
      <div className="kpi-value">{value}</div>
      {subtitle && <div className="kpi-subtitle">{subtitle}</div>}
    </div>
  );
}
