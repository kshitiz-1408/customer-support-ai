"use client";

import React, { useState } from "react";
import { Send, Loader2 } from "lucide-react";

interface ChatInputProps {
  onSendMessage: (text: string) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSendMessage, disabled = false }: ChatInputProps) {
  const [inputText, setInputText] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || disabled) return;
    
    onSendMessage(inputText.trim());
    setInputText("");
  };

  return (
    <form onSubmit={handleSubmit} className="p-4 border-t border-zinc-900 bg-zinc-950">
      <div className="flex gap-2">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          disabled={disabled}
          placeholder="Ask a question (triggers backend health check)..."
          className="flex-1 text-xs font-semibold rounded-lg bg-zinc-900/60 border border-zinc-850 px-4 py-3 text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!inputText.trim() || disabled}
          className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-zinc-800 text-white rounded-lg px-4 flex items-center justify-center transition-colors cursor-pointer group"
        >
          {disabled ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4.5 w-4.5 text-zinc-300 group-hover:text-white transition-colors" />
          )}
        </button>
      </div>
    </form>
  );
}
