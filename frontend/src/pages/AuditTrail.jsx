import React from 'react';
import './AuditTrail.css';

export default function AuditTrail({ data }) {
  if (!data) {
    return (
      <div className="audit-trail animate-fade-in">
        <header className="dashboard-header">
          <h1>Technical Audit Trail</h1>
          <p className="text-subtle">Detailed breakdown of AI extractions and validations across all 8 phases.</p>
        </header>
        <div className="glass-panel p-6 empty-state mt-6">
          <div className="upload-icon mb-4" style={{fontSize: '3rem', opacity: 0.5}}>🔍</div>
          <h2>No Active Request</h2>
          <p className="text-subtle">Please submit a Prior Authorization document first to view its audit trail.</p>
        </div>
      </div>
    );
  }

  const { 
    clinical_evidence, 
    phase3_routing, 
    phase4_ncd_results: ncd_decision, 
    phase4_lcd_results: lcd_decision, 
    phase4_article_results: article_decision, 
    phase7_decision,
    final_explanation 
  } = data;

  const renderStatusBadge = (status) => {
    if (!status) return null;
    const cleanStatus = status.replace(' ', '-');
    return <span className={`status-badge status-${cleanStatus}`}>{status}</span>;
  };

  const renderReasoning = (reasoningText) => {
    if (!reasoningText) return null;
    
    // Parse the structured reasoning text if it follows the template
    const parsed = {
      requirement: '',
      patientEvidence: '',
      policyEvidence: '',
      reasoning: reasoningText
    };

    if (reasoningText.includes('Requirement:') && reasoningText.includes('Patient Evidence:')) {
      try {
        const sections = reasoningText.split('\n\n');
        sections.forEach(section => {
          if (section.startsWith('Requirement:')) parsed.requirement = section.replace('Requirement:', '').trim();
          if (section.startsWith('Patient Evidence:')) parsed.patientEvidence = section.replace('Patient Evidence:', '').trim();
          if (section.startsWith('Policy Evidence:')) parsed.policyEvidence = section.replace('Policy Evidence:', '').trim();
          if (section.startsWith('Reasoning:')) parsed.reasoning = section.replace('Reasoning:', '').trim();
        });
      } catch (e) {
        // Fallback to raw text
      }
    }

    if (parsed.requirement || parsed.patientEvidence) {
      return (
        <div className="reasoning-structured">
          {parsed.requirement && (
            <div className="reasoning-block">
              <span className="reasoning-label">Policy Requirement</span>
              <div className="reasoning-content">{parsed.requirement}</div>
            </div>
          )}
          <div className="comparison-grid">
            <div className="comparison-column patient">
              <span className="reasoning-label">Patient EHR Evidence</span>
              <div className="reasoning-content">{parsed.patientEvidence || "Not Found"}</div>
            </div>
            <div className="comparison-column policy">
              <span className="reasoning-label">CMS Policy Rules</span>
              <div className="reasoning-content">{parsed.policyEvidence || "N/A"}</div>
            </div>
          </div>
          <div className="reasoning-block mt-3">
            <span className="reasoning-label">AI Logic</span>
            <div className="reasoning-content">{parsed.reasoning}</div>
          </div>
        </div>
      );
    }

    return <p className="text-subtle">{reasoningText}</p>;
  };

  return (
    <div className="audit-trail animate-fade-in pb-10">
      <header className="dashboard-header mb-6">
        <h1>Technical Audit Trail</h1>
        <p className="text-subtle">Detailed breakdown of AI extractions and validations across all phases.</p>
      </header>

      {/* Phase 1 & 2: Clinical Extraction */}
      {clinical_evidence && (
        <section className="audit-section">
          <div className="flex-between">
            <h3>Phase 1 & 2: Clinical Evidence Extraction</h3>
            <span className="status-badge status-APPROVED">EXTRACTED</span>
          </div>
          
          <div className="metric-row">
            <span className="metric-label">Patient Demographics</span>
            <span>Age: {clinical_evidence.demographics?.age || 'N/A'}, Gender: {clinical_evidence.demographics?.gender || 'N/A'}</span>
          </div>

          <div className="mt-4">
            <h4 className="text-accent mb-2">Diagnoses & Conditions:</h4>
            <div className="checklist-grid">
              {clinical_evidence.diagnosis_codes?.map((code, i) => (
                <div className="checklist-item" key={i}>
                  <span className="checklist-label">ICD-10 Code</span>
                  <span className="val-PASS">{code}</span>
                </div>
              ))}
            </div>
          </div>

          {(clinical_evidence.vital_signs?.length > 0 || clinical_evidence.diagnostic_results?.length > 0) && (
            <div className="mt-4">
              <h4 className="text-accent mb-2">Vitals & Diagnostics:</h4>
              <div className="checklist-grid">
                {clinical_evidence.vital_signs?.map((v, i) => (
                  <div className="checklist-item" key={`v-${i}`}>
                    <span className="checklist-label">{v.name}</span>
                    <span style={{ fontWeight: 'bold' }}>{v.value || 'Yes'}</span>
                  </div>
                ))}
                {clinical_evidence.diagnostic_results?.map((d, i) => (
                  <div className="checklist-item" key={`d-${i}`}>
                    <span className="checklist-label">{d.test_name}</span>
                    <span style={{ fontWeight: 'bold' }}>{d.value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      )}

      {/* Phase 3: Routing */}
      {phase3_routing && (
        <section className="audit-section">
          <div className="flex-between">
            <h3>Phase 3: Policy & Code Routing</h3>
            <span className="status-badge status-COVERED">ROUTED</span>
          </div>
          
          <div className="metric-row">
            <span className="metric-label">Requested HCPCS Code</span>
            <span className="val-PASS">{phase3_routing.requested_hcpcs}</span>
          </div>
          
          <div className="mt-4">
            <h4 className="text-accent mb-2">Applicable CMS Policies Resolved:</h4>
            <div className="checklist-grid">
              <div className="checklist-item">
                <span className="checklist-label">NCD Policy IDs</span>
                <span style={{ fontWeight: 'bold', color: 'var(--text)' }}>{phase3_routing.ncd_policies?.join(', ') || 'None'}</span>
              </div>
              <div className="checklist-item">
                <span className="checklist-label">LCD Policy IDs</span>
                <span style={{ fontWeight: 'bold', color: 'var(--text)' }}>{phase3_routing.lcd_policies?.join(', ') || 'None'}</span>
              </div>
              <div className="checklist-item">
                <span className="checklist-label">Article Policy IDs</span>
                <span style={{ fontWeight: 'bold', color: 'var(--text)' }}>{phase3_routing.article_policies?.join(', ') || 'None'}</span>
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Phase 4: NCD */}
      {ncd_decision && (
        <section className="audit-section">
          <div className="flex-between">
            <h3>Phase 4: NCD Evaluation</h3>
            {renderStatusBadge(ncd_decision.ncd_determination)}
          </div>
          
          <div className="metric-row">
            <span className="metric-label">Semantic Similarity Score</span>
            <span>{(ncd_decision.semantic_similarity_score * 100).toFixed(1)}%</span>
          </div>
          <div className="metric-row">
            <span className="metric-label">Confidence Score</span>
            <span>{(ncd_decision.confidence_score * 100).toFixed(1)}%</span>
          </div>

          <div className="mt-4">
            <h4 className="text-accent mb-2">AI Reasoning:</h4>
            {renderReasoning(ncd_decision.reasoning)}
          </div>

          {ncd_decision.key_policy_excerpts?.length > 0 && (
            <div className="excerpts-list">
              {ncd_decision.key_policy_excerpts.map((excerpt, idx) => (
                <p key={idx}>{excerpt}</p>
              ))}
            </div>
          )}
        </section>
      )}

      {/* Phase 5: LCD */}
      {lcd_decision && (
        <section className={`audit-section ${lcd_decision.lcd_determination === 'SKIPPED' ? 'skipped-section' : ''}`}>
          <div className="flex-between">
            <h3>{lcd_decision.lcd_determination === 'SKIPPED' ? 'PHASE 5 — LCD EVALUATION SKIPPED' : 'Phase 5: LCD Evaluation'}</h3>
            {renderStatusBadge(lcd_decision.lcd_determination)}
          </div>
          
          {lcd_decision.lcd_determination === 'SKIPPED' ? (
            <div className="mt-4">
              <h4 className="text-accent mb-2">Reason:</h4>
              <p className="text-subtle" style={{ color: '#e74c3c' }}>{lcd_decision.reasoning}</p>
            </div>
          ) : (
            <>
              <div className="metric-row">
                <span className="metric-label">Semantic Similarity Score</span>
                <span>{(lcd_decision.semantic_similarity_score * 100).toFixed(1)}%</span>
              </div>
              <div className="metric-row">
                <span className="metric-label">Confidence Score</span>
                <span>{(lcd_decision.confidence_score * 100).toFixed(1)}%</span>
              </div>

              <div className="mt-4">
                <h4 className="text-accent mb-2">AI Reasoning:</h4>
                {renderReasoning(lcd_decision.reasoning)}
              </div>

              {lcd_decision.key_policy_excerpts?.length > 0 && (
                <div className="excerpts-list">
                  {lcd_decision.key_policy_excerpts.map((excerpt, idx) => (
                    <p key={idx}>{excerpt}</p>
                  ))}
                </div>
              )}
            </>
          )}
        </section>
      )}

      {/* Phase 6: Article */}
      {article_decision && (
        <section className="audit-section">
          <div className="flex-between">
            <h3>Phase 6: Article & Coding Evaluation</h3>
            {renderStatusBadge(article_decision.article_determination)}
          </div>

          <div className="mt-4">
            <h4 className="text-accent mb-2">Administrative Validation Checklist:</h4>
            <div className="checklist-grid">
              {Object.entries(article_decision.validation_checklist).map(([key, val]) => (
                <div className="checklist-item" key={key}>
                  <span className="checklist-label">{key.toUpperCase().replace(/_/g, ' ')}</span>
                  <span className={`val-${val}`}>{val}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-6">
            <h4 className="text-accent mb-2">AI Reasoning:</h4>
            <p className="text-subtle">{article_decision.reasoning}</p>
          </div>
        </section>
      )}

      {/* Phase 7: Decision */}
      {phase7_decision && (
        <section className="audit-section">
          <div className="flex-between">
            <h3>Phase 7: Final Decision Output</h3>
            <span className={`status-badge status-${phase7_decision.recommendation}`}>{phase7_decision.recommendation}</span>
          </div>
          
          <div className="metric-row">
            <span className="metric-label">Overall Confidence Score</span>
            <span>{(phase7_decision.overall_confidence_score * 100).toFixed(1)}%</span>
          </div>

          <div className="mt-4">
            <h4 className="text-accent mb-2">Evidence Summary:</h4>
            <p className="text-subtle">{phase7_decision.evidence_summary}</p>
          </div>

          <div className="mt-4">
            <h4 className="text-accent mb-2" style={{color: '#e74c3c'}}>Gap Analysis:</h4>
            <p className="text-subtle">{phase7_decision.gap_analysis}</p>
          </div>
        </section>
      )}

      {/* Phase 8: Final Explanation */}
      {final_explanation && (
        <section className="audit-section">
          <div className="flex-between">
            <h3>Phase 8: Generated Explanation Letter</h3>
            <span className="status-badge status-APPROVED">GENERATED</span>
          </div>
          
          <div className="mt-4 markdown-body p-4" style={{ background: 'rgba(0,0,0,0.2)', borderRadius: '8px' }}>
             <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', margin: 0 }}>
               {final_explanation}
             </pre>
          </div>
        </section>
      )}

    </div>
  );
}
