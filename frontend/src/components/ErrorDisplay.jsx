import React from 'react';

export function ErrorDisplay({ errors = [], warnings = [], onDismiss }) {
  if (errors.length === 0 && warnings.length === 0) return null;

  return (
    <div style={{ marginBottom: '16px' }}>
      {errors.length > 0 && (
        <div className="alert alert-error">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
            <strong>Error</strong>
            {onDismiss && (
              <button
                onClick={onDismiss}
                style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontSize: '12px' }}
              >
                Dismiss
              </button>
            )}
          </div>
          {errors.map((err, i) => (
            <div key={i}>{err}</div>
          ))}
        </div>
      )}

      {warnings.length > 0 && (
        <div className="alert alert-info">
          {warnings.map((w, i) => (
            <div key={i}>{w}</div>
          ))}
        </div>
      )}
    </div>
  );
}
