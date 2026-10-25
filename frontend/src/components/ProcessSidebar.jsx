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
  assessment,
  onNavigate,
  onBack,
  userRole,
  currentUser
}) {
  const isEmployee = userRole === 'employee';

  const stages = [
    {
      id: 'eligibility',
      number: '1',
      title: 'Eligibility Assessment',
      desc: assessment ? (assessment.outcome === 'ELIGIBLE' ? 'Qualified (Underwriting Passed)' : assessment.outcome.replace('_', ' ')) : 'Risk evaluation',
      badge: assessment ? (assessment.outcome === 'ELIGIBLE' ? 'Qualified' : 'Assessed') : null,
      badgeClass: assessment ? (assessment.outcome === 'ELIGIBLE' ? 'gold' : 'basic') : null,
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          <path d="M9 12l2 2 4-4" />
        </svg>
      ),
      disabled: false
    },
    {
      id: 'plans',
      number: '2',
      title: 'Choose Plan',
      desc: selectedPlan ? selectedPlan.plan_name : 'Select active policy portfolio',
      badge: selectedPlan ? (selectedPlan.display_title || selectedPlan.plan_category) : null,
      badgeClass: selectedPlan ? selectedPlan.plan_category.toLowerCase() : null,
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
          <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
        </svg>
      ),
      disabled: !assessment && !isEmployee
    },
    {
      id: 'chat',
      number: '3',
      title: 'Policy Chat',
      desc: selectedPlan ? `Grounded Q&A (${selectedPlan.plan_id})` : 'Select a plan to start chat',
      badge: activeStage === 'chat' ? 'Active Scope' : null,
      badgeClass: 'active-stage',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          <line x1="9" y1="10" x2="15" y2="10" />
        </svg>
      ),
      disabled: !selectedPlan
    }
  ];

  return (
    <aside className="process-sidebar" aria-label="Process Navigation">
      {/* Top Header of Sidebar: Back button on top left when in chat */}
      <div className="sidebar-top-header">
        {activeStage === 'chat' ? (
          <button
            type="button"
            className="sidebar-back-btn"
            onClick={onBack}
            title="Back"
            aria-label="Back"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
              <line x1="19" y1="12" x2="5" y2="12"></line>
              <polyline points="12 19 5 12 12 5"></polyline>
            </svg>
            <span>Back</span>
          </button>
        ) : (
          <div className="sidebar-brand-mark">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
            <span>Policy Assistant</span>
          </div>
        )}
      </div>

      <nav className="process-nav-list" role="navigation">
        {stages.map((stage) => {
          const isActive = activeStage === stage.id;
          const isCompleted =
            (stage.id === 'eligibility' && assessment && activeStage !== 'eligibility') ||
            (stage.id === 'plans' && selectedPlan && activeStage === 'chat');

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
                </div>
              </div>
            </button>
          );
        })}
      </nav>
    </aside>
  );
}

export default ProcessSidebar;
