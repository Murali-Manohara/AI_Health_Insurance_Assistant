import React, { useState } from 'react';

export function ChatInterface() {
  const [messages, setMessages] = useState([
    {
      id: 1,
      sender: 'assistant',
      text: 'Ask questions about uploaded insurance policy terms, waiting periods, or benefits.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      sources: []
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  const handleSend = (textToSend) => {
    const query = textToSend || inputText;
    if (!query.trim()) return;

    const userMsg = {
      id: Date.now(),
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText('');
    setIsTyping(true);

    setTimeout(() => {
      const assistantMsg = {
        id: Date.now() + 1,
        sender: 'assistant',
        text: `Retrieval match for "${query}": Policy documents ingested into ChromaDB are indexed with section hierarchies and embeddings. In Phase 2, this interface connects directly to the query retrieval pipeline.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        sources: ['Section 11: Waiting Periods', 'Section 5: Major Surgery Benefit']
      };
      setMessages((prev) => [...prev, assistantMsg]);
      setIsTyping(false);
    }, 600);
  };

  return (
    <div className="card">
      <div style={{ marginBottom: '16px' }}>
        <h3 className="card-title" style={{ marginBottom: '4px' }}>Policy Query Assistant</h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
          Query terms and conditions across ingested insurance documents.
        </p>
      </div>

      <div className="chat-window">
        <div className="chat-history">
          {messages.map((m) => (
            <div key={m.id} className={`chat-bubble ${m.sender}`}>
              <div style={{ fontSize: '11px', color: m.sender === 'user' ? '#e0f2fe' : 'var(--text-muted)', marginBottom: '4px' }}>
                {m.sender === 'user' ? 'You' : 'Assistant'} • {m.timestamp}
              </div>
              <div>{m.text}</div>
              {m.sources && m.sources.length > 0 && (
                <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid var(--border)', fontSize: '12px' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Sources: </span>
                  {m.sources.join(', ')}
                </div>
              )}
            </div>
          ))}
          {isTyping && (
            <div className="chat-bubble assistant">
              <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>Searching policies...</span>
            </div>
          )}
        </div>

        <div className="chat-input-row">
          <input
            type="text"
            className="chat-input"
            placeholder="Type your question regarding policy terms..."
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          />
          <button
            className="btn btn-primary"
            onClick={() => handleSend()}
            disabled={!inputText.trim()}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
