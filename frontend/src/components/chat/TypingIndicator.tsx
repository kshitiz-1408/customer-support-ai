import React from "react";
import { Sparkles } from "lucide-react";

export default function TypingIndicator() {
  return (
    <div className="flex gap-3.5 mr-auto">
      {/* Bot Icon */}
      <div className="h-8 w-8 rounded-lg shrink-0 flex items-center justify-center bg-zinc-800 text-zinc-300 border border-zinc-700/60">
        <Sparkles className="h-4 w-4 text-violet-400 animate-pulse" />
      </div>

      {/* Pulsing Dots Bubble */}
      <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-850 p-4 rounded-2xl rounded-tl-none flex items-center gap-1.5 shadow-sm">
        <span className="h-2 w-2 rounded-full bg-zinc-600 animate-bounce [animation-delay:-0.3s]" />
        <span className="h-2 w-2 rounded-full bg-zinc-500 animate-bounce [animation-delay:-0.15s]" />
        <span className="h-2 w-2 rounded-full bg-zinc-600 animate-bounce" />
      </div>
    </div>
  );
}
