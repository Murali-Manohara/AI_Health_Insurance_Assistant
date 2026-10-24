import React, { useState, useEffect, useMemo } from 'react';

function formatHistoryTime(isoString) {
  if (!isoString) return 'Just now';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    const now = new Date();
    const isToday = d.toDateString() === now.toDateString();
    const timeStr = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    if (isToday) {
      return `Today, ${timeStr}`;
    }
    const month = d.toLocaleDateString([], { month: 'short', day: 'numeric' });
    return `${month}, ${timeStr}`;
  } catch {
    return isoString;
  }
}

function getPlanBadgeClass(planId = '') {
  const p = planId.toLowerCase();
  if (p.includes('gold')) return 'gold';
  if (p.includes('basic')) return 'basic';
  if (p.includes('prem')) return 'premium';
  if (p.includes('emp')) return 'employee';
  return 'default';
}

function formatPlanLabel(planId = '') {
  const p = planId.toUpperCase();
  if (p.includes('BASIC')) return 'Basic';
  if (p.includes('GOLD')) return 'Gold';
  if (p.includes('PREMIUM')) return 'Premium';
  if (p.includes('EMP')) return 'Staff';
  return planId;
}

/**
 * ChatActionsSidebar — Right Sidebar dedicated to Quick Actions and ChatGPT-style Conversation History.
 * Saves and lists user conversations with a structured history table, filterable by plan and search query.
 */
export function ChatActionsSidebar({
  isOpen,
  activeTab = 'history', // 'quick_actions' | 'history'
  onSelectTab,
  onClose,
  messages = [],
  quickActions = [],
  currentConversationId = null,
  selectedPlan = null,
  authToken = null,
  userRole = 'customer',
  historyRefreshTrigger = 0,
  onTriggerAction,
  onLoadConversation,
  onStartNewChat,
  onSelectHistory
}) {
  const [conversations, setConversations] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [historyError, setHistoryError] = useState(null);
  const [planFilter, setPlanFilter] = useState('all'); // 'all' | 'current'
  const [searchQuery, setSearchQuery] = useState('');

  // Fetch saved conversations from backend whenever panel opens or refresh is triggered
  useEffect(() => {
    if (!isOpen || activeTab !== 'history') return;

    let isMounted = true;
    const fetchHistory = async () => {
      setLoadingHistory(true);
      setHistoryError(null);
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
          res = await fetch('/api/conversations', { headers });
        } catch {
          res = await fetch('http://127.0.0.1:8000/api/conversations', { headers });
        }

        if (!res.ok) {
          throw new Error(`Failed to load history (${res.status})`);
        }

        const data = await res.json();
        if (isMounted) {
          setConversations(Array.isArray(data) ? data : []);
        }
      } catch (err) {
        if (isMounted) {
          setHistoryError(err.message);
        }
      } finally {
        if (isMounted) {
          setLoadingHistory(false);
        }
      }
    };

    fetchHistory();

    return () => {
      isMounted = false;
    };
  }, [isOpen, activeTab, historyRefreshTrigger, authToken, userRole]);

  // Filter conversations based on plan scope and search query
  const filteredConversations = useMemo(() => {
    let list = conversations;

    if (planFilter === 'current' && selectedPlan?.plan_id) {
      list = list.filter((c) => c.selected_plan_id === selectedPlan.plan_id);
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter((c) =>
        (c.preview_title && c.preview_title.toLowerCase().includes(q)) ||
        (c.selected_plan_id && c.selected_plan_id.toLowerCase().includes(q))
      );
    }

    return list;
  }, [conversations, planFilter, selectedPlan, searchQuery]);

  if (!isOpen) return null;

  const currentPlanId = selectedPlan?.plan_id || '';
  const currentPlanCount = conversations.filter((c) => c.selected_plan_id === currentPlanId).length;

  return (
    <aside className="chat-actions-sidebar" aria-label="Quick Actions and History">
      {/* Top Header with Tab Switcher & Close Button */}
      <div className="actions-sidebar-header">
        <div className="actions-tab-switcher">
          <button
            type="button"
            className={`actions-tab-btn ${activeTab === 'history' ? 'active' : ''}`}
            onClick={() => onSelectTab('history')}
            title="View saved conversation history table"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <polyline points="12 6 12 12 16 14"></polyline>
            </svg>
            <span>History</span>
            {conversations.length > 0 && (
              <span className="actions-count-pill">{conversations.length}</span>
            )}
          </button>

          <button
            type="button"
            className={`actions-tab-btn ${activeTab === 'quick_actions' ? 'active' : ''}`}
            onClick={() => onSelectTab('quick_actions')}
            title="View suggested policy quick actions"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
            </svg>
            <span>Quick Actions</span>
          </button>
        </div>

        <button
          type="button"
          className="actions-close-btn"
          onClick={onClose}
          aria-label="Close sidebar"
          title="Close panel"
        >
          ✕
        </button>
      </div>

      {/* Sidebar Content Area */}
      <div className="actions-sidebar-body">
        {/* TAB 1: CONVERSATION HISTORY TABLE (ChatGPT Style) */}
        {activeTab === 'history' && (
          <div className="actions-panel-content">
            <div className="history-panel-topbar">
              <div className="history-panel-headline">
                <div>
                  <span className="actions-panel-eyebrow">PERSISTENT MEMORY</span>
                  <h4 className="actions-panel-title">Conversation History</h4>
                </div>
                {onStartNewChat && (
                  <button
                    type="button"
                    className="btn btn-primary history-new-btn"
                    onClick={onStartNewChat}
                    title="Start fresh conversation"
                  >
                    + New Chat
                  </button>
                )}
              </div>

              {/* Filter Pills & Search Input */}
              <div className="history-filter-bar">
                <div className="history-scope-pills">
                  <button
                    type="button"
                    className={`history-pill-btn ${planFilter === 'all' ? 'active' : ''}`}
                    onClick={() => setPlanFilter('all')}
                  >
                    All Plans ({conversations.length})
                  </button>
                  <button
                    type="button"
                    className={`history-pill-btn ${planFilter === 'current' ? 'active' : ''}`}
                    onClick={() => setPlanFilter('current')}
                    title={`Only show chats for ${selectedPlan?.display_title || 'current plan'}`}
                  >
                    Current Plan ({currentPlanCount})
                  </button>
                </div>

                <div className="history-search-box">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="11" cy="11" r="8"></circle>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                  </svg>
                  <input
                    type="text"
                    className="history-search-input"
                    placeholder="Search past conversations..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                  {searchQuery && (
                    <button
                      type="button"
                      className="history-search-clear"
                      onClick={() => setSearchQuery('')}
                      title="Clear search"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                      </svg>
                    </button>
                  )}
                </div>
              </div>
            </div>

            {loadingHistory && conversations.length === 0 ? (
              <div className="actions-empty-state">
                <div className="auth-spinner" style={{ width: '22px', height: '22px', margin: '0 auto 10px auto' }}></div>
                <div className="actions-empty-text">Loading saved conversations...</div>
              </div>
            ) : historyError ? (
              <div className="chat-error-banner" style={{ margin: '8px 0' }}>
                <span>{historyError}</span>
              </div>
            ) : filteredConversations.length === 0 ? (
              <div className="actions-empty-state">
                <div className="actions-empty-icon">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--text-light)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                  </svg>
                </div>
                <div className="actions-empty-title">
                  {searchQuery ? 'No matching conversations' : 'No conversation history'}
                </div>
                <div className="actions-empty-text">
                  {searchQuery
                    ? 'Try searching with different keywords or switch to All Plans.'
                    : 'Any question you ask is automatically saved. Start a chat to begin building your policy history!'}
                </div>
                {onStartNewChat && (
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ marginTop: '12px', fontSize: '12px' }}
                    onClick={onStartNewChat}
                  >
                    Start a New Chat
                  </button>
                )}
              </div>
            ) : (
              /* Proper Conversation History Table */
              <div className="history-table-wrapper">
                <table className="conversation-history-table">
                  <thead>
                    <tr>
                      <th className="th-topic">Conversation Topic</th>
                      <th className="th-plan">Plan</th>
                      <th className="th-action">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredConversations.map((conv) => {
                      const isActive = conv.conversation_id === currentConversationId;
                      const badgeClass = getPlanBadgeClass(conv.selected_plan_id);

                      return (
                        <tr
                          key={conv.conversation_id}
                          className={`history-row ${isActive ? 'active-row' : ''}`}
                          onClick={() => onLoadConversation && onLoadConversation(conv.conversation_id, conv.selected_plan_id)}
                          title="Click to resume this conversation"
                        >
                          <td className="td-topic">
                            <div className="history-topic-main">
                              <span className="history-row-icon">
                                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                                </svg>
                              </span>
                              <div className="history-topic-text-group">
                                <span className="history-row-title">{conv.preview_title}</span>

                                <div className="history-row-meta">
                                  {isActive ? (
                                    <span className="history-active-tag">● Active Session</span>
                                  ) : (
                                    <span className="history-time-tag">
                                      {formatHistoryTime(conv.updated_at || conv.created_at)}
                                    </span>
                                  )}
                                  <span className="history-msg-tag">
                                    {conv.message_count} {conv.message_count === 1 ? 'turn' : 'turns'}
                                  </span>
                                </div>
                              </div>
                            </div>
                          </td>

                          <td className="td-plan">
                            <span className={`plan-badge-pill ${badgeClass}`} title={conv.selected_plan_id}>
                              {formatPlanLabel(conv.selected_plan_id)}
                            </span>
                          </td>

                          <td className="td-action">
                            {isActive ? (
                              <span className="history-current-indicator">Open</span>
                            ) : (
                              <button
                                type="button"
                                className="history-open-btn"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  if (onLoadConversation) {
                                    onLoadConversation(conv.conversation_id, conv.selected_plan_id);
                                  }
                                }}
                                title="Open past chat"
                              >
                                Resume →
                              </button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: QUICK ACTIONS */}
        {activeTab === 'quick_actions' && (
          <div className="actions-panel-content">
            <div className="actions-panel-intro">
              <span className="actions-panel-eyebrow">GROUNDED INTELLIGENCE</span>
              <h4 className="actions-panel-title">Policy Quick Actions</h4>
              <p className="actions-panel-desc">
                Select an action to instantly retrieve verified terms, payout limits, or clause breakdowns.
              </p>
            </div>

            <div className="actions-cards-stack">
              {quickActions.map((action) => (
                <button
                  key={action.id}
                  type="button"
                  className="action-card-item"
                  onClick={() => onTriggerAction(action.prompt)}
                  title={`Run: "${action.prompt}"`}
                >
                  <div className="action-card-icon-box">{action.icon}</div>
                  <div className="action-card-info">
                    <div className="action-card-title">{action.title}</div>
                    <div className="action-card-desc">{action.desc}</div>
                  </div>
                  <svg
                    className="action-card-arrow"
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <line x1="5" y1="12" x2="19" y2="12"></line>
                    <polyline points="12 5 19 12 12 19"></polyline>
                  </svg>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}

export default ChatActionsSidebar;
