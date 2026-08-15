import React, { useState, useEffect } from 'react';

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
  const [activeTab, setActiveTab] = useState<string>('evidence');

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
  }, []);

  const handleSelectRequest = (reqId: string, list: RequestItem[] = requests) => {
    setSelectedRequestId(reqId);
    const found = list.find((r) => r.request_id === reqId);
    if (found) {
      setSelectedRequest(found);
      setOverrideDate(found.request_date);
      // Attempt to auto-detect state from provider/encounters in ingestion if needed
      // Colorado CO is default, allow manual change
      setOverrideState('CO');
    }
  };

  const handleRouteRetrieve = () => {
    if (!selectedRequestId) return;
    setLoading(true);
    setError(null);
    setIntakeData(null);

    const url = `http://localhost:8000/api/prior-auth/${selectedRequestId}/route-and-retrieve?override_state=${overrideState}&override_date=${overrideDate}`;
    
    fetch(url, { method: 'POST' })
      .then((res) => {
        if (!res.ok) throw new Error("Workflow routing request failed.");
        return res.json();
      })
      .then((data) => {
        setIntakeData(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
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
                style={{ marginTop: '12px' }}
              >
                {loading ? <span className="spinner"></span> : null}
                Compile Evidence & Route Policy
              </button>
            </div>
          )}
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
                <button
                  className={`tab-btn ${activeTab === 'provenance' ? 'active' : ''}`}
                  onClick={() => setActiveTab('provenance')}
                >
                  Audit Trace & Provenance
                </button>
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
