"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import Navbar from "@/components/layout/Navbar";
import Sidebar from "@/components/layout/Sidebar";
import { api } from "@/services/api";
import {
  TrendingUp, Users, MessageSquare, Clipboard, BookOpen, Cpu, HardDrive,
  Activity, ArrowUpRight, ArrowDownRight, RefreshCw, Calendar, Sparkles,
  CheckCircle, AlertTriangle, ShieldAlert, Clock, BarChart3, Database,
  ArrowRight, ShieldCheck, Compass
} from "lucide-react";

// Types
interface OverviewStats {
  total_users: number;
  active_users: number;
  total_conversations: number;
  total_messages: number;
  total_tickets: number;
  open_tickets: number;
  closed_tickets: number;
  total_documents: number;
  total_administrators: number;
}

interface DailyCount {
  date: string;
  count: number;
}

interface UsageStats {
  conversations_per_day: DailyCount[];
  messages_per_day: DailyCount[];
  new_users_per_day: DailyCount[];
  tickets_per_day: DailyCount[];
}

interface AIStats {
  average_ai_response_time: number;
  average_confidence_score: number;
  intent_distribution: Record<string, number>;
  agent_routing_distribution: Record<string, number>;
  rag_retrieval_count: number;
  gemini_request_count: number;
  failed_ai_requests: number;
  ai_success_rate: number;
}

interface SystemStats {
  database_status: string;
  vector_index_status: string;
  total_embeddings: number;
  startup_time: string;
  api_uptime: number;
  memory_usage?: number;
  cpu_usage?: number;
}

export default function AdminAnalyticsPage() {
  const { currentUser, loading: authLoading } = useAuth();
  const router = useRouter();

  // Guard routing
  useEffect(() => {
    if (!authLoading && (!currentUser || currentUser.role !== "admin")) {
      router.push("/");
    }
  }, [currentUser, authLoading, router]);

  // States
  const [range, setRange] = useState("7d");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [overview, setOverview] = useState<OverviewStats | null>(null);
  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [ai, setAi] = useState<AIStats | null>(null);
  const [system, setSystem] = useState<SystemStats | null>(null);

  // Auto-refresh state
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [refreshIntervalId, setRefreshIntervalId] = useState<NodeJS.Timeout | null>(null);

  const fetchAnalyticsData = async () => {
    setLoading(true);
    setError(null);
    try {
      let params = `?range=${range}`;
      if (startDate && endDate) {
        params = `?start_date=${new Date(startDate).toISOString()}&end_date=${new Date(endDate).toISOString()}`;
      }

      const [resOverview, resUsage, resAi, resSystem] = await Promise.all([
        api.get("/admin/analytics/overview"),
        api.get(`/admin/analytics/usage${params}`),
        api.get(`/admin/analytics/ai${params}`),
        api.get("/admin/analytics/system")
      ]);

      setOverview(resOverview.data);
      setUsage(resUsage.data);
      setAi(resAi.data);
      setSystem(resSystem.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || "Failed to load analytics records.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (currentUser && currentUser.role === "admin") {
      fetchAnalyticsData();
    }
  }, [range, startDate, endDate, currentUser]);

  // Handle auto refresh toggle
  useEffect(() => {
    if (autoRefresh) {
      const id = setInterval(() => {
        fetchAnalyticsData();
      }, 30000); // 30 seconds interval
      setRefreshIntervalId(id);
    } else {
      if (refreshIntervalId) {
        clearInterval(refreshIntervalId);
        setRefreshIntervalId(null);
      }
    }
    return () => {
      if (refreshIntervalId) clearInterval(refreshIntervalId);
    };
  }, [autoRefresh]);

  const handleCustomRangeApply = (e: React.FormEvent) => {
    e.preventDefault();
    if (startDate && endDate) {
      fetchAnalyticsData();
    }
  };

  // Custom SVG line chart component
  const SvgLineChart = ({ data, title, color = "indigo" }: { data: DailyCount[]; title: string; color?: string }) => {
    if (!data || data.length === 0) return <div className="text-center text-zinc-500 py-10">No data points in range</div>;

    const maxVal = Math.max(...data.map(d => d.count), 5);
    const height = 150;
    const width = 500;
    const padding = 25;

    const points = data.map((d, index) => {
      const x = padding + (index / (data.length - 1 || 1)) * (width - padding * 2);
      const y = height - padding - (d.count / maxVal) * (height - padding * 2);
      return { x, y, date: d.date, count: d.count };
    });

    const pathData = points.reduce((acc, p, index) => {
      return index === 0 ? `M ${p.x} ${p.y}` : `${acc} L ${p.x} ${p.y}`;
    }, "");

    const areaPath = points.length > 0 
      ? `${pathData} L ${points[points.length - 1].x} ${height - padding} L ${points[0].x} ${height - padding} Z`
      : "";

    const strokeColors: Record<string, string> = {
      violet: "stroke-violet-500",
      indigo: "stroke-indigo-500",
      emerald: "stroke-emerald-500",
      amber: "stroke-amber-500"
    };

    const fillColors: Record<string, string> = {
      violet: "fill-violet-500/10",
      indigo: "fill-indigo-500/10",
      emerald: "fill-emerald-500/10",
      amber: "fill-amber-500/10"
    };

    const dotColors: Record<string, string> = {
      violet: "fill-violet-600 stroke-white",
      indigo: "fill-indigo-600 stroke-white",
      emerald: "fill-emerald-600 stroke-white",
      amber: "fill-amber-600 stroke-white"
    };

    return (
      <div className="bg-slate-55 dark:bg-slate-950 p-4 rounded-xl border border-slate-200/50 dark:border-slate-800 flex flex-col justify-between">
        <div className="flex justify-between items-center mb-4">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">{title}</span>
          <span className="text-sm font-extrabold text-slate-700 dark:text-slate-200">
            Total: {data.reduce((sum, d) => sum + d.count, 0)}
          </span>
        </div>

        <svg viewBox={`0 0 ${width} ${height}`} className="w-full overflow-visible">
          {/* Grid lines */}
          <line x1={padding} y1={padding} x2={width - padding} y2={padding} stroke="var(--color-slate-200)" className="stroke-slate-200 dark:stroke-slate-850" strokeDasharray="3 3" />
          <line x1={padding} y1={height / 2} x2={width - padding} y2={height / 2} stroke="var(--color-slate-200)" className="stroke-slate-200 dark:stroke-slate-850" strokeDasharray="3 3" />
          <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="var(--color-slate-200)" className="stroke-slate-200 dark:stroke-slate-800" />

          {/* Area fill */}
          {areaPath && <path d={areaPath} className={fillColors[color] || "fill-indigo-500/10"} />}
          
          {/* Stroke path */}
          {pathData && <path d={pathData} fill="none" className={`${strokeColors[color] || "stroke-indigo-500"} stroke-[2.5]`} />}

          {/* Dots & labels */}
          {points.map((p, i) => (
            <g key={i} className="group cursor-pointer">
              <circle cx={p.x} cy={p.y} r="4.5" className={`${dotColors[color] || "fill-indigo-600 stroke-white"} stroke-2 hover:r-6 transition-all`} />
              
              {/* Tooltip Overlay */}
              <g className="opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity duration-150">
                <rect x={Math.max(10, p.x - 45)} y={p.y - 35} width="90" height="25" rx="5" className="fill-slate-900 dark:fill-slate-100" />
                <text x={p.x} y={p.y - 18} textAnchor="middle" className="text-[10px] font-bold fill-white dark:fill-slate-950">
                  {p.count} ({p.date.split("-").slice(1).join("/")})
                </text>
              </g>
            </g>
          ))}
        </svg>
      </div>
    );
  };

  const formatUptime = (seconds: number): string => {
    const d = Math.floor(seconds / (3600 * 24));
    const h = Math.floor((seconds % (3600 * 24)) / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return `${d}d ${h}h ${m}m`;
  };

  if (authLoading || (!currentUser || currentUser.role !== "admin")) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="h-10 w-10 text-violet-600 animate-spin" />
          <span className="text-sm font-medium text-slate-600 dark:text-slate-400">Authenticating access privileges...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col">
      <Navbar />
      <div className="flex flex-1">
        <Sidebar />
        <main className="flex-1 p-6 md:p-8 max-w-7xl mx-auto w-full transition-colors duration-200">
          
          {/* Header */}
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
            <div>
              <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-indigo-600 via-violet-600 to-pink-600 bg-clip-text text-transparent">
                System Analytics Dashboard
              </h1>
              <p className="text-slate-500 dark:text-slate-400 mt-1">
                Real-time usage metrics, AI agent routing, RAG retrievals, and system diagnostics health.
              </p>
            </div>
            
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 px-3 py-1.5 rounded-xl shadow-sm text-xs font-semibold">
                <span className={`h-2.5 w-2.5 rounded-full ${autoRefresh ? "bg-emerald-500 animate-pulse" : "bg-slate-400"}`} />
                Auto Refresh (30s)
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                  className="ml-1 cursor-pointer h-4 w-4 accent-violet-600"
                />
              </div>

              <button
                onClick={fetchAnalyticsData}
                disabled={loading}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-850 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-xl text-xs font-bold flex items-center gap-2 transition-all disabled:opacity-50"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
                Refresh
              </button>
            </div>
          </div>

          {error && (
            <div className="bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900/50 text-red-700 dark:text-red-400 p-4 rounded-xl mb-6 flex gap-3 items-center">
              <ShieldAlert className="h-5 w-5 flex-shrink-0" />
              <span className="text-sm font-medium">{error}</span>
            </div>
          )}

          {/* Quick Filters */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-4 mb-8 shadow-sm flex flex-col md:flex-row gap-4 items-stretch md:items-center justify-between">
            <div className="flex flex-wrap gap-1.5">
              {[
                { label: "Today", value: "today" },
                { label: "Last 7 Days", value: "7d" },
                { label: "Last 30 Days", value: "30d" },
                { label: "Last 90 Days", value: "90d" }
              ].map(btn => (
                <button
                  key={btn.value}
                  onClick={() => {
                    setStartDate("");
                    setEndDate("");
                    setRange(btn.value);
                  }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                    range === btn.value && !startDate
                      ? "bg-violet-600 text-white shadow-sm"
                      : "bg-slate-50 dark:bg-slate-950 hover:bg-slate-100 dark:hover:bg-slate-850 text-slate-650 dark:text-slate-350"
                  }`}
                >
                  {btn.label}
                </button>
              ))}
            </div>

            <form onSubmit={handleCustomRangeApply} className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400 font-bold uppercase tracking-wider">Custom</span>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="px-2.5 py-1.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-medium focus:outline-none focus:ring-1 focus:ring-violet-600"
                />
                <span className="text-xs text-slate-400 font-medium">to</span>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="px-2.5 py-1.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg text-xs font-medium focus:outline-none focus:ring-1 focus:ring-violet-600"
                />
              </div>
              <button
                type="submit"
                disabled={!startDate || !endDate}
                className="px-3.5 py-1.5 bg-violet-600 hover:bg-violet-750 text-white rounded-lg text-xs font-bold disabled:opacity-40 transition-all"
              >
                Apply
              </button>
            </form>
          </div>

          {loading && !overview ? (
            <div className="py-24 flex flex-col items-center gap-3">
              <RefreshCw className="h-10 w-10 text-violet-600 animate-spin" />
              <span className="text-sm font-medium text-slate-400">Loading system metrics parameters...</span>
            </div>
          ) : (
            <>
              {/* Overview grid cards */}
              {overview && (
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                  <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm flex items-center justify-between">
                    <div>
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Total Users</span>
                      <h3 className="text-2xl font-black mt-1.5">{overview.total_users}</h3>
                      <span className="text-[10px] font-bold text-slate-400 mt-1 block">Active: {overview.active_users}</span>
                    </div>
                    <div className="h-11 w-11 rounded-xl bg-indigo-50 dark:bg-indigo-950/20 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
                      <Users className="h-5 w-5" />
                    </div>
                  </div>

                  <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm flex items-center justify-between">
                    <div>
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Conversations</span>
                      <h3 className="text-2xl font-black mt-1.5">{overview.total_conversations}</h3>
                      <span className="text-[10px] font-bold text-slate-400 mt-1 block">Messages: {overview.total_messages}</span>
                    </div>
                    <div className="h-11 w-11 rounded-xl bg-violet-50 dark:bg-violet-950/20 text-violet-600 dark:text-violet-400 flex items-center justify-center">
                      <MessageSquare className="h-5 w-5" />
                    </div>
                  </div>

                  <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm flex items-center justify-between">
                    <div>
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Total Tickets</span>
                      <h3 className="text-2xl font-black mt-1.5">{overview.total_tickets}</h3>
                      <div className="flex gap-2 mt-1">
                        <span className="text-[10px] font-bold text-amber-500">Open: {overview.open_tickets}</span>
                        <span className="text-[10px] font-bold text-emerald-500">Closed: {overview.closed_tickets}</span>
                      </div>
                    </div>
                    <div className="h-11 w-11 rounded-xl bg-amber-50 dark:bg-amber-950/20 text-amber-650 dark:text-amber-400 flex items-center justify-center">
                      <Clipboard className="h-5 w-5" />
                    </div>
                  </div>

                  <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 rounded-2xl shadow-sm flex items-center justify-between">
                    <div>
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Knowledge Docs</span>
                      <h3 className="text-2xl font-black mt-1.5">{overview.total_documents}</h3>
                      <span className="text-[10px] font-bold text-slate-400 mt-1 block">Vector Embeddings</span>
                    </div>
                    <div className="h-11 w-11 rounded-xl bg-emerald-50 dark:bg-emerald-950/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
                      <BookOpen className="h-5 w-5" />
                    </div>
                  </div>
                </div>
              )}

              {/* Usage Charts Section */}
              {usage && (
                <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm mb-8">
                  <h2 className="text-lg font-extrabold flex items-center gap-2 border-b border-slate-100 dark:border-slate-800 pb-4 mb-6">
                    <TrendingUp className="h-5 w-5 text-indigo-500" />
                    Customer Service Usage Trends
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <SvgLineChart data={usage.conversations_per_day} title="Daily Conversations Created" color="violet" />
                    <SvgLineChart data={usage.messages_per_day} title="Daily Message volume" color="indigo" />
                    <SvgLineChart data={usage.tickets_per_day} title="Daily Support Tickets Opened" color="amber" />
                    <SvgLineChart data={usage.new_users_per_day} title="New Registrations" color="emerald" />
                  </div>
                </div>
              )}

              {/* AI performance stats and charts */}
              {ai && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
                  
                  {/* AI KPIs Card */}
                  <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm lg:col-span-1">
                    <h2 className="text-lg font-extrabold flex items-center gap-2 border-b border-slate-100 dark:border-slate-800 pb-4 mb-5">
                      <Cpu className="h-5 w-5 text-violet-500" />
                      AI Performance KPIs
                    </h2>
                    <div className="space-y-4">
                      <div className="flex justify-between items-center py-2 border-b border-slate-50 dark:border-slate-850">
                        <span className="text-xs text-slate-400 font-bold uppercase tracking-wider">Avg Response Time</span>
                        <span className="text-sm font-bold flex items-center gap-1.5">
                          <Clock className="h-4 w-4 text-violet-500" />
                          {ai.average_ai_response_time}s
                        </span>
                      </div>
                      <div className="flex justify-between items-center py-2 border-b border-slate-50 dark:border-slate-850">
                        <span className="text-xs text-slate-400 font-bold uppercase tracking-wider">Avg Confidence Score</span>
                        <span className="text-sm font-bold flex items-center gap-1.5">
                          <Sparkles className="h-4 w-4 text-indigo-500" />
                          {Math.round(ai.average_confidence_score * 100)}%
                        </span>
                      </div>
                      <div className="flex justify-between items-center py-2 border-b border-slate-50 dark:border-slate-850">
                        <span className="text-xs text-slate-400 font-bold uppercase tracking-wider">Gemini Request Count</span>
                        <span className="text-sm font-semibold">{ai.gemini_request_count}</span>
                      </div>
                      <div className="flex justify-between items-center py-2 border-b border-slate-50 dark:border-slate-850">
                        <span className="text-xs text-slate-400 font-bold uppercase tracking-wider">RAG Retrieval Count</span>
                        <span className="text-sm font-semibold text-emerald-600 dark:text-emerald-400">{ai.rag_retrieval_count}</span>
                      </div>
                      <div className="flex justify-between items-center py-2 border-b border-slate-50 dark:border-slate-850">
                        <span className="text-xs text-slate-400 font-bold uppercase tracking-wider">Failed AI Requests</span>
                        <span className="text-sm font-semibold text-red-500">{ai.failed_ai_requests}</span>
                      </div>
                      <div className="flex justify-between items-center py-2">
                        <span className="text-xs text-slate-400 font-bold uppercase tracking-wider">AI Success Rate</span>
                        <span className="text-sm font-extrabold text-emerald-600 dark:text-emerald-400">
                          {Math.round(ai.ai_success_rate * 10000) / 100}%
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Intent Distribution */}
                  <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm lg:col-span-1">
                    <h2 className="text-lg font-extrabold flex items-center gap-2 border-b border-slate-100 dark:border-slate-800 pb-4 mb-5">
                      <BarChart3 className="h-5 w-5 text-indigo-500" />
                      Intent distribution
                    </h2>
                    
                    {Object.keys(ai.intent_distribution).length === 0 ? (
                      <div className="text-center text-zinc-550 py-12 text-sm">No intent messages parsed.</div>
                    ) : (
                      <div className="space-y-4">
                        {Object.entries(ai.intent_distribution).map(([key, val]) => {
                          const total = Object.values(ai.intent_distribution).reduce((a, b) => a + b, 0);
                          const pct = Math.round((val / total) * 100);
                          return (
                            <div key={key}>
                              <div className="flex justify-between text-xs font-bold mb-1">
                                <span className="uppercase text-slate-500">{key}</span>
                                <span>{val} ({pct}%)</span>
                              </div>
                              <div className="w-full h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                                <div 
                                  className="h-full rounded-full bg-gradient-to-r from-violet-500 to-indigo-500" 
                                  style={{ width: `${pct}%` }}
                                />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  {/* Agent routing maps */}
                  <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm lg:col-span-1">
                    <h2 className="text-lg font-extrabold flex items-center gap-2 border-b border-slate-100 dark:border-slate-800 pb-4 mb-5">
                      <Compass className="h-5 w-5 text-emerald-500" />
                      Agent Routing maps
                    </h2>
                    
                    {Object.keys(ai.agent_routing_distribution).length === 0 ? (
                      <div className="text-center text-zinc-550 py-12 text-sm">No agent routes resolved.</div>
                    ) : (
                      <div className="space-y-4">
                        {Object.entries(ai.agent_routing_distribution).map(([key, val]) => {
                          const total = Object.values(ai.agent_routing_distribution).reduce((a, b) => a + b, 0);
                          const pct = Math.round((val / total) * 100);
                          return (
                            <div key={key}>
                              <div className="flex justify-between text-xs font-bold mb-1">
                                <span className="text-slate-500">{key}</span>
                                <span>{val} ({pct}%)</span>
                              </div>
                              <div className="w-full h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                                <div 
                                  className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-500" 
                                  style={{ width: `${pct}%` }}
                                />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>

                </div>
              )}

              {/* System Diagnostics Status */}
              {system && (
                <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-6 shadow-sm">
                  <h2 className="text-lg font-extrabold flex items-center gap-2 border-b border-slate-100 dark:border-slate-800 pb-4 mb-6">
                    <Activity className="h-5 w-5 text-indigo-500" />
                    System Diagnostics & Health
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    
                    {/* Database Health */}
                    <div className="bg-slate-55 dark:bg-slate-950 p-4 rounded-xl border border-slate-200/50 dark:border-slate-800 flex items-center justify-between">
                      <div>
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Database Status</span>
                        <h4 className="text-base font-extrabold mt-1 uppercase text-slate-700 dark:text-slate-200">{system.database_status}</h4>
                      </div>
                      <div className={`h-8 w-8 rounded-full flex items-center justify-center ${
                        system.database_status === "connected" ? "bg-emerald-55 text-emerald-600" : "bg-red-50 text-red-500"
                      }`}>
                        {system.database_status === "connected" ? <ShieldCheck className="h-5 w-5" /> : <ShieldAlert className="h-5 w-5" />}
                      </div>
                    </div>

                    {/* Vector Store Health */}
                    <div className="bg-slate-55 dark:bg-slate-950 p-4 rounded-xl border border-slate-200/50 dark:border-slate-800 flex items-center justify-between">
                      <div>
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Vector Index (FAISS)</span>
                        <h4 className="text-base font-extrabold mt-1 text-slate-700 dark:text-slate-200">{system.total_embeddings} vectors</h4>
                      </div>
                      <div className="h-8 w-8 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center">
                        <Database className="h-4 w-4" />
                      </div>
                    </div>

                    {/* API Uptime */}
                    <div className="bg-slate-55 dark:bg-slate-950 p-4 rounded-xl border border-slate-200/50 dark:border-slate-800 flex items-center justify-between">
                      <div>
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">API Uptime</span>
                        <h4 className="text-base font-extrabold mt-1 text-slate-700 dark:text-slate-200">{formatUptime(system.api_uptime)}</h4>
                      </div>
                      <div className="h-8 w-8 rounded-full bg-violet-50 text-violet-600 flex items-center justify-center">
                        <Clock className="h-4 w-4" />
                      </div>
                    </div>

                    {/* System Host Metrics */}
                    <div className="bg-slate-55 dark:bg-slate-950 p-4 rounded-xl border border-slate-200/50 dark:border-slate-800">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Host Hardware Health</span>
                      <div className="flex flex-col gap-1.5 mt-2">
                        {system.cpu_usage !== undefined && system.cpu_usage !== null && (
                          <div className="flex justify-between text-xs font-semibold text-slate-650 dark:text-slate-350">
                            <span>CPU</span>
                            <span>{system.cpu_usage}%</span>
                          </div>
                        )}
                        {system.memory_usage !== undefined && system.memory_usage !== null && (
                          <div className="flex justify-between text-xs font-semibold text-slate-650 dark:text-slate-350">
                            <span>Memory</span>
                            <span>{system.memory_usage}%</span>
                          </div>
                        )}
                        {system.cpu_usage === undefined && (
                          <span className="text-xs text-slate-400">No CPU/Memory metrics available.</span>
                        )}
                      </div>
                    </div>

                  </div>
                </div>
              )}
            </>
          )}

        </main>
      </div>
    </div>
  );
}
