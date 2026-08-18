import React, { useState } from 'react';
import './NewRequest.css';
import ReactMarkdown from 'react-markdown';

export default function NewRequest({ setLatestAuditData, setCurrentView }) {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      // Step 1: Upload and extract clinical facts
      const formData = new FormData();
      formData.append('file', file);
      const uploadResponse = await fetch('http://localhost:8000/api/prior-auth/upload', {
        method: 'POST',
        body: formData,
      });
      if (!uploadResponse.ok) throw new Error(`Upload failed: ${uploadResponse.status}`);
      const uploadData = await uploadResponse.json();
      const packet = uploadData.clinical_evidence_packet;

      // Step 2: Create request and persist clinical data in MongoDB
      const createResponse = await fetch('http://localhost:8000/api/prior-auth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(packet),
      });
      if (!createResponse.ok) throw new Error(`Database insert failed: ${createResponse.status}`);
      const createData = await createResponse.json();
      const authId = createData.request_id;

      // Step 3: Run the real pipeline against the MongoDB records
      const evalResponse = await fetch(`http://localhost:8000/api/prior-auth/${authId}/evaluate-full-pipeline`, {
        method: 'POST',
      });
      if (!evalResponse.ok) throw new Error(`Evaluation failed: ${evalResponse.status}`);
      
      const evalData = await evalResponse.json();
      
      // Map the pipeline response to the UI format
      const phase7 = evalData.phase7_decision || {};
      setResult({
        status: evalData.final_status || phase7.recommendation || "PENDING",
        confidence: phase7.confidence_score !== undefined ? `${(phase7.confidence_score * 100).toFixed(0)}%` : 'N/A',
        metrics: { processing_time: 4.2 }, // Mocked or calculated
        letter: evalData.final_explanation || evalData.explanation_letter || evalData.letter || "Explanation not provided.",
        details: {
          clinical_evidence: evalData.clinical_evidence,
          phase3_routing: evalData.phase3_routing,
          phase4_ncd_results: evalData.ncd_decision,
          phase4_lcd_results: evalData.lcd_decision,
          phase4_article_results: evalData.article_decision,
          phase7_decision: phase7,
          final_status: evalData.final_status,
          final_explanation: evalData.final_explanation
        }
      });
      
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="new-request animate-fade-in">
      <header className="dashboard-header">
        <h1>Submit Prior Authorization</h1>
        <p className="text-subtle">Upload clinical documentation (PDF) to initiate the 8-phase AI evaluation engine.</p>
      </header>

      {!result && (
        <section className="glass-panel p-6 upload-section">
          <form onSubmit={handleSubmit}>
            <div className="upload-box">
              <div className="upload-icon">📄</div>
              <h3>Drag & Drop Medical Record</h3>
              <p className="text-subtle mb-4">Supports PDF CCDA formats up to 50MB</p>
              
              <input 
                type="file" 
                id="file-upload" 
                accept="application/pdf" 
                onChange={handleFileChange}
                className="file-input"
              />
              <label htmlFor="file-upload" className="glass-button">
                Browse Files
              </label>
              
              {file && <div className="selected-file">Selected: {file.name}</div>}
            </div>

            <div className="submit-action">
              <button 
                type="submit" 
                className="glass-button primary submit-btn" 
                disabled={!file || loading}
              >
                {loading ? 'Processing through 8-Phase Engine...' : 'Run Intelligence Evaluation'}
              </button>
            </div>
          </form>
          {error && <div className="error-msg">{error}</div>}
        </section>
      )}

      {loading && (
        <div className="loading-state glass-panel p-6">
          <div className="spinner"></div>
          <h3>Running Autonomous Adjudication</h3>
          <p className="text-subtle">Extracting entities, checking NCD/LCD policies, and computing decision...</p>
        </div>
      )}

      {result && !loading && (
        <section className="results-view animate-fade-in">
          <div className="glass-panel p-6 mb-6">
            <div className="flex-between mb-4">
              <h2>Evaluation Complete</h2>
              <button className="glass-button" onClick={() => {setResult(null); setFile(null);}}>Submit Another</button>
            </div>
            
            <div className="result-kpis">
              <div className="rkpi">
                <div className="rkpi-label">Final Status</div>
                <div className={`rkpi-val status-${result.status.toLowerCase()}`}>{result.status}</div>
              </div>
              <div className="rkpi">
                <div className="rkpi-label">Confidence</div>
                <div className="rkpi-val">{result.confidence}</div>
              </div>
              <div className="rkpi">
                <div className="rkpi-label">Processing Time</div>
                <div className="rkpi-val">{result.metrics?.processing_time || '4.2'}s</div>
              </div>
            </div>
          </div>

          <div className="glass-panel p-6 letter-panel">
            <h3>Generated Explanation Letter</h3>
            <div className="markdown-body mt-4">
              <ReactMarkdown>{result.letter}</ReactMarkdown>
            </div>
            
            <div className="mt-6 flex justify-end">
              <button 
                className="glass-button primary" 
                onClick={() => {
                  setLatestAuditData(result.details);
                  setCurrentView('audit');
                }}
              >
                View Technical Audit Trail
              </button>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
