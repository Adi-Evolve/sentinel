import { useState, useRef, useEffect } from "react";
import { MessageSquare, Send, Loader2, Sparkles, X, ChevronRight } from "lucide-react";

export default function NaturalLanguageQuery({ result }) {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([
    {
      type: "system",
      text: "Ask me anything about your logs! Try:\n• 'Show failed logins from Russia'\n• 'What was the most active IP?'\n• 'Did we have SQL injection attempts?'",
    },
  ]);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Debug log
  console.log("NaturalLanguageQuery rendered, result:", result, "isOpen:", isOpen);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
    }
  }, [isOpen]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim() || loading || !result?.scan_id) return;

    const userQuestion = query.trim();
    setQuery("");
    setMessages((prev) => [...prev, { type: "user", text: userQuestion }]);
    setLoading(true);

    try {
      const response = await fetch(`/api/llm/query/${result.scan_id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: userQuestion }),
      });

      const data = await response.json();

      let responseText = data.summary || "Query processed successfully.";

      // Format results if available
      if (data.results && data.results.length > 0) {
        responseText += `\n\nFound ${data.results.length} results:`;
        data.results.slice(0, 5).forEach((item, idx) => {
          if (item.ip) {
            responseText += `\n${idx + 1}. IP: ${item.ip}${item.count ? ` (${item.count} events)` : ""}`;
          } else if (item.timestamp) {
            responseText += `\n${idx + 1}. ${new Date(item.timestamp).toLocaleString()}`;
          }
        });
        if (data.results.length > 5) {
          responseText += `\n... and ${data.results.length - 5} more`;
        }
      } else {
        responseText += "\n\nNo matching events found.";
      }

      setMessages((prev) => [
        ...prev,
        {
          type: "assistant",
          text: responseText,
          interpretation: data.interpretation,
          llmAvailable: data.llm_available,
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          type: "assistant",
          text: "Sorry, I couldn't process that query. Please try again.",
          error: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const suggestions = [
    "Show failed logins",
    "Most active IP addresses",
    "Events from last hour",
    "Any SQL injection attempts?",
    "Suspicious countries",
  ];

  if (!isOpen) {
    return (
      <button 
        className="nlq-fab" 
        onClick={() => setIsOpen(true)} 
        title="Ask AI about your logs"
        style={{ 
          position: 'fixed', 
          bottom: '24px', 
          right: '24px', 
          zIndex: 9999,
          background: 'linear-gradient(135deg, #8b5cf6, #6366f1)',
          padding: '14px 20px',
          borderRadius: '50px',
          color: 'white',
          fontWeight: '600',
          border: '3px solid #00ff00',
          boxShadow: '0 4px 20px rgba(139, 92, 246, 0.4)',
          cursor: 'pointer'
        }}
      >
        <Sparkles size={20} />
        <span>Ask AI</span>
      </button>
    );
  }

  return (
    <div className="nlq-panel">
      <div className="nlq-header">
        <div className="nlq-title">
          <Sparkles size={18} />
          <span>AI Log Assistant</span>
        </div>
        <button className="nlq-close" onClick={() => setIsOpen(false)}>
          <X size={18} />
        </button>
      </div>

      <div className="nlq-messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`nlq-message ${msg.type}`}>
            {msg.type === "user" && <div className="nlq-avatar user">You</div>}
            {msg.type === "assistant" && <div className="nlq-avatar ai">AI</div>}
            <div className="nlq-bubble">
              <div className="nlq-text">{msg.text}</div>
              {msg.interpretation && (
                <div className="nlq-interpretation">
                  <ChevronRight size={12} />
                  <span>Query interpreted using {msg.llmAvailable ? "local LLM" : "keyword matching"}</span>
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="nlq-message assistant">
            <div className="nlq-avatar ai">AI</div>
            <div className="nlq-bubble">
              <Loader2 size={16} className="nlq-spinner" />
              <span>Analyzing your logs...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {messages.length === 1 && (
        <div className="nlq-suggestions">
          {suggestions.map((s, idx) => (
            <button key={idx} className="nlq-suggestion" onClick={() => setQuery(s)}>
              {s}
            </button>
          ))}
        </div>
      )}

      <form className="nlq-input-area" onSubmit={handleSubmit}>
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask about your logs..."
          disabled={loading}
          className="nlq-input"
        />
        <button type="submit" disabled={!query.trim() || loading} className="nlq-send">
          <Send size={18} />
        </button>
      </form>
    </div>
  );
}
