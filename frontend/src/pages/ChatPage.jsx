import React, { useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import ChatInput from "../components/ChatInput";
import MessageList from "../components/MessageList";

export default function ChatPage() {
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

  const suggested = useMemo(
    () => [
      "What was the total revenue in the last 30 days?"
    ],
    []
  );

  const [messages, setMessages] = useState([
    { role: "assistant", text: "Hello, welcome to ShopSight. Feel free to ask me about your sales data. I can answer a variety of questions about your data by transforming your natural language into relevant analytics queries." }
  ]);
  const [loading, setLoading] = useState(false);

  const listEndRef = useRef(null);
  useEffect(() => {
    listEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  function getLastResponseContext() {
    let lastResponse = null;
    let lastQuery = "";
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      const m = messages[i];
      if (!lastResponse && m.role === "assistant" && m.response) {
        lastResponse = m.response;
      }
      if (!lastQuery && m.role === "user" && m.text) {
        lastQuery = m.text;
      }
      if (lastResponse && lastQuery) break;
    }
    return lastResponse
      ? {
          last_query: lastQuery,
          last_response: lastResponse
        }
      : null;
  }

  async function sendQuestion(text) {
    setLoading(true);

    setMessages((prev) => [...prev, { role: "user", text }]);
    const followupContext = getLastResponseContext();

    try {
      const payload = {
        message: text,
        is_followup: false,
        followup_context: followupContext
      };

      const res = await axios.post(`${apiBaseUrl}/chat`, payload, { timeout: 120000 });
      const data = res.data;

      const assistantText =
        data?.insight ??
        "Got it. I computed an answer from the dataset.";

      setMessages((prev) => [...prev, { role: "assistant", text: assistantText, response: data }]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Sorry, I couldn’t reach the server. Please try again in a moment." }
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="pageHeader">
        <div className="pageHeaderTitle">ShopSight</div>
      </div>

      <div className="container">
        <div className="card pageCard">
          <div className="chatShell">
            <div className="panelTitleRow">
              <div className="panelTitle">Predictive Queries</div>
              <button
                className="btn btnGhost"
                onClick={() => {
                  setMessages([{ role: "assistant", text: "Ask me about product performance, revenue by category, or sales trends." }]);
                }}
                disabled={loading}
              >
                Reset
              </button>
            </div>

            <MessageList messages={messages} loading={loading} />
            <div ref={listEndRef} />

            <div className="sectionTitle" style={{ marginTop: 6 }}>
              Suggested prompts
            </div>
            <div className="chipRow">
              {suggested.map((s, idx) => (
                <div className="chip" key={idx} onClick={() => sendQuestion(s)} role="button" tabIndex={0}>
                  {s}
                </div>
              ))}
            </div>

            <ChatInput
              onSend={sendQuestion}
              disabled={loading}
              placeholder="Ask: top products, revenue by category, or sales trend..."
            />
          </div>
        </div>
      </div>
    </div>
  );
}

