import React from 'react';

/**
 * ProcessSidebar — Persistent Left Navigation Sidebar for Customer and Employee workspaces.
 * Follows the high-end executive pattern established in the Administrator Workspace:
 * - Professional vector SVG icons
 * - Active dot indicators & status pills
 * - Scope authorization footer
 */
export function ProcessSidebar({
  activeStage,
  selectedPlan,
  onNavigate,
  userRole,
  currentUser
}) {
  const isEmployee = userRole === 'employee';

  const stages = [
    {
      id: 'plans',
      number: '1',
      title: 'Choose Plan',
      desc: selectedPlan ? selectedPlan.plan_name : 'Select active policy portfolio',
      badge: selectedPlan ? (selectedPlan.display_title || selectedPlan.plan_category) : null,
      badgeClass: selectedPlan ? selectedPlan.plan_category.toLowerCase() : null,
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          <path d="m9 12 2 2 4-4" />
        </svg>
      ),
      disabled: false
    },
    {
      id: 'chat',
      number: '2',
      title: 'Policy Chat',
      desc: selectedPlan ? `Grounded Q&A (${selectedPlan.plan_id})` : 'Select a plan to start chat',
      badge: activeStage === 'chat' ? 'Active Scope' : null,
      badgeClass: 'active-stage',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          <line x1="9" y1="10" x2="15" y2="10" />
        </svg>
      ),
      disabled: !selectedPlan
    }
  ];

  return (
    <aside className="process-sidebar" aria-label="Process Navigation">
      <div className="process-sidebar-header">
        <span className="process-sidebar-label">
          {isEmployee ? 'Corporate Workspace' : 'Insurance Assistant'}
        </span>
        <span className="admin-status-pill">Active Session</span>
      </div>

      <nav className="process-nav-list" role="navigation">
        {stages.map((stage) => {
          const isActive = activeStage === stage.id;
          const isCompleted = stage.id === 'plans' && selectedPlan && activeStage !== 'plans';

          return (
            <button
              key={stage.id}
              type="button"
              className={`process-nav-item ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''} ${stage.disabled ? 'disabled' : ''}`}
              onClick={() => !stage.disabled && onNavigate(stage.id)}
              disabled={stage.disabled}
              title={stage.disabled ? 'Select a plan first to unlock Policy Chat' : stage.title}
              aria-current={isActive ? 'step' : undefined}
            >
              <div className="process-nav-icon-col">
                <div className={`process-step-circle ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''}`}>
                  {isCompleted ? (
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#ffffff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  ) : (
                    stage.icon
                  )}
                </div>
              </div>

              <div className="process-nav-info">
                <div className="process-nav-title-row">
                  <span className="process-nav-title">{stage.title}</span>
                  {isActive && <span className="admin-active-dot" aria-hidden="true">•</span>}
                  {stage.badge && !isActive && (
                    <span className={`process-mini-badge ${stage.badgeClass || ''}`}>
                      {stage.badge}
                    </span>
                  )}
                </div>
                <div className="process-nav-desc">{stage.desc}</div>
              </div>
            </button>
          );
        })}
      </nav>

      {/* Matching Enterprise Footer Authorization Scope Badge */}
      <div className="admin-sidebar-footer" style={{ marginTop: 'auto' }}>
        <div
          className="admin-scope-badge"
          style={isEmployee ? { color: '#065f46', background: '#ecfdf5' } : { color: '#0369a1', background: '#e0f2fe' }}
        >
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
          <span>{isEmployee ? 'Corporate Scope Active' : 'Customer Grounding Active'}</span>
        </div>
      </div>
    </aside>
  );
}

export default ProcessSidebar;
