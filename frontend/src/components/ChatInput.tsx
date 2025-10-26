'use client';

import { useState } from 'react';

interface ChatInputProps {
  onSend: (query: string) => void;
  isConnected: boolean;
}

export default function ChatInput({ onSend, isConnected }: ChatInputProps) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && isConnected) {
      onSend(query);
      setQuery('');
    }
  };

  return (
    <form onSubmit={handleSubmit} className="chat-input">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={isConnected ? "Ask about radiology cases..." : "Connecting..."}
        disabled={!isConnected}
        className="query-input"
      />
      <button type="submit" disabled={!isConnected || !query.trim()} className="send-btn">
        Send
      </button>
    </form>
  );
}
