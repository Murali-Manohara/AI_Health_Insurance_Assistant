import React, { useState, useEffect, useRef } from 'react';
import MarkdownContent from './MarkdownContent';

export function PlanChatScreen({ selectedPlan, userRole, authToken, onBackToPlans, onUnauthorized }) {
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expandedSources, setExpandedSources] = useState({});
  const messagesEndRef = useRef(null);

  useEffect(() => {
    startNewConversation();
  }, [selectedPlan, userRole, authToken]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const startNewConversation = async () => {
    if (!selectedPlan) return;
    setLoading(true);
    setError(null);
    setMessages([]);
    setExpandedSources({});

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
        res = await fetch('/api/conversations', {
          method: 'POST',
          headers,
          body: JSON.stringify({ selected_plan_id: selectedPlan.plan_id })
        });
      } catch {
        res = await fetch('http://127.0.0.1:8000/api/conversations', {
          method: 'POST',
          headers,
          body: JSON.stringify({ selected_plan_id: selectedPlan.plan_id })
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
        throw new Error(data.detail || `HTTP ${res.status}: Failed to start conversation`);
      }

      setConversationId(data.conversation_id);

      // Initial welcome message
      const isEmployee = selectedPlan.plan_id === 'EMP-INS-001';
      const welcome = {
        message_id: 'welcome_msg',
        role: 'assistant',
        content: `You are consulting **${selectedPlan.plan_name}** (${selectedPlan.plan_id}). Ask questions regarding benefit payouts, waiting periods, ICU limits, surgery categories, or ask to compare with other customer plans.` +
          (isEmployee ? '\n\n*(Note: This employee document contains illustrative reference terms).*' : ''),
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        citations: []
      };
      setMessages([welcome]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = async (textToSend) => {
    const query = textToSend || inputText;
    if (!query.trim() || !conversationId) return;

    const userMessage = {
      message_id: `user_${Date.now()}`,
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

  const quickPrompts = [
    'What is the Daily Hospital Cash benefit?',
    'What are the waiting periods for pre-existing conditions?',
    'What is the ICU limit per day and per year?',
    selectedPlan.plan_id === 'HS-BASIC-001' ? 'Compare with Gold' : 'Compare with Basic'
  ];

  return (
    <div className="card">
      {/* Top Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', paddingBottom: '12px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button className="btn btn-secondary" onClick={onBackToPlans} style={{ fontSize: '12px', padding: '6px 12px' }}>
            ← Back to Plans
          </button>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className={`plan-badge ${selectedPlan.plan_category.toLowerCase()}`}>
                {selectedPlan.display_title || selectedPlan.plan_category}
              </span>
              <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-main)' }}>
                {selectedPlan.plan_name}
              </h3>
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Active Policy: <code>{selectedPlan.plan_id}</code> • Scope: Plan-Scoped
            </div>
          </div>
        </div>

        <button className="btn btn-secondary" onClick={startNewConversation} style={{ fontSize: '12px', padding: '6px 12px' }}>
          ↺ New Conversation
        </button>
      </div>

      {error && (
        <div className="alert alert-error" style={{ marginBottom: '16px' }}>
          <strong>Error:</strong> {error}
          <button className="btn btn-secondary" style={{ marginLeft: '12px', padding: '4px 8px', fontSize: '11px' }} onClick={() => handleSendMessage(inputText)}>
            Retry
          </button>
        </div>
      )}

      {/* Chat Messages */}
      <div className="chat-window" style={{ height: '520px' }}>
        <div className="chat-history">
          {messages.map((m) => {
            const hasCitations = m.citations && m.citations.length > 0;
            const isSourcesOpen = !!expandedSources[m.message_id];

            return (
              <div key={m.message_id} className={`chat-bubble ${m.role}`}>
                <div style={{ fontSize: '11px', color: m.role === 'user' ? '#e0f2fe' : 'var(--text-muted)', marginBottom: '4px', display: 'flex', justifyContent: 'space-between' }}>
                  <span>{m.role === 'user' ? 'You' : 'AI Insurance Assistant'}</span>
                  <span>{m.timestamp}</span>
                </div>

                {m.role === 'assistant' ? (
                  <MarkdownContent content={m.content} />
                ) : (
                  <div style={{ whiteSpace: 'pre-wrap' }}>{m.content}</div>
                )}

                {/* Unverified employee disclaimer banner if applicable */}
                {m.contains_unverified_notice && (
                  <div className="unverified-banner">
                    <span>⚠️</span>
                    <span>Contains illustrative demonstration data.</span>
                  </div>
                )}

                {/* Expandable Citations Drawer */}
                {hasCitations && (
                  <div className="citation-box">
                    <div className="citation-header" onClick={() => toggleSources(m.message_id)}>
                      <span>Verified Policy Sources ({m.citations.length})</span>
                      <span>{isSourcesOpen ? '▲ Hide' : '▼ View Evidence'}</span>
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
            );
          })}

          {loading && (
            <div className="chat-bubble assistant" style={{ fontStyle: 'italic', color: 'var(--text-muted)' }}>
              Retrieving authorized policy evidence & generating grounded answer...
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Quick Suggestion Chips */}
        <div className="prompt-chips">
          {quickPrompts.map((q, idx) => (
            <button key={idx} className="prompt-chip" onClick={() => handleSendMessage(q)} disabled={loading}>
              {q}
            </button>
          ))}
        </div>

        {/* Input Bar */}
        <div className="chat-input-row">
          <input
            type="text"
            className="chat-input"
            placeholder={`Ask about ${selectedPlan.display_title || 'policy'} terms, waiting periods, or limits...`}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !loading && handleSendMessage()}
            disabled={loading}
          />
          <button
            className="btn btn-primary"
            onClick={() => handleSendMessage()}
            disabled={loading || !inputText.trim()}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
