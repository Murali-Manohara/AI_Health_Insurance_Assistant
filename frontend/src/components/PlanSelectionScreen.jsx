import React, { useState, useEffect } from 'react';

export function PlanSelectionScreen({ userRole, authToken, onSelectPlan, onUnauthorized }) {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchPlans();
  }, [userRole, authToken]);

  const fetchPlans = async () => {
    setLoading(true);
    setError(null);
    try {
      const headers = { 'X-User-Role': userRole };
      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
      }
      let res;
      try {
        res = await fetch('/api/plans', { headers });
      } catch {
        res = await fetch('http://127.0.0.1:8000/api/plans', { headers });
      }

      if (res.status === 401 && onUnauthorized) {
        onUnauthorized();
        return;
      }
      const text = await res.text();
      let data = {};
      if (text) {
        try { data = JSON.parse(text); } catch { data = { detail: text }; }
      }
      if (!res.ok) {
        throw new Error(data.detail || `Failed to load plans: HTTP ${res.status}`);
      }
      setPlans(data.plans || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getPlanTheme = (planId = '', category = '') => {
    const id = planId.toUpperCase();
    if (id.includes('BASIC')) {
      return {
        color: '#0284c7',
        badgeBg: '#e0f2fe',
        badgeText: '#0369a1',
        tag: 'Customer Scope',
        icon: (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#0284c7" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
          </svg>
        )
      };
    }
    if (id.includes('GOLD')) {
      return {
        color: '#d97706',
        badgeBg: '#fef3c7',
        badgeText: '#b45309',
        tag: 'Customer Scope',
        icon: (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#d97706" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
          </svg>
        )
      };
    }
    if (id.includes('PREM')) {
      return {
        color: '#7c3aed',
        badgeBg: '#ede9fe',
        badgeText: '#6d28d9',
        tag: 'Customer Scope',
        icon: (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#7c3aed" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M6 3h12l4 6-10 13L2 9z" />
            <path d="M11 3 8 9l4 13 4-13-3-6" />
          </svg>
        )
      };
    }
    return {
      color: '#059669',
      badgeBg: '#ecfdf5',
      badgeText: '#065f46',
      tag: 'Corporate Employee Exclusive',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
          <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
        </svg>
      )
    };
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '10px 8px 32px 8px' }}>
      {/* Executive Header matching Admin style */}
      <div className="ingestion-title-group" style={{ marginBottom: '26px' }}>
        <div className="admin-badge-tag">
          {userRole === 'employee' ? 'CORPORATE PLANS • EMPLOYEE ACCESS SCOPE' : 'AUTHORIZED POLICY PORTFOLIO • PLAN SELECTION'}
        </div>
        <h1 className="ingestion-heading" style={{ fontSize: '22px' }}>Choose Your Insurance Plan</h1>
        <p className="ingestion-subheading">
          Select an authorized insurance policy below to initiate a plan-scoped conversational assistant. 
          Inquiries are grounded against official clauses, hospital cash schedules, and coverage terms.
        </p>
      </div>

      {loading && (
        <div className="card" style={{ textAlign: 'center', padding: '48px', color: 'var(--text-muted)' }}>
          <div className="admin-spinner" style={{ margin: '0 auto 12px auto' }}></div>
          <span>Loading authorized insurance plans...</span>
        </div>
      )}

      {error && (
        <div className="admin-error-banner" style={{ marginBottom: '20px' }}>
          <span><strong>Error loading plans:</strong> {error}</span>
          <button className="admin-retry-btn" onClick={fetchPlans}>
            Retry
          </button>
        </div>
      )}

      {!loading && !error && (
        <div className="plan-cards-grid" style={{ gap: '22px' }}>
          {plans.map((p) => {
            const isEmployeePlan = p.plan_id === 'EMP-INS-001';
            const theme = getPlanTheme(p.plan_id, p.plan_category);

            return (
              <div
                key={p.plan_id}
                className="plan-card"
                style={{
                  borderLeft: `4px solid ${theme.color}`,
                  display: 'flex',
                  flexDirection: 'column',
                  padding: '24px',
                  borderRadius: '8px',
                  background: '#ffffff',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.04)'
                }}
              >
                {/* Card Top Row with Badge & Scope Tag */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                  <span
                    className="plan-code-badge"
                    style={{
                      background: theme.badgeBg,
                      color: theme.badgeText,
                      padding: '3px 8px',
                      borderRadius: '4px',
                      fontSize: '11px',
                      fontWeight: 700,
                      fontFamily: 'monospace'
                    }}
                  >
                    {p.plan_id}
                  </span>
                  <span style={{ fontSize: '10.5px', fontWeight: 600, color: '#64748b', textTransform: 'uppercase' }}>
                    {theme.tag}
                  </span>
                </div>

                {/* Plan Title & Icon */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                  <div style={{ width: '34px', height: '34px', borderRadius: '8px', background: theme.badgeBg, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                    {theme.icon}
                  </div>
                  <div>
                    <h3 className="plan-card-title" style={{ fontSize: '16.5px', fontWeight: 700, margin: 0 }}>
                      {p.plan_name}
                    </h3>
                    <span style={{ fontSize: '11px', color: 'var(--text-light)' }}>
                      Category: <strong>{p.display_title || p.plan_category}</strong>
                    </span>
                  </div>
                </div>

                <p className="plan-card-desc" style={{ fontSize: '12.5px', color: 'var(--text-muted)', lineHeight: 1.45, margin: '8px 0 16px 0' }}>
                  {p.description}
                </p>

                {/* Highlights List with Green Checkmarks */}
                <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: '12px', marginBottom: '18px', flex: 1 }}>
                  <span style={{ fontSize: '10.5px', fontWeight: 700, color: '#64748b', letterSpacing: '0.04em', textTransform: 'uppercase', display: 'block', marginBottom: '8px' }}>
                    Coverage Terms & Highlights
                  </span>
                  <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                    {p.highlights && p.highlights.map((h, idx) => (
                      <li key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', padding: '5px 0', fontSize: '12px', color: '#334155' }}>
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, marginTop: '2px' }}>
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                        <span>{h}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                {isEmployeePlan && (
                  <div className="unverified-banner" style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                      <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
                      <line x1="12" y1="9" x2="12" y2="13" />
                      <line x1="12" y1="17" x2="12.01" y2="17" />
                    </svg>
                    <span>Contains illustrative corporate demonstration schedules.</span>
                  </div>
                )}

                <button
                  className="btn btn-primary"
                  style={{ width: '100%', marginTop: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', padding: '10px 16px', fontWeight: 600, fontSize: '13px' }}
                  onClick={() => onSelectPlan(p)}
                >
                  <span>Open {p.display_title || 'Policy'} Assistant</span>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="5" y1="12" x2="19" y2="12" />
                    <polyline points="12 5 19 12 12 19" />
                  </svg>
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default PlanSelectionScreen;
