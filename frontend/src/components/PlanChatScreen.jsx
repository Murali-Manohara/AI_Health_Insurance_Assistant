import React, { useState, useEffect, useRef } from 'react';
import MarkdownContent from './MarkdownContent';
import { ChatActionsSidebar } from './ChatActionsSidebar';

export function PlanChatScreen({
  selectedPlan,
  userRole,
  authToken,
  onBackToPlans,
  onSwitchPlan,
  onUnauthorized
}) {
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedSources, setExpandedSources] = useState({});
  const [isActionsSidebarOpen, setIsActionsSidebarOpen] = useState(false);
  const [actionsSidebarTab, setActionsSidebarTab] = useState('history'); // Default to history tab
  const [historyRefreshTrigger, setHistoryRefreshTrigger] = useState(0);
  const messagesEndRef = useRef(null);


  useEffect(() => {
    // Session preservation across page refresh:
    // Check if an active session was already loaded for this plan and role
    const sessionKey = `active_conv_${userRole}_${selectedPlan?.plan_id}`;
    const savedConvId = sessionStorage.getItem(sessionKey);
    if (savedConvId) {
      handleLoadConversation(savedConvId, selectedPlan?.plan_id, true);
    } else {
      startNewConversation();
    }
  }, [selectedPlan?.plan_id, userRole, authToken]);


  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const startNewConversation = async () => {
    if (!selectedPlan) return;
    setLoading(true);
    setError(null);
    setMessages([]);
    setExpandedSources({});
    setIsActionsSidebarOpen(false);

    try {
      const headers = {
        'Content-Type': 'application/json',
        'X-User-Role': userRole
      };
      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
      }

      const reqPayload = {
        selected_plan_id: selectedPlan.plan_id,
        plan_id: selectedPlan.plan_id
      };

      let res;
      try {
        res = await fetch('/api/conversations', {
          method: 'POST',
          headers,
          body: JSON.stringify(reqPayload)
        });
      } catch {
        res = await fetch('http://127.0.0.1:8000/api/conversations', {
          method: 'POST',
          headers,
          body: JSON.stringify(reqPayload)
        });
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
        let msg = `Server error (HTTP ${res.status})`;
        if (typeof data.detail === 'string') {
          msg = data.detail;
        } else if (Array.isArray(data.detail)) {
          msg = data.detail.map((d) => d.msg || JSON.stringify(d)).join(', ');
        } else if (data.detail && typeof data.detail === 'object') {
          msg = JSON.stringify(data.detail);
        }
        throw new Error(msg);
      }

      setConversationId(data.conversation_id);
      const sessionKey = `active_conv_${userRole}_${selectedPlan.plan_id}`;
      sessionStorage.setItem(sessionKey, data.conversation_id);
      setHistoryRefreshTrigger((prev) => prev + 1);


      const welcomeMessage = {
        message_id: 'welcome-' + Date.now(),
        role: 'assistant',
        content: `You are consulting **${selectedPlan.plan_name}** (\`${selectedPlan.plan_id}\`). Ask questions regarding benefit payouts, waiting periods, ICU limits, surgery categories, or ask to compare with other customer plans.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        citations: []
      };
      setMessages([welcomeMessage]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleLoadConversation = async (targetConvId, targetPlanId, isAutoResume = false) => {
    if (!targetConvId) return;

    setLoading(true);
    setError(null);
    try {
      const headers = {
        'Content-Type': 'application/json',
        'X-User-Role': userRole
      };
      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
      }

      let res;
      try {
        res = await fetch(`/api/conversations/${targetConvId}`, { headers });
      } catch {
        res = await fetch(`http://127.0.0.1:8000/api/conversations/${targetConvId}`, { headers });
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
        // If 404 Not Found or 403 Forbidden, clean up stale sessionStorage
        const targetKey = targetPlanId || selectedPlan?.plan_id;
        const sessionKey = `active_conv_${userRole}_${targetKey}`;
        sessionStorage.removeItem(sessionKey);

        if (isAutoResume || res.status === 404 || res.status === 403) {
          // Seamless auto-fallback to a fresh conversation without blocking error
          await startNewConversation();
          return;
        }

        throw new Error(data.detail || `Server error (HTTP ${res.status})`);
      }

      setConversationId(data.conversation_id);
      const targetKey = targetPlanId || selectedPlan.plan_id;
      const sessionKey = `active_conv_${userRole}_${targetKey}`;
      sessionStorage.setItem(sessionKey, data.conversation_id);

      if (data.messages && data.messages.length > 0) {
        setMessages(data.messages);
      } else {
        const welcomeMessage = {
          message_id: 'welcome-' + Date.now(),
          role: 'assistant',
          content: `You are consulting **${selectedPlan.plan_name}** (\`${selectedPlan.plan_id}\`). This chat session has been resumed.`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          citations: []
        };
        setMessages([welcomeMessage]);
      }

      if (targetPlanId && targetPlanId !== selectedPlan.plan_id && onSwitchPlan) {
        onSwitchPlan(targetPlanId);
      }
      setHistoryRefreshTrigger((prev) => prev + 1);

    } catch (err) {
      if (isAutoResume) {
        const targetKey = targetPlanId || selectedPlan?.plan_id;
        const sessionKey = `active_conv_${userRole}_${targetKey}`;
        sessionStorage.removeItem(sessionKey);
        await startNewConversation();
      } else {
        setError(`Failed to resume conversation: ${err.message}`);
      }
    } finally {
      setLoading(false);
    }
  };


  const handleSendMessage = async (textToSend) => {
    const query = textToSend || inputText;
    if (!query || !query.trim() || !conversationId) return;

    const userMessage = {
      message_id: 'user-' + Date.now(),
      role: 'user',
      content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      citations: []
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputText('');
    setLoading(true);
    setError(null);

    try {
      const headers = {
        'Content-Type': 'application/json',
        'X-User-Role': userRole
      };
      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
      }

      let res;
      try {
        res = await fetch(`/api/conversations/${conversationId}/messages`, {
          method: 'POST',
          headers,
          body: JSON.stringify({ query })
        });
      } catch {
        res = await fetch(`http://127.0.0.1:8000/api/conversations/${conversationId}/messages`, {
          method: 'POST',
          headers,
          body: JSON.stringify({ query })
        });
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
        throw new Error(data.detail || `Server error (HTTP ${res.status})`);
      }

      setMessages((prev) => [...prev, data.message]);
      setHistoryRefreshTrigger((prev) => prev + 1);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }

  };

  const toggleSources = (msgId) => {
    setExpandedSources((prev) => ({
      ...prev,
      [msgId]: !prev[msgId]
    }));
  };


  // Exactly six RAG-grounded actions tailored to the active policy with professional vector icons
  const quickActionsList = [
    {
      id: 'summary',
      icon: (
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
          <line x1="16" y1="13" x2="8" y2="13"></line>
          <line x1="16" y1="17" x2="8" y2="17"></line>
        </svg>
      ),
      title: 'Executive Summary',
      prompt: 'Provide an executive summary of key benefits, hospital cash, and limits under this policy.',
      desc: 'Overview of core coverage terms & daily allowances.'
    },
    {
      id: 'surgery',
      icon: (
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
        </svg>
      ),
      title: 'Surgical Benefits & Tiers',
      prompt: 'Explain surgical insurance benefits, categories, and payable percentages.',
      desc: 'Breakdown of Major Surgery tiers & Other Surgery daily benefits.'
    },
    {
      id: 'comparison',
      icon: (
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="18" cy="18" r="3"></circle>
          <circle cx="6" cy="6" r="3"></circle>
          <path d="M13 6h3a2 2 0 0 1 2 2v7"></path>
          <line x1="6" y1="9" x2="6" y2="21"></line>
        </svg>
      ),
      title: selectedPlan.plan_id === 'HS-BASIC-001' ? 'Compare Basic with Gold' : 'Compare with Basic Plan',
      prompt: selectedPlan.plan_id === 'HS-BASIC-001' ? 'Compare Health Shield Basic and Health Shield Gold' : 'Compare this plan with Health Shield Basic',
      desc: 'Side-by-side comparative table of benefits & limits.'
    },
    {
      id: 'waiting',
      icon: (
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <polyline points="12 6 12 12 16 14"></polyline>
        </svg>
      ),
      title: 'Waiting Periods',
      prompt: 'What are the waiting periods for pre-existing diseases and specific conditions?',
      desc: 'Details on 30-day initial, 2-year specific, and pre-existing exclusion rules.'
    },
    {
      id: 'icu',
      icon: (
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 21h18"></path>
          <path d="M5 21V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16"></path>
          <line x1="9" y1="10" x2="15" y2="10"></line>
          <line x1="12" y1="7" x2="12" y2="13"></line>
        </svg>
      ),
      title: 'ICU & Room Rent Limits',
      prompt: 'What are the ICU daily limits, maximum days, and hospital stay criteria?',
      desc: '24-hour hospitalization rules and ICU allowances.'
    },
    {
      id: 'claims',
      icon: (
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
          <polyline points="9 12 11 14 15 10"></polyline>
        </svg>
      ),
      title: 'Claim Filing Process',
      prompt: 'What is the claim filing procedure and documentation requirement?',
      desc: 'Recommended step-by-step submission guidelines.'
    }
  ];


  const userMessages = messages.filter((m) => m.role === 'user');

  const handleToggleMenu = () => {
    setIsActionsSidebarOpen((prev) => !prev);
  };

  return (
    <div className={`chat-workspace-shell ${isActionsSidebarOpen ? 'actions-open' : ''}`}>
      {/* Primary Chat Column */}
      <div className="chat-main-column">
        {/* Top Header / Action Bar */}
        <div className="chat-workspace-header">
          <div className="chat-header-left">
            <div className="chat-header-info">
              <div className="chat-header-title-row" style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                <h3 className="chat-header-title" style={{ fontSize: '15px', fontWeight: 700, margin: 0 }}>
                  {selectedPlan.plan_name}
                </h3>
                <span
                  className="plan-code-badge"
                  style={{
                    background: '#f1f5f9',
                    color: '#334155',
                    padding: '2px 7px',
                    borderRadius: '4px',
                    fontSize: '11px',
                    fontWeight: 700,
                    fontFamily: 'monospace'
                  }}
                >
                  {selectedPlan.plan_id}
                </span>
                <span className="pipeline-chip" style={{ fontSize: '11px', padding: '2px 8px' }}>
                  <span className="chip-dot emerald"></span> Plan-Scoped Grounding
                </span>
              </div>
            </div>
          </div>

          {/* Header Controls: Styled "New Chat" & adjacent "Menu" button to toggle the right-side chat panel */}
          <div className="chat-header-right">
            <button
              type="button"
              className="chat-hdr-btn chat-new-chat-btn"
              onClick={startNewConversation}
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
              className={`chat-hdr-btn chat-menu-toggle-btn ${isActionsSidebarOpen ? 'active' : ''}`}
              onClick={handleToggleMenu}
              title={isActionsSidebarOpen ? "Close side menu" : "Open side menu (History & Quick Actions)"}
              aria-label="Toggle chat side menu"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="3" y1="12" x2="21" y2="12"></line>
                <line x1="3" y1="6" x2="21" y2="6"></line>
                <line x1="3" y1="18" x2="21" y2="18"></line>
              </svg>
              <span>Menu</span>
              {userMessages.length > 0 && (
                <span className="chat-menu-badge">{userMessages.length}</span>
              )}
            </button>
          </div>
        </div>

        {error && (
          <div className="chat-error-banner" role="alert">
            <span><strong>Error:</strong> {error}</span>
            <button
              className="btn btn-secondary"
              style={{ padding: '3px 8px', fontSize: '11px' }}
              onClick={() => {
                if (inputText.trim() && conversationId) {
                  handleSendMessage(inputText);
                } else {
                  startNewConversation();
                }
              }}
            >
              Retry
            </button>
          </div>
        )}

        {/* Scrollable Messages Container */}
        <div className="chat-messages-scroll-area">
          <div className="chat-messages-container">
            {messages.map((m) => {
              const isUser = m.role === 'user';
              const hasCitations = m.citations && m.citations.length > 0;
              const isSourcesOpen = !!expandedSources[m.message_id];

              return (
                <div key={m.message_id} className={`chat-message-row ${isUser ? 'user' : 'assistant'}`}>
                  {/* AI Avatar Badge on the left for Assistant */}
                  {!isUser && (
                    <div className="chat-avatar-badge assistant" title="AI Insurance Assistant">
                      AI
                    </div>
                  )}

                  {/* Message Bubble Card */}
                  <div className={`chat-message-bubble ${isUser ? 'user' : 'assistant'}`}>
                    {isUser ? (
                      <div className="chat-user-text">{m.content}</div>
                    ) : (
                      <div className="chat-assistant-body">
                        <MarkdownContent content={m.content} />

                        {/* Unverified employee disclaimer banner if applicable */}
                        {m.contains_unverified_notice && (
                          <div className="unverified-banner">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
                              <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path>
                              <line x1="12" y1="9" x2="12" y2="13"></line>
                              <line x1="12" y1="17" x2="12.01" y2="17"></line>
                            </svg>
                            <span>Contains illustrative demonstration data.</span>
                          </div>
                        )}

                        {/* Expandable Citations Drawer */}
                        {hasCitations && (
                          <div className="citation-box">
                            <div className="citation-header" onClick={() => toggleSources(m.message_id)}>
                              <span>Verified Policy Sources ({m.citations.length})</span>
                              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                                <span>{isSourcesOpen ? 'Hide Evidence' : 'View Evidence'}</span>
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                  {isSourcesOpen ? <polyline points="18 15 12 9 6 15"></polyline> : <polyline points="6 9 12 15 18 9"></polyline>}
                                </svg>
                              </span>
                            </div>


                            {isSourcesOpen && (
                              <div style={{ marginTop: '6px' }}>
                                {m.citations.map((c, idx) => (
                                  <div key={idx} className="citation-item">
                                    <div className="citation-meta">
                                      <span>{c.plan_name} — Section {c.section_number}: {c.section_title}</span>
                                      <span style={{ color: 'var(--text-light)', fontSize: '10px' }}>
                                        Pages {c.source_page_start}-{c.source_page_end}
                                      </span>
                                    </div>
                                    <div className="citation-snippet">{c.snippet}</div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* User Avatar Badge on the right for User Query */}
                  {isUser && (
                    <div className="chat-avatar-badge user" title={userRole === 'employee' ? 'Staff Underwriter' : 'Customer Policyholder'}>
                      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
                        <circle cx="12" cy="7" r="4" />
                      </svg>
                    </div>
                  )}

                </div>
              );
            })}

            {loading && (
              <div className="chat-message-row assistant">
                <div className="chat-avatar-badge assistant" title="AI Insurance Assistant">AI</div>
                <div className="chat-message-bubble assistant loading">
                  <div className="chat-loading-dots">
                    <span></span><span></span><span></span>
                  </div>
                  <span style={{ fontStyle: 'italic', color: 'var(--text-muted)', fontSize: '12.5px' }}>
                    Retrieving authorized policy evidence & generating grounded answer...
                  </span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Elevated Bottom Input Dock */}
        <div className="chat-bottom-dock">
          <div className="chat-input-wrapper">
            <div className="chat-input-field-container">
              <span className="chat-input-prefix-icon" title="Query input">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
              </span>
              <input
                type="text"
                className="chat-input-field"
                placeholder={`Ask about ${selectedPlan.display_title || 'policy'} terms, waiting periods, or limits...`}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !loading && handleSendMessage()}
                disabled={loading}
              />
              <button
                type="button"
                className={`chat-submit-circle-btn ${inputText.trim() ? 'has-content' : ''}`}
                onClick={() => handleSendMessage()}
                disabled={loading || !inputText.trim()}
                title={inputText.trim() ? "Send query" : "Enter a question about this policy"}
              >
                {loading ? (
                  <div className="chat-submit-spinner" />
                ) : (
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="22" y1="2" x2="11" y2="13" />
                    <polygon points="22 2 15 22 11 13 2 9 22 2" />
                  </svg>
                )}
              </button>
            </div>
            <div className="chat-input-footer-hint">
              <span className="hint-pill">
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
                Strictly Grounded: <strong>{selectedPlan.plan_id}</strong>
              </span>
              <span className="hint-text">Press <strong>Enter ↵</strong> to send query</span>
            </div>
          </div>
        </div>
      </div>

      {/* Right Sidebar: Dedicated for Quick Actions & History Table */}
      <ChatActionsSidebar
        isOpen={isActionsSidebarOpen}
        activeTab={actionsSidebarTab}
        onSelectTab={(tab) => setActionsSidebarTab(tab)}
        onClose={() => setIsActionsSidebarOpen(false)}
        messages={messages}
        quickActions={quickActionsList}
        currentConversationId={conversationId}
        selectedPlan={selectedPlan}
        authToken={authToken}
        userRole={userRole}
        historyRefreshTrigger={historyRefreshTrigger}
        onTriggerAction={(prompt) => handleSendMessage(prompt)}
        onLoadConversation={handleLoadConversation}
        onStartNewChat={startNewConversation}
        onSelectHistory={(query) => setInputText(query)}
      />

    </div>
  );
}

export default PlanChatScreen;
