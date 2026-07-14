"use client";

import React, { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import Navbar from "@/components/layout/Navbar";
import Sidebar from "@/components/layout/Sidebar";
import { api } from "@/services/api";
import { Loader2, CheckCircle2, AlertCircle, Save, Lock } from "lucide-react";

export default function SettingsPage() {
  const { currentUser, logout } = useAuth();

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

  if (!currentUser) return null;

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
      
      // Briefly reload window context or trigger state refresh
      if (typeof window !== "undefined") {
        setTimeout(() => {
          window.location.reload();
        }, 1500);
      }
    } catch (err: unknown) {
      const errorObj = err as { message?: string } | null;
      setInfoError(errorObj?.message || "Failed to update profile name.");
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
      
      // Clean inputs
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");

      // Log out after 2.5 seconds to force re-authentication
      setTimeout(async () => {
        await logout();
      }, 2500);

    } catch (err: unknown) {
      const errorObj = err as { message?: string } | null;
      setSecError(errorObj?.message || "Incorrect current password or invalid new password.");
      setSecLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col selection:bg-indigo-500/30 font-sans">
      {/* Navbar Header */}
      <Navbar />

      <div className="flex-1 flex max-w-7xl mx-auto w-full relative">
        {/* Navigation Sidebar */}
        <Sidebar />

        {/* Settings Content Container */}
        <main className="flex-1 p-8 text-zinc-300">
          
          <div className="max-w-2xl mx-auto space-y-8">
            {/* Page Header */}
            <div>
              <h1 className="text-xl font-bold text-zinc-100">Account Settings</h1>
              <p className="text-xs text-zinc-500 mt-1 font-semibold">Update your portal profile info and security credentials</p>
            </div>

            {/* Form 1: Profile Information */}
            <div className="bg-zinc-900/50 border border-zinc-850 backdrop-blur-xl rounded-2xl p-8 shadow-xl shadow-black/30">
              <h2 className="text-sm font-bold text-zinc-100 mb-6 flex items-center gap-2">
                <span className="h-5 w-1 bg-indigo-500 rounded-full" />
                Profile Information
              </h2>

              {infoError && (
                <div className="mb-6 px-4 py-3 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-start gap-2.5 text-rose-450">
                  <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                  <span className="text-xs font-semibold leading-relaxed">{infoError}</span>
                </div>
              )}

              {infoSuccess && (
                <div className="mb-6 px-4 py-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-start gap-2.5 text-emerald-400">
                  <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" />
                  <span className="text-xs font-semibold leading-relaxed">{infoSuccess}</span>
                </div>
              )}

              <form onSubmit={handleInfoSubmit} className="space-y-5">
                {/* Email Address (Immutable) */}
                <div className="space-y-1.5">
                  <label className="text-[11px] font-bold text-zinc-500 uppercase tracking-wide px-0.5">Email Address (Cannot change)</label>
                  <input
                    type="email"
                    disabled
                    value={currentUser.email}
                    className="w-full bg-zinc-950/40 border border-zinc-900/80 rounded-xl py-2.5 px-4 text-xs font-bold text-zinc-650 cursor-not-allowed"
                  />
                </div>

                {/* Full Name (Modifiable) */}
                <div className="space-y-1.5">
                  <label htmlFor="fullName" className="text-[11px] font-bold text-zinc-400 tracking-wide uppercase px-0.5">Full Name</label>
                  <input
                    id="fullName"
                    type="text"
                    required
                    disabled={infoLoading}
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="w-full bg-zinc-950/60 border border-zinc-850 rounded-xl py-2.5 px-4 text-xs text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-indigo-500/80 focus:ring-2 focus:ring-indigo-500/10 transition-all disabled:opacity-50 font-bold"
                  />
                </div>

                {/* Save Info Button */}
                <div className="flex justify-end pt-2">
                  <button
                    type="submit"
                    disabled={infoLoading}
                    className="bg-indigo-500 hover:bg-indigo-400 text-white font-bold py-2.5 px-4 rounded-xl shadow-md flex items-center gap-2 transition-all cursor-pointer text-xs disabled:opacity-50 disabled:cursor-not-allowed active:scale-95"
                  >
                    {infoLoading ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Save className="h-3.5 w-3.5" />
                    )}
                    Save Profile
                  </button>
                </div>
              </form>
            </div>

            {/* Form 2: Change Password */}
            <div className="bg-zinc-900/50 border border-zinc-850 backdrop-blur-xl rounded-2xl p-8 shadow-xl shadow-black/30">
              <h2 className="text-sm font-bold text-zinc-100 mb-6 flex items-center gap-2">
                <span className="h-5 w-1 bg-violet-600 rounded-full" />
                Change Password
              </h2>

              {secError && (
                <div className="mb-6 px-4 py-3 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-start gap-2.5 text-rose-450">
                  <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                  <span className="text-xs font-semibold leading-relaxed">{secError}</span>
                </div>
              )}

              {secSuccess && (
                <div className="mb-6 px-4 py-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-start gap-2.5 text-emerald-400">
                  <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" />
                  <span className="text-xs font-semibold leading-relaxed">{secSuccess}</span>
                </div>
              )}

              <form onSubmit={handlePasswordSubmit} className="space-y-4">
                {/* Current Password */}
                <div className="space-y-1.5">
                  <label htmlFor="currPassword" className="text-[11px] font-bold text-zinc-400 tracking-wide uppercase px-0.5">Current Password</label>
                  <input
                    id="currPassword"
                    type="password"
                    required
                    disabled={secLoading || !!secSuccess}
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    className="w-full bg-zinc-950/60 border border-zinc-850 rounded-xl py-2.5 px-4 text-xs text-zinc-200 placeholder-zinc-650 focus:outline-none focus:border-indigo-500/80 focus:ring-2 focus:ring-indigo-500/10 transition-all disabled:opacity-50"
                    placeholder="••••••••"
                  />
                </div>

                {/* New Password */}
                <div className="space-y-1.5">
                  <label htmlFor="newPassword" className="text-[11px] font-bold text-zinc-400 tracking-wide uppercase px-0.5">New Password</label>
                  <input
                    id="newPassword"
                    type="password"
                    required
                    disabled={secLoading || !!secSuccess}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    className="w-full bg-zinc-950/60 border border-zinc-850 rounded-xl py-2.5 px-4 text-xs text-zinc-200 placeholder-zinc-650 focus:outline-none focus:border-indigo-500/80 focus:ring-2 focus:ring-indigo-500/10 transition-all disabled:opacity-50"
                    placeholder="••••••••"
                  />
                </div>

                {/* Confirm New Password */}
                <div className="space-y-1.5">
                  <label htmlFor="confPassword" className="text-[11px] font-bold text-zinc-400 tracking-wide uppercase px-0.5">Confirm New Password</label>
                  <input
                    id="confPassword"
                    type="password"
                    required
                    disabled={secLoading || !!secSuccess}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full bg-zinc-950/60 border border-zinc-850 rounded-xl py-2.5 px-4 text-xs text-zinc-200 placeholder-zinc-650 focus:outline-none focus:border-indigo-500/80 focus:ring-2 focus:ring-indigo-500/10 transition-all disabled:opacity-50"
                    placeholder="••••••••"
                  />
                </div>

                {/* Password Rules Card */}
                <div className="bg-zinc-950/30 rounded-xl p-3.5 border border-zinc-900/50 space-y-1">
                  <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-wide">Complexity Checklist</p>
                  <ul className="text-[10px] font-semibold text-zinc-600 list-disc list-inside space-y-0.5">
                    <li>Minimum 8 characters length</li>
                    <li>Must differ from your current password</li>
                    <li>Contains at least one number and one special char</li>
                  </ul>
                </div>

                {/* Change Password Button */}
                <div className="flex justify-end pt-2">
                  <button
                    type="submit"
                    disabled={secLoading || !!secSuccess}
                    className="bg-violet-600 hover:bg-violet-500 text-white font-bold py-2.5 px-4 rounded-xl shadow-md flex items-center gap-2 transition-all cursor-pointer text-xs disabled:opacity-50 disabled:cursor-not-allowed active:scale-95"
                  >
                    {secLoading ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Lock className="h-3.5 w-3.5" />
                    )}
                    Update Password
                  </button>
                </div>
              </form>
            </div>

          </div>

        </main>
      </div>
    </div>
  );
}
