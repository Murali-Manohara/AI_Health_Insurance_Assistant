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

  const getBadgeClass = (category) => {
    const cat = (category || '').toLowerCase();
    if (cat.includes('basic')) return 'basic';
    if (cat.includes('gold')) return 'gold';
    if (cat.includes('premium')) return 'premium';
    return 'employee';
  };

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '20px', fontWeight: 600, color: 'var(--text-main)', marginBottom: '4px' }}>
          Choose your insurance plan
        </h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
          Select an authorized insurance plan below to open a plan-scoped conversational assistant. 
          Questions will search your selected policy terms by default.
        </p>
      </div>

      {loading && (
        <div className="card" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
          Loading authorized insurance plans...
        </div>
      )}

      {error && (
        <div className="alert alert-error" style={{ marginBottom: '20px' }}>
          <strong>Error loading plans:</strong> {error}
          <button className="btn btn-secondary" style={{ marginLeft: '12px' }} onClick={fetchPlans}>
            Retry
          </button>
        </div>
      )}

      {!loading && !error && (
        <div className="plan-cards-grid">
          {plans.map((p) => {
            const isEmployeePlan = p.plan_id === 'EMP-INS-001';
            return (
              <div key={p.plan_id} className="plan-card">
                <div className="plan-card-header">
                  <span className={`plan-badge ${getBadgeClass(p.plan_category)}`}>
                    {p.display_title || p.plan_category}
                  </span>
                  <h3 className="plan-card-title">{p.plan_name}</h3>
                  <div style={{ fontSize: '11px', color: 'var(--text-light)', marginTop: '2px' }}>
                    ID: {p.plan_id} • {p.audience === 'employee' ? 'Employee Exclusive' : 'Customer Policy'}
                  </div>
                </div>

                <p className="plan-card-desc">{p.description}</p>

                <ul className="plan-card-highlights">
                  {p.highlights && p.highlights.map((h, idx) => (
                    <li key={idx}>{h}</li>
                  ))}
                </ul>

                {isEmployeePlan && (
                  <div className="unverified-banner" style={{ marginBottom: '16px' }}>
                    <span>⚠️</span>
                    <span>Contains illustrative demonstration schedules.</span>
                  </div>
                )}

                <button
                  className="btn btn-primary"
                  style={{ width: '100%', marginTop: 'auto' }}
                  onClick={() => onSelectPlan(p)}
                >
                  Open {p.display_title} Chat →
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
