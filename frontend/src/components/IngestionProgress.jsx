import React from 'react';

export function IngestionProgress({ currentStage, completedStages = [], status }) {
  return (
    <div className="progress-box">
      <div className="progress-header">
        <span>{currentStage || 'Processing document...'}</span>
        <span>{status === 'FAILED' ? 'Failed' : 'In Progress'}</span>
      </div>
      <div className="progress-bar-bg">
        <div
          className="progress-bar-fill"
          style={{ width: status === 'FAILED' ? '100%' : '75%' }}
        ></div>
      </div>
    </div>
  );
}
