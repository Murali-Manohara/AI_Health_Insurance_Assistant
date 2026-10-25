import React from 'react';

/**
 * AdminSidebar — Dedicated Administrator Workspace Sidebar
 * Contains EXACTLY TWO primary navigation items:
 * 1. Document Ingestion
 * 2. Admin Dashboard
 */
export function AdminSidebar({ activeTab, onNavigate }) {
  const navItems = [
    {
      id: 'ingestion',
      title: 'Document Ingestion',
      subtitle: 'PDF Pipeline & Knowledge Base',
      icon: (
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="admin-nav-icon"
        >
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
          <line x1="12" y1="18" x2="12" y2="12"></line>
          <line x1="9" y1="15" x2="15" y2="15"></line>
        </svg>
      )
    },
    {
      id: 'dashboard',
      title: 'Admin Dashboard',
      subtitle: 'Analytics & System Governance',
      icon: (
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="admin-nav-icon"
        >
          <rect x="3" y="3" width="7" height="9"></rect>
          <rect x="14" y="3" width="7" height="5"></rect>
          <rect x="14" y="12" width="7" height="9"></rect>
          <rect x="3" y="16" width="7" height="5"></rect>
        </svg>
      )
    }
  ];

  return (
    <aside className="process-sidebar admin-sidebar" aria-label="Administrator Navigation">
      <div className="sidebar-top-header" style={{ display: 'flex', alignItems: 'center', height: '56px', minHeight: '56px', padding: '0 8px', borderBottom: '1px solid rgba(214, 214, 216, 0.40)', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#007aff', boxShadow: '0 0 8px rgba(0, 122, 255, 0.6)' }} />
          <span style={{ fontSize: '13px', fontWeight: 800, color: '#000000', letterSpacing: '-0.01em' }}>
            Administrator Mode
          </span>
        </div>
      </div>

      <nav className="process-nav-list admin-nav-list" role="navigation">
        {navItems.map((item) => {
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              type="button"
              className={`process-nav-item admin-nav-item ${isActive ? 'active' : ''}`}
              onClick={() => onNavigate(item.id)}
              aria-current={isActive ? 'page' : undefined}
            >
              <div className="process-nav-icon-col">
                <div className={`process-step-circle admin-step-circle ${isActive ? 'active' : ''}`}>
                  {item.icon}
                </div>
              </div>

              <div className="process-nav-info">
                <div className="process-nav-title-row">
                  <span className="process-nav-title admin-nav-title">{item.title}</span>
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

export default AdminSidebar;
