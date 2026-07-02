"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, MessageSquare, BookOpen, Settings, HelpCircle } from "lucide-react";

export default function Sidebar() {
  const pathname = usePathname();

  const navigation = [
    { name: "Dashboard", href: "/", icon: LayoutDashboard },
    { name: "Support Chat", href: "/chat", icon: MessageSquare },
  ];

  return (
    <aside className="w-64 bg-zinc-950 border-r border-zinc-900 flex flex-col h-[calc(100vh-73px)] sticky top-[73px] p-4 justify-between shrink-0 hidden md:flex">
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
          </nav>
        </div>

        <div className="h-[1px] bg-zinc-900" />
      </div>

      {/* Footer Settings tabs */}
      <div className="space-y-1">
        <Link 
          href="#"
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-bold text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          <Settings className="h-4 w-4" />
          Settings
        </Link>
        <Link 
          href="#"
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-bold text-zinc-500 hover:text-zinc-300 transition-colors"
        >
          <HelpCircle className="h-4 w-4" />
          Help Desk
        </Link>
      </div>
    </aside>
  );
}
