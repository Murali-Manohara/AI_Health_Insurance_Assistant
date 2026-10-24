import React, { useState, useEffect } from 'react';
import { PlanSelectionScreen } from './components/PlanSelectionScreen';
import { PlanChatScreen } from './components/PlanChatScreen';
import { IngestionPage } from './pages/IngestionPage';
import { LoginScreen } from './components/LoginScreen';
import { SignupScreen } from './components/SignupScreen';
import { authApi } from './services/authApi';
import './styles/main.css';

export function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [authToken, setAuthToken] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authScreen, setAuthScreen] = useState('login'); // 'login' | 'signup'

  const [activeTab, setActiveTab] = useState('plans'); // 'plans' | 'chat' | 'ingestion'
  const [selectedPlan, setSelectedPlan] = useState(null);

  // Restore authenticated session on page refresh
  useEffect(() => {
    async function restoreSession() {
      setAuthLoading(true);
      const token = authApi.getToken();
      if (token) {
        setAuthToken(token);
        const user = await authApi.getCurrentUser();
        if (user) {
          setCurrentUser(user);
        } else {
          setCurrentUser(null);
          setAuthToken(null);
        }
      }
      setAuthLoading(false);
    }
    restoreSession();
  }, []);

  const handleLoginSuccess = (user, token) => {
    setCurrentUser(user);
    setAuthToken(token);
    setActiveTab('plans');
    setSelectedPlan(null);
  };

  const handleLogout = async () => {
    await authApi.logout();
    setCurrentUser(null);
    setAuthToken(null);
    setSelectedPlan(null);
    setActiveTab('plans');
    setAuthScreen('login');
  };

  const handleSelectPlan = (plan) => {
    setSelectedPlan(plan);
    setActiveTab('chat');
  };

  const handleBackToPlans = () => {
    setActiveTab('plans');
  };

  // If restoring session, show clean loading state
  if (authLoading) {
    return (
      <div className="app-container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
          <div className="auth-spinner" style={{ width: '28px', height: '28px', margin: '0 auto 12px auto', borderTopColor: 'var(--accent)' }}></div>
          <p style={{ fontSize: '13px' }}>Verifying secure session...</p>
        </div>
      </div>
    );
  }

  // Phase 5 Gate: Unauthenticated users can only access Login and Signup
  if (!currentUser) {
    return (
      <div className="app-container">
        <header className="app-header">
          <div>
            <h1 className="brand-title">AI Insurance Assistant</h1>
            <p className="brand-subtitle">
              Plan-Scoped, Role-Aware RAG Policy Intelligence
            </p>
          </div>
        </header>

        <main>
          {authScreen === 'login' ? (
            <LoginScreen
              onLoginSuccess={handleLoginSuccess}
              onSwitchToSignup={() => setAuthScreen('signup')}
            />
          ) : (
            <SignupScreen
              onSignupSuccess={handleLoginSuccess}
              onSwitchToLogin={() => setAuthScreen('login')}
            />
          )}
        </main>
      </div>
    );
  }

  // Authenticated State: Full Protected Application Access
  const userRole = currentUser.role || 'customer';

  return (
    <div className="app-container">
      {/* Top Application Header */}
      <header className="app-header">
        <div>
          <h1 className="brand-title">AI Insurance Assistant</h1>
          <p className="brand-subtitle">
            Plan-Scoped, Role-Aware RAG Policy Intelligence
          </p>
        </div>

        {/* Authenticated User Session Bar */}
        <div className="user-session-bar">
          <div className="user-identity-badge">
            <span style={{ fontWeight: 600 }}>{currentUser.full_name || currentUser.email}</span>
            <span className={`user-role-tag ${userRole}`}>
              {userRole}
            </span>
            {!currentUser.is_approved && userRole === 'customer' && (
              <span title="Employee approval pending" style={{ fontSize: '11px', color: '#b45309' }}>
                (Staff Pending)
              </span>
            )}
          </div>

          <button
            type="button"
            className="logout-btn"
            onClick={handleLogout}
            title="End session and log out"
          >
            Sign Out
          </button>
        </div>
      </header>

      {/* Primary Navigation Tabs */}
      <nav className="tabs" style={{ marginBottom: '20px' }}>
        <button
          className={`tab-btn ${activeTab === 'plans' ? 'active' : ''}`}
          onClick={() => setActiveTab('plans')}
        >
          1. Choose Plan
        </button>
        <button
          className={`tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => {
            if (selectedPlan) setActiveTab('chat');
            else setActiveTab('plans');
          }}
          disabled={!selectedPlan}
          title={!selectedPlan ? 'Select a plan first' : ''}
        >
          2. Policy Chat {selectedPlan ? `(${selectedPlan.display_title || selectedPlan.plan_category})` : ''}
        </button>
        <button
          className={`tab-btn ${activeTab === 'ingestion' ? 'active' : ''}`}
          onClick={() => setActiveTab('ingestion')}
        >
          Ingestion Admin
        </button>
      </nav>

      {/* Screen Views */}
      <main>
        {activeTab === 'plans' && (
          <PlanSelectionScreen
            userRole={userRole}
            authToken={authToken}
            onSelectPlan={handleSelectPlan}
            onUnauthorized={handleLogout}
          />
        )}

        {activeTab === 'chat' && selectedPlan && (
          <PlanChatScreen
            selectedPlan={selectedPlan}
            userRole={userRole}
            authToken={authToken}
            onBackToPlans={handleBackToPlans}
            onUnauthorized={handleLogout}
          />
        )}

        {activeTab === 'ingestion' && (
          <IngestionPage />
        )}
      </main>
    </div>
  );
}

export default App;
