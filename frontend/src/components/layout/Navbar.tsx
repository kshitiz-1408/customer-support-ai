"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import axios from "axios";
import { Sparkles, Activity, MessageSquare, AlertTriangle, Loader2 } from "lucide-react";

export default function Navbar() {
  const [connection, setConnection] = useState<"checking" | "connected" | "disconnected">("checking");

  useEffect(() => {
    const checkConnection = async () => {
      const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      try {
        const response = await axios.get(`${backendUrl}/health`);
        if (response.data?.status === "ok") {
          setConnection("connected");
        } else {
          setConnection("disconnected");
        }
      } catch {
        setConnection("disconnected");
      }
    };

    checkConnection();
    
    // Refresh status every 10 seconds
    const interval = setInterval(checkConnection, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <nav className="sticky top-0 z-30 backdrop-blur-md bg-zinc-950/75 border-b border-zinc-900 px-6 py-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="h-9 w-9 rounded-lg bg-gradient-to-tr from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/25 group-hover:scale-105 transition-transform duration-200">
            <Sparkles className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold text-zinc-100 group-hover:text-white transition-colors">
              Customer Support AI
            </h1>
            <p className="text-[10px] text-zinc-500 font-semibold tracking-wider uppercase">Portal Console</p>
          </div>
        </Link>

        {/* Links & Metrics */}
        <div className="flex items-center gap-6">
          <Link href="/chat" className="flex items-center gap-2 text-xs font-bold text-zinc-400 hover:text-zinc-200 transition-colors">
            <MessageSquare className="h-4 w-4" />
            Support Chat
          </Link>
          
          <div className="h-4 w-[1px] bg-zinc-800" />

          {/* Dynamic Connection Indicator */}
          {connection === "checking" && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-zinc-900/40 border border-zinc-850 text-indigo-400">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              <span className="text-[10px] font-bold">Checking Connection...</span>
            </div>
          )}

          {connection === "connected" && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span className="text-[10px] font-bold flex items-center gap-1.5">
                <Activity className="h-3.5 w-3.5" />
                Backend Connected
              </span>
            </div>
          )}

          {connection === "disconnected" && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-450">
              <span className="relative flex h-2 w-2">
                <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
              </span>
              <span className="text-[10px] font-bold flex items-center gap-1.5">
                <AlertTriangle className="h-3.5 w-3.5" />
                Backend Disconnected
              </span>
            </div>
          )}
        </div>

      </div>
    </nav>
  );
}
