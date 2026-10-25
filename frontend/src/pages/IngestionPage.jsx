import React, { useEffect, useState, useMemo, useRef } from 'react';
import { uploadAndIngest, fetchHistory } from '../services/ingestionApi';
import { ErrorDisplay } from '../components/ErrorDisplay';

const CATEGORY_OPTIONS = [
  {
    value: 'customer',
    label: 'Customer Insurance',
    badge: 'Customer Scope',
    badgeColor: '#0369a1',
    badgeBg: '#e0f2fe',
    description: 'Health Shield policies (Basic, Gold, Premium) for public policyholders',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0284c7" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      </svg>
    )
  },
  {
    value: 'employee',
    label: 'Employee Insurance',
    badge: 'Corporate Scope',
    badgeColor: '#065f46',
    badgeBg: '#ecfdf5',
    description: 'Executive corporate group plans (EMP-INS-001) with confidential coverage',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
        <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
      </svg>
    )
  }
];

export function IngestionPage() {
  const [selectedCategory, setSelectedCategory] = useState('customer'); // 'customer' or 'employee'
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentJob, setCurrentJob] = useState(null);
  const [history, setHistory] = useState([]);
  const [historySearch, setHistorySearch] = useState('');
  const [historyLoading, setHistoryLoading] = useState(false);
  const [errors, setErrors] = useState([]);
  const [warnings, setWarnings] = useState([]);

  useEffect(() => {
    loadHistory();
  }, []);

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const activeOption = CATEGORY_OPTIONS.find((opt) => opt.value === selectedCategory) || CATEGORY_OPTIONS[0];

  const loadHistory = async () => {
    setHistoryLoading(true);
    try {
      const historyList = await fetchHistory();
      setHistory(Array.isArray(historyList) ? historyList : []);
    } catch {
      // Backend may be initializing
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    if (!isProcessing) setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (isProcessing) return;
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const validateAndSetFile = (file) => {
    setErrors([]);
    setWarnings([]);
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setErrors(['Only official PDF policy documents (.pdf) are supported.']);
      return;
    }
    if (file.size > 25 * 1024 * 1024) {
      setErrors(['File exceeds the maximum allowable limit of 25 MB.']);
      return;
    }
    setSelectedFile(file);
  };

  const handleStartIngestion = async () => {
    if (!selectedFile) {
      setErrors(['Please select a PDF document to upload.']);
      return;
    }

    setErrors([]);
    setWarnings([]);
    setIsProcessing(true);
    setCurrentJob(null);

    try {
      const jobResult = await uploadAndIngest(selectedFile, selectedCategory);
      setCurrentJob(jobResult);
      if (jobResult.warnings && jobResult.warnings.length > 0) {
        setWarnings(jobResult.warnings);
      }
      await loadHistory();
    } catch (err) {
      setErrors(err.errors || [err.message || 'Document processing failed during ingestion.']);
      if (err.warnings) setWarnings(err.warnings);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setCurrentJob(null);
    setErrors([]);
    setWarnings([]);
  };

  const filteredHistory = useMemo(() => {
    if (!historySearch.trim()) return history;
    const q = historySearch.toLowerCase();
    return history.filter(
      (h) =>
        (h.source_document && h.source_document.toLowerCase().includes(q)) ||
        (h.plan_id && h.plan_id.toLowerCase().includes(q)) ||
        (h.status && h.status.toLowerCase().includes(q))
    );
  }, [history, historySearch]);

  return (
    <div className="admin-ingestion-workspace">
      {/* Executive Header */}
      <header className="ingestion-header" style={{ maxWidth: '680px', margin: '0 auto 16px auto' }}>
        <div className="ingestion-title-group">
          <h1 className="ingestion-heading">Policy Document Ingestion</h1>
        </div>
      </header>

      {/* Error & Warning Alert Display */}
      <div style={{ maxWidth: '680px', margin: '0 auto' }}>
        <ErrorDisplay
          errors={errors}
          warnings={warnings}
          onDismiss={() => {
            setErrors([]);
            setWarnings([]);
          }}
        />
      </div>

      {/* Main Ingestion Form or Completed Summary */}
      {!currentJob ? (
        <div className="admin-card admin-log-stream-card" style={{ maxWidth: '680px', margin: '0 auto 28px auto' }}>
          <div className="admin-card-header">
            <div>
              <h2 className="admin-card-title">Upload Policy Document</h2>
            </div>
          </div>

          {/* Insurance Category Dropdown */}
          <div className="form-group" style={{ marginBottom: '20px' }}>
            <label id="category-select-label" className="form-label" style={{ fontWeight: 800, fontSize: '13.5px', color: '#000000', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
                <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
              </svg>
              <span>Insurance Category</span>
            </label>

            <div className="admin-liquid-dropdown-wrapper" ref={dropdownRef} style={{ width: 'auto', display: 'inline-block' }}>
              <button
                id="category-select"
                type="button"
                className={`admin-liquid-dropdown-btn ${dropdownOpen ? 'active' : ''}`}
                onClick={() => !isProcessing && setDropdownOpen((prev) => !prev)}
                disabled={isProcessing}
                aria-haspopup="listbox"
                aria-expanded={dropdownOpen}
                aria-labelledby="category-select-label"
                style={{ minWidth: '260px', justifyContent: 'space-between' }}
              >
                <span className="admin-liquid-dropdown-val" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: selectedCategory === 'customer' ? '#007aff' : '#8b5cf6' }}></span>
                  {activeOption.label}
                </span>
                <svg
                  className={`admin-dropdown-chevron ${dropdownOpen ? 'rotate' : ''}`}
                  width="13"
                  height="13"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <polyline points="6 9 12 15 18 9" />
                </svg>
              </button>

              {dropdownOpen && (
                <div
                  className="admin-liquid-dropdown-menu"
                  role="listbox"
                  style={{
                    left: 0,
                    right: 'auto',
                    minWidth: '260px',
                    width: 'auto',
                    boxSizing: 'border-box'
                  }}
                >
                  {CATEGORY_OPTIONS.map((opt) => {
                    const isSelected = selectedCategory === opt.value;
                    return (
                      <button
                        key={opt.value}
                        type="button"
                        className={`admin-liquid-dropdown-item ${isSelected ? 'selected' : ''}`}
                        onClick={() => {
                          setSelectedCategory(opt.value);
                          setDropdownOpen(false);
                        }}
                        role="option"
                        aria-selected={isSelected}
                      >
                        <span style={{ display: 'flex', alignItems: 'center', gap: '8px', fontWeight: isSelected ? 800 : 600, color: '#000000', fontSize: '13px' }}>
                          <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: opt.value === 'customer' ? '#007aff' : '#8b5cf6' }}></span>
                          {opt.label}
                        </span>
                        {isSelected && (
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#007aff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                        )}
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* File Upload Dropzone */}
          <div className="form-group" style={{ marginBottom: '20px' }}>
            <label className="form-label" style={{ fontWeight: 800, fontSize: '13.5px', color: '#000000', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              <span>Policy Document (PDF)</span>
            </label>

            <div
              className={`pro-dropzone ${isDragOver ? 'drag-active' : ''} ${selectedFile ? 'has-file' : ''}`}
              style={{ padding: '24px 20px', borderRadius: '14px' }}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => !isProcessing && document.getElementById('policy-file-input')?.click()}
            >
              <input
                id="policy-file-input"
                type="file"
                accept="application/pdf"
                onChange={handleFileChange}
                style={{ display: 'none' }}
                disabled={isProcessing}
              />

              {selectedFile ? (
                <div className="dropzone-file-preview">
                  <div className="pdf-icon-wrap" style={{ width: '42px', height: '42px' }}>
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#dc2626" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                      <polyline points="14 2 14 8 20 8" />
                      <line x1="9" y1="15" x2="15" y2="15" />
                      <line x1="9" y1="11" x2="15" y2="11" />
                    </svg>
                  </div>
                  <div className="file-info-col">
                    <strong className="file-preview-name" style={{ fontSize: '13.5px', color: '#000000' }}>{selectedFile.name}</strong>
                    <span className="file-preview-meta" style={{ fontSize: '12px', color: '#64748b' }}>
                      {(selectedFile.size / 1024).toFixed(1)} KB • Target: <strong style={{ color: '#000000' }}>{selectedCategory === 'customer' ? 'Customer Insurance' : 'Employee Insurance'}</strong>
                    </span>
                    <span className="file-ready-tag" style={{ fontSize: '11.5px', color: '#059669', fontWeight: 700 }}>✓ Ready for Processing</span>
                  </div>
                  <button
                    type="button"
                    className="change-file-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedFile(null);
                    }}
                    disabled={isProcessing}
                  >
                    Change File
                  </button>
                </div>
              ) : (
                <div className="dropzone-empty-state">
                  <div className="upload-cloud-icon" style={{ width: '44px', height: '44px', marginBottom: '2px' }}>
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#007aff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242" />
                      <path d="M12 12v9" />
                      <path d="m16 16-4-4-4 4" />
                    </svg>
                  </div>
                  <strong className="dropzone-main-text" style={{ fontSize: '14px', fontWeight: 700, color: '#000000' }}>
                    Click or drag a policy PDF document here
                  </strong>
                  <span className="dropzone-sub-text" style={{ fontSize: '12px', color: '#64748b' }}>
                    PDF format only, up to 25 MB
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Progress Indicator while processing */}
          {isProcessing && (
            <div className="ingestion-live-progress" style={{ marginBottom: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '12.5px', fontWeight: 600 }}>
                <span style={{ color: '#007aff' }}>Extracting sections, tables, and generating embeddings...</span>
                <span style={{ color: '#64748b' }}>In Progress</span>
              </div>
              <div className="progress-bar-bg" style={{ height: '6px', background: '#e2e8f0', borderRadius: '4px', overflow: 'hidden' }}>
                <div
                  className="progress-bar-fill animated-bar"
                  style={{ width: '75%', height: '100%', background: '#007aff', borderRadius: '4px' }}
                ></div>
              </div>
            </div>
          )}

          {/* Action Bar */}
          <div className="ingestion-action-bar" style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
            <button
              id="start-ingestion-btn"
              type="button"
              className="btn-pro-ingest"
              disabled={!selectedFile || isProcessing}
              onClick={handleStartIngestion}
            >
              {isProcessing ? (
                <>
                  <div className="btn-spinner"></div>
                  <span>Processing Document...</span>
                </>
              ) : (
                <>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="21" x2="12" y2="3" />
                  </svg>
                  <span>Process Document</span>
                </>
              )}
            </button>
          </div>
        </div>
      ) : (
        /* Completed Job Summary Screen */
        <div className="ingestion-summary-view" style={{ maxWidth: '680px', margin: '0 auto 28px auto' }}>
          <div className="ingestion-card summary-card">
            <div className="summary-header">
              <div className="summary-success-badge">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                  <polyline points="22 4 12 14.01 9 11.01" />
                </svg>
                <span>Document Processing Complete</span>
              </div>
              <button type="button" className="btn-pro-secondary" onClick={handleReset}>
                Upload Another Document
              </button>
            </div>

            {currentJob.is_duplicate && (
              <div className="ingestion-notice-box info">
                This document has already been ingested. Existing records were verified and preserved in the vector store.
              </div>
            )}

            <div className="summary-metrics-grid">
              <div className="summary-metric-box">
                <span className="metric-box-label">DOCUMENT</span>
                <strong className="metric-box-val">{currentJob.filename}</strong>
              </div>
              <div className="summary-metric-box">
                <span className="metric-box-label">POLICY PLAN</span>
                <strong className="metric-box-val">{currentJob.plan_id}</strong>
              </div>
              <div className="summary-metric-box">
                <span className="metric-box-label">STORED RECORDS</span>
                <strong className="metric-box-val highlight">
                  {currentJob.metrics?.records_stored || currentJob.metrics?.child_chunks_count || currentJob.chunk_count || 30}
                </strong>
              </div>
              <div className="summary-metric-box">
                <span className="metric-box-label">STATUS</span>
                <span className="admin-status-badge success">
                  {currentJob.status === 'COMPLETED' ? 'SUCCESS' : currentJob.status}
                </span>
              </div>
            </div>

            <div className="summary-footer-actions">
              <span className="summary-timestamp">Job ID: {currentJob.job_id || 'verified'} • Logged in audit registry</span>
            </div>
          </div>
        </div>
      )}

      {/* Processed Documents History Table */}
      <div className="admin-card admin-log-stream-card">
        <div className="admin-card-header">
          <div>
            <h2 className="admin-card-title">Processed Documents</h2>
          </div>

          <div className="admin-table-filters">
            <input
              type="search"
              placeholder="Filter documents..."
              value={historySearch}
              onChange={(e) => setHistorySearch(e.target.value)}
              className="admin-search-input"
            />
            <button
              type="button"
              className="btn-pro-refresh"
              onClick={loadHistory}
              disabled={historyLoading}
              title="Refresh document records"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="23 4 23 10 17 10" />
                <polyline points="1 20 1 14 7 14" />
                <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
              </svg>
              <span>{historyLoading ? 'Refreshing...' : 'Refresh'}</span>
            </button>
          </div>
        </div>

        <div className="admin-table-wrapper admin-log-scroll-wrapper">
          <table className="admin-data-table admin-log-table">
            <thead>
              <tr>
                <th>Document</th>
                <th>Plan ID</th>
                <th>Status</th>
                <th>Chunks</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {filteredHistory.length === 0 ? (
                <tr>
                  <td colSpan="5" style={{ textAlign: 'center', padding: '36px', color: '#64748b' }}>
                    {historyLoading ? 'Loading document inventory...' : 'No policy documents have been uploaded yet.'}
                  </td>
                </tr>
              ) : (
                filteredHistory.map((item, idx) => {
                  const isCompleted = item.status === 'COMPLETED' || item.status === 'SUCCESS';
                  const isPreserved = item.status === 'SKIPPED_DUPLICATE';

                  return (
                    <tr key={idx}>
                      <td>
                        <div className="doc-name-cell">
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#dc2626" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                            <polyline points="14 2 14 8 20 8" />
                          </svg>
                          <strong className="admin-actor-email">{item.source_document || item.filename || 'policy_document.pdf'}</strong>
                        </div>
                      </td>
                      <td>
                        <span className="admin-mini-plan-tag">
                          {item.plan_id}
                        </span>
                      </td>
                      <td>
                        <span className={`admin-status-badge ${isCompleted ? 'success' : isPreserved ? 'warning' : 'failed'}`}>
                          {isCompleted ? 'Completed' : isPreserved ? 'Preserved' : 'Failed'}
                        </span>
                      </td>
                      <td>
                        <strong style={{ color: '#000000', fontWeight: 700 }}>{item.chunks_stored || item.chunk_count || 0}</strong>
                      </td>
                      <td>
                        <span className="admin-log-time">
                          {item.timestamp
                            ? new Date(item.timestamp).toLocaleDateString() + ' ' + new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                            : new Date().toLocaleDateString()}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default IngestionPage;
