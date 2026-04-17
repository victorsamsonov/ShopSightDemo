import React from "react";
import InsightCard from "./InsightCard";
import ResultChart from "./ResultChart";
import ResultTable from "./ResultTable";

function Avatar({ role }) {
  const txt = role === "user" ? "U" : "S";
  return <div className="avatar">{txt}</div>;
}

export default function MessageList({ messages, loading = false }) {
  return (
    <div className="chatMessages" aria-label="Chat messages">
      {messages.map((m, idx) => (
        <div className="msgRow" key={idx}>
          <Avatar role={m.role} />
          <div className={`bubble ${m.role === "user" ? "user" : ""} ${m.response ? "rich" : ""}`}>
            {m.response ? (
              <>
                <InsightCard
                  kpi={m.response.kpi}
                  insight={m.response.insight || m.text}
                />
                <ResultChart outputType={m.response.output_type} chart={m.response.chart} />
                <ResultTable table={m.response.table} />
              </>
            ) : (
              <div className="msgText">{m.text}</div>
            )}
          </div>
        </div>
      ))}
      {loading ? <LoadingMessage /> : null}
    </div>
  );
}

export function LoadingMessage() {
  return (
    <div className="msgRow">
      <Avatar role="assistant" />
      <div className="bubble loadingBubble">
        <div className="typingDots" aria-label="Loading response">
          <span />
          <span />
          <span />
        </div>
      </div>
    </div>
  );
}

