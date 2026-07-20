"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import Navbar from "@/components/layout/Navbar";
import Sidebar from "@/components/layout/Sidebar";
import { api } from "@/services/api";
import { 
  Search, ChevronLeft, ChevronRight, X, ShieldAlert,
  Calendar, CheckCircle2, AlertCircle, Info, RefreshCw, Eye
} from "lucide-react";

interface AuditLog {
  audit_id: string;
  timestamp: string;
  actor_user_id?: string;
  actor_email?: string;
  actor_role?: string;
  action: string;
  resource_type: string;
  resource_id: string;
  target_user_id?: string;
  target_email?: string;
  status: string;
  ip_address?: string;
  user_agent?: string;
  previous_value?: unknown;
  new_value?: unknown;
  additional_metadata?: Record<string, unknown>;
}

export default function AdminAuditLogsPage() {
  const { currentUser, loading: authLoading } = useAuth();
  const router = useRouter();

  // Guard routing
  useEffect(() => {
    if (!authLoading && (!currentUser || currentUser.role !== "admin")) {
      router.push("/");
    }
  }, [currentUser, authLoading, router]);

  // Page States
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(10);
  
  // Search & Filters
  const [search, setSearch] = useState("");
  const [actionFilter, setActionFilter] = useState("");
  const [actorFilter, setActorFilter] = useState("");
  const [targetFilter, setTargetFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Drawer States
  const [selectedLogId, setSelectedLogId] = useState<string | null>(null);
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [drawerError, setDrawerError] = useState<string | null>(null);

  const fetchLogs = useCallback(async () => {
    if (!currentUser || currentUser.role !== "admin") return;
    setLoading(true);
    setError(null);
    try {
      let url = `/admin/audit?page=${page}&limit=${limit}`;
      if (search.trim()) url += `&search=${encodeURIComponent(search)}`;
      if (actionFilter) url += `&action=${actionFilter}`;
      if (actorFilter.trim()) url += `&actor=${encodeURIComponent(actorFilter)}`;
      if (targetFilter.trim()) url += `&target_user=${encodeURIComponent(targetFilter)}`;
      if (statusFilter) url += `&status=${statusFilter}`;
      
      if (startDate) {
        url += `&start_date=${new Date(startDate).toISOString()}`;
      }
      if (endDate) {
        url += `&end_date=${new Date(endDate).toISOString()}`;
      }

      const res = await api.get(url);
      setLogs(res.data.logs);
      setTotal(res.data.total);
    } catch (err: unknown) {
      const errorObj = err as { message?: string };
      setError(errorObj.message || "Failed to load audit logs.");
    } finally {
      setLoading(false);
    }
  }, [currentUser, page, limit, search, actionFilter, actorFilter, targetFilter, statusFilter, startDate, endDate]);

  useEffect(() => {
    void (async () => {
      await Promise.resolve();
      fetchLogs();
    })();
  }, [fetchLogs]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchLogs();
  };

  const handleClearFilters = () => {
    setSearch("");
    setActionFilter("");
    setActorFilter("");
    setTargetFilter("");
    setStatusFilter("");
    setStartDate("");
    setEndDate("");
    setPage(1);
  };

  // Open Log specifications details drawer
  const handleOpenDrawer = async (logId: string) => {
    setSelectedLogId(logId);
    setDrawerLoading(true);
    setDrawerError(null);
    try {
      const res = await api.get(`/admin/audit/${logId}`);
      setSelectedLog(res.data);
    } catch (err: unknown) {
      const errorObj = err as { message?: string };
      setDrawerError(errorObj.message || "Failed to retrieve audit log specs details.");
    } finally {
      setDrawerLoading(false);
    }
  };

  const handleCloseDrawer = () => {
    setSelectedLogId(null);
    setSelectedLog(null);
  };

  if (authLoading || !currentUser || currentUser.role !== "admin") {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Navbar />
      
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        
        <main className="flex-1 overflow-y-auto p-6 md:p-8 space-y-8">
          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-800 pb-5">
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
                <ShieldAlert className="h-8 w-8 text-indigo-500" />
                Audit Logs Explorer
              </h1>
              <p className="text-slate-400 mt-1">
                Audit system events, administrative privileges, database changes, and access records.
              </p>
            </div>
            <button
              onClick={() => fetchLogs()}
              disabled={loading}
              className="self-start md:self-auto flex items-center gap-2 bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-200 px-4 py-2 rounded-lg text-sm font-medium transition duration-200"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh Logs
            </button>
          </div>

          {/* Search and Filters */}
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-5 space-y-4 backdrop-blur-md">
            <form onSubmit={handleSearchSubmit} className="flex flex-col lg:flex-row gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-3 h-4.5 w-4.5 text-slate-500" />
                <input
                  type="text"
                  placeholder="Global search logs (email, action, status, IDs)..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-10 pr-4 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition duration-200"
                />
              </div>
              <div className="flex flex-wrap gap-3">
                <button
                  type="submit"
                  className="bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-5 py-2.5 rounded-lg transition duration-200"
                >
                  Search
                </button>
                <button
                  type="button"
                  onClick={handleClearFilters}
                  className="bg-slate-950 border border-slate-800 hover:bg-slate-900 text-slate-300 text-sm font-medium px-5 py-2.5 rounded-lg transition duration-200"
                >
                  Clear Filters
                </button>
              </div>
            </form>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 pt-2">
              {/* Action Filter */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Action</label>
                <select
                  value={actionFilter}
                  onChange={(e) => setActionFilter(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  <option value="">All Actions</option>
                  <option value="login">Login</option>
                  <option value="login_failed">Login Failed</option>
                  <option value="logout">Logout</option>
                  <option value="password_reset">Password Reset</option>
                  <option value="password_changed">Password Changed</option>
                  <option value="role_changed">Role Changed</option>
                  <option value="account_activated">Account Activated</option>
                  <option value="account_deactivated">Account Deactivated</option>
                  <option value="kb_document_uploaded">KB Upload</option>
                  <option value="kb_document_deleted">KB Delete</option>
                  <option value="kb_document_reindexed">KB Reindexed</option>
                  <option value="kb_reindexed_all">KB Reindexed All</option>
                  <option value="conversation_viewed">Conversation Viewed</option>
                  <option value="ticket_created">Ticket Created</option>
                  <option value="ticket_updated">Ticket Updated</option>
                  <option value="ticket_deleted">Ticket Deleted</option>
                </select>
              </div>

              {/* Actor Filter */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Actor</label>
                <input
                  type="text"
                  placeholder="ID or Email..."
                  value={actorFilter}
                  onChange={(e) => setActorFilter(e.target.value)}
                  onBlur={() => fetchLogs()}
                  className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 placeholder-slate-600"
                />
              </div>

              {/* Target Filter */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Target</label>
                <input
                  type="text"
                  placeholder="ID or Email..."
                  value={targetFilter}
                  onChange={(e) => setTargetFilter(e.target.value)}
                  onBlur={() => fetchLogs()}
                  className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 placeholder-slate-600"
                />
              </div>

              {/* Status Filter */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Status</label>
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  <option value="">All Statuses</option>
                  <option value="success">Success</option>
                  <option value="failed">Failed</option>
                </select>
              </div>

              {/* Date Filters */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                  <Calendar className="h-3.5 w-3.5" /> Start Date
                </label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
                  <Calendar className="h-3.5 w-3.5" /> End Date
                </label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-950/40 border border-red-900/60 rounded-xl p-4 flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-red-500 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-red-200">Error retrieving logs</p>
                <p className="text-xs text-red-400 mt-1">{error}</p>
              </div>
            </div>
          )}

          {/* Logs Table */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-2xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 bg-slate-950/60">
                    <th className="p-4 text-xs font-bold text-slate-400 uppercase tracking-wider">Timestamp</th>
                    <th className="p-4 text-xs font-bold text-slate-400 uppercase tracking-wider">Actor</th>
                    <th className="p-4 text-xs font-bold text-slate-400 uppercase tracking-wider">Action</th>
                    <th className="p-4 text-xs font-bold text-slate-400 uppercase tracking-wider">Target</th>
                    <th className="p-4 text-xs font-bold text-slate-400 uppercase tracking-wider">Resource</th>
                    <th className="p-4 text-xs font-bold text-slate-400 uppercase tracking-wider">Status</th>
                    <th className="p-4 text-xs font-bold text-slate-400 uppercase tracking-wider text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80">
                  {loading ? (
                    <tr>
                      <td colSpan={7} className="p-8 text-center text-slate-500 text-sm">
                        <div className="flex items-center justify-center gap-2">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-500"></div>
                          Querying datastore audit logs...
                        </div>
                      </td>
                    </tr>
                  ) : logs.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="p-8 text-center text-slate-500 text-sm">
                        No audit log records match the search queries.
                      </td>
                    </tr>
                  ) : (
                    logs.map((log) => (
                      <tr 
                        key={log.audit_id} 
                        className="hover:bg-slate-800/30 transition duration-150 group"
                      >
                        <td className="p-4 text-xs font-mono text-slate-400">
                          {new Date(log.timestamp).toLocaleString()}
                        </td>
                        <td className="p-4 text-sm font-medium text-slate-200">
                          <div>{log.actor_email || "Anonymous"}</div>
                          <div className="text-xs text-slate-500">{log.actor_role || "none"}</div>
                        </td>
                        <td className="p-4 text-sm font-semibold">
                          <span className="text-indigo-400 bg-indigo-950/40 px-2 py-0.5 rounded border border-indigo-900/40">
                            {log.action}
                          </span>
                        </td>
                        <td className="p-4 text-sm text-slate-300">
                          {log.target_email ? (
                            <div>
                              <div>{log.target_email}</div>
                              <div className="text-xs text-slate-500 font-mono">ID: {log.target_user_id}</div>
                            </div>
                          ) : (
                            <span className="text-slate-600">-</span>
                          )}
                        </td>
                        <td className="p-4 text-sm text-slate-300">
                          <span className="text-slate-400 capitalize">{log.resource_type}</span>
                          <span className="text-xs block text-slate-500 font-mono">ID: {log.resource_id}</span>
                        </td>
                        <td className="p-4 text-sm">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${
                            log.status === 'success' 
                              ? 'text-emerald-400 bg-emerald-950/30 border-emerald-900/40' 
                              : 'text-red-400 bg-red-950/30 border-red-900/40'
                          }`}>
                            {log.status === 'success' ? (
                              <>
                                <CheckCircle2 className="h-3 w-3" />
                                Success
                              </>
                            ) : (
                              <>
                                <AlertCircle className="h-3 w-3" />
                                Failed
                              </>
                            )}
                          </span>
                        </td>
                        <td className="p-4 text-center">
                          <button
                            onClick={() => handleOpenDrawer(log.audit_id)}
                            className="bg-slate-950 border border-slate-800 hover:bg-slate-850 text-indigo-400 hover:text-indigo-300 p-2 rounded-lg transition duration-200 inline-flex items-center justify-center gap-1.5 text-xs font-semibold"
                          >
                            <Eye className="h-4 w-4" />
                            Inspect
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination footer */}
            <div className="border-t border-slate-800 bg-slate-950/40 p-4 flex items-center justify-between gap-4">
              <span className="text-sm text-slate-400">
                Showing <span className="font-semibold text-slate-200">{logs.length > 0 ? (page - 1) * limit + 1 : 0}</span> to <span className="font-semibold text-slate-200">{Math.min(page * limit, total)}</span> of <span className="font-semibold text-slate-200">{total}</span> events
              </span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(p - 1, 1))}
                  disabled={page === 1}
                  className="bg-slate-900 border border-slate-800 hover:bg-slate-850 disabled:opacity-50 text-slate-300 p-2 rounded-lg transition"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <span className="text-sm font-medium text-slate-200 px-3">
                  Page {page} of {Math.ceil(total / limit) || 1}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(p + 1, Math.ceil(total / limit)))}
                  disabled={page >= Math.ceil(total / limit)}
                  className="bg-slate-900 border border-slate-800 hover:bg-slate-850 disabled:opacity-50 text-slate-300 p-2 rounded-lg transition"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        </main>
      </div>

      {/* Details Side Drawer */}
      {selectedLogId && (
        <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/60 backdrop-blur-sm transition duration-300">
          {/* Backdrop Closer */}
          <div className="flex-1" onClick={handleCloseDrawer}></div>
          
          {/* Drawer Container */}
          <div className="w-full max-w-xl md:max-w-2xl bg-slate-900 border-l border-slate-800 p-6 shadow-2xl flex flex-col h-full overflow-hidden animate-slide-in">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-4 shrink-0">
              <div>
                <h3 className="text-lg font-bold text-white flex items-center gap-2">
                  <Info className="h-5 w-5 text-indigo-400" />
                  Audit Specifications Detail
                </h3>
                <p className="text-xs text-slate-500 font-mono mt-1">ID: {selectedLogId}</p>
              </div>
              <button
                onClick={handleCloseDrawer}
                className="text-slate-400 hover:text-slate-200 p-2 hover:bg-slate-800 rounded-lg transition"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Content Body */}
            <div className="flex-1 overflow-y-auto py-6 space-y-6">
              {drawerLoading ? (
                <div className="h-full flex items-center justify-center flex-col gap-3 text-slate-500">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
                  Retrieving complete audit payload...
                </div>
              ) : drawerError ? (
                <div className="bg-red-950/30 border border-red-900/40 rounded-xl p-4 text-red-400 text-sm">
                  {drawerError}
                </div>
              ) : selectedLog ? (
                <div className="space-y-6">
                  {/* Actor Box */}
                  <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4">
                    <h4 className="text-xs font-bold text-indigo-400 uppercase tracking-widest mb-3">Who Performed Action</h4>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-slate-500 text-xs uppercase block">User ID</span>
                        <span className="font-mono text-slate-300 break-all">{selectedLog.actor_user_id || "Anonymous"}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-xs uppercase block">Email</span>
                        <span className="text-slate-300">{selectedLog.actor_email || "Anonymous"}</span>
                      </div>
                      <div className="col-span-2">
                        <span className="text-slate-500 text-xs uppercase block">Role Privilege</span>
                        <span className="text-slate-200 capitalize font-medium">{selectedLog.actor_role || "none"}</span>
                      </div>
                    </div>
                  </div>

                  {/* Target Box */}
                  <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4">
                    <h4 className="text-xs font-bold text-indigo-400 uppercase tracking-widest mb-3">Affected Target</h4>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      {selectedLog.target_user_id ? (
                        <>
                          <div>
                            <span className="text-slate-500 text-xs uppercase block">User ID</span>
                            <span className="font-mono text-slate-300 break-all">{selectedLog.target_user_id}</span>
                          </div>
                          <div>
                            <span className="text-slate-500 text-xs uppercase block">Email</span>
                            <span className="text-slate-300">{selectedLog.target_email || "unknown"}</span>
                          </div>
                        </>
                      ) : (
                        <div className="col-span-2 text-slate-500 italic">No specific target user records affected.</div>
                      )}
                    </div>
                  </div>

                  {/* Operation Details */}
                  <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 space-y-4 text-sm">
                    <h4 className="text-xs font-bold text-indigo-400 uppercase tracking-widest">Operation Specifications</h4>
                    <div className="grid grid-cols-2 gap-y-4 gap-x-4">
                      <div>
                        <span className="text-slate-500 text-xs uppercase block">Action</span>
                        <span className="font-semibold text-white">{selectedLog.action}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-xs uppercase block">Timestamp (UTC)</span>
                        <span className="text-slate-300 font-mono text-xs">{new Date(selectedLog.timestamp).toUTCString()}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-xs uppercase block">Resource Type</span>
                        <span className="text-slate-300 capitalize">{selectedLog.resource_type}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-xs uppercase block">Resource ID</span>
                        <span className="font-mono text-slate-300 text-xs break-all">{selectedLog.resource_id}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-xs uppercase block">IP Address</span>
                        <span className="font-mono text-slate-300">{selectedLog.ip_address || "Unavailable"}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 text-xs uppercase block">User Agent</span>
                        <span className="text-slate-300 text-xs line-clamp-2" title={selectedLog.user_agent}>
                          {selectedLog.user_agent || "Unavailable"}
                        </span>
                      </div>
                      <div className="col-span-2">
                        <span className="text-slate-500 text-xs uppercase block">Outcome Status</span>
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold ${
                          selectedLog.status === 'success' ? 'text-emerald-400 bg-emerald-950/40' : 'text-red-400 bg-red-950/40'
                        }`}>
                          {selectedLog.status}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Value Changes (Previous / New Value Differencing) */}
                  {(selectedLog.previous_value !== undefined || selectedLog.new_value !== undefined) && (
                    <div className="space-y-3">
                      <h4 className="text-xs font-bold text-indigo-400 uppercase tracking-widest">Modified Values</h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 flex flex-col">
                          <span className="text-slate-500 text-xs uppercase block mb-1">Old / Previous Value</span>
                          <pre className="text-red-400 font-mono text-xs overflow-x-auto whitespace-pre-wrap flex-1 bg-slate-900/60 p-2.5 rounded border border-red-950/50">
                            {selectedLog.previous_value !== null ? String(selectedLog.previous_value) : "[None / Null]"}
                          </pre>
                        </div>
                        <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 flex flex-col">
                          <span className="text-slate-500 text-xs uppercase block mb-1">New / Updated Value</span>
                          <pre className="text-emerald-400 font-mono text-xs overflow-x-auto whitespace-pre-wrap flex-1 bg-slate-900/60 p-2.5 rounded border border-emerald-950/50">
                            {selectedLog.new_value !== null ? String(selectedLog.new_value) : "[None / Null]"}
                          </pre>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Additional Metadata JSON */}
                  {selectedLog.additional_metadata && Object.keys(selectedLog.additional_metadata).length > 0 && (
                    <div className="space-y-2">
                      <h4 className="text-xs font-bold text-indigo-400 uppercase tracking-widest">Metadata Payload</h4>
                      <pre className="bg-slate-950 text-slate-300 font-mono text-xs p-4 rounded-xl border border-slate-800 overflow-x-auto">
                        {JSON.stringify(selectedLog.additional_metadata, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
