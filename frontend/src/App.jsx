import React, { useState, useEffect } from 'react';
import { EligibilityScreen } from './components/EligibilityScreen';
import { PlanSelectionScreen } from './components/PlanSelectionScreen';
import { PlanChatScreen } from './components/PlanChatScreen';
import { ConfirmReviewScreen } from './components/ConfirmReviewScreen';
import { IngestionPage } from './pages/IngestionPage';
import { AdminDashboardPage } from './pages/AdminDashboardPage';
import { LoginScreen } from './components/LoginScreen';
import { SignupScreen } from './components/SignupScreen';
import { ProcessSidebar } from './components/ProcessSidebar';
import { AdminSidebar } from './components/AdminSidebar';
import { ProfileDrawer } from './components/ProfileDrawer';
import { authApi } from './services/authApi';
import { eligibilityApi } from './services/eligibilityApi';
import './styles/main.css';

export function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [authToken, setAuthToken] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authScreen, setAuthScreen] = useState('login'); // 'login' | 'signup'

  // Customer navigation state: Stage 1 'eligibility' -> Stage 2 'plans' -> Stage 3 'chat'
  const [activeTab, setActiveTab] = useState('eligibility');
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [userAssessment, setUserAssessment] = useState(null);

  // Administrator navigation state: strictly two items ('dashboard' | 'ingestion')
  const [adminTab, setAdminTab] = useState('dashboard');

  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isChatMenuOpen, setIsChatMenuOpen] = useState(false);
  const [newChatTrigger, setNewChatTrigger] = useState(0);
  const [userMessageCount, setUserMessageCount] = useState(0);
  const [isClaimPredictorOpen, setIsClaimPredictorOpen] = useState(false);

  // Restore authenticated session and active navigation stage on page refresh
  useEffect(() => {
    async function restoreSession() {
      setAuthLoading(true);
      const token = authApi.getToken();
      if (token) {
        setAuthToken(token);
        const user = await authApi.getCurrentUser();
        if (user) {
          setCurrentUser(user);

          const savedPlan = sessionStorage.getItem('ins_app_selected_plan');
          const savedTab = sessionStorage.getItem('ins_app_active_tab');
          const savedAdminTab = sessionStorage.getItem('ins_app_admin_tab');

          if (savedAdminTab) {
            setAdminTab(savedAdminTab);
          }

          if (user.role !== 'admin') {
            try {
              const eligData = await eligibilityApi.getMyAssessment();
              if (eligData && eligData.has_assessment && eligData.assessment) {
                setUserAssessment(eligData.assessment);
                const isEligible = eligData.assessment.outcome === 'ELIGIBLE';
                if (isEligible) {
                  const activeSel = eligData.active_plan_selection;
                  const isConfirmed = Boolean(
                    user.is_confirmed ||
                    user.confirmation_status === 'CONFIRMED' ||
                    activeSel?.status === 'CONFIRMED' ||
                    activeSel?.confirmed_at
                  );

                  let planToSet = null;
                  if (savedPlan) {
                    try {
                      planToSet = JSON.parse(savedPlan);
                    } catch {
                      planToSet = null;
                    }
                  }

                  if (!planToSet && activeSel) {
                    const pId = activeSel.selected_plan_id;
                    planToSet = {
                      plan_id: pId,
                      plan_name: pId.includes('GOLD')
                        ? 'Health Shield — Gold'
                        : pId.includes('PREM')
                        ? 'Health Shield — Premium'
                        : pId.includes('EMP')
                        ? 'Executive Employee Insurance Plan'
                        : 'Health Shield — Basic',
                      plan_category: pId.includes('GOLD')
                        ? 'Gold'
                        : pId.includes('PREM')
                        ? 'Premium'
                        : pId.includes('EMP')
                        ? 'Employee Exclusive'
                        : 'Basic',
                      display_title: pId.includes('GOLD')
                        ? 'Gold Plan'
                        : pId.includes('PREM')
                        ? 'Premium Plan'
                        : pId.includes('EMP')
                        ? 'Employee Plan'
                        : 'Basic Plan',
                      status: isConfirmed ? 'CONFIRMED' : (activeSel.status || 'ACTIVE'),
                      is_confirmed: isConfirmed,
                      confirmed_at: activeSel.confirmed_at || user.confirmed_at || null
                    };
                  }

                  if (planToSet) {
                    if (isConfirmed) {
                      planToSet.is_confirmed = true;
                      planToSet.status = 'CONFIRMED';
                      if (activeSel?.confirmed_at) {
                        planToSet.confirmed_at = activeSel.confirmed_at;
                      } else if (user.confirmed_at) {
                        planToSet.confirmed_at = user.confirmed_at;
                      }
                    }
                    setSelectedPlan(planToSet);
                    sessionStorage.setItem('ins_app_selected_plan', JSON.stringify(planToSet));

                    if (isConfirmed && user.role !== 'admin') {
                      setActiveTab(savedTab === 'chat' ? 'chat' : 'confirm');
                    } else {
                      setActiveTab(savedTab || 'chat');
                    }
                  } else {
                    setActiveTab(savedTab === 'eligibility' ? 'eligibility' : 'plans');
                  }
                } else {
                  setSelectedPlan(null);
                  sessionStorage.removeItem('ins_app_selected_plan');
                  setActiveTab('eligibility');
                  sessionStorage.setItem('ins_app_active_tab', 'eligibility');
                }
              } else {
                setUserAssessment(null);
                setActiveTab('eligibility');
                sessionStorage.setItem('ins_app_active_tab', 'eligibility');
              }
            } catch {
              setActiveTab('eligibility');
            }
          }
        } else {
          setCurrentUser(null);
          setAuthToken(null);
        }
      }
      setAuthLoading(false);
    }
    restoreSession();
  }, []);

  const handleLoginSuccess = async (user, token) => {
    setCurrentUser(user);
    setAuthToken(token);
    setIsProfileOpen(false);

    if (user.role === 'admin') {
      setAdminTab('dashboard');
      sessionStorage.setItem('ins_app_admin_tab', 'dashboard');
    } else {
      try {
        const eligData = await eligibilityApi.getMyAssessment();
        if (eligData && eligData.has_assessment && eligData.assessment) {
          setUserAssessment(eligData.assessment);
          const isEligible = eligData.assessment.outcome === 'ELIGIBLE';
          if (isEligible) {
            const activeSel = eligData.active_plan_selection;
            const isConfirmed = Boolean(
              user.is_confirmed ||
              user.confirmation_status === 'CONFIRMED' ||
              activeSel?.status === 'CONFIRMED' ||
              activeSel?.confirmed_at
            );

            if (activeSel) {
              const pId = activeSel.selected_plan_id;
              const restoredPlan = {
                plan_id: pId,
                plan_name: pId.includes('GOLD')
                  ? 'Health Shield — Gold'
                  : pId.includes('PREM')
                  ? 'Health Shield — Premium'
                  : pId.includes('EMP')
                  ? 'Executive Employee Insurance Plan'
                  : 'Health Shield — Basic',
                plan_category: pId.includes('GOLD')
                  ? 'Gold'
                  : pId.includes('PREM')
                  ? 'Premium'
                  : pId.includes('EMP')
                  ? 'Employee Exclusive'
                  : 'Basic',
                display_title: pId.includes('GOLD')
                  ? 'Gold Plan'
                  : pId.includes('PREM')
                  ? 'Premium Plan'
                  : pId.includes('EMP')
                  ? 'Employee Plan'
                  : 'Basic Plan',
                status: isConfirmed ? 'CONFIRMED' : (activeSel.status || 'ACTIVE'),
                is_confirmed: isConfirmed,
                confirmed_at: activeSel.confirmed_at || user.confirmed_at || null
              };
              setSelectedPlan(restoredPlan);
              sessionStorage.setItem('ins_app_selected_plan', JSON.stringify(restoredPlan));

              if (isConfirmed && user.role !== 'admin') {
                setActiveTab('confirm');
                sessionStorage.setItem('ins_app_active_tab', 'confirm');
              } else {
                setActiveTab('chat');
                sessionStorage.setItem('ins_app_active_tab', 'chat');
              }
            } else {
              setSelectedPlan(null);
              sessionStorage.removeItem('ins_app_selected_plan');
              setActiveTab('plans');
              sessionStorage.setItem('ins_app_active_tab', 'plans');
            }
          } else {
            setSelectedPlan(null);
            sessionStorage.removeItem('ins_app_selected_plan');
            setActiveTab('eligibility');
            sessionStorage.setItem('ins_app_active_tab', 'eligibility');
          }
        } else {
          setUserAssessment(null);
          setSelectedPlan(null);
          sessionStorage.removeItem('ins_app_selected_plan');
          setActiveTab('eligibility');
          sessionStorage.setItem('ins_app_active_tab', 'eligibility');
        }
      } catch {
        setActiveTab('eligibility');
      }
    }
  };

  const handleAssessmentComplete = (result) => {
    setUserAssessment(result);
    if (result && result.outcome === 'ELIGIBLE') {
      setActiveTab('plans');
      sessionStorage.setItem('ins_app_active_tab', 'plans');
    }
  };

  const handleLogout = async () => {
    await authApi.logout();
    setCurrentUser(null);
    setAuthToken(null);
    setSelectedPlan(null);
    setUserAssessment(null);
    setActiveTab('eligibility');
    setAdminTab('dashboard');
    setAuthScreen('login');
    setIsProfileOpen(false);
    setIsClaimPredictorOpen(false);
    sessionStorage.removeItem('ins_app_selected_plan');
    sessionStorage.removeItem('ins_app_active_tab');
    sessionStorage.removeItem('ins_app_admin_tab');
    Object.keys(sessionStorage).forEach((key) => {
      if (key.startsWith('active_conv_')) {
        sessionStorage.removeItem(key);
      }
    });
  };

  const handleSelectPlan = async (plan) => {
    await eligibilityApi.selectPlan(plan.plan_id);
    setSelectedPlan(plan);
    setActiveTab('chat');
    sessionStorage.setItem('ins_app_selected_plan', JSON.stringify(plan));
    sessionStorage.setItem('ins_app_active_tab', 'chat');
  };

  const handleBackToPlans = () => {
    setActiveTab('plans');
    setIsChatMenuOpen(false);
    sessionStorage.setItem('ins_app_active_tab', 'plans');
  };

  // If restoring session, show clean loading state
  if (authLoading) {
    return (
      <div className="auth-loading-screen">
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
      <div className="auth-page-container">
        <header className="auth-page-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 className="brand-title">AI Insurance Assistant</h1>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="auth-brand-badge" style={{ margin: 0 }}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
              <span>Encrypted Session</span>
            </span>
          </div>
        </header>

        <main className="auth-page-main">
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

  // Authenticated State: Full Protected Application Access (100vh Edge-to-Edge)
  const userRole = currentUser.role || 'customer';
  const isAdmin = userRole === 'admin';

  return (
    <div className="app-workspace-root">
      {/* Left Column: Persistent Sidebar extending full height (100vh) overlapping top bar */}
      <aside className="workspace-col-left">
        {isAdmin ? (
          <AdminSidebar
            activeTab={adminTab}
            onNavigate={(tab) => {
              setAdminTab(tab);
              sessionStorage.setItem('ins_app_admin_tab', tab);
            }}
          />
        ) : (
          <ProcessSidebar
            activeStage={activeTab}
            selectedPlan={selectedPlan}
            assessment={userAssessment}
            onNavigate={(stage) => {
              if (stage === 'eligibility') {
                setActiveTab('eligibility');
                sessionStorage.setItem('ins_app_active_tab', 'eligibility');
              } else if (stage === 'plans') {
                handleBackToPlans();
              } else if (stage === 'chat' && selectedPlan) {
                setActiveTab('chat');
                sessionStorage.setItem('ins_app_active_tab', 'chat');
              } else if (stage === 'confirm' && selectedPlan && userRole !== 'admin') {
                setActiveTab('confirm');
                sessionStorage.setItem('ins_app_active_tab', 'confirm');
              }
            }}
            onBack={handleBackToPlans}
            userRole={userRole}
            currentUser={currentUser}
          />
        )}
      </aside>

      {/* Right Column: Top Application Header + Main Content */}
      <div className="workspace-main-area">
        {/* Top Application Header (Fixed 52px height) */}
        <header className="app-header">
          <div className="app-header-left">
            {!isAdmin && (
              <h1 className="brand-title">AI Insurance Assistant</h1>
            )}
          </div>

          {/* Top Right Actions: New Chat & Menu (when in chat) + User Profile Button */}
          <div className="header-right-actions">
            {!isAdmin && activeTab === 'chat' && (
              <>
                {userRole === 'employee' && (
                  <button
                    type="button"
                    className={`chat-hdr-btn claim-predictor-btn ${isClaimPredictorOpen ? 'active' : ''}`}
                    onClick={() => {
                      setIsClaimPredictorOpen((prev) => {
                        const next = !prev;
                        if (next) setIsChatMenuOpen(false);
                        return next;
                      });
                    }}
                    title={isClaimPredictorOpen ? "Close Claim Predictor sidebar" : "Open Insurance Claim Predictor"}
                    aria-label="Claim Predictor"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
                    </svg>
                    <span>Claim Predictor</span>
                  </button>
                )}

                <button
                  type="button"
                  className="chat-hdr-btn chat-new-chat-btn"
                  onClick={() => setNewChatTrigger((prev) => prev + 1)}
                  title="Start a fresh conversation session"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="12" y1="5" x2="12" y2="19"></line>
                    <line x1="5" y1="12" x2="19" y2="12"></line>
                  </svg>
                  <span>New Chat</span>
                </button>

                <button
                  type="button"
                  className={`chat-hdr-btn chat-menu-toggle-btn ${isChatMenuOpen ? 'active' : ''}`}
                  onClick={() => {
                    setIsChatMenuOpen((prev) => {
                      const next = !prev;
                      if (next) setIsClaimPredictorOpen(false);
                      return next;
                    });
                  }}
                  title={isChatMenuOpen ? "Close side menu" : "Open side menu (History & Quick Actions)"}
                  aria-label="Toggle chat side menu"
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="3" y1="12" x2="21" y2="12"></line>
                    <line x1="3" y1="6" x2="21" y2="6"></line>
                    <line x1="3" y1="18" x2="21" y2="18"></line>
                  </svg>
                  <span>Menu</span>
                </button>
              </>
            )}

            <button
              type="button"
              className={`user-profile-icon-btn ${isProfileOpen ? 'active' : ''}`}
              onClick={() => setIsProfileOpen(!isProfileOpen)}
              title="User Profile & Settings"
              aria-label="User Profile"
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="user-icon-svg"
              >
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
              </svg>
              <span className="mini-user-avatar-dot">
                {(currentUser.full_name || currentUser.email || 'U')[0].toUpperCase()}
              </span>
            </button>
          </div>
        </header>

        {/* Main Workspace Frame */}
        <div className="workspace-layout">
          <main className="workspace-col-center">
            {isAdmin ? (
              <>
                {adminTab === 'dashboard' && (
                  <div className="scrollable-page-container" style={{ padding: '8px 16px 24px 16px' }}>
                    <AdminDashboardPage />
                  </div>
                )}

                {adminTab === 'ingestion' && (
                  <div className="scrollable-page-container" style={{ padding: '8px 16px 24px 16px' }}>
                    <IngestionPage />
                  </div>
                )}
              </>
            ) : (
              <>
                {activeTab === 'eligibility' && (
                  <div
                    className="scrollable-page-container"
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      minHeight: 'calc(100vh - 52px)',
                      padding: '24px 16px'
                    }}
                  >
                    <EligibilityScreen
                      user={currentUser}
                      onAssessmentComplete={handleAssessmentComplete}
                    />
                  </div>
                )}

                {activeTab === 'plans' && (
                  <div className="scrollable-page-container">
                    <PlanSelectionScreen
                      userRole={userRole}
                      authToken={authToken}
                      onSelectPlan={handleSelectPlan}
                      onUnauthorized={handleLogout}
                    />
                  </div>
                )}

                {activeTab === 'chat' && selectedPlan && (
                  <PlanChatScreen
                    selectedPlan={selectedPlan}
                    userRole={userRole}
                    authToken={authToken}
                    onBackToPlans={handleBackToPlans}
                    onSwitchPlan={(planOrId) => {
                      if (typeof planOrId === 'string') {
                        const idUpper = planOrId.toUpperCase();
                        const updatedPlan = {
                          plan_id: planOrId,
                          plan_name: idUpper.includes('GOLD')
                            ? 'Health Shield — Gold'
                            : idUpper.includes('PREM')
                            ? 'Comprehensive Health Shield — Platinum'
                            : idUpper.includes('EMP')
                            ? 'Corporate Employee Group Insurance'
                            : 'Health Shield — Basic',
                          plan_category: idUpper.includes('GOLD')
                            ? 'Gold'
                            : idUpper.includes('PREM')
                            ? 'Platinum'
                            : idUpper.includes('EMP')
                            ? 'Staff'
                            : 'Basic',
                          display_title: idUpper.includes('GOLD')
                            ? 'Gold Plan'
                            : idUpper.includes('PREM')
                            ? 'Platinum Plan'
                            : idUpper.includes('EMP')
                            ? 'Employee Staff Plan'
                            : 'Basic Plan'
                        };
                        setSelectedPlan(updatedPlan);
                        sessionStorage.setItem('ins_app_selected_plan', JSON.stringify(updatedPlan));
                      } else {
                        handleSelectPlan(planOrId);
                      }
                    }}
                    onUnauthorized={handleLogout}
                    isActionsSidebarOpen={isChatMenuOpen}
                    onCloseActionsSidebar={() => setIsChatMenuOpen(false)}
                    isClaimPredictorOpen={isClaimPredictorOpen}
                    onCloseClaimPredictor={() => setIsClaimPredictorOpen(false)}
                    newChatTrigger={newChatTrigger}
                    onMessageCountChange={setUserMessageCount}
                  />
                )}

                {activeTab === 'confirm' && selectedPlan && userRole !== 'admin' && (
                  <div className="scrollable-page-container">
                    <ConfirmReviewScreen
                      currentUser={currentUser}
                      selectedPlan={selectedPlan}
                      assessment={userAssessment}
                      onConfirmationSuccess={(confData, proceedToChat = false) => {
                        const confDate = confData.confirmedAt || new Date().toISOString();
                        setCurrentUser((prev) => ({
                          ...prev,
                          is_confirmed: true,
                          confirmed_at: confDate,
                          confirmation_status: 'CONFIRMED'
                        }));
                        setSelectedPlan((prev) => {
                          const updated = {
                            ...(prev || {}),
                            is_confirmed: true,
                            status: 'CONFIRMED',
                            confirmed_at: confDate
                          };
                          sessionStorage.setItem('ins_app_selected_plan', JSON.stringify(updated));
                          return updated;
                        });
                        if (proceedToChat) {
                          setActiveTab('chat');
                          sessionStorage.setItem('ins_app_active_tab', 'chat');
                        } else {
                          setActiveTab('confirm');
                          sessionStorage.setItem('ins_app_active_tab', 'confirm');
                        }
                      }}
                      onBackToPlans={handleBackToPlans}
                    />
                  </div>
                )}
              </>
            )}
          </main>
        </div>
      </div>

      {/* On-Click Right Sidebar: Profile Section & Logout */}
      <ProfileDrawer
        isOpen={isProfileOpen}
        onClose={() => setIsProfileOpen(false)}
        currentUser={currentUser}
        selectedPlan={selectedPlan}
        assessment={userAssessment}
        onLogout={handleLogout}
      />
    </div>
  );
}

export default App;

