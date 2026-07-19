"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, MessageSquare, Settings, HelpCircle, ShieldAlert, Clipboard, User, BookOpen, Activity, Server } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

export default function Sidebar() {
  const pathname = usePathname();
  const { currentUser } = useAuth();

  const navigation = [
    { name: "Dashboard", href: "/", icon: LayoutDashboard },
    { name: "Support Chat", href: "/chat", icon: MessageSquare },
  ];

  return (
    <aside className="w-64 bg-zinc-950 border-r border-zinc-900 flex flex-col h-[calc(100vh-73px)] sticky top-[73px] p-4 justify-between shrink-0 hidden md:flex font-sans">
      <div className="space-y-6">
        <div>
          <span className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest px-3">Navigation</span>
          <nav className="mt-2 space-y-1">
            {navigation.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-bold transition-all ${
                    active
                      ? "bg-indigo-500/10 text-indigo-400 border-l-2 border-indigo-500"
                      : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/40"
                  }`}
                >
                  <item.icon className="h-4 w-4" />
                  {item.name}
                </Link>
              );
            })}
            
            {currentUser?.role === "admin" && (
              <>
                <div className="h-[1px] bg-zinc-900 my-2" />
                <span className="text-[10px] font-bold text-zinc-600 uppercase tracking-widest px-3 block mb-1">Admin Ops</span>
                <Link
                  href="/admin/users"
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-bold transition-all ${
                    pathname === "/admin/users"
                      ? "bg-amber-500/10 text-amber-400 border-l-2 border-amber-500"
                      : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/40"
                  }`}
                >
                  <User className="h-4 w-4" />
                  Manage Users
                </Link>
                <Link
                  href="/admin/tickets"
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-bold transition-all ${
                    pathname === "/admin/tickets"
                      ? "bg-amber-500/10 text-amber-400 border-l-2 border-amber-500"
                      : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/40"
                  }`}
                >
                  <Clipboard className="h-4 w-4" />
                  Manage Tickets
                </Link>
                <Link
                  href="/admin/conversations"
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-bold transition-all ${
                    pathname === "/admin/conversations"
                      ? "bg-amber-500/10 text-amber-400 border-l-2 border-amber-500"
                      : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/40"
                  }`}
                >
                  <MessageSquare className="h-4 w-4" />
                  Inspect Chats
                </Link>
                <Link
                  href="/admin/knowledge"
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-bold transition-all ${
                    pathname === "/admin/knowledge"
                      ? "bg-amber-500/10 text-amber-400 border-l-2 border-amber-500"
                      : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/40"
                  }`}
                >
                  <BookOpen className="h-4 w-4" />
                  Manage KB
                </Link>
                <Link
                  href="/admin/analytics"
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-bold transition-all ${
                    pathname === "/admin/analytics"
                      ? "bg-amber-500/10 text-amber-400 border-l-2 border-amber-500"
                      : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/40"
                  }`}
                >
                  <Activity className="h-4 w-4" />
                  Analytics
                </Link>
                <Link
                  href="/admin/audit"
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-bold transition-all ${
                    pathname === "/admin/audit"
                      ? "bg-amber-500/10 text-amber-400 border-l-2 border-amber-500"
                      : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/40"
                  }`}
                >
                  <ShieldAlert className="h-4 w-4" />
                  Audit Logs
                </Link>
                <Link
                  href="/admin/monitoring"
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-bold transition-all ${
                    pathname === "/admin/monitoring"
                      ? "bg-amber-500/10 text-amber-400 border-l-2 border-amber-500"
                      : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/40"
                  }`}
                >
                  <Server className="h-4 w-4" />
                  System Status
                </Link>
              </>
            )}
          </nav>
        </div>

        <div className="h-[1px] bg-zinc-900" />
      </div>

      {/* Footer Settings tabs */}
      <div className="space-y-1">
        <Link 
          href="/settings"
          className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-bold transition-all ${
            pathname === "/settings"
              ? "bg-indigo-500/10 text-indigo-400 border-l-2 border-indigo-500"
              : "text-zinc-550 hover:text-zinc-300 hover:bg-zinc-900/40"
          }`}
        >
          <Settings className="h-4 w-4" />
          Settings
        </Link>
        <Link 
          href="/help"
          className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-bold transition-all ${
            pathname === "/help"
              ? "bg-indigo-500/10 text-indigo-400 border-l-2 border-indigo-500"
              : "text-zinc-550 hover:text-zinc-300 hover:bg-zinc-900/40"
          }`}
        >
          <HelpCircle className="h-4 w-4" />
          Help Desk
        </Link>
      </div>
    </aside>
  );
}
