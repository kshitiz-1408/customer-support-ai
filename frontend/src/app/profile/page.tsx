"use client";

import React from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import Navbar from "@/components/layout/Navbar";
import Sidebar from "@/components/layout/Sidebar";
import { User, Mail, Calendar, Award, ShieldCheck, ArrowRight, Settings } from "lucide-react";

export default function ProfilePage() {
  const { currentUser } = useAuth();

  if (!currentUser) return null;

  const formatDate = (isoString?: string) => {
    if (!isoString) return "N/A";
    return new Date(isoString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  };

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col selection:bg-indigo-500/30 font-sans">
      {/* Navbar Header */}
      <Navbar />

      <div className="flex-1 flex max-w-7xl mx-auto w-full relative">
        {/* Navigation Sidebar */}
        <Sidebar />

        {/* Profile Content Container */}
        <main className="flex-1 p-8 text-zinc-300">
          
          <div className="max-w-2xl mx-auto">
            {/* Page header */}
            <div className="flex items-center justify-between mb-8">
              <div>
                <h1 className="text-xl font-bold text-zinc-100">User Profile</h1>
                <p className="text-xs text-zinc-500 mt-1 font-semibold">Your portal identity and security settings</p>
              </div>
              <Link 
                href="/settings" 
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-zinc-900 border border-zinc-800 text-xs font-bold text-indigo-400 hover:bg-zinc-850 hover:text-indigo-300 transition-all shadow-md active:scale-95"
              >
                <Settings className="h-4 w-4 animate-spin-slow" />
                Edit Settings
              </Link>
            </div>

            {/* Profile Detail Card */}
            <div className="bg-zinc-900/50 border border-zinc-850 backdrop-blur-xl rounded-2xl p-8 shadow-xl shadow-black/30 space-y-6">
              
              {/* Header Profile Badge */}
              <div className="flex items-center gap-5 pb-6 border-b border-zinc-850">
                <div className="h-16 w-16 rounded-2xl bg-gradient-to-tr from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/10">
                  <span className="text-xl font-extrabold text-white">
                    {currentUser.full_name.charAt(0).toUpperCase()}
                  </span>
                </div>
                <div>
                  <h2 className="text-base font-bold text-zinc-100">{currentUser.full_name}</h2>
                  <p className="text-xs text-zinc-500 font-semibold tracking-wide mt-0.5">{currentUser.email}</p>
                </div>
              </div>

              {/* Account properties list */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                
                {/* Full Name */}
                <div className="flex items-start gap-3.5">
                  <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-850 text-zinc-400">
                    <User className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Full Name</p>
                    <p className="text-sm font-bold text-zinc-200 mt-1">{currentUser.full_name}</p>
                  </div>
                </div>

                {/* Email Address */}
                <div className="flex items-start gap-3.5">
                  <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-850 text-zinc-400">
                    <Mail className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Email Address</p>
                    <p className="text-sm font-bold text-zinc-200 mt-1">{currentUser.email}</p>
                  </div>
                </div>

                {/* Account Role */}
                <div className="flex items-start gap-3.5">
                  <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-850 text-zinc-400">
                    <Award className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Role Privileges</p>
                    <p className="text-sm font-bold text-zinc-200 mt-1 capitalize flex items-center gap-1.5">
                      {currentUser.role}
                      {currentUser.role === "admin" && (
                        <span className="px-1.5 py-0.5 text-[9px] bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded-full font-bold">Admin Portal</span>
                      )}
                    </p>
                  </div>
                </div>

                {/* Verification Status */}
                <div className="flex items-start gap-3.5">
                  <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-850 text-zinc-400">
                    <ShieldCheck className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Security Status</p>
                    <p className="text-sm font-bold text-zinc-200 mt-1 flex items-center gap-1.5">
                      {currentUser.is_verified ? "Verified User" : "Standard Active Account"}
                      <span className="px-1.5 py-0.5 text-[9px] bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-full font-bold">Active</span>
                    </p>
                  </div>
                </div>

                {/* Joined Date */}
                <div className="flex items-start gap-3.5">
                  <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-850 text-zinc-400">
                    <Calendar className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Account Created</p>
                    <p className="text-sm font-bold text-zinc-200 mt-1">
                      {formatDate(currentUser.created_at)}
                    </p>
                  </div>
                </div>

              </div>

              {/* Action Callout */}
              <div className="pt-6 border-t border-zinc-850 flex justify-end">
                <Link 
                  href="/settings" 
                  className="flex items-center gap-1.5 text-xs font-bold text-indigo-400 hover:text-indigo-300 transition-colors"
                >
                  Configure Account Settings
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              </div>

            </div>
          </div>

        </main>
      </div>
    </div>
  );
}
