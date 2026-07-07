"use client";

import React, { useRef, useEffect } from "react";
import MessageBubble, { ChatMessage } from "./MessageBubble";
import TypingIndicator from "./TypingIndicator";
import ChatInput from "./ChatInput";
import { Sparkles, MessageSquare } from "lucide-react";

interface ChatWindowProps {
  messages: ChatMessage[];
  loading: boolean;
  onSendMessage: (text: string) => void;
  onClearChat?: () => void;
}

export default function ChatWindow({ messages, loading, onSendMessage, onClearChat }: ChatWindowProps) {
  const listRef = useRef<HTMLDivElement>(null);

  // Auto scroll to bottom
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages, loading]);

  return (
    <div className="flex-1 flex flex-col bg-zinc-950 border border-zinc-900 rounded-xl overflow-hidden shadow-2xl relative h-[calc(100vh-105px)]">
      
      {/* Upper header */}
      <div className="p-4 border-b border-zinc-900 flex items-center justify-between bg-zinc-950">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-indigo-500/10 flex items-center justify-center border border-indigo-500/20 text-indigo-400">
            <MessageSquare className="h-4 w-4" />
          </div>
          <div>
            <h2 className="text-xs font-bold text-zinc-100">AI Customer Support</h2>
            <p className="text-[9px] text-zinc-500 font-bold">Latency diagnostics enabled</p>
          </div>
        </div>

        {onClearChat && (
          <button
            onClick={onClearChat}
            className="px-3 py-1.5 rounded-lg border border-zinc-800 bg-zinc-900/50 hover:bg-zinc-800 hover:text-white text-[11px] font-bold text-zinc-400 transition-all cursor-pointer flex items-center gap-1.5 active:scale-95"
          >
            New Chat
          </button>
        )}
      </div>

      {/* Main chat messages log */}
      <div 
        ref={listRef}
        className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-zinc-900 scrollbar-track-transparent"
      >
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center max-w-sm mx-auto space-y-4">
            <div className="h-12 w-12 rounded-2xl bg-gradient-to-tr from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Sparkles className="h-6 w-6 text-white animate-pulse" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-zinc-200">Start a Diagnostic Session</h4>
              <p className="text-xs text-zinc-500 mt-2 leading-relaxed">
                Send a message to ping the backend API `/health` endpoint. The assistant will retrieve and print raw telemetry configurations.
              </p>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))
        )}

        {/* Dynamic Typing Indicator */}
        {loading && <TypingIndicator />}
      </div>

      {/* Input bar */}
      <ChatInput onSendMessage={onSendMessage} disabled={loading} />

    </div>
  );
}
