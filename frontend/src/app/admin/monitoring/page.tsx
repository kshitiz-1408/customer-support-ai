"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import Navbar from "@/components/layout/Navbar";
import Sidebar from "@/components/layout/Sidebar";
import { api } from "@/services/api";
import { 
  Activity, Database, Cpu, HardDrive, WifiOff, RefreshCw, 
  AlertCircle, CheckCircle2, Clock, Sparkles, Server, Network
} from "lucide-react";

interface ServiceStatus {
  status: string;
  last_check: string;
  response_time: number;
  error?: string | null;
}

interface ServicesData {
  mongodb: ServiceStatus;
  gemini: ServiceStatus;
  embeddings: ServiceStatus;
  vector_store: ServiceStatus;
  background_services: ServiceStatus;
}

interface HealthData {
  overall_status: string;
  backend_status: string;
  frontend_status: string;
  database_status: string;
  gemini_status: string;
  rag_status: string;
  vector_index_status: string;
  uptime: number;
  version: string;
}

interface PerformanceData {
  average_response_time: number;
  requests_per_minute: number;
  active_users: number;
  active_conversations: number;
  memory_usage: number;
  cpu_usage: number;
  startup_duration: number;
  database_latency: number;
}

export default function AdminMonitoringPage() {
  const { currentUser, loading: authLoading } = useAuth();
  const router = useRouter();

  // Guard routing
  useEffect(() => {
    if (!authLoading && (!currentUser || currentUser.role !== "admin")) {
      router.push("/");
    }
  }, [currentUser, authLoading, router]);

  // States
  const [health, setHealth] = useState<HealthData | null>(null);
  const [performance, setPerformance] = useState<PerformanceData | null>(null);
  const [services, setServices] = useState<ServicesData | null>(null);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [isOnline, setIsOnline] = useState(() => typeof window !== "undefined" ? navigator.onLine : true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const autoRefreshIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Network connection status
  useEffect(() => {
    if (typeof window !== "undefined") {
      const handleOnline = () => setIsOnline(true);
      const handleOffline = () => setIsOnline(false);
      window.addEventListener("online", handleOnline);
      window.addEventListener("offline", handleOffline);
      return () => {
        window.removeEventListener("online", handleOnline);
        window.removeEventListener("offline", handleOffline);
      };
    }
  }, []);

  const fetchData = useCallback(async () => {
    if (!currentUser || currentUser.role !== "admin") return;
    setLoading(true);
    setError(null);
    try {
      const [resHealth, resPerf, resServ] = await Promise.all([
        api.get("/admin/system/health"),
        api.get("/admin/system/performance"),
        api.get("/admin/system/services")
      ]);
      setHealth(resHealth.data);
      setPerformance(resPerf.data);
      setServices(resServ.data);
      setLastUpdated(new Date());
    } catch (err: unknown) {
      const errorObj = err as { message?: string };
      setError(errorObj.message || "Failed to load system diagnostics.");
    } finally {
      setLoading(false);
    }
  }, [currentUser]);

  useEffect(() => {
    void (async () => {
      await Promise.resolve();
      fetchData();
    })();
  }, [fetchData]);

  // Auto-refresh configuration (every 30 seconds)
  useEffect(() => {
    if (autoRefresh && currentUser && currentUser.role === "admin") {
      autoRefreshIntervalRef.current = setInterval(() => {
        fetchData();
      }, 30000);
    }
    return () => {
      if (autoRefreshIntervalRef.current) {
        clearInterval(autoRefreshIntervalRef.current);
      }
    };
  }, [autoRefresh, currentUser, fetchData]);

  const handleManualRefresh = () => {
    fetchData();
  };

  // Helper formatting uptime (seconds -> d h m s)
  const formatUptime = (seconds: number) => {
    const d = Math.floor(seconds / (3600 * 24));
    const h = Math.floor((seconds % (3600 * 24)) / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    
    const parts = [];
    if (d > 0) parts.push(`${d}d`);
    if (h > 0) parts.push(`${h}h`);
    if (m > 0) parts.push(`${m}m`);
    parts.push(`${s}s`);
    return parts.join(" ");
  };

  if (authLoading || !currentUser || currentUser.role !== "admin") {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  // Get status color mappings
  const getStatusBadge = (status: string) => {
    const lower = status ? status.toLowerCase() : "";
    if (lower === "healthy" || lower === "loaded" || lower === "connected" || lower === "ok") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-950/30 text-emerald-400 border border-emerald-900/40">
          <CheckCircle2 className="h-3 w-3" />
          Healthy
        </span>
      );
    } else if (lower === "warning" || lower === "empty") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-950/30 text-amber-400 border border-amber-900/40">
          <AlertCircle className="h-3 w-3" />
          Warning
        </span>
      );
    } else {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-950/30 text-red-400 border border-red-900/40">
          <AlertCircle className="h-3 w-3" />
          Critical
        </span>
      );
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Navbar />
      
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        
        <main className="flex-1 overflow-y-auto p-6 md:p-8 space-y-8">
          
          {/* Offline Banner */}
          {!isOnline && (
            <div className="bg-amber-950/50 border border-amber-900/60 rounded-xl p-4 flex items-center gap-3">
              <WifiOff className="h-5 w-5 text-amber-400 shrink-0" />
              <div>
                <p className="text-sm font-semibold text-amber-200">System is Offline</p>
                <p className="text-xs text-amber-400 mt-0.5">Please check your internet connection. Automatic updates are suspended.</p>
              </div>
            </div>
          )}

          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-5">
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
                <Activity className="h-8 w-8 text-indigo-500" />
                System Health & Monitoring
              </h1>
              <p className="text-slate-400 mt-1">
                Real-time visibility into microservices state, infrastructure load, and AI pipeline status.
              </p>
            </div>
            
            <div className="flex flex-wrap items-center gap-4">
              {/* Last Checked Tracers */}
              {lastUpdated && (
                <div className="text-xs text-slate-500 flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" />
                  Last check: {lastUpdated.toLocaleTimeString()}
                </div>
              )}

              {/* Auto Refresh Toggle */}
              <label className="flex items-center gap-2 bg-slate-900 border border-slate-800 px-3 py-2 rounded-lg text-sm text-slate-300 select-none cursor-pointer hover:bg-slate-850 transition">
                <input 
                  type="checkbox" 
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                  className="rounded bg-slate-950 border-slate-800 text-indigo-600 focus:ring-indigo-500 focus:ring-offset-slate-900" 
                />
                Auto-Refresh (30s)
              </label>

              {/* Manual Refresh */}
              <button
                onClick={handleManualRefresh}
                disabled={loading}
                className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm font-medium transition duration-200"
              >
                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                Refresh Status
              </button>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-950/40 border border-red-900/60 rounded-xl p-4 flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-500 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-red-200">Retrieval Failure</p>
                <p className="text-xs text-red-400 mt-1">{error}</p>
              </div>
            </div>
          )}

          {/* Summary Health Alert Card */}
          {health && (
            <div className={`p-5 rounded-xl border flex flex-col md:flex-row items-start md:items-center justify-between gap-4 backdrop-blur-md transition ${
              health.overall_status === 'healthy' 
                ? 'bg-emerald-950/10 border-emerald-900/40' 
                : health.overall_status === 'warning' 
                ? 'bg-amber-950/10 border-amber-900/40'
                : 'bg-red-950/10 border-red-900/40'
            }`}>
              <div className="flex items-center gap-4">
                <div className={`p-3 rounded-lg ${
                  health.overall_status === 'healthy' 
                    ? 'bg-emerald-500/10 text-emerald-400' 
                    : health.overall_status === 'warning' 
                    ? 'bg-amber-500/10 text-amber-400'
                    : 'bg-red-500/10 text-red-400'
                }`}>
                  <Server className="h-6 w-6" />
                </div>
                <div>
                  <h2 className="text-lg font-bold text-white flex items-center gap-2">
                    Overall Status: <span className="capitalize">{health.overall_status}</span>
                  </h2>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Uptime: <span className="text-slate-200 font-medium">{formatUptime(health.uptime)}</span> | API Version: <span className="text-slate-200 font-mono">{health.version}</span>
                  </p>
                </div>
              </div>
              <div className="flex flex-wrap gap-2.5">
                <span className="text-xs bg-slate-900 border border-slate-800 text-slate-300 px-3 py-1.5 rounded-lg">
                  Backend: <span className="text-emerald-400 font-semibold uppercase">{health.backend_status}</span>
                </span>
                <span className="text-xs bg-slate-900 border border-slate-800 text-slate-300 px-3 py-1.5 rounded-lg">
                  Database: <span className={health.database_status === 'healthy' ? 'text-emerald-400 font-semibold uppercase' : 'text-red-400 font-semibold uppercase'}>{health.database_status}</span>
                </span>
                <span className="text-xs bg-slate-900 border border-slate-800 text-slate-300 px-3 py-1.5 rounded-lg">
                  Gemini API: <span className={health.gemini_status === 'healthy' ? 'text-emerald-400 font-semibold uppercase' : 'text-red-400 font-semibold uppercase'}>{health.gemini_status}</span>
                </span>
              </div>
            </div>
          )}

          {/* Performance KPIs Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            
            {/* CPU Usage Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 relative overflow-hidden group hover:border-slate-700 transition">
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">CPU Usage</p>
                  <p className="text-3xl font-extrabold text-white mt-2">
                    {performance ? `${performance.cpu_usage}%` : "0%"}
                  </p>
                </div>
                <div className="p-2.5 bg-slate-950 rounded-lg text-indigo-400">
                  <Cpu className="h-5 w-5" />
                </div>
              </div>
              <div className="mt-4 w-full bg-slate-950 rounded-full h-1.5 overflow-hidden">
                <div 
                  className="bg-indigo-500 h-full transition-all duration-500" 
                  style={{ width: `${performance ? performance.cpu_usage : 0}%` }}
                ></div>
              </div>
            </div>

            {/* Memory Usage Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 relative overflow-hidden group hover:border-slate-700 transition">
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Memory Usage</p>
                  <p className="text-3xl font-extrabold text-white mt-2">
                    {performance ? `${performance.memory_usage}%` : "0%"}
                  </p>
                </div>
                <div className="p-2.5 bg-slate-950 rounded-lg text-emerald-400">
                  <HardDrive className="h-5 w-5" />
                </div>
              </div>
              <div className="mt-4 w-full bg-slate-950 rounded-full h-1.5 overflow-hidden">
                <div 
                  className="bg-emerald-500 h-full transition-all duration-500" 
                  style={{ width: `${performance ? performance.memory_usage : 0}%` }}
                ></div>
              </div>
            </div>

            {/* Active Operations Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 relative overflow-hidden group hover:border-slate-700 transition">
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Platform Load</p>
                  <p className="text-2xl font-bold text-white mt-2">
                    {performance ? `${performance.active_users} Users` : "0 Users"}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    {performance ? `${performance.active_conversations} Active Chats` : "0 Active Chats"}
                  </p>
                </div>
                <div className="p-2.5 bg-slate-950 rounded-lg text-pink-400">
                  <Network className="h-5 w-5" />
                </div>
              </div>
            </div>

            {/* AI Response Speed Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 relative overflow-hidden group hover:border-slate-700 transition">
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">AI Latency</p>
                  <p className="text-3xl font-extrabold text-white mt-2">
                    {performance ? `${performance.average_response_time}s` : "0.0s"}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    {performance ? `${performance.requests_per_minute} req/min` : "0.0 req/min"}
                  </p>
                </div>
                <div className="p-2.5 bg-slate-950 rounded-lg text-amber-400">
                  <Sparkles className="h-5 w-5" />
                </div>
              </div>
            </div>

          </div>

          {/* Secondary Diagnostics Stats */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            
            {/* Database Latency */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-slate-950 text-indigo-400 rounded-lg">
                  <Database className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">DB Latency</p>
                  <p className="text-xl font-bold text-white mt-1">
                    {performance ? `${performance.database_latency} ms` : "0.0 ms"}
                  </p>
                </div>
              </div>
              <span className="text-xs text-slate-650">Lightweight ping</span>
            </div>

            {/* Application Startup Timings */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-slate-950 text-emerald-400 rounded-lg">
                  <Clock className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Startup timings</p>
                  <p className="text-xl font-bold text-white mt-1">
                    {performance ? `${(performance.startup_duration / 1000).toFixed(2)}s` : "0.00s"}
                  </p>
                </div>
              </div>
              <span className="text-xs text-slate-650">Lifespan prewarm</span>
            </div>

            {/* Vector Store Size */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-slate-950 text-pink-400 rounded-lg">
                  <HardDrive className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">FAISS Vector Index</p>
                  <p className="text-xl font-bold text-white mt-1">
                    {health ? `${health.vector_index_status}` : "empty"}
                  </p>
                </div>
              </div>
              <span className="text-xs text-slate-650">Status Check</span>
            </div>

          </div>

          {/* Microservices Details Card */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl">
            <div className="p-5 border-b border-slate-800 bg-slate-950/40 flex justify-between items-center">
              <div>
                <h3 className="text-lg font-bold text-white">Component Microservices Status</h3>
                <p className="text-xs text-slate-400 mt-1">Breakdown checklist of all internal database, embedding models, and generative APIs.</p>
              </div>
            </div>
            
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-950/60">
                    <th className="p-4 text-xs font-bold text-slate-400 uppercase tracking-wider">Service Name</th>
                    <th className="p-4 text-xs font-bold text-slate-400 uppercase tracking-wider">Status</th>
                    <th className="p-4 text-xs font-bold text-slate-400 uppercase tracking-wider font-mono">Response Time (ms)</th>
                    <th className="p-4 text-xs font-bold text-slate-400 uppercase tracking-wider">Last Check Time</th>
                    <th className="p-4 text-xs font-bold text-slate-400 uppercase tracking-wider">Diagnostic Errors / Metadata</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80">
                  {loading && !services ? (
                    <tr>
                      <td colSpan={5} className="p-8 text-center text-slate-500 text-sm">
                        <div className="flex items-center justify-center gap-2">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-500"></div>
                          Checking service availability...
                        </div>
                      </td>
                    </tr>
                  ) : !services ? (
                    <tr>
                      <td colSpan={5} className="p-8 text-center text-slate-500 text-sm">
                        No service status data returned from backend diagnostics api.
                      </td>
                    </tr>
                  ) : (
                    <>
                      {/* MongoDB */}
                      <tr className="hover:bg-slate-800/30 transition duration-150">
                        <td className="p-4 text-sm font-semibold text-white flex items-center gap-2">
                          <Database className="h-4 w-4 text-indigo-400" />
                          MongoDB Atlas
                        </td>
                        <td className="p-4 text-sm">{getStatusBadge(services.mongodb.status)}</td>
                        <td className="p-4 text-sm font-mono">{services.mongodb.response_time} ms</td>
                        <td className="p-4 text-xs text-slate-500">{new Date(services.mongodb.last_check).toLocaleString()}</td>
                        <td className="p-4 text-sm">
                          {services.mongodb.error ? (
                            <span className="text-red-400 font-medium text-xs break-all">{services.mongodb.error}</span>
                          ) : (
                            <span className="text-slate-500 italic text-xs">Connection initialized and operational.</span>
                          )}
                        </td>
                      </tr>

                      {/* Gemini API */}
                      <tr className="hover:bg-slate-800/30 transition duration-150">
                        <td className="p-4 text-sm font-semibold text-white flex items-center gap-2">
                          <Sparkles className="h-4 w-4 text-amber-400" />
                          Google Gemini LLM
                        </td>
                        <td className="p-4 text-sm">{getStatusBadge(services.gemini.status)}</td>
                        <td className="p-4 text-sm font-mono">{services.gemini.response_time} ms</td>
                        <td className="p-4 text-xs text-slate-500">{new Date(services.gemini.last_check).toLocaleString()}</td>
                        <td className="p-4 text-sm">
                          {services.gemini.error ? (
                            <span className="text-red-400 font-medium text-xs break-all">{services.gemini.error}</span>
                          ) : (
                            <span className="text-slate-500 italic text-xs">SDK Client initialized and ready.</span>
                          )}
                        </td>
                      </tr>

                      {/* Embeddings model */}
                      <tr className="hover:bg-slate-800/30 transition duration-150">
                        <td className="p-4 text-sm font-semibold text-white flex items-center gap-2">
                          <Cpu className="h-4 w-4 text-emerald-400" />
                          SentenceTransformers Model
                        </td>
                        <td className="p-4 text-sm">{getStatusBadge(services.embeddings.status)}</td>
                        <td className="p-4 text-sm font-mono">{services.embeddings.response_time} ms</td>
                        <td className="p-4 text-xs text-slate-500">{new Date(services.embeddings.last_check).toLocaleString()}</td>
                        <td className="p-4 text-sm">
                          {services.embeddings.error ? (
                            <span className="text-red-400 font-medium text-xs break-all">{services.embeddings.error}</span>
                          ) : (
                            <span className="text-slate-500 italic text-xs">In-memory model loaded successfully.</span>
                          )}
                        </td>
                      </tr>

                      {/* Vector store */}
                      <tr className="hover:bg-slate-800/30 transition duration-150">
                        <td className="p-4 text-sm font-semibold text-white flex items-center gap-2">
                          <HardDrive className="h-4 w-4 text-pink-400" />
                          FAISS Vector Store
                        </td>
                        <td className="p-4 text-sm">{getStatusBadge(services.vector_store.status)}</td>
                        <td className="p-4 text-sm font-mono">{services.vector_store.response_time} ms</td>
                        <td className="p-4 text-xs text-slate-500">{new Date(services.vector_store.last_check).toLocaleString()}</td>
                        <td className="p-4 text-sm">
                          {services.vector_store.error ? (
                            <span className="text-red-400 font-medium text-xs break-all">{services.vector_store.error}</span>
                          ) : (
                            <span className="text-slate-500 italic text-xs">Memory indices mapped successfully.</span>
                          )}
                        </td>
                      </tr>

                      {/* Background services */}
                      <tr className="hover:bg-slate-800/30 transition duration-150">
                        <td className="p-4 text-sm font-semibold text-white flex items-center gap-2">
                          <Activity className="h-4 w-4 text-indigo-400" />
                          Document Pipeline Orchestrator
                        </td>
                        <td className="p-4 text-sm">{getStatusBadge(services.background_services.status)}</td>
                        <td className="p-4 text-sm font-mono">-</td>
                        <td className="p-4 text-xs text-slate-500">{new Date(services.background_services.last_check).toLocaleString()}</td>
                        <td className="p-4 text-sm">
                          {services.background_services.error ? (
                            <span className="text-red-400 font-medium text-xs break-all">{services.background_services.error}</span>
                          ) : (
                            <span className="text-slate-500 italic text-xs">Background reindexing and loading engine is active.</span>
                          )}
                        </td>
                      </tr>
                    </>
                  )}
                </tbody>
              </table>
            </div>

          </div>

        </main>
      </div>

    </div>
  );
}
