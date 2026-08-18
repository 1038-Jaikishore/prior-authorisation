import React, { useState } from 'react';
import './PolicyExplorer.css';

export default function PolicyExplorer() {
  const [policyType, setPolicyType] = useState('ncd');
  const [policyId, setPolicyId] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!policyId.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      // Hit the actual backend API endpoints
      const response = await fetch(`http://localhost:8000/api/policy/${policyType}/${encodeURIComponent(policyId.trim())}`);
      
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error(`${policyType.toUpperCase()} document with ID '${policyId}' not found in MongoDB.`);
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Helper to pretty-print JSON with colors (basic implementation)
  const syntaxHighlight = (json) => {
    if (typeof json != 'string') {
         json = JSON.stringify(json, undefined, 2);
    }
    json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
        let cls = 'json-number';
        if (/^"/.test(match)) {
            if (/:$/.test(match)) {
                cls = 'json-key';
            } else {
                cls = 'json-string';
            }
        } else if (/true|false/.test(match)) {
            cls = 'json-boolean';
        } else if (/null/.test(match)) {
            cls = 'json-null';
        }
        return '<span class="' + cls + '">' + match + '</span>';
    });
  };

  return (
    <div className="policy-explorer animate-fade-in">
      <header className="dashboard-header mb-6">
        <h1>CMS Policy Explorer</h1>
        <p className="text-subtle">Query the MongoDB instance directly to retrieve live NCD, LCD, and Article records.</p>
      </header>

      <section className="glass-panel p-6 mb-6">
        <form onSubmit={handleSearch} className="search-section">
          <div className="search-input-group">
            <select 
              className="policy-type-select"
              value={policyType}
              onChange={(e) => setPolicyType(e.target.value)}
            >
              <option value="ncd">NCD</option>
              <option value="lcd">LCD</option>
              <option value="article">Article</option>
            </select>
            <input 
              type="text"
              className="policy-id-input"
              placeholder={policyType === 'ncd' ? 'e.g., 240.2' : policyType === 'lcd' ? 'e.g., L33718' : 'e.g., A52467'}
              value={policyId}
              onChange={(e) => setPolicyId(e.target.value)}
            />
          </div>
          <button type="submit" className="glass-button primary search-btn" disabled={loading || !policyId.trim()}>
            {loading ? 'Searching DB...' : 'Fetch Policy'}
          </button>
        </form>
      </section>

      {error && (
        <section className="glass-panel p-6 error-card animate-fade-in">
          <h3 style={{color: '#e74c3c'}}>Search Failed</h3>
          <p className="text-subtle mt-2">{error}</p>
        </section>
      )}

      {result && (
        <section className="glass-panel p-6 result-card">
          <div className="meta-grid">
            <div className="meta-item">
              <span className="meta-label">Title</span>
              <span className="meta-value">{result.title || 'N/A'}</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Status</span>
              <span className="meta-value" style={{color: '#2ecc71'}}>{result.status || 'Active'}</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Effective Date</span>
              <span className="meta-value">{result.effective_date || 'N/A'}</span>
            </div>
          </div>

          <h3 className="mb-4">Raw Database Payload</h3>
          <div className="json-view">
            <pre dangerouslySetInnerHTML={{ __html: syntaxHighlight(result) }}></pre>
          </div>
        </section>
      )}

      {!result && !error && !loading && (
        <div className="glass-panel p-6 empty-state">
          <div style={{fontSize: '3rem', opacity: 0.3, marginBottom: '1rem'}}>🏛️</div>
          <h2>Search CMS Coverage Database</h2>
          <p className="text-subtle mt-2">Select a document type and enter an ID to view the full raw JSON document.</p>
        </div>
      )}
    </div>
  );
}
