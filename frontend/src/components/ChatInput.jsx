import React, { useState } from "react";

export default function ChatInput({ onSend, disabled, placeholder }) {
  const [text, setText] = useState("");

  function submit() {
    const trimmed = text.trim();
    if (!trimmed) return;
    onSend(trimmed);
    setText("");
  }

  return (
    <div className="chatComposer">
      <input
        className="input"
        value={text}
        disabled={disabled}
        placeholder={placeholder ?? "Ask a question..."}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") submit();
        }}
      />
      <button className="btn" disabled={disabled} onClick={submit}>
        Send
      </button>
    </div>
  );
}

