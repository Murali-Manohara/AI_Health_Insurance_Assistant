import React from 'react';

export function IngestionHistory({ history = [], onRefresh, isLoading = false }) {
  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 className="card-title" style={{ margin: 0 }}>Processed Documents</h3>
        <button onClick={onRefresh} className="btn btn-secondary" disabled={isLoading}>
          {isLoading ? 'Updating...' : 'Refresh'}
        </button>
      </div>

      {history.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', fontSize: '13px', padding: '16px 0' }}>
          No policy documents have been uploaded yet.
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
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
              {history.map((item, idx) => (
                <tr key={idx}>
                  <td style={{ fontWeight: 500 }}>{item.source_document}</td>
                  <td>{item.plan_id}</td>
                  <td>
                    <span className={`status-tag ${item.status === 'COMPLETED' ? 'success' : item.status === 'SKIPPED_DUPLICATE' ? 'skipped' : 'failed'}`}>
                      {item.status === 'COMPLETED' ? 'Completed' : item.status === 'SKIPPED_DUPLICATE' ? 'Preserved' : item.status}
                    </span>
                  </td>
                  <td>{item.chunks_stored}</td>
                  <td style={{ color: 'var(--text-muted)' }}>
                    {new Date(item.timestamp).toLocaleDateString()} {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
