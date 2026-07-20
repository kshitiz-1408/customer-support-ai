"use client";

import React, { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import Navbar from "@/components/layout/Navbar";
import Sidebar from "@/components/layout/Sidebar";
import { api } from "@/services/api";
import { 
  Loader2, CheckCircle2, AlertCircle, Save, Lock, User, Shield, 
  Bell, Eye, Bot, Trash2, Laptop, Sun, Moon 
} from "lucide-react";
import { useTheme } from "@/context/ThemeContext";

export default function SettingsPage() {
  const { currentUser, logout } = useAuth();

  // Active Tab State (profile, security, notifications, appearance, ai, danger)
  const [activeTab, setActiveTab] = useState("profile");

  // Profile Info Form State
  const [fullName, setFullName] = useState(currentUser?.full_name || "");
  const [infoLoading, setInfoLoading] = useState(false);
  const [infoError, setInfoError] = useState<string | null>(null);
  const [infoSuccess, setInfoSuccess] = useState<string | null>(null);

  // Security Form State
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [secLoading, setSecLoading] = useState(false);
  const [secError, setSecError] = useState<string | null>(null);
  const [secSuccess, setSecSuccess] = useState<string | null>(null);

  // Notification Preferences State (Local state simulation)
  const [prefEmail, setPrefEmail] = useState(true);
  const [prefTicket, setPrefTicket] = useState(true);
  const [prefAI, setPrefAI] = useState(false);
  const [prefProd, setPrefProd] = useState(true);
  const [prefLoading, setPrefLoading] = useState(false);
  const [prefSuccess, setPrefSuccess] = useState<string | null>(null);

  // Appearance State (Global theme context)
  const { theme, setTheme } = useTheme();
  const [accentColor, setAccentColor] = useState("indigo");
  const [fontSize, setFontSize] = useState("medium");

  // AI Preferences State (Local state simulation)
  const [aiSources, setAiSources] = useState(true);
  const [aiStreaming, setAiStreaming] = useState(false);
  const [aiTicketSuggestions, setAiTicketSuggestions] = useState(true);
  const [aiMemory, setAiMemory] = useState(true);
  const [aiVerbosity, setAiVerbosity] = useState("balanced");

  if (!currentUser) return null;

  const formatDate = (isoString?: string) => {
    if (!isoString) return "N/A";
    return new Date(isoString).toLocaleString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const handleInfoSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setInfoLoading(true);
    setInfoError(null);
    setInfoSuccess(null);

    if (!fullName.trim()) {
      setInfoError("Full name cannot be empty.");
      setInfoLoading(false);
      return;
    }

    try {
      await api.patch("/users/me", { full_name: fullName.trim() });
      setInfoSuccess("Profile name updated successfully.");
      
      // Reload profile context context
      if (typeof window !== "undefined") {
        setTimeout(() => {
          window.location.reload();
        }, 1500);
      }
    } catch (err: unknown) {
      const errorObj = err as { response?: { data?: { detail?: string } }; message?: string };
      setInfoError(errorObj.response?.data?.detail || errorObj.message || "Failed to update profile name.");
    } finally {
      setInfoLoading(false);
    }
  };

  const validatePassword = (pwd: string): string | null => {
    if (pwd.length < 8) return "Password must be at least 8 characters long.";
    if (!/[A-Z]/.test(pwd)) return "Password must contain at least one uppercase letter.";
    if (!/[a-z]/.test(pwd)) return "Password must contain at least one lowercase letter.";
    if (!/[0-9]/.test(pwd)) return "Password must contain at least one digit.";
    const specialChars = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~";
    const hasSpecial = pwd.split("").some(char => specialChars.includes(char));
    if (!hasSpecial) return "Password must contain at least one special character.";
    return null;
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSecLoading(true);
    setSecError(null);
    setSecSuccess(null);

    if (!currentPassword || !newPassword || !confirmPassword) {
      setSecError("Please fill in all password fields.");
      setSecLoading(false);
      return;
    }

    if (newPassword !== confirmPassword) {
      setSecError("New passwords do not match.");
      setSecLoading(false);
      return;
    }

    if (currentPassword === newPassword) {
      setSecError("New password must be different from current password.");
      setSecLoading(false);
      return;
    }

    const pwdErr = validatePassword(newPassword);
    if (pwdErr) {
      setSecError(pwdErr);
      setSecLoading(false);
      return;
    }

    try {
      await api.post("/users/change-password", {
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });

      setSecSuccess("Password changed successfully! Logging out of all sessions...");
      
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");

      setTimeout(async () => {
        await logout();
      }, 2500);

    } catch (err: unknown) {
      const errorObj = err as { response?: { data?: { detail?: string } }; message?: string };
      setSecError(errorObj.response?.data?.detail || errorObj.message || "Incorrect current password or invalid new password.");
      setSecLoading(false);
    }
  };

  const handlePrefsSave = (e: React.FormEvent) => {
    e.preventDefault();
    setPrefLoading(true);
    setPrefSuccess(null);
    setTimeout(() => {
      setPrefLoading(false);
      setPrefSuccess("Notification preferences saved successfully.");
    }, 800);
  };

  const tabItems = [
    { id: "profile", label: "Profile", icon: User },
    { id: "security", label: "Security & Login", icon: Shield },
    { id: "notifications", label: "Notifications", icon: Bell },
    { id: "appearance", label: "Appearance", icon: Eye },
    { id: "ai", label: "AI Preferences", icon: Bot },
    { id: "danger", label: "Danger Zone", icon: Trash2 },
  ];

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col selection:bg-indigo-500/30 font-sans">
      <Navbar />

      <div className="flex-1 flex max-w-7xl mx-auto w-full relative">
        <Sidebar />

        <main className="flex-1 p-6 md:p-8 text-zinc-300">
          <div className="max-w-4xl mx-auto">
            {/* Header */}
            <div className="mb-8">
              <h1 className="text-xl font-extrabold text-zinc-100 tracking-tight">System Settings</h1>
              <p className="text-xs text-zinc-500 mt-1 font-semibold">Customize profile details, login security parameters, and notification alerts</p>
            </div>

            {/* Layout Splitter */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              
              {/* Vertical navigation tabs */}
              <div className="md:col-span-1 space-y-1">
                {tabItems.map((item) => {
                  const Icon = item.icon;
                  const active = activeTab === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => setActiveTab(item.id)}
                      className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-xs font-bold text-left transition-all ${
                        active
                          ? "bg-indigo-500/10 text-indigo-400 border-l-2 border-indigo-500"
                          : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/40"
                      }`}
                    >
                      <Icon className="h-4 w-4" />
                      {item.label}
                    </button>
                  );
                })}
              </div>

              {/* Setting Content Panel */}
              <div className="md:col-span-3">
                
                {/* 1. Profile Panel */}
                {activeTab === "profile" && (
                  <div className="bg-zinc-900/40 border border-zinc-850 backdrop-blur-xl rounded-2xl p-6 sm:p-8 shadow-xl space-y-6">
                    <h2 className="text-sm font-bold text-zinc-100 flex items-center gap-2 pb-4 border-b border-zinc-900">
                      <span className="h-5 w-1 bg-indigo-500 rounded-full" />
                      Profile Identity
                    </h2>

                    {infoError && (
                      <div className="px-4 py-3 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-start gap-2.5 text-rose-405 text-xs font-semibold">
                        <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                        {infoError}
                      </div>
                    )}

                    {infoSuccess && (
                      <div className="px-4 py-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-start gap-2.5 text-emerald-400 text-xs font-semibold">
                        <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" />
                        {infoSuccess}
                      </div>
                    )}

                    <div className="flex flex-col sm:flex-row items-center gap-5 pb-6 border-b border-zinc-900">
                      <div className="h-16 w-16 rounded-2xl bg-gradient-to-tr from-indigo-500 to-violet-600 flex items-center justify-center text-xl font-extrabold text-white shadow-lg">
                        {currentUser.full_name.charAt(0).toUpperCase()}
                      </div>
                      <div className="text-center sm:text-left">
                        <h3 className="text-sm font-bold text-zinc-200">{currentUser.full_name}</h3>
                        <p className="text-xs text-zinc-500 font-semibold mt-1">{currentUser.email}</p>
                        <span className="inline-block px-2 py-0.5 rounded bg-zinc-950 text-[10px] font-bold text-zinc-550 border border-zinc-900/60 uppercase mt-2">
                          Role: {currentUser.role}
                        </span>
                      </div>
                    </div>

                    <form onSubmit={handleInfoSubmit} className="space-y-4">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="space-y-1.5">
                          <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider px-0.5">Email Address</label>
                          <input
                            type="email"
                            disabled
                            value={currentUser.email}
                            className="w-full bg-zinc-950/40 border border-zinc-900 rounded-xl py-2.5 px-4 text-xs font-bold text-zinc-600 cursor-not-allowed"
                          />
                        </div>
                        <div className="space-y-1.5">
                          <label htmlFor="fullName" className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider px-0.5">Full Name</label>
                          <input
                            id="fullName"
                            type="text"
                            required
                            disabled={infoLoading}
                            value={fullName}
                            onChange={(e) => setFullName(e.target.value)}
                            className="w-full bg-zinc-950/60 border border-zinc-850 rounded-xl py-2.5 px-4 text-xs text-zinc-200 placeholder-zinc-650 focus:outline-none focus:border-indigo-500 transition-colors font-bold"
                          />
                        </div>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 text-xs">
                        <div>
                          <span className="text-zinc-500 font-semibold">Account Created:</span>
                          <p className="text-zinc-300 font-bold mt-1">{formatDate(currentUser.created_at)}</p>
                        </div>
                        <div>
                          <span className="text-zinc-500 font-semibold">Last Login Trace:</span>
                          <p className="text-zinc-300 font-bold mt-1">{formatDate(currentUser.last_login)}</p>
                        </div>
                      </div>

                      <div className="flex justify-end pt-4 border-t border-zinc-900">
                        <button
                          type="submit"
                          disabled={infoLoading}
                          className="bg-indigo-500 hover:bg-indigo-400 text-white font-bold py-2.5 px-4 rounded-xl shadow-md flex items-center gap-2 transition-all cursor-pointer text-xs disabled:opacity-50 active:scale-95"
                        >
                          {infoLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                          Save Profile Changes
                        </button>
                      </div>
                    </form>
                  </div>
                )}

                {/* 2. Security Panel */}
                {activeTab === "security" && (
                  <div className="bg-zinc-900/40 border border-zinc-850 backdrop-blur-xl rounded-2xl p-6 sm:p-8 shadow-xl space-y-6">
                    <h2 className="text-sm font-bold text-zinc-100 flex items-center gap-2 pb-4 border-b border-zinc-900">
                      <span className="h-5 w-1 bg-indigo-500 rounded-full" />
                      Login Credential Security
                    </h2>

                    {secError && (
                      <div className="px-4 py-3 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-start gap-2.5 text-rose-405 text-xs font-semibold">
                        <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                        {secError}
                      </div>
                    )}

                    {secSuccess && (
                      <div className="px-4 py-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-start gap-2.5 text-emerald-400 text-xs font-semibold">
                        <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" />
                        {secSuccess}
                      </div>
                    )}

                    <form onSubmit={handlePasswordSubmit} className="space-y-4">
                      <div className="space-y-1.5">
                        <label htmlFor="currPassword" className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider px-0.5">Current Password</label>
                        <input
                          id="currPassword"
                          type="password"
                          required
                          disabled={secLoading || !!secSuccess}
                          value={currentPassword}
                          onChange={(e) => setCurrentPassword(e.target.value)}
                          className="w-full bg-zinc-950/60 border border-zinc-850 rounded-xl py-2.5 px-4 text-xs text-zinc-200 placeholder-zinc-650 focus:outline-none focus:border-indigo-500 transition-colors"
                          placeholder="••••••••"
                        />
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="space-y-1.5">
                          <label htmlFor="newPassword" className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider px-0.5">New Password</label>
                          <input
                            id="newPassword"
                            type="password"
                            required
                            disabled={secLoading || !!secSuccess}
                            value={newPassword}
                            onChange={(e) => setNewPassword(e.target.value)}
                            className="w-full bg-zinc-950/60 border border-zinc-850 rounded-xl py-2.5 px-4 text-xs text-zinc-200 placeholder-zinc-650 focus:outline-none focus:border-indigo-500 transition-colors"
                            placeholder="••••••••"
                          />
                        </div>
                        <div className="space-y-1.5">
                          <label htmlFor="confPassword" className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider px-0.5">Confirm New Password</label>
                          <input
                            id="confPassword"
                            type="password"
                            required
                            disabled={secLoading || !!secSuccess}
                            value={confirmPassword}
                            onChange={(e) => setConfirmPassword(e.target.value)}
                            className="w-full bg-zinc-950/60 border border-zinc-850 rounded-xl py-2.5 px-4 text-xs text-zinc-200 placeholder-zinc-650 focus:outline-none focus:border-indigo-500 transition-colors"
                            placeholder="••••••••"
                          />
                        </div>
                      </div>

                      {/* Password Complexity Card */}
                      <div className="bg-zinc-950/30 border border-zinc-900 p-4 rounded-xl space-y-1">
                        <p className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider">Complexity Requirements</p>
                        <ul className="text-[10px] font-semibold text-zinc-600 list-disc list-inside space-y-0.5">
                          <li>Minimum 8 characters length</li>
                          <li>Must differ from current password</li>
                          <li>Contains at least one number and special character</li>
                        </ul>
                      </div>

                      <div className="flex justify-end pt-4 border-t border-zinc-900">
                        <button
                          type="submit"
                          disabled={secLoading || !!secSuccess}
                          className="bg-indigo-500 hover:bg-indigo-400 text-white font-bold py-2.5 px-4 rounded-xl shadow-md flex items-center gap-2 transition-all cursor-pointer text-xs disabled:opacity-50 active:scale-95"
                        >
                          {secLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Lock className="h-3.5 w-3.5" />}
                          Update Password
                        </button>
                      </div>
                    </form>

                    {/* Placeholder Active Sessions */}
                    <div className="border-t border-zinc-900 pt-6">
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="text-xs font-bold text-zinc-200">Active Account Sessions</h3>
                          <p className="text-[10px] text-zinc-500 font-semibold mt-0.5">Logout of other devices (Coming Soon)</p>
                        </div>
                        <button
                          disabled
                          className="px-3.5 py-2 rounded-xl bg-zinc-900 border border-zinc-800 text-[10px] font-bold text-zinc-500 cursor-not-allowed"
                        >
                          Logout All Sessions
                        </button>
                      </div>
                    </div>

                  </div>
                )}

                {/* 3. Notifications Panel */}
                {activeTab === "notifications" && (
                  <div className="bg-zinc-900/40 border border-zinc-850 backdrop-blur-xl rounded-2xl p-6 sm:p-8 shadow-xl space-y-6">
                    <h2 className="text-sm font-bold text-zinc-100 flex items-center gap-2 pb-4 border-b border-zinc-900">
                      <span className="h-5 w-1 bg-indigo-500 rounded-full" />
                      Notification Preferences
                    </h2>

                    {prefSuccess && (
                      <div className="px-4 py-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-start gap-2.5 text-emerald-400 text-xs font-semibold">
                        <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" />
                        {prefSuccess}
                      </div>
                    )}

                    <form onSubmit={handlePrefsSave} className="space-y-5">
                      
                      {/* Email Notifications */}
                      <label className="flex items-start gap-3 cursor-pointer group">
                        <input
                          type="checkbox"
                          checked={prefEmail}
                          onChange={(e) => setPrefEmail(e.target.checked)}
                          className="mt-1 h-4 w-4 rounded bg-zinc-950 border border-zinc-850 text-indigo-500 focus:ring-0 focus:ring-offset-0 cursor-pointer"
                        />
                        <div>
                          <span className="text-xs font-bold text-zinc-300 group-hover:text-zinc-200 transition-colors">Email Notifications</span>
                          <p className="text-[10px] text-zinc-500 font-semibold mt-0.5">Receive digests and summary notifications to your registered email</p>
                        </div>
                      </label>

                      {/* Ticket Updates */}
                      <label className="flex items-start gap-3 cursor-pointer group">
                        <input
                          type="checkbox"
                          checked={prefTicket}
                          onChange={(e) => setPrefTicket(e.target.checked)}
                          className="mt-1 h-4 w-4 rounded bg-zinc-950 border border-zinc-850 text-indigo-500 focus:ring-0 focus:ring-offset-0 cursor-pointer"
                        />
                        <div>
                          <span className="text-xs font-bold text-zinc-300 group-hover:text-zinc-200 transition-colors">Ticket Updates</span>
                          <p className="text-[10px] text-zinc-500 font-semibold mt-0.5">Get notified instantly when ticket assignments or statuses change</p>
                        </div>
                      </label>

                      {/* AI response alerts */}
                      <label className="flex items-start gap-3 cursor-pointer group">
                        <input
                          type="checkbox"
                          checked={prefAI}
                          onChange={(e) => setPrefAI(e.target.checked)}
                          className="mt-1 h-4 w-4 rounded bg-zinc-950 border border-zinc-850 text-indigo-500 focus:ring-0 focus:ring-offset-0 cursor-pointer"
                        />
                        <div>
                          <span className="text-xs font-bold text-zinc-300 group-hover:text-zinc-200 transition-colors">AI Response Notifications</span>
                          <p className="text-[10px] text-zinc-500 font-semibold mt-0.5">Send notification alert once agent runs finish generating replies</p>
                        </div>
                      </label>

                      {/* Product updates */}
                      <label className="flex items-start gap-3 cursor-pointer group">
                        <input
                          type="checkbox"
                          checked={prefProd}
                          onChange={(e) => setPrefProd(e.target.checked)}
                          className="mt-1 h-4 w-4 rounded bg-zinc-950 border border-zinc-850 text-indigo-500 focus:ring-0 focus:ring-offset-0 cursor-pointer"
                        />
                        <div>
                          <span className="text-xs font-bold text-zinc-300 group-hover:text-zinc-200 transition-colors">Product Announcements</span>
                          <p className="text-[10px] text-zinc-500 font-semibold mt-0.5">Stay informed about system optimizations and developer notes</p>
                        </div>
                      </label>

                      <div className="flex justify-end pt-4 border-t border-zinc-900">
                        <button
                          type="submit"
                          disabled={prefLoading}
                          className="bg-indigo-500 hover:bg-indigo-400 text-white font-bold py-2.5 px-4 rounded-xl shadow-md flex items-center gap-2 transition-all cursor-pointer text-xs disabled:opacity-50 active:scale-95"
                        >
                          {prefLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                          Save Preferences
                        </button>
                      </div>

                    </form>
                  </div>
                )}

                {/* 4. Appearance Panel */}
                {activeTab === "appearance" && (
                  <div className="bg-zinc-900/40 border border-zinc-850 backdrop-blur-xl rounded-2xl p-6 sm:p-8 shadow-xl space-y-6">
                    <h2 className="text-sm font-bold text-zinc-100 flex items-center gap-2 pb-4 border-b border-zinc-900">
                      <span className="h-5 w-1 bg-indigo-500 rounded-full" />
                      Layout Theme Appearance
                    </h2>

                    {/* Dark/Light mode buttons */}
                    <div>
                      <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider mb-3">Theme Selection</h3>
                      <div className="grid grid-cols-3 gap-3">
                        <button
                          onClick={() => setTheme("light")}
                          className={`flex flex-col items-center gap-2 p-4 rounded-xl border text-xs font-bold transition-all active:scale-95 ${
                            theme === "light"
                              ? "bg-indigo-500 text-white border-indigo-500 shadow-md shadow-indigo-500/10"
                              : "bg-zinc-950/40 text-zinc-550 border-zinc-900 hover:bg-zinc-900/40"
                          }`}
                        >
                          <Sun className="h-5 w-5" />
                          Light Mode
                        </button>
                        <button
                          onClick={() => setTheme("dark")}
                          className={`flex flex-col items-center gap-2 p-4 rounded-xl border text-xs font-bold transition-all active:scale-95 ${
                            theme === "dark"
                              ? "bg-indigo-500 text-white border-indigo-500 shadow-md shadow-indigo-500/10"
                              : "bg-zinc-950/40 text-zinc-550 border-zinc-900 hover:bg-zinc-900/40"
                          }`}
                        >
                          <Moon className="h-5 w-5" />
                          Dark Mode
                        </button>
                        <button
                          onClick={() => setTheme("system")}
                          className={`flex flex-col items-center gap-2 p-4 rounded-xl border text-xs font-bold transition-all active:scale-95 ${
                            theme === "system"
                              ? "bg-indigo-500 text-white border-indigo-500 shadow-md shadow-indigo-500/10"
                              : "bg-zinc-950/40 text-zinc-550 border-zinc-900 hover:bg-zinc-900/40"
                          }`}
                        >
                          <Laptop className="h-5 w-5" />
                          System Default
                        </button>
                      </div>
                    </div>

                    {/* Accent Color placeholder */}
                    <div className="border-t border-zinc-900 pt-5">
                      <h3 className="text-xs font-bold text-zinc-450 uppercase tracking-wider mb-2">Accent Color (Coming Soon)</h3>
                      <div className="flex gap-2.5">
                        {["indigo", "violet", "emerald", "amber", "rose"].map((c) => (
                          <button
                            key={c}
                            disabled
                            onClick={() => setAccentColor(c)}
                            className={`h-6 w-6 rounded-full capitalize cursor-not-allowed opacity-60 border-2 ${
                              c === "indigo" ? "bg-indigo-500" :
                              c === "violet" ? "bg-violet-600" :
                              c === "emerald" ? "bg-emerald-500" :
                              c === "amber" ? "bg-amber-500" : "bg-rose-500"
                            } ${accentColor === c ? "border-white" : "border-transparent"}`}
                          />
                        ))}
                      </div>
                    </div>

                    {/* Font size placeholder */}
                    <div className="border-t border-zinc-900 pt-5">
                      <h3 className="text-xs font-bold text-zinc-450 uppercase tracking-wider mb-2.5">Typography Scaling (Coming Soon)</h3>
                      <div className="flex gap-2">
                        {["small", "medium", "large"].map((sz) => (
                          <button
                            key={sz}
                            disabled
                            onClick={() => setFontSize(sz)}
                            className={`px-3 py-1.5 border border-zinc-800 rounded-lg text-xs font-bold capitalize cursor-not-allowed opacity-60 ${
                              fontSize === sz ? "bg-zinc-800 text-zinc-100" : "bg-zinc-950/40 text-zinc-500"
                            }`}
                          >
                            {sz}
                          </button>
                        ))}
                      </div>
                    </div>

                  </div>
                )}

                {/* 5. AI Preferences Panel */}
                {activeTab === "ai" && (
                  <div className="bg-zinc-900/40 border border-zinc-850 backdrop-blur-xl rounded-2xl p-6 sm:p-8 shadow-xl space-y-6">
                    <h2 className="text-sm font-bold text-zinc-100 flex items-center gap-2 pb-4 border-b border-zinc-900">
                      <span className="h-5 w-1 bg-indigo-500 rounded-full" />
                      AI Model Configurations
                    </h2>

                    <div className="space-y-4">
                      
                      {/* Show Response sources */}
                      <label className="flex items-start gap-3 cursor-pointer group">
                        <input
                          type="checkbox"
                          checked={aiSources}
                          onChange={(e) => setAiSources(e.target.checked)}
                          className="mt-1 h-4 w-4 rounded bg-zinc-950 border border-zinc-850 text-indigo-500 focus:ring-0 focus:ring-offset-0 cursor-pointer"
                        />
                        <div>
                          <span className="text-xs font-bold text-zinc-300 group-hover:text-zinc-200 transition-colors">Show Reference Sources</span>
                          <p className="text-[10px] text-zinc-500 font-semibold mt-0.5">Explicitly display knowledge citations and articles at the end of replies</p>
                        </div>
                      </label>

                      {/* Streaming responses */}
                      <label className="flex items-start gap-3 cursor-pointer group">
                        <input
                          type="checkbox"
                          checked={aiStreaming}
                          onChange={(e) => setAiStreaming(e.target.checked)}
                          className="mt-1 h-4 w-4 rounded bg-zinc-950 border border-zinc-850 text-indigo-500 focus:ring-0 focus:ring-offset-0 cursor-pointer"
                        />
                        <div>
                          <span className="text-xs font-bold text-zinc-300 group-hover:text-zinc-200 transition-colors">Stream Responses</span>
                          <p className="text-[10px] text-zinc-500 font-semibold mt-0.5">Render words as they generate rather than waiting for completion (Coming Soon)</p>
                        </div>
                      </label>

                      {/* Auto-create ticket suggestions */}
                      <label className="flex items-start gap-3 cursor-pointer group">
                        <input
                          type="checkbox"
                          checked={aiTicketSuggestions}
                          onChange={(e) => setAiTicketSuggestions(e.target.checked)}
                          className="mt-1 h-4 w-4 rounded bg-zinc-950 border border-zinc-850 text-indigo-500 focus:ring-0 focus:ring-offset-0 cursor-pointer"
                        />
                        <div>
                          <span className="text-xs font-bold text-zinc-300 group-hover:text-zinc-200 transition-colors">Auto-create ticket suggestions</span>
                          <p className="text-[10px] text-zinc-500 font-semibold mt-0.5">Identify unresolved complaints and suggest filing formal support tickets</p>
                        </div>
                      </label>

                      {/* Conversation memory */}
                      <label className="flex items-start gap-3 cursor-pointer group">
                        <input
                          type="checkbox"
                          checked={aiMemory}
                          onChange={(e) => setAiMemory(e.target.checked)}
                          className="mt-1 h-4 w-4 rounded bg-zinc-950 border border-zinc-850 text-indigo-500 focus:ring-0 focus:ring-offset-0 cursor-pointer"
                        />
                        <div>
                          <span className="text-xs font-bold text-zinc-300 group-hover:text-zinc-200 transition-colors">Long-term Session Memory</span>
                          <p className="text-[10px] text-zinc-500 font-semibold mt-0.5">Enable contextual awareness across multi-turn user message histories</p>
                        </div>
                      </label>

                      {/* Response verbosity */}
                      <div className="border-t border-zinc-900 pt-4 space-y-1.5">
                        <label className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">Response Verbosity Style</label>
                        <select
                          value={aiVerbosity}
                          onChange={(e) => setAiVerbosity(e.target.value)}
                          className="w-full py-2 px-3 rounded-xl bg-zinc-950 border border-zinc-850 text-xs text-zinc-300 focus:outline-none focus:border-indigo-500 transition-colors cursor-pointer"
                        >
                          <option value="concise">Concise & Direct (Speed optimized)</option>
                          <option value="balanced">Balanced Contextual (Recommended)</option>
                          <option value="detailed">Thorough & Detailed (Long explanations)</option>
                        </select>
                      </div>

                    </div>
                  </div>
                )}

                {/* 6. Danger Zone Panel */}
                {activeTab === "danger" && (
                  <div className="bg-zinc-900/40 border border-red-950/30 backdrop-blur-xl rounded-2xl p-6 sm:p-8 shadow-xl space-y-6">
                    <h2 className="text-sm font-bold text-red-400 flex items-center gap-2 pb-4 border-b border-red-950/20">
                      <span className="h-5 w-1 bg-red-500 rounded-full" />
                      Danger System Scope
                    </h2>

                    <div className="space-y-4">
                      
                      {/* Clear Chat History */}
                      <div className="flex items-center justify-between p-4 bg-red-500/5 border border-red-950/20 rounded-xl">
                        <div>
                          <h3 className="text-xs font-bold text-zinc-200">Clear Active Chats</h3>
                          <p className="text-[10px] text-zinc-500 font-semibold mt-0.5">Purges history database. (Coming Soon)</p>
                        </div>
                        <button
                          disabled
                          className="px-4 py-2 rounded-xl bg-zinc-950 hover:bg-zinc-900 text-xs font-bold text-red-500/40 border border-red-950/20 cursor-not-allowed"
                        >
                          Clear Chats
                        </button>
                      </div>

                      {/* Export Conversational Data */}
                      <div className="flex items-center justify-between p-4 bg-zinc-900/20 border border-zinc-850 rounded-xl">
                        <div>
                          <h3 className="text-xs font-bold text-zinc-200">Export All Data</h3>
                          <p className="text-[10px] text-zinc-500 font-semibold mt-0.5">Download full JSON log of logs. (Coming Soon)</p>
                        </div>
                        <button
                          disabled
                          className="px-4 py-2 rounded-xl bg-zinc-950 hover:bg-zinc-900 text-xs font-bold text-zinc-500 border border-zinc-800 cursor-not-allowed"
                        >
                          Export Data
                        </button>
                      </div>

                      {/* Delete Account */}
                      <div className="flex items-center justify-between p-4 bg-red-500/10 border border-red-500/20 rounded-xl">
                        <div>
                          <h3 className="text-xs font-bold text-red-400">Permanently Delete Account</h3>
                          <p className="text-[10px] text-red-500/60 font-semibold mt-0.5">This action deletes email registration. (Coming Soon)</p>
                        </div>
                        <button
                          disabled
                          className="px-4 py-2 rounded-xl bg-red-500/20 hover:bg-red-500/30 text-xs font-bold text-red-400 cursor-not-allowed"
                        >
                          Delete Account
                        </button>
                      </div>

                    </div>
                  </div>
                )}

              </div>

            </div>

          </div>
        </main>
      </div>
    </div>
  );
}
