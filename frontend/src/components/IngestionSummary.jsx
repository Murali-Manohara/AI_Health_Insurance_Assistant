import React from 'react';

export function IngestionSummary({ job, onReset }) {
  const isDuplicate = job.is_duplicate || job.status === 'SKIPPED_DUPLICATE';
  const metrics = job.metrics || {};

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 className="card-title" style={{ margin: 0 }}>Document Processing Complete</h3>
        <button onClick={onReset} className="btn btn-secondary">
          Upload Another Document
        </button>
      </div>

      {isDuplicate && (
        <div className="alert alert-info">
          This document has already been ingested. Existing records were verified and preserved.
        </div>
      )}

      {job.warnings && job.warnings.length > 0 && (
        <div className="alert alert-info">
          {job.warnings.map((w, i) => (
            <div key={i}>{w}</div>
          ))}
        </div>
      )}

      <div className="summary-grid">
        <div className="summary-item">
          <div className="summary-label">Document</div>
          <div className="summary-value" style={{ fontSize: '14px', wordBreak: 'break-all' }}>{job.filename}</div>
        </div>
        <div className="summary-item">
          <div className="summary-label">Policy Plan</div>
          <div className="summary-value" style={{ fontSize: '14px' }}>{job.plan_id}</div>
        </div>
        <div className="summary-item">
          <div className="summary-label">Status</div>
          <div className="summary-value" style={{ fontSize: '14px', color: '#0369a1' }}>
            {job.status === 'COMPLETED' ? 'Success' : job.status}
          </div>
        </div>
        <div className="summary-item">
          <div className="summary-label">Stored Records</div>
          <div className="summary-value">{metrics.records_stored || metrics.child_chunks_count || 0}</div>
        </div>
      </div>
    </div>
  );
}
