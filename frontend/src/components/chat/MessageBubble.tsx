import React from "react";
import { User, Sparkles } from "lucide-react";

export interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
  timestamp: Date;
}

interface MessageBubbleProps {
  message: ChatMessage;
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.sender === "user";

  return (
    <div className={`flex gap-3.5 max-w-[85%] ${isUser ? "ml-auto flex-row-reverse" : "mr-auto"}`}>
      
      {/* Avatar */}
      <div className={`h-8 w-8 rounded-lg shrink-0 flex items-center justify-center border text-xs font-bold ${
        isUser 
          ? "bg-indigo-500/10 text-indigo-400 border-indigo-500/20" 
          : "bg-zinc-800 text-zinc-300 border-zinc-700/60"
      }`}>
        {isUser ? <User className="h-4.5 w-4.5" /> : <Sparkles className="h-4 w-4 text-violet-400" />}
      </div>

      {/* Bubble block */}
      <div className="space-y-1">
        <div className={`p-3.5 rounded-2xl shadow-sm text-xs leading-relaxed ${
          isUser 
            ? "bg-gradient-to-r from-indigo-500 to-violet-600 text-white rounded-tr-none" 
            : "bg-zinc-900/50 backdrop-blur-sm border border-zinc-850 text-zinc-200 rounded-tl-none font-medium"
        }`}>
          {/* Support formatting payload */}
          {message.text.startsWith("{") || message.text.startsWith("[") ? (
            <pre className="text-[10px] font-mono text-zinc-400 overflow-x-auto bg-zinc-950 p-2.5 rounded-lg border border-zinc-900/80 mt-1 max-w-full">
              {message.text}
            </pre>
          ) : (
            <p className="whitespace-pre-wrap">{message.text}</p>
          )}
        </div>
        
        {/* Timestamp */}
        <p className={`text-[9px] text-zinc-600 font-bold px-1.5 ${isUser ? "text-right" : "text-left"}`}>
          {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </p>
      </div>

    </div>
  );
}
