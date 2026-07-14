"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { Sparkles, Loader2, Mail, Lock, AlertCircle } from "lucide-react";

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      setError("Please fill in all fields.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await login(email, password);
      // login action will auto redirect to '/'
    } catch (err: unknown) {
      const errorObj = err as { message?: string } | null;
      setError(errorObj?.message || "Failed to log in. Please check your credentials.");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col justify-center items-center px-4 relative selection:bg-indigo-500/30 font-sans">
      {/* Decorative Gradients */}
      <div className="absolute top-1/4 left-1/4 -translate-x-1/2 -translate-y-1/2 w-[350px] h-[350px] rounded-full bg-indigo-500/10 blur-[100px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 translate-x-1/2 translate-y-1/2 w-[350px] h-[350px] rounded-full bg-violet-600/10 blur-[100px] pointer-events-none" />

      {/* Main card container */}
      <div className="w-full max-w-md z-10">
        
        {/* Portal Branding */}
        <div className="flex flex-col items-center mb-8">
          <div className="h-12 w-12 rounded-xl bg-gradient-to-tr from-indigo-500 to-violet-600 flex items-center justify-center shadow-xl shadow-indigo-500/20 mb-4 animate-pulse">
            <Sparkles className="h-6 w-6 text-white" />
          </div>
          <h2 className="text-xl font-bold text-zinc-100">Welcome Back</h2>
          <p className="text-xs text-zinc-500 mt-1.5 font-medium tracking-wide">Sign in to Customer Support AI Console</p>
        </div>

        {/* Login Form Card */}
        <div className="bg-zinc-900/50 border border-zinc-800/80 backdrop-blur-xl rounded-2xl p-8 shadow-2xl shadow-black/50">
          
          {error && (
            <div className="mb-6 px-4 py-3 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-start gap-2.5 text-rose-400">
              <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
              <span className="text-xs font-semibold leading-relaxed">{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Email Field */}
            <div className="space-y-2">
              <label htmlFor="email" className="text-xs font-bold text-zinc-400 tracking-wide uppercase px-0.5">Email Address</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-zinc-600">
                  <Mail className="h-4 w-4" />
                </div>
                <input
                  id="email"
                  type="email"
                  required
                  disabled={loading}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-zinc-950/60 border border-zinc-850 rounded-xl py-3 pl-11 pr-4 text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-indigo-500/80 focus:ring-2 focus:ring-indigo-500/10 transition-all disabled:opacity-50"
                  placeholder="name@example.com"
                />
              </div>
            </div>

            {/* Password Field */}
            <div className="space-y-2">
              <label htmlFor="password" className="text-xs font-bold text-zinc-400 tracking-wide uppercase px-0.5">Password</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-zinc-600">
                  <Lock className="h-4 w-4" />
                </div>
                <input
                  id="password"
                  type="password"
                  required
                  disabled={loading}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-zinc-950/60 border border-zinc-850 rounded-xl py-3 pl-11 pr-4 text-sm text-zinc-200 placeholder-zinc-600 focus:outline-none focus:border-indigo-500/80 focus:ring-2 focus:ring-indigo-500/10 transition-all disabled:opacity-50"
                  placeholder="••••••••"
                />
              </div>
            </div>

            {/* Remember & Options */}
            <div className="flex items-center justify-between pt-1">
              <label className="flex items-center gap-2 group cursor-pointer">
                <input 
                  type="checkbox" 
                  disabled={loading}
                  className="h-4 w-4 bg-zinc-950/60 border border-zinc-850 rounded focus:ring-0 text-indigo-500 focus:ring-offset-0 accent-indigo-500" 
                />
                <span className="text-[11px] font-bold text-zinc-500 group-hover:text-zinc-400 transition-colors">Remember Session</span>
              </label>
              <a href="#" className="text-[11px] font-bold text-indigo-400 hover:text-indigo-300 transition-colors">Forgot Password?</a>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gradient-to-r from-indigo-500 to-violet-600 hover:from-indigo-400 hover:to-violet-500 text-white font-bold py-3 px-4 rounded-xl shadow-lg shadow-indigo-500/10 flex items-center justify-center gap-2 transition-all duration-200 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed text-sm mt-2.5 active:scale-[0.98]"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Logging in...</span>
                </>
              ) : (
                <span>Log In</span>
              )}
            </button>
          </form>
        </div>

        {/* Call to Register */}
        <p className="text-center text-xs text-zinc-500 font-medium mt-6">
          {"Don't have an account? "}
          <Link href="/register" className="font-bold text-indigo-400 hover:text-indigo-300 transition-colors">
            Register Here
          </Link>
        </p>

      </div>
    </div>
  );
}
