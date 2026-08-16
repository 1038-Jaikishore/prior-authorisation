import { useState, useEffect } from 'react';

interface RequestItem {
  request_id: string;
  patient_id: string;
  provider_id: string;
  requested_procedure_code: { display_value: string };
  diagnosis_code: any;
  request_date: string;
  clinical_indication?: string;
  medical_necessity?: string;
  provider_justification?: string;
  previous_treatment_info?: string;
}

export default function App() {
  const [requests, setRequests] = useState<RequestItem[]>([]);
  const [selectedRequestId, setSelectedRequestId] = useState<string>('');
  const [selectedRequest, setSelectedRequest] = useState<RequestItem | null>(null);
  
  // Form controls
  const [overrideState, setOverrideState] = useState<string>('CO');
  const [overrideDate, setOverrideDate] = useState<string>('');
  
  // Loading & Outputs
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [intakeData, setIntakeData] = useState<any | null>(null);
  const [evaluationData, setEvaluationData] = useState<any | null>(null);
  const [decisionData, setDecisionData] = useState<any | null>(null);
  const [activeTab, setActiveTab] = useState<string>('evidence');

  // Volume 8 Reviewer Workflow States
  const [casesQueue, setCasesQueue] = useState<any[]>([]);
  const [queueFilter, setQueueFilter] = useState<string>('ALL');
  const [explanationData, setExplanationData] = useState<any | null>(null);
  const [reviewHistory, setReviewHistory] = useState<any[]>([]);
  const [auditEvents, setAuditEvents] = useState<any[]>([]);

  // Reviewer Action Form States
  const [reviewerId, setReviewerId] = useState<string>('demo_reviewer_1');
  const [actionType, setActionType] = useState<string>('ACCEPT_RECOMMENDATION');
  const [actionReason, setActionReason] = useState<string>('');
  const [overrideDisp, setOverrideDisp] = useState<string>('APPROVE');
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const loadCasesQueue = () => {
    fetch('http://localhost:8000/api/review/cases')
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load requests from backend.");
        return res.json();
      })
      .then((data) => {
        setCasesQueue(data);
      })
      .catch((err) => console.error("Error loading case queue list:", err));
  };

  const fetchCaseDetails = async (reqId: string) => {
    try {
      const caseRes = await fetch(`http://localhost:8000/api/review/cases/${reqId}`);
      if (caseRes.ok) {
        const caseVal = await caseRes.json();
        setEvaluationData(caseVal.evaluation_bundle);
        setDecisionData(caseVal.decision_support_result);
        setExplanationData(caseVal.decision_explanation);
        setReviewHistory(caseVal.review_history || []);
        setAuditEvents(caseVal.audit_events || []);
      }
    } catch (err: any) {
      console.error("Failed to load case review context details: ", err);
    }
  };

  // Load request list on mount
  useEffect(() => {
    fetch('http://localhost:8000/api/prior-auth')
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load requests from backend.");
        return res.json();
      })
      .then((data) => {
        setRequests(data);
        if (data.length > 0) {
          handleSelectRequest(data[0].request_id, data);
        }
      })
      .catch((err) => setError(err.message));
      
    loadCasesQueue();
  }, []);

  const handleSelectRequest = (reqId: string, list: RequestItem[] = requests) => {
    setSelectedRequestId(reqId);
    setIntakeData(null);
    setEvaluationData(null);
    setDecisionData(null);
    setExplanationData(null);
    setReviewHistory([]);
    setAuditEvents([]);
    setActionReason('');
    setActionMessage(null);
    setError(null);
    const found = list.find((r) => r.request_id === reqId);
    if (found) {
      setSelectedRequest(found);
      setOverrideDate(found.request_date);
      setOverrideState('CO');
      
      // Auto-load details if request is selected
      fetchCaseDetails(reqId);
    }
  };

  const handleActionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRequestId) return;
    setActionMessage(null);
    setError(null);
    
    try {
      const params = new URLSearchParams({
        action: actionType,
        reason: actionReason,
        reviewer_id: reviewerId
      });
      if (actionType === 'OVERRIDE_RECOMMENDATION') {
        params.append('intended_disposition', overrideDisp);
      }
      
      const res = await fetch(`http://localhost:8000/api/review/cases/${selectedRequestId}/action?${params.toString()}`, {
        method: 'POST'
      });
      if (!res.ok) {
        const detail = await res.json();
        throw new Error(detail.detail || "Failed to submit reviewer action.");
      }
      
      setActionMessage("✓ Reviewer action submitted and logged in audit timeline successfully.");
      setActionReason('');
      
      // Reload queue and history
      loadCasesQueue();
      await fetchCaseDetails(selectedRequestId);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleRouteRetrieve = () => {
    if (!selectedRequestId) return;
    setLoading(true);
    setError(null);
    setIntakeData(null);
    setEvaluationData(null);
    setDecisionData(null);

    const url = `http://localhost:8000/api/prior-auth/${selectedRequestId}/route-and-retrieve?override_state=${overrideState}&override_date=${overrideDate}`;
    
    fetch(url, { method: 'POST' })
      .then((res) => {
        if (!res.ok) throw new Error("Workflow routing request failed.");
        return res.json();
      })
      .then((data) => {
        setIntakeData(data);
        setLoading(false);
        setActiveTab('evidence');
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  };

  const handleEvaluate = async () => {
    if (!selectedRequestId) return;
    setLoading(true);
    setError(null);
    setEvaluationData(null);
    setDecisionData(null);
    setIntakeData(null);

    try {
      const intakeRes = await fetch(`http://localhost:8000/api/prior-auth/${selectedRequestId}/route-and-retrieve?override_state=${overrideState}&override_date=${overrideDate}`, { method: 'POST' });
      if (!intakeRes.ok) throw new Error("Intake compilation & policy routing failed.");
      const intakeVal = await intakeRes.json();
      setIntakeData(intakeVal);

      const evalRes = await fetch(`http://localhost:8000/api/prior-auth/${selectedRequestId}/evaluate?override_state=${overrideState}&override_date=${overrideDate}`, { method: 'POST' });
      if (!evalRes.ok) throw new Error("Policy requirement clinical evaluation failed.");
      const evalVal = await evalRes.json();
      setEvaluationData(evalVal);

      const decisionRes = await fetch(`http://localhost:8000/api/prior-auth/${selectedRequestId}/decision-support`, { method: 'POST' });
      if (!decisionRes.ok) throw new Error("Prior authorization decision support computation failed.");
      const decisionVal = await decisionRes.json();
      setDecisionData(decisionVal);
      
      setLoading(false);
      setActiveTab('decision');
    } catch (err: any) {
      setError(err.message);
      setLoading(false);
    }
  };

  return (
    <div className="container">
      {/* Header Banner */}
      <header className="header">
        <div>
          <h1>CMS Prior Authorization Intake Dashboard</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginTop: '6px' }}>
            Structured evidence packet compiler and policy routing/RAG lookup engine.
          </p>
        </div>
        <div className="banner-support">
          <strong>PROTOTYPE DECISION SUPPORT ENGINE</strong><br />
          This system assists with clinical text indexing, retrieval, and deterministic policy routing. 
          Final coverage decisions reside strictly with Medicare human reviewers.
        </div>
      </header>

      {/* Main Grid */}
      <div className="grid-main">
        {/* Left Form Panel */}
        <aside className="card" style={{ alignSelf: 'start' }}>
          <h2 className="card-title">Intake Case Setup</h2>
          
          <div className="form-group">
            <label className="form-label">Select Synthetic Case Request</label>
            <select
              className="form-control"
              value={selectedRequestId}
              onChange={(e) => handleSelectRequest(e.target.value)}
            >
              {requests.map((r) => (
                <option key={r.request_id} value={r.request_id}>
                  {r.request_id} (Procedure: {r.requested_procedure_code.display_value})
                </option>
              ))}
            </select>
          </div>

          {selectedRequest && (
            <div style={{ marginTop: '20px', borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
              <div className="form-group">
                <span className="form-label">Patient ID</span>
                <code style={{ fontSize: '13px' }}>{selectedRequest.patient_id}</code>
              </div>
              <div className="form-group">
                <span className="form-label">Provider ID</span>
                <code style={{ fontSize: '13px' }}>{selectedRequest.provider_id}</code>
              </div>
              <div className="form-group">
                <span className="form-label">Requested CPT/HCPCS</span>
                <span className="badge badge-info">{selectedRequest.requested_procedure_code.display_value}</span>
              </div>
              <div className="form-group">
                <span className="form-label">Urgency</span>
                <span>{(selectedRequest as any).urgency || 'Standard'}</span>
              </div>
              
              <div className="form-group">
                <label className="form-label">Override Routing State</label>
                <select
                  className="form-control"
                  value={overrideState}
                  onChange={(e) => setOverrideState(e.target.value)}
                >
                  <option value="CO">Colorado (CO)</option>
                  <option value="TX">Texas (TX)</option>
                  <option value="FL">Florida (FL)</option>
                  <option value="CA">California (CA)</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Override Date of Service</label>
                <input
                  type="date"
                  className="form-control"
                  value={overrideDate}
                  onChange={(e) => setOverrideDate(e.target.value)}
                />
              </div>

              <button
                className="btn-primary"
                onClick={handleRouteRetrieve}
                disabled={loading}
                style={{ marginTop: '12px', width: '100%' }}
              >
                {loading ? <span className="spinner"></span> : null}
                Compile Evidence & Route Policy
              </button>
              
              <button
                className="btn-primary"
                onClick={handleEvaluate}
                disabled={loading}
                style={{ 
                  marginTop: '10px', 
                  width: '100%', 
                  background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                  boxShadow: '0 4px 12px rgba(79, 70, 229, 0.2)' 
                }}
              >
                {loading ? <span className="spinner"></span> : null}
                Run Policy Evaluation Engine
              </button>
            </div>
          )}

          {/* Case Review Queue Section */}
          <div style={{ marginTop: '20px', borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
            <h3 style={{ fontSize: '14px', margin: '0 0 10px 0', color: 'var(--text-primary)' }}>Case Review Queue</h3>
            
            <div className="form-group" style={{ marginBottom: '12px' }}>
              <label className="form-label" style={{ fontSize: '11px' }}>Filter Disposition</label>
              <select
                className="form-control"
                style={{ fontSize: '12px', padding: '6px' }}
                value={queueFilter}
                onChange={(e) => setQueueFilter(e.target.value)}
              >
                <option value="ALL">All Recommendations</option>
                <option value="APPROVE">Approve</option>
                <option value="DENY">Deny</option>
                <option value="PEND">Pend</option>
                <option value="NURSE_REVIEW">Nurse Review</option>
                <option value="DECISION_SUPPORT_UNAVAILABLE">Decision Support N/A</option>
              </select>
            </div>

            <div style={{ maxHeight: '320px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px', paddingRight: '4px' }}>
              {(() => {
                const filtered = casesQueue.filter((c: any) => queueFilter === 'ALL' || c.current_recommendation === queueFilter);
                if (filtered.length === 0) {
                  return <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textAlign: 'center', padding: '12px' }}>No cases found.</div>;
                }
                return filtered.map((c: any) => {
                  const statusColors: any = {
                    APPROVE: '#10B981',
                    DENY: '#EF4444',
                    PEND: '#F59E0B',
                    NURSE_REVIEW: '#8B5CF6',
                    DECISION_SUPPORT_UNAVAILABLE: '#9CA3AF',
                    AWAITING_INTAKE: '#6B7280'
                  };
                  const badgeColor = statusColors[c.current_recommendation] || '#fff';
                  const isSelected = c.authorization_id === selectedRequestId;
                  return (
                    <div
                      key={c.authorization_id}
                      onClick={() => handleSelectRequest(c.authorization_id)}
                      style={{
                        background: isSelected ? 'rgba(99, 102, 241, 0.08)' : 'rgba(255,255,255,0.01)',
                        border: isSelected ? '1px solid #6366f1' : '1px solid var(--border-color)',
                        padding: '10px',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '4px'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '12px', fontWeight: 'bold', color: isSelected ? '#818cf8' : 'var(--text-primary)' }}>
                          {c.authorization_id}
                        </span>
                        <span className="badge" style={{ fontSize: '10px', padding: '2px 6px', background: `${badgeColor}15`, color: badgeColor, border: `1px solid ${badgeColor}30` }}>
                          {c.current_recommendation.replace('_', ' ')}
                        </span>
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                        Patient: <strong>{c.patient_name}</strong>
                      </div>
                      <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.3)', display: 'flex', justifyContent: 'space-between' }}>
                        <span>HCPCS: <code>{c.requested_service}</code></span>
                        <span>Last Updated: {c.last_updated ? new Date(c.last_updated).toLocaleDateString() : 'N/A'}</span>
                      </div>
                    </div>
                  );
                });
              })()}
            </div>
          </div>
        </aside>

        {/* Right Dashboard Panel */}
        <main className="card" style={{ minHeight: '500px' }}>
          {loading && (
            <div className="loading-container">
              <span className="spinner" style={{ width: '40px', height: '40px' }}></span>
              <p style={{ color: 'var(--text-secondary)' }}>Compiling clinical evidence and routing CMS regulations...</p>
            </div>
          )}

          {error && (
            <div className="alert-box" style={{ background: 'rgba(239, 68, 68, 0.1)', borderColor: 'rgba(239, 68, 68, 0.2)', color: '#F87171' }}>
              <div className="alert-title">Intake Process Failed</div>
              <p>{error}</p>
            </div>
          )}

          {!loading && !error && !intakeData && (
            <div style={{ textAlign: 'center', padding: '80px 20px', color: 'var(--text-secondary)' }}>
              <h3 style={{ color: 'var(--text-primary)', marginBottom: '12px' }}>Awaiting Case Execution</h3>
              <p>Select a synthetic patient request in the panel and trigger the intake workflow to review the structured evidence packet.</p>
            </div>
          )}

          {!loading && !error && intakeData && (
            <div>
              {/* Warnings Block */}
              {intakeData.warnings && intakeData.warnings.length > 0 && (
                <div className="alert-box">
                  <div className="alert-title">Intake Warnings & Missing Clinical Facts</div>
                  <ul className="alert-list">
                    {intakeData.warnings.map((w: string, i: number) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Tabs list */}
              <div className="tabs">
                <button
                  className={`tab-btn ${activeTab === 'evidence' ? 'active' : ''}`}
                  onClick={() => setActiveTab('evidence')}
                >
                  Clinical Evidence Packet
                </button>
                <button
                  className={`tab-btn ${activeTab === 'routing' ? 'active' : ''}`}
                  onClick={() => setActiveTab('routing')}
                >
                  CMS Policy Routing
                </button>
                <button
                  className={`tab-btn ${activeTab === 'rag' ? 'active' : ''}`}
                  onClick={() => setActiveTab('rag')}
                >
                  Retrieved Policy Snippets (RAG)
                </button>
                {evaluationData && (
                  <>
                    <button
                      className={`tab-btn ${activeTab === 'evaluation' ? 'active' : ''}`}
                      onClick={() => setActiveTab('evaluation')}
                      style={{ borderBottomColor: activeTab === 'evaluation' ? '#6366f1' : 'transparent', color: activeTab === 'evaluation' ? '#818cf8' : 'var(--text-secondary)' }}
                    >
                      💡 Requirements Evaluation
                    </button>
                    <button
                      className={`tab-btn ${activeTab === 'validation' ? 'active' : ''}`}
                      onClick={() => setActiveTab('validation')}
                      style={{ borderBottomColor: activeTab === 'validation' ? '#6366f1' : 'transparent', color: activeTab === 'validation' ? '#818cf8' : 'var(--text-secondary)' }}
                    >
                      🛡️ Coding Validation
                    </button>
                  </>
                )}
                {decisionData && (
                  <button
                    className={`tab-btn ${activeTab === 'decision' ? 'active' : ''}`}
                    onClick={() => setActiveTab('decision')}
                    style={{ borderBottomColor: activeTab === 'decision' ? '#10b981' : 'transparent', color: activeTab === 'decision' ? '#34d399' : 'var(--text-secondary)' }}
                  >
                    ⚖️ Decision Support
                  </button>
                )}
                {explanationData && (
                  <button
                    className={`tab-btn ${activeTab === 'explanation' ? 'active' : ''}`}
                    onClick={() => setActiveTab('explanation')}
                    style={{ borderBottomColor: activeTab === 'explanation' ? '#8b5cf6' : 'transparent', color: activeTab === 'explanation' ? '#a78bfa' : 'var(--text-secondary)' }}
                  >
                    📝 Reviewer Explanation & Action
                  </button>
                )}
                <button
                  className={`tab-btn ${activeTab === 'provenance' ? 'active' : ''}`}
                  onClick={() => setActiveTab('provenance')}
                >
                  Audit Trace & Provenance
                </button>
                {auditEvents.length > 0 && (
                  <button
                    className={`tab-btn ${activeTab === 'audit_trail' ? 'active' : ''}`}
                    onClick={() => setActiveTab('audit_trail')}
                    style={{ borderBottomColor: activeTab === 'audit_trail' ? '#3b82f6' : 'transparent', color: activeTab === 'audit_trail' ? '#60a5fa' : 'var(--text-secondary)' }}
                  >
                    📋 Workflow Audit Trail
                  </button>
                )}
              </div>

              {/* Tab 1: Clinical Evidence Packet */}
              {activeTab === 'evidence' && (
                <div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px' }}>
                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                      <h4 style={{ margin: '0 0 12px 0', fontSize: '14px', color: 'var(--text-secondary)' }}>Patient Demographics</h4>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px' }}>
                        <div><strong>First Name:</strong> {intakeData.clinical_evidence_packet.demographics.first_name}</div>
                        <div><strong>Last Name:</strong> {intakeData.clinical_evidence_packet.demographics.last_name}</div>
                        <div><strong>Age:</strong> {intakeData.clinical_evidence_packet.demographics.age} ({intakeData.clinical_evidence_packet.demographics.dob})</div>
                        <div><strong>Gender:</strong> {intakeData.clinical_evidence_packet.demographics.gender}</div>
                      </div>
                    </div>
                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
                      <h4 style={{ margin: '0 0 12px 0', fontSize: '14px', color: 'var(--text-secondary)' }}>Insurance & Location</h4>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px' }}>
                        <div><strong>Plan Type:</strong> {intakeData.clinical_evidence_packet.demographics.insurance_plan}</div>
                        <div><strong>Member ID:</strong> {intakeData.clinical_evidence_packet.demographics.member_id}</div>
                        <div><strong>Resolved State:</strong> <span className="badge badge-info">{intakeData.clinical_evidence_packet.demographics.state_code}</span></div>
                      </div>
                    </div>
                  </div>

                  {/* Conditions List */}
                  <h3 style={{ fontSize: '16px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px', margin: '24px 0 12px 0' }}>Patient Diagnosis History</h3>
                  {intakeData.clinical_evidence_packet.conditions.length > 0 ? (
                    <table className="evidence-table">
                      <thead>
                        <tr>
                          <th>Diagnosis Code</th>
                          <th>Name</th>
                          <th>Onset Date</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {intakeData.clinical_evidence_packet.conditions.map((c: any, i: number) => (
                          <tr key={i}>
                            <td><code>{c.diagnosis_code?.display_value || c.diagnosis_code}</code></td>
                            <td>{c.diagnosis_name}</td>
                            <td>{c.onset_date}</td>
                            <td><span className="badge badge-success">{c.condition_type || 'Active'}</span></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>No diagnosis conditions recorded.</p>
                  )}

                  {/* Diagnostic Results */}
                  <h3 style={{ fontSize: '16px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px', margin: '28px 0 12px 0' }}>Laboratory & Diagnostic Results</h3>
                  {intakeData.clinical_evidence_packet.diagnostic_results.length > 0 ? (
                    <table className="evidence-table">
                      <thead>
                        <tr>
                          <th>Test Name</th>
                          <th>Result Value</th>
                          <th>Reference Range</th>
                          <th>Recorded Date</th>
                          <th>Alert Flag</th>
                        </tr>
                      </thead>
                      <tbody>
                        {intakeData.clinical_evidence_packet.diagnostic_results.map((r: any, i: number) => (
                          <tr key={i}>
                            <td><strong>{r.test_name}</strong></td>
                            <td>{r.result_value}</td>
                            <td>{r.reference_range}</td>
                            <td>{r.test_date}</td>
                            <td>
                              {r.abnormal_flag === 'Y' || r.abnormal_flag === true ? (
                                <span className="badge badge-danger">Abnormal</span>
                              ) : (
                                <span className="badge badge-success">Normal</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>No lab test results recorded.</p>
                  )}

                  {/* Medications attempted */}
                  <h3 style={{ fontSize: '16px', borderBottom: '1px solid var(--border-color)', paddingBottom: '8px', margin: '28px 0 12px 0' }}>Conservative Medication History</h3>
                  {intakeData.clinical_evidence_packet.medications.length > 0 ? (
                    <table className="evidence-table">
                      <thead>
                        <tr>
                          <th>Medication Name</th>
                          <th>Dosage</th>
                          <th>Start Date</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {intakeData.clinical_evidence_packet.medications.map((m: any, i: number) => (
                          <tr key={i}>
                            <td>{m.medication_name}</td>
                            <td>{m.dosage}</td>
                            <td>{m.start_date}</td>
                            <td><span className="badge badge-info">{m.status}</span></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>No prior medication therapy recorded.</p>
                  )}
                </div>
              )}

              {/* Tab 2: CMS Policy Routing */}
              {activeTab === 'routing' && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                    <h3 style={{ fontSize: '16px', margin: 0 }}>Resolved Deterministic Routing Rules</h3>
                    <span className={`badge ${intakeData.policy_routing.routing_status === 'RESOLVED' ? 'badge-success' : 'badge-warning'}`}>
                      {intakeData.policy_routing.routing_status}
                    </span>
                  </div>

                  {/* NCD matches */}
                  <h4 style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '8px' }}>Matched National Coverage Determinations (NCDs)</h4>
                  {intakeData.policy_routing.applicable_ncds.length > 0 ? (
                    <table className="evidence-table" style={{ marginBottom: '24px' }}>
                      <thead>
                        <tr>
                          <th>NCD ID</th>
                          <th>Benefit Category</th>
                          <th>Effective Date</th>
                          <th>Source Document ID</th>
                        </tr>
                      </thead>
                      <tbody>
                        {intakeData.policy_routing.applicable_ncds.map((n: any, i: number) => (
                          <tr key={i}>
                            <td><strong>NCD {n.ncd_id}</strong></td>
                            <td>{n.benefit_category}</td>
                            <td>{n.effective_date}</td>
                            <td><code>{n.document_display_id}</code></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '24px' }}>No matching NCD rules resolved.</p>
                  )}

                  {/* LCD matches */}
                  <h4 style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '8px' }}>Matched Local Coverage Determinations (LCDs)</h4>
                  {intakeData.policy_routing.applicable_lcds.length > 0 ? (
                    <table className="evidence-table" style={{ marginBottom: '24px' }}>
                      <thead>
                        <tr>
                          <th>LCD ID</th>
                          <th>LCD Title</th>
                          <th>Version</th>
                          <th>Effective Date</th>
                        </tr>
                      </thead>
                      <tbody>
                        {intakeData.policy_routing.applicable_lcds.map((l: any, i: number) => (
                          <tr key={i}>
                            <td><strong>{l.lcd_id}</strong></td>
                            <td>{l.title}</td>
                            <td>v{l.version}</td>
                            <td>{l.effective_date}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '24px' }}>No matching LCD rules resolved.</p>
                  )}

                  {/* Related Articles */}
                  <h4 style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '8px' }}>Active Billing and Coding Articles</h4>
                  {intakeData.policy_routing.related_articles.length > 0 ? (
                    <table className="evidence-table">
                      <thead>
                        <tr>
                          <th>Article ID</th>
                          <th>Article Title</th>
                          <th>Version</th>
                          <th>Effective Date</th>
                        </tr>
                      </thead>
                      <tbody>
                        {intakeData.policy_routing.related_articles.map((a: any, i: number) => (
                          <tr key={i}>
                            <td><strong>{a.article_id}</strong></td>
                            <td>{a.title}</td>
                            <td>v{a.article_version}</td>
                            <td>{a.effective_date}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>No active related Articles resolved.</p>
                  )}
                </div>
              )}

              {/* Tab 3: Policy RAG Text snippets */}
              {activeTab === 'rag' && (
                <div>
                  <h3 style={{ fontSize: '16px', marginBottom: '16px' }}>Retrieved Policy Text Chunks</h3>
                  {intakeData.policy_retrieval.results.length > 0 ? (
                    <div>
                      {intakeData.policy_retrieval.results.map((item: any, i: number) => (
                        <div key={i} className="chunk-card">
                          <div className="chunk-header">
                            <div>
                              <span style={{ fontWeight: 600, marginRight: '8px' }}>
                                {item.document_type} {item.document_id} (v{item.document_version})
                              </span>
                              | Section: <code style={{ fontSize: '12px' }}>{item.section}</code>
                            </div>
                            <span className="citation-tag">{item.citation?.chunk_id || 'Citation Missing'}</span>
                          </div>
                          <div className="chunk-text">{item.text}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>No matching text snippets resolved from search index.</p>
                  )}
                </div>
              )}

              {/* Tab: Policy Requirement Evaluation */}
              {activeTab === 'evaluation' && evaluationData && (
                <div>
                  <h3 style={{ fontSize: '16px', marginBottom: '12px' }}>Clinical Policy Requirement Matching</h3>
                  
                  {/* Summary Stats */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' }}>
                    <div style={{ background: 'rgba(34, 197, 94, 0.1)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(34, 197, 94, 0.2)', textAlign: 'center' }}>
                      <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#4ADE80' }}>{evaluationData.summary.met}</div>
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>MET</div>
                    </div>
                    <div style={{ background: 'rgba(239, 68, 68, 0.1)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.2)', textAlign: 'center' }}>
                      <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#F87171' }}>{evaluationData.summary.not_met}</div>
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>NOT MET</div>
                    </div>
                    <div style={{ background: 'rgba(245, 158, 11, 0.1)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(245, 158, 11, 0.2)', textAlign: 'center' }}>
                      <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#FBBF24' }}>{evaluationData.summary.unclear}</div>
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>UNCLEAR</div>
                    </div>
                    <div style={{ background: 'rgba(156, 163, 175, 0.1)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(156, 163, 175, 0.2)', textAlign: 'center' }}>
                      <div style={{ fontSize: '20px', fontWeight: 'bold', color: '#9CA3AF' }}>{evaluationData.summary.not_applicable}</div>
                      <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>N/A</div>
                    </div>
                  </div>

                  {/* Requirements List */}
                  <table className="evidence-table">
                    <thead>
                      <tr>
                        <th>Requirement Criteria</th>
                        <th style={{ width: '120px' }}>Status</th>
                        <th>Evidence / Rationale</th>
                        <th style={{ width: '180px' }}>Citation & Source</th>
                      </tr>
                    </thead>
                    <tbody>
                      {evaluationData.requirement_evaluations.map((ev: any, idx: number) => {
                        const statusColors: any = {
                          MET: { bg: 'rgba(34, 197, 94, 0.1)', color: '#4ADE80' },
                          NOT_MET: { bg: 'rgba(239, 68, 68, 0.1)', color: '#F87171' },
                          UNCLEAR: { bg: 'rgba(245, 158, 11, 0.1)', color: '#FBBF24' },
                          NOT_APPLICABLE: { bg: 'rgba(156, 163, 175, 0.1)', color: '#9CA3AF' }
                        };
                        const col = statusColors[ev.status] || { bg: 'rgba(0,0,0,0.1)', color: '#fff' };
                        return (
                          <tr key={idx}>
                            <td>
                              <div style={{ fontWeight: 500, fontSize: '13px' }}>{ev.policy_requirement.requirement_text}</div>
                              <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                                Type: <code style={{ color: '#818cf8' }}>{ev.policy_requirement.requirement_type}</code> | Role: <strong>{ev.policy_requirement.policy_role}</strong>
                              </div>
                            </td>
                            <td>
                              <span className="badge" style={{ background: col.bg, color: col.color, display: 'inline-block', width: '100%', textAlign: 'center' }}>
                                {ev.status}
                              </span>
                            </td>
                            <td style={{ fontSize: '13px' }}>
                              <div>{ev.rationale}</div>
                              {ev.matching_evidence.length > 0 && (
                                <div style={{ marginTop: '6px', fontSize: '11px', color: '#38BDF8' }}>
                                  Matched facts: {ev.matching_evidence.map((m: any) => `${m.display_value} (${m.value})`).join(', ')}
                                </div>
                              )}
                              {ev.missing_information.length > 0 && (
                                <div style={{ marginTop: '6px', fontSize: '11px', color: '#FBBF24' }}>
                                  Missing: {ev.missing_information.join('; ')}
                                </div>
                              )}
                            </td>
                            <td style={{ fontSize: '11px' }}>
                              <div>Policy Chunk: <code>{ev.policy_citation.split(':').slice(-2).join(':')}</code></div>
                              {ev.patient_provenance.length > 0 && (
                                <div style={{ color: 'var(--text-secondary)', marginTop: '4px' }}>
                                  Patient Ref: <code>{ev.patient_provenance[0].collection}/{ev.patient_provenance[0].record_id.slice(-8)}</code>
                                </div>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>

                  {/* Missing Information Highlight */}
                  {evaluationData.missing_information.length > 0 && (
                    <div style={{ marginTop: '24px', background: 'rgba(245, 158, 11, 0.05)', border: '1px solid rgba(245, 158, 11, 0.1)', padding: '16px', borderRadius: '8px' }}>
                      <h4 style={{ color: '#FBBF24', margin: '0 0 8px 0', fontSize: '14px' }}>⚠️ Missing Clinical Information Gaps</h4>
                      <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '13px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {evaluationData.missing_information.map((info: string, i: number) => (
                          <li key={i}>{info}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Tab: Coding & Administrative Validations */}
              {activeTab === 'validation' && evaluationData && (
                <div>
                  <h3 style={{ fontSize: '16px', marginBottom: '16px' }}>Deterministic Code & Administrative Validation</h3>
                  <table className="evidence-table">
                    <thead>
                      <tr>
                        <th>Validator Rule</th>
                        <th style={{ width: '120px' }}>Status</th>
                        <th>Subject Checked</th>
                        <th>Matched Policy Document</th>
                        <th>Validation Reason / Details</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[...evaluationData.coding_validations, ...evaluationData.administrative_validations].map((val: any, idx: number) => {
                        const statusColors: any = {
                          PASS: { bg: 'rgba(34, 197, 94, 0.1)', color: '#4ADE80' },
                          FAIL: { bg: 'rgba(239, 68, 68, 0.1)', color: '#F87171' },
                          WARNING: { bg: 'rgba(245, 158, 11, 0.1)', color: '#FBBF24' },
                          UNKNOWN: { bg: 'rgba(156, 163, 175, 0.1)', color: '#9CA3AF' },
                          NOT_EVALUATED: { bg: 'rgba(156, 163, 175, 0.1)', color: '#9CA3AF' }
                        };
                        const col = statusColors[val.status] || { bg: 'rgba(0,0,0,0.1)', color: '#fff' };
                        return (
                          <tr key={idx}>
                            <td><strong>{val.validator}</strong></td>
                            <td>
                              <span className="badge" style={{ background: col.bg, color: col.color, display: 'inline-block', width: '100%', textAlign: 'center' }}>
                                {val.status}
                              </span>
                            </td>
                            <td><code>{val.subject}</code></td>
                            <td>{val.policy_document ? <code>{val.policy_document}</code> : 'N/A'}</td>
                            <td style={{ fontSize: '13px' }}>{val.reason}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Tab: Decision Support */}
              {activeTab === 'decision' && decisionData && (
                <div>
                  {/* Recommended Disposition Card */}
                  {(() => {
                    const disp = decisionData.recommended_disposition;
                    const dispColors: any = {
                      APPROVE: { bg: 'rgba(16, 185, 129, 0.1)', border: '#10B981', text: '#34D399' },
                      DENY: { bg: 'rgba(239, 68, 68, 0.1)', border: '#EF4444', text: '#F87171' },
                      PEND: { bg: 'rgba(245, 158, 11, 0.1)', border: '#F59E0B', text: '#FBBF24' },
                      NURSE_REVIEW: { bg: 'rgba(139, 92, 246, 0.1)', border: '#8B5CF6', text: '#A78BFA' },
                      DECISION_SUPPORT_UNAVAILABLE: { bg: 'rgba(156, 163, 175, 0.1)', border: '#9CA3AF', text: '#D1D5DB' }
                    };
                    const col = dispColors[disp] || { bg: 'rgba(0,0,0,0.1)', border: '#fff', text: '#fff' };
                    return (
                      <div style={{
                        background: col.bg,
                        border: `1px solid ${col.border}`,
                        padding: '20px',
                        borderRadius: '8px',
                        marginBottom: '24px'
                      }}>
                        <div style={{ fontSize: '13px', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--text-secondary)' }}>
                          Decision Support Recommendation
                        </div>
                        <h2 style={{ fontSize: '28px', margin: '4px 0', color: col.text }}>
                          {disp.replace('_', ' ')}
                        </h2>
                        <div style={{ fontSize: '13px', marginTop: '6px', color: 'var(--text-secondary)', display: 'flex', gap: '16px' }}>
                          <div><strong>Certainty:</strong> <span style={{ color: '#fff' }}>{decisionData.decision_certainty}</span></div>
                          <div><strong>Requires Human Review:</strong> <span style={{ color: '#fff' }}>{decisionData.requires_human_review ? 'YES' : 'NO'}</span></div>
                          <div><strong>Rule Version:</strong> <code>{decisionData.rule_version}</code></div>
                        </div>
                        <p style={{ margin: '12px 0 0 0', fontSize: '12px', color: 'rgba(255,255,255,0.4)', fontStyle: 'italic' }}>
                          ⚠ Decision-Support Helper recommendation based on documented CMS criteria. This is not an irreversible autonomous determination.
                        </p>
                      </div>
                    );
                  })()}

                  {/* Why this recommendation section */}
                  <div style={{
                    background: 'rgba(255,255,255,0.01)',
                    border: '1px solid var(--border-color)',
                    padding: '20px',
                    borderRadius: '8px',
                    marginBottom: '24px'
                  }}>
                    <h3 style={{ fontSize: '15px', margin: '0 0 12px 0' }}>Why this recommendation?</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px' }}>
                      {decisionData.reason_codes.includes('PA_ALL_MANDATORY_CRITERIA_MET') && (
                        <div style={{ color: '#34D399' }}>✓ All mandatory CMS clinical and administrative requirements are fully met.</div>
                      )}
                      {decisionData.reason_codes.includes('PA_MANDATORY_CRITERION_UNCLEAR') && (
                        <div style={{ color: '#FBBF24' }}>⚠ A mandatory coverage criterion cannot currently be verified because patient clinical documentation is missing or unclear.</div>
                      )}
                      {decisionData.reason_codes.includes('PA_MANDATORY_CRITERION_NOT_MET') && (
                        <div style={{ color: '#F87171' }}>✗ A mandatory coverage criterion was explicitly evaluated as unsatisfied by documented patient clinical evidence.</div>
                      )}
                      {decisionData.reason_codes.includes('PA_CODING_BLOCKING_FAILURE') && (
                        <div style={{ color: '#F87171' }}>✗ A deterministic coding check failed (such as non-covered diagnosis, service code mismatch, or expired dates).</div>
                      )}
                      {decisionData.reason_codes.includes('PA_POLICY_UNCERTAIN') && (
                        <div style={{ color: '#A78BFA' }}>⚬ Policy applicability is uncertain due to missing geography state codes or multiple conflicting LCD coverage rules.</div>
                      )}
                      {decisionData.reason_codes.includes('PA_POLICY_UNAVAILABLE') && (
                        <div style={{ color: '#9CA3AF' }}>⚬ Custom synthetic code request detected. Automated decision mapping is unavailable.</div>
                      )}

                      <div style={{ marginTop: '8px', borderTop: '1px solid var(--border-color)', paddingTop: '8px' }}>
                        <strong>Decision Reason Codes:</strong> {decisionData.reason_codes.map((c: string) => <code key={c} style={{ marginLeft: '6px' }}>{c}</code>)}
                      </div>
                    </div>
                  </div>

                  {/* Missing Information requests */}
                  {decisionData.missing_information.length > 0 && (
                    <div style={{ marginBottom: '24px' }}>
                      <h3 style={{ fontSize: '15px', margin: '0 0 12px 0', color: '#FBBF24' }}>📋 Information Needed (Missing Documentation Requests)</h3>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        {decisionData.missing_information.map((req: any, i: number) => (
                          <div key={i} style={{
                            background: 'rgba(245, 158, 11, 0.05)',
                            border: '1px solid rgba(245, 158, 11, 0.2)',
                            padding: '16px',
                            borderRadius: '8px'
                          }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '6px' }}>
                              <span style={{ color: '#FBBF24', fontWeight: 'bold' }}>Priority: {req.priority}</span>
                              <span style={{ color: 'var(--text-secondary)' }}>Type: {req.request_type}</span>
                            </div>
                            <p style={{ margin: '0 0 10px 0', fontSize: '13px', fontWeight: '500' }}>{req.description}</p>
                            {req.policy_citation && (
                              <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                                <strong>Source Policy Citation:</strong> <code>{req.policy_citation}</code>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Decision Factors */}
                  <h3 style={{ fontSize: '15px', margin: '24px 0 12px 0' }}>Decisive Coverage Factors</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {decisionData.decision_factors.map((fac: any, i: number) => {
                      const effectStyles: any = {
                        SUPPORTS_APPROVAL: { label: 'Supports Approval', border: 'rgba(16, 185, 129, 0.2)', bg: 'rgba(16, 185, 129, 0.02)', color: '#34D399' },
                        BLOCKING_FAILURE: { label: 'Blocking Failure', border: 'rgba(239, 68, 68, 0.2)', bg: 'rgba(239, 68, 68, 0.02)', color: '#F87171' },
                        BLOCKING_MISSING_INFORMATION: { label: 'Missing Documentation', border: 'rgba(245, 158, 11, 0.2)', bg: 'rgba(245, 158, 11, 0.02)', color: '#FBBF24' },
                        NON_BLOCKING_WARNING: { label: 'Non-Blocking Warning', border: 'rgba(245, 158, 11, 0.2)', bg: 'rgba(245, 158, 11, 0.02)', color: '#FBBF24' },
                        REQUIRES_HUMAN_REVIEW: { label: 'Manual Review Required', border: 'rgba(139, 92, 246, 0.2)', bg: 'rgba(139, 92, 246, 0.02)', color: '#A78BFA' },
                        INFORMATIONAL: { label: 'Informational', border: 'var(--border-color)', bg: 'rgba(255,255,255,0.01)', color: 'var(--text-secondary)' }
                      };
                      const est = effectStyles[fac.effect] || { label: fac.effect, border: 'var(--border-color)', bg: 'none', color: '#fff' };
                      return (
                        <div key={i} style={{
                          background: est.bg,
                          border: `1px solid ${est.border}`,
                          padding: '16px',
                          borderRadius: '8px'
                        }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                            <strong style={{ fontSize: '13px' }}>{fac.factor_id}</strong>
                            <span style={{ fontSize: '11px', textTransform: 'uppercase', color: est.color, fontWeight: 'bold' }}>
                              {est.label}
                            </span>
                          </div>
                          <p style={{ margin: '0 0 10px 0', fontSize: '13px' }}>{fac.description}</p>
                          <div style={{ display: 'flex', gap: '20px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                            {fac.policy_citation && (
                              <div><strong>Citation:</strong> <code>{fac.policy_citation}</code></div>
                            )}
                            {fac.patient_provenance && fac.patient_provenance.length > 0 && (
                              <div>
                                <strong>Provenance:</strong> {fac.patient_provenance.map((p: any, idx: number) => (
                                  <span key={idx} style={{ marginLeft: '4px' }}><code>{p.collection} ({p.record_id})</code></span>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Audit Metadata */}
                  <div style={{ marginTop: '30px', paddingTop: '16px', borderTop: '1px solid var(--border-color)', fontSize: '11px', color: 'rgba(255,255,255,0.3)', display: 'flex', justifyContent: 'space-between' }}>
                    <div><strong>Decision ID:</strong> <code>{decisionData.decision_id}</code></div>
                    <div><strong>Evaluation ID:</strong> <code>{decisionData.evaluation_id}</code></div>
                    <div><strong>Timestamp:</strong> {decisionData.created_at}</div>
                  </div>
                </div>
              )}

              {/* Tab: Reviewer Explanation & Action */}
              {activeTab === 'explanation' && explanationData && (
                <div>
                  <h3 style={{ fontSize: '16px', marginBottom: '16px', color: '#a78bfa' }}>📝 Reviewer Case Synthesis & Explanation</h3>
                  
                  {/* Synthesis Summary */}
                  <div style={{ background: 'rgba(139, 92, 246, 0.05)', border: '1px solid rgba(139, 92, 246, 0.2)', padding: '16px', borderRadius: '8px', marginBottom: '20px' }}>
                    <h4 style={{ margin: '0 0 8px 0', fontSize: '13px', textTransform: 'uppercase', color: '#a78bfa' }}>Synthesis Summary</h4>
                    <p style={{ margin: '0', fontSize: '14px', lineHeight: '1.5' }}>{explanationData.summary}</p>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
                    {/* Why this recommendation list */}
                    <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)', padding: '16px', borderRadius: '8px' }}>
                      <h4 style={{ margin: '0 0 10px 0', fontSize: '13px', color: 'var(--text-secondary)' }}>Why this recommendation</h4>
                      <ul style={{ margin: '0', paddingLeft: '20px', fontSize: '13px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {explanationData.why.map((w: string, idx: number) => <li key={idx}>{w}</li>)}
                      </ul>
                    </div>
                    {/* Policy summary list */}
                    <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)', padding: '16px', borderRadius: '8px' }}>
                      <h4 style={{ margin: '0 0 10px 0', fontSize: '13px', color: 'var(--text-secondary)' }}>CMS Policy Sources</h4>
                      <ul style={{ margin: '0', paddingLeft: '20px', fontSize: '13px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {explanationData.policy_summary.map((p: string, idx: number) => <li key={idx}>{p}</li>)}
                      </ul>
                    </div>
                  </div>

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '24px' }}>
                    {/* Satisfied list */}
                    <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)', padding: '16px', borderRadius: '8px' }}>
                      <h4 style={{ margin: '0 0 10px 0', fontSize: '13px', color: '#34D399' }}>✓ Satisfied Criteria</h4>
                      <ul style={{ margin: '0', paddingLeft: '20px', fontSize: '13px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {explanationData.satisfied_requirements.map((s: string, idx: number) => <li key={idx} style={{ color: '#a7f3d0' }}>{s}</li>)}
                      </ul>
                    </div>
                    {/* Unresolved / failed list */}
                    <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)', padding: '16px', borderRadius: '8px' }}>
                      <h4 style={{ margin: '0 0 10px 0', fontSize: '13px', color: '#F87171' }}>✗ Unresolved / Failed Criteria</h4>
                      <ul style={{ margin: '0', paddingLeft: '20px', fontSize: '13px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {explanationData.blocking_requirements.length > 0 ? (
                          explanationData.blocking_requirements.map((b: string, idx: number) => <li key={idx} style={{ color: '#fca5a5' }}>{b}</li>)
                        ) : (
                          <li style={{ color: 'var(--text-secondary)' }}>No failed criteria or blocking requirements identified.</li>
                        )}
                      </ul>
                    </div>
                  </div>

                  {/* Information needed */}
                  {explanationData.missing_information.length > 0 && (
                    <div style={{ background: 'rgba(245, 158, 11, 0.02)', border: '1px solid rgba(245, 158, 11, 0.1)', padding: '16px', borderRadius: '8px', marginBottom: '24px' }}>
                      <h4 style={{ margin: '0 0 10px 0', fontSize: '13px', color: '#FBBF24' }}>📋 Information Needed</h4>
                      <ul style={{ margin: '0', paddingLeft: '20px', fontSize: '13px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                        {explanationData.missing_information.map((m: string, idx: number) => <li key={idx} style={{ color: '#fef3c7' }}>{m}</li>)}
                      </ul>
                    </div>
                  )}

                  {/* Human Reviewer Action Form */}
                  <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)', padding: '20px', borderRadius: '8px', marginBottom: '24px' }}>
                    <h3 style={{ fontSize: '15px', margin: '0 0 16px 0', color: 'var(--text-primary)' }}>✍ Submit Human Reviewer Action</h3>
                    
                    {actionMessage && (
                      <div style={{ background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.2)', color: '#34D399', padding: '12px', borderRadius: '6px', marginBottom: '16px', fontSize: '13px' }}>
                        {actionMessage}
                      </div>
                    )}

                    <form onSubmit={handleActionSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                        <div className="form-group">
                          <label className="form-label" style={{ fontSize: '12px' }}>Reviewer Identity</label>
                          <input
                            type="text"
                            className="form-control"
                            required
                            value={reviewerId}
                            onChange={(e) => setReviewerId(e.target.value)}
                          />
                        </div>
                        <div className="form-group">
                          <label className="form-label" style={{ fontSize: '12px' }}>Workflow Action</label>
                          <select
                            className="form-control"
                            value={actionType}
                            onChange={(e) => setActionType(e.target.value)}
                          >
                            <option value="ACCEPT_RECOMMENDATION">Accept Recommendation</option>
                            <option value="REQUEST_MORE_INFORMATION">Request More Information</option>
                            <option value="ESCALATE">Escalate</option>
                            <option value="OVERRIDE_RECOMMENDATION">Override Recommendation</option>
                          </select>
                        </div>
                      </div>

                      {actionType === 'OVERRIDE_RECOMMENDATION' && (
                        <div className="form-group">
                          <label className="form-label" style={{ fontSize: '12px', color: '#F87171' }}>
                            Intended Reviewer Disposition (Override)
                          </label>
                          <select
                            className="form-control"
                            value={overrideDisp}
                            onChange={(e) => setOverrideDisp(e.target.value)}
                          >
                            <option value="APPROVE">Approve</option>
                            <option value="DENY">Deny</option>
                            <option value="PEND">Pend</option>
                            <option value="NURSE_REVIEW">Nurse Review</option>
                          </select>
                          <p style={{ margin: '6px 0 0 0', fontSize: '11px', color: 'rgba(255,255,255,0.4)', fontStyle: 'italic' }}>
                            ⚠ The original system recommendation will remain preserved in the audit history.
                          </p>
                        </div>
                      )}

                      <div className="form-group">
                        <label className="form-label" style={{ fontSize: '12px' }}>Justification / Reason Description</label>
                        <textarea
                          className="form-control"
                          rows={3}
                          required
                          placeholder="Provide detailed clinical or administrative rationale statement for this action..."
                          value={actionReason}
                          onChange={(e) => setActionReason(e.target.value)}
                        />
                      </div>

                      <button type="submit" className="btn-primary" style={{ alignSelf: 'start', padding: '10px 24px' }}>
                        Submit Action Log
                      </button>
                    </form>
                  </div>

                  {/* Review History */}
                  <div>
                    <h3 style={{ fontSize: '15px', margin: '24px 0 12px 0' }}>📝 Review History Logs</h3>
                    {reviewHistory.length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        {reviewHistory.map((h: any, idx: number) => (
                          <div key={idx} style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)', padding: '14px', borderRadius: '8px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '6px', color: 'var(--text-secondary)' }}>
                              <span><strong>Reviewer:</strong> {h.reviewer_id}</span>
                              <span>{new Date(h.timestamp).toLocaleString()}</span>
                            </div>
                            <div style={{ fontSize: '13px', fontWeight: 'bold', marginBottom: '4px', color: h.action === 'OVERRIDE_RECOMMENDATION' ? '#F87171' : 'var(--text-primary)' }}>
                              {h.action.replace('_', ' ')} {h.intended_disposition ? `➔ ${h.intended_disposition}` : ''}
                            </div>
                            <p style={{ margin: '0', fontSize: '13px', color: 'rgba(255,255,255,0.7)' }}>{h.reason}</p>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>No reviewer actions logged yet for this request.</p>
                    )}
                  </div>

                  {/* Generated By Details */}
                  <div style={{ marginTop: '30px', paddingTop: '16px', borderTop: '1px solid var(--border-color)', fontSize: '11px', color: 'rgba(255,255,255,0.25)', display: 'flex', justifyContent: 'space-between' }}>
                    <div><strong>Synthesis Provider:</strong> <code>{explanationData.generated_by?.provider || 'deterministic'}</code></div>
                    <div><strong>Model:</strong> <code>{explanationData.generated_by?.model || 'rule_engine'}</code></div>
                    <div><strong>Prompt Version:</strong> <code>{explanationData.generated_by?.prompt_version || 'v1'}</code></div>
                  </div>
                </div>
              )}

              {/* Tab: Workflow Audit Trail */}
              {activeTab === 'audit_trail' && (
                <div>
                  <h3 style={{ fontSize: '16px', marginBottom: '16px', color: '#60a5fa' }}>📋 Workflow Audit Trail Timeline</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', position: 'relative', paddingLeft: '24px', borderLeft: '2px solid var(--border-color)' }}>
                    {auditEvents.map((evt: any, idx: number) => {
                      const eventColors: any = {
                        REQUEST_CREATED: '#60A5FA',
                        EVIDENCE_PACKET_BUILT: '#34D399',
                        POLICY_ROUTED: '#818CF8',
                        POLICY_RETRIEVED: '#FB7185',
                        EVALUATION_CREATED: '#A78BFA',
                        DECISION_SUPPORT_CREATED: '#FBBF24',
                        EXPLANATION_GENERATED: '#A78BFA',
                        REVIEWER_ACTION_RECORDED: '#34D399',
                        RECOMMENDATION_OVERRIDDEN: '#F87171'
                      };
                      const dotColor = eventColors[evt.event_type] || '#fff';
                      return (
                        <div key={idx} style={{ position: 'relative', marginBottom: '4px' }}>
                          <div style={{
                            position: 'absolute',
                            left: '-31px',
                            top: '4px',
                            width: '12px',
                            height: '12px',
                            borderRadius: '50%',
                            background: dotColor,
                            border: '3px solid #0f172a'
                          }} />
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                            <span><strong>Event:</strong> <code style={{ color: dotColor }}>{evt.event_type}</code></span>
                            <span>{new Date(evt.timestamp).toLocaleString()}</span>
                          </div>
                          <div style={{ fontSize: '13px', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border-color)', padding: '10px 14px', borderRadius: '6px' }}>
                            <div style={{ fontSize: '12px', marginBottom: '4px' }}>
                              <strong>Actor:</strong> <code>{evt.actor_id} ({evt.actor_type})</code> | <strong>Event ID:</strong> <code>{evt.event_id}</code>
                            </div>
                            {evt.metadata && Object.keys(evt.metadata).length > 0 && (
                              <pre style={{ margin: '6px 0 0 0', padding: '6px', background: 'rgba(0,0,0,0.2)', borderRadius: '4px', fontSize: '11px', overflowX: 'auto', color: 'rgba(255,255,255,0.6)' }}>
                                {JSON.stringify(evt.metadata, null, 2)}
                              </pre>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Tab 4: Audit Trace / Provenance */}
              {activeTab === 'provenance' && (
                <div>
                  <h3 style={{ fontSize: '16px', marginBottom: '16px' }}>Clinical Fact Trace & Provenance</h3>
                  <table className="evidence-table">
                    <thead>
                      <tr>
                        <th>Fact Type</th>
                        <th>Standard Value / Snippet</th>
                        <th>Source Collection</th>
                        <th>Source ID Reference</th>
                        <th>Source Column</th>
                      </tr>
                    </thead>
                    <tbody>
                      {intakeData.clinical_evidence_packet.provenance.map((p: any, i: number) => (
                        <tr key={i}>
                          <td><strong>{p.fact_type}</strong></td>
                          <td style={{ maxWidth: '280px', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                            <code>{p.value}</code>
                          </td>
                          <td><code>{p.source_collection}</code></td>
                          <td><code>{p.source_record_id}</code></td>
                          <td><code>{p.source_field}</code></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
