import React, { useState, useEffect, useRef } from 'react';
import { Bot, Send, Trash2, Sparkles, MessageSquare, CornerDownLeft } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

export default function AIChatInterface({ user, promptInject }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);

  // Auto-fetch conversation history for user_id on load
  useEffect(() => {
    if (user?.user_id) {
      fetchHistory();
    }
  }, [user]);

  // Handle injected prompt from external components (e.g. Incident detail "Ask AI")
  useEffect(() => {
    if (promptInject) {
      sendMessage(promptInject);
    }
  }, [promptInject]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const fetchHistory = async () => {
    try {
      const res = await fetch(`/api/history/${user.user_id}?limit=50`);
      if (!res.ok) return;
      const data = await res.json();
      if (data.messages && data.messages.length > 0) {
        setMessages(data.messages);
      } else {
        // Default welcome message if history is empty
        setMessages([
          {
            role: 'assistant',
            content: `Hello ${user.user_name || 'Engineer'}! I am your Incident Assistant. Ask me anything about current or past infrastructure incidents, SQL analytics, or failure resolutions.`,
            route: 'GENERAL'
          }
        ]);
      }
    } catch (err) {
      console.error('Error fetching chat history:', err);
    }
  };

  const handleClearHistory = async () => {
    if (!window.confirm('Are you sure you want to clear all conversation history?')) return;
    try {
      const res = await fetch(`/api/history/${user.user_id}`, { method: 'DELETE' });
      if (res.ok) {
        setMessages([
          {
            role: 'assistant',
            content: 'Conversation history has been cleared. How can I help you today?',
            route: 'GENERAL'
          }
        ]);
      }
    } catch (err) {
      console.error('Error clearing history:', err);
    }
  };

  const sendMessage = async (textToSend) => {
    const questionText = textToSend || input.trim();
    if (!questionText || loading) return;

    if (!textToSend) setInput('');

    // Append user message immediately
    const userMsg = { role: 'user', content: questionText };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setError(null);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.user_id,
          question: questionText
        }),
      });

      if (!res.ok) {
        throw new Error('Failed to reach Incident Assistant backend');
      }

      const data = await res.json();

      const aiMsg = {
        role: 'assistant',
        content: data.answer,
        route: data.route
      };

      setMessages((prev) => [...prev, aiMsg]);
    } catch (err) {
      setError(err.message);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `⚠️ Error: ${err.message}. Please verify the backend and Ollama are running.`,
          route: 'INVALID'
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const presetPrompts = [
    'Can you give me the top 5 critical incidents and short description?',
    'Did we see any incident related to EC2 instance failure before?',
    'How many open incidents are there?',
    'Count of incidents assigned to Arjun Menon',
    'Who opened INC20260465 and when was it opened?'
  ];

  return (
    <div className="ai-interface-container">
      <div className="ai-header">
        <div className="ai-header-left">
          <div className="ai-avatar">
            <Bot size={20} />
          </div>
          <div>
            <div className="ai-title">AI Incident Assistant</div>
            <div className="ai-subtitle">Autonomous Intent Router (SQL, Vector & Contextual Reasoning)</div>
          </div>
        </div>

        <div className="ai-actions">
          <button className="btn-clear-chat" onClick={handleClearHistory} title="Clear conversation history from database">
            <Trash2 size={14} />
            <span>Clear History</span>
          </button>
        </div>
      </div>

      <div className="chat-messages">
        {messages.map((msg, index) => (
          <div key={index} className={`message-item ${msg.role}`}>
            <div className="msg-avatar">
              {msg.role === 'user' ? 'U' : <Bot size={18} />}
            </div>
            <div className="msg-bubble">
              {msg.role === 'assistant' && msg.route && (
                <div className={`route-badge ${msg.route}`}>
                  <Sparkles size={10} style={{ marginRight: '4px' }} />
                  {msg.route} ROUTE
                </div>
              )}
              <div style={{ wordBreak: 'break-word' }}>
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              </div>
            </div>
          </div>
        ))}

        {loading && (
          <div className="message-item assistant">
            <div className="msg-avatar">
              <Bot size={18} />
            </div>
            <div className="msg-bubble" style={{ color: '#9ca3af', fontStyle: 'italic' }}>
              Thinking & querying database...
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Preset Suggestion Chips */}
      <div className="suggestions-bar">
        {presetPrompts.map((prompt, i) => (
          <button key={i} className="suggestion-chip" onClick={() => sendMessage(prompt)}>
            <MessageSquare size={12} style={{ display: 'inline', marginRight: '6px' }} />
            {prompt}
          </button>
        ))}
      </div>

      {/* Chat Input Bar */}
      <form
        className="chat-input-area"
        onSubmit={(e) => {
          e.preventDefault();
          sendMessage();
        }}
      >
        <input
          type="text"
          className="chat-input"
          placeholder="Ask AI assistant about incidents, system errors, counts, or history..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button type="submit" className="btn-send" disabled={loading || !input.trim()}>
          <span>Send</span>
          <Send size={16} />
        </button>
      </form>
    </div>
  );
}
