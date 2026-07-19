"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import Navbar from "@/components/layout/Navbar";
import Sidebar from "@/components/layout/Sidebar";
import { api } from "@/services/api";
import { 
  Search, Filter, ChevronLeft, ChevronRight, X, ShieldAlert,
  CheckCircle, AlertTriangle, RefreshCw, Eye, ShieldCheck, Mail, Calendar, Key, AlertCircle,
  Clock, PlusCircle, User, MessageSquare, Clipboard, Activity, Send
} from "lucide-react";

interface TicketItem {
  id: number;
  ticket_id: string;
  customer_name: string;
  customer_email: string;
  subject: string;
  description: string;
  priority: string;
  category: string;
  status: string;
  created_at: string;
  updated_at: string;
  assigned_agent?: string;
  resolution_notes?: string;
  conversation_id?: string;
  user_id?: string;
}

interface TicketMetrics {
  open_tickets: number;
  closed_tickets: number;
  high_priority: number;
  average_resolution_time: number;
  tickets_created_today: number;
}

interface ChatMessage {
  _id: string;
  conversation_id: string;
  sender: string;
  content: string;
  created_at: string;
  user_id?: string;
}

interface TicketNote {
  _id: string;
  ticket_id: string;
  admin_id: string;
  admin_name: string;
  content: string;
  timestamp: string;
}

interface AuditLog {
  _id: string;
  admin_id: string;
  target_user_id: string;
  action: string;
  timestamp: string;
  previous_value?: string;
  new_value?: string;
}

interface TicketDetailsResponse {
  ticket: TicketItem;
  messages: ChatMessage[];
  notes: TicketNote[];
  history: AuditLog[];
}

interface AdminUser {
  id: string;
  full_name: string;
  email: string;
}

export default function AdminTicketsPage() {
  const { currentUser, loading: authLoading } = useAuth();
  const router = useRouter();

  // Guard routing
  useEffect(() => {
    if (!authLoading && (!currentUser || currentUser.role !== "admin")) {
      router.push("/");
    }
  }, [currentUser, authLoading, router]);

  // Page States
  const [tickets, setTickets] = useState<TicketItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(10);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [agentFilter, setAgentFilter] = useState("");
  const [sortBy, setSortBy] = useState("created_at");
  const [sortOrder, setSortOrder] = useState("desc");
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Metrics State
  const [metrics, setMetrics] = useState<TicketMetrics | null>(null);
  const [metricsLoading, setMetricsLoading] = useState(false);

  // Drawer States
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
  const [ticketDetails, setTicketDetails] = useState<TicketDetailsResponse | null>(null);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [drawerError, setDrawerError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // New Note Composer
  const [newNoteContent, setNewNoteContent] = useState("");

  // List of active admins for assignment
  const [adminsList, setAdminsList] = useState<AdminUser[]>([]);

  // Load ticket metrics
  const fetchMetrics = async () => {
    setMetricsLoading(true);
    try {
      const res = await api.get("/admin/tickets/metrics");
      setMetrics(res.data);
    } catch (err: any) {
      console.error("Failed to load metrics:", err);
    } finally {
      setMetricsLoading(false);
    }
  };

  // Load active admin list
  const fetchAdmins = async () => {
    try {
      const res = await api.get("/admin/users?role=admin&limit=100");
      setAdminsList(res.data.users);
    } catch (err: any) {
      console.error("Failed to resolve admin list:", err);
    }
  };

  // Load ticket items
  const fetchTickets = async () => {
    if (!currentUser || currentUser.role !== "admin") return;
    setLoading(true);
    setError(null);
    try {
      let url = `/admin/tickets?page=${page}&limit=${limit}&sort_by=${sortBy}&sort_order=${sortOrder}`;
      if (search.trim()) url += `&search=${encodeURIComponent(search)}`;
      if (statusFilter) url += `&status=${statusFilter}`;
      if (priorityFilter) url += `&priority=${priorityFilter}`;
      if (categoryFilter) url += `&category=${categoryFilter}`;
      if (agentFilter !== "") {
        // filter unassigned vs specific admin email
        url += `&assigned_agent=${encodeURIComponent(agentFilter)}`;
      }

      const res = await api.get(url);
      setTickets(res.data.tickets);
      setTotal(res.data.total);
    } catch (err: any) {
      setError(err.message || "Failed to load support ticket directory.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTickets();
    fetchMetrics();
    fetchAdmins();
  }, [page, search, statusFilter, priorityFilter, categoryFilter, agentFilter, sortBy, sortOrder, currentUser]);

  // Load Drawer Details
  const fetchDetails = async (idStr: string) => {
    setDrawerLoading(true);
    setDrawerError(null);
    try {
      const res = await api.get(`/admin/tickets/${idStr}`);
      setTicketDetails(res.data);
    } catch (err: any) {
      setDrawerError(err.message || "Failed to resolve detailed ticket logs.");
    } finally {
      setDrawerLoading(false);
    }
  };

  const handleOpenDrawer = (idStr: string) => {
    setSelectedTicketId(idStr);
    setTicketDetails(null);
    setNewNoteContent("");
    fetchDetails(idStr);
  };

  const handleCloseDrawer = () => {
    setSelectedTicketId(null);
    setTicketDetails(null);
    setNewNoteContent("");
  };

  // Ticket Operations
  const handleAssignAgent = async (ticket: TicketItem, newAgent: string) => {
    setActionLoading(true);
    setSuccessMsg(null);
    setDrawerError(null);
    try {
      await api.patch(`/admin/tickets/${ticket.ticket_id}/assign`, {
        assigned_agent: newAgent === "unassigned" ? null : newAgent
      });
      
      setSuccessMsg(`Ticket ${ticket.ticket_id} assignment updated.`);
      fetchTickets();
      fetchMetrics();
      if (selectedTicketId === ticket.ticket_id) {
        fetchDetails(ticket.ticket_id);
      }
    } catch (err: any) {
      setDrawerError(err.response?.data?.detail || err.message || "Assignment change failed.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleUpdateStatus = async (ticket: TicketItem, newStatus: string) => {
    setActionLoading(true);
    setSuccessMsg(null);
    setDrawerError(null);
    try {
      await api.patch(`/admin/tickets/${ticket.ticket_id}/status`, {
        status: newStatus
      });
      
      setSuccessMsg(`Ticket ${ticket.ticket_id} status updated to ${newStatus.toUpperCase()}.`);
      fetchTickets();
      fetchMetrics();
      if (selectedTicketId === ticket.ticket_id) {
        fetchDetails(ticket.ticket_id);
      }
    } catch (err: any) {
      setDrawerError(err.response?.data?.detail || err.message || "Status change failed.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleUpdatePriority = async (ticket: TicketItem, newPriority: string) => {
    setActionLoading(true);
    setSuccessMsg(null);
    setDrawerError(null);
    try {
      await api.patch(`/admin/tickets/${ticket.ticket_id}/priority`, {
        priority: newPriority
      });
      
      setSuccessMsg(`Ticket ${ticket.ticket_id} priority set to ${newPriority.toUpperCase()}.`);
      fetchTickets();
      fetchMetrics();
      if (selectedTicketId === ticket.ticket_id) {
        fetchDetails(ticket.ticket_id);
      }
    } catch (err: any) {
      setDrawerError(err.response?.data?.detail || err.message || "Priority change failed.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTicketId || !newNoteContent.trim()) return;
    setActionLoading(true);
    setDrawerError(null);
    try {
      await api.post(`/admin/tickets/${selectedTicketId}/notes`, {
        content: newNoteContent.trim()
      });
      
      setNewNoteContent("");
      fetchDetails(selectedTicketId);
    } catch (err: any) {
      setDrawerError(err.response?.data?.detail || err.message || "Failed to add internal compliance note.");
    } finally {
      setActionLoading(false);
    }
  };

  if (authLoading || !currentUser || currentUser.role !== "admin") {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="h-7 w-7 text-indigo-500 animate-spin" />
          <p className="text-xs font-bold text-zinc-500 tracking-wider">Verifying Administrator Access...</p>
        </div>
      </div>
    );
  }

  const totalPages = Math.ceil(total / limit) || 1;

  const formatDate = (isoString?: string) => {
    if (!isoString) return "N/A";
    return new Date(isoString).toLocaleString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatDuration = (seconds?: number) => {
    if (seconds === undefined || seconds === null) return "N/A";
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const mins = seconds / 60;
    if (mins < 60) return `${Math.round(mins)}m`;
    const hrs = mins / 60;
    if (hrs < 24) return `${Math.round(hrs)}h`;
    return `${Math.round(hrs / 24)}d`;
  };

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col selection:bg-indigo-500/30 font-sans">
      <Navbar />

      <div className="flex-1 flex max-w-7xl mx-auto w-full relative">
        <Sidebar />

        <main className="flex-1 p-6 md:p-8 text-zinc-300 relative overflow-hidden">
          
          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
            <div>
              <div className="flex items-center gap-2">
                <Clipboard className="h-5 w-5 text-indigo-400" />
                <h1 className="text-xl font-extrabold text-zinc-100 tracking-tight">Support Tickets Admin</h1>
              </div>
              <p className="text-xs text-zinc-500 font-semibold mt-1">Resolve customer issues, update status parameters, and document internal compliance notes</p>
            </div>

            {/* Notification alert */}
            {(successMsg || error) && (
              <div className="flex items-center gap-3 animate-fade-in">
                {successMsg && (
                  <div className="px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-xl text-xs font-bold flex items-center gap-2 shadow-lg">
                    <CheckCircle className="h-4 w-4" />
                    {successMsg}
                  </div>
                )}
                {error && (
                  <div className="px-4 py-2 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl text-xs font-bold flex items-center gap-2 shadow-lg">
                    <AlertTriangle className="h-4 w-4" />
                    {error}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Metrics summary cards */}
          {metrics && (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
              <div className="p-4 bg-zinc-900/40 border border-zinc-850 rounded-2xl relative shadow-md">
                <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block">Open Tickets</span>
                <span className="text-xl font-extrabold text-indigo-400 mt-2 block">{metrics.open_tickets}</span>
                <Clock className="absolute right-4 bottom-4 h-5 w-5 text-zinc-800" />
              </div>
              <div className="p-4 bg-zinc-900/40 border border-zinc-850 rounded-2xl relative shadow-md">
                <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block">Closed & Resolved</span>
                <span className="text-xl font-extrabold text-emerald-400 mt-2 block">{metrics.closed_tickets}</span>
                <CheckCircle className="absolute right-4 bottom-4 h-5 w-5 text-zinc-800" />
              </div>
              <div className="p-4 bg-zinc-900/40 border border-zinc-850 rounded-2xl relative shadow-md">
                <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block">High Priority</span>
                <span className="text-xl font-extrabold text-rose-450 mt-2 block">{metrics.high_priority}</span>
                <AlertTriangle className="absolute right-4 bottom-4 h-5 w-5 text-zinc-800" />
              </div>
              <div className="p-4 bg-zinc-900/40 border border-zinc-850 rounded-2xl relative shadow-md">
                <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block">Created Today</span>
                <span className="text-xl font-extrabold text-amber-400 mt-2 block">{metrics.tickets_created_today}</span>
                <Calendar className="absolute right-4 bottom-4 h-5 w-5 text-zinc-800" />
              </div>
              <div className="p-4 bg-zinc-900/40 border border-zinc-850 rounded-2xl relative shadow-md">
                <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block">Avg Resolution Time</span>
                <span className="text-xl font-extrabold text-zinc-200 mt-2 block">{formatDuration(metrics.average_resolution_time)}</span>
                <Activity className="absolute right-4 bottom-4 h-5 w-5 text-zinc-800" />
              </div>
            </div>
          )}

          {/* Filtering & searching actions */}
          <div className="bg-zinc-900/40 border border-zinc-850 rounded-2xl p-5 mb-6 backdrop-blur-md shadow-xl">
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-4">
              
              {/* Search Bar */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
                <input
                  type="text"
                  placeholder="Search subject or email..."
                  value={search}
                  onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                  className="w-full pl-9 pr-4 py-2 rounded-xl bg-zinc-950 border border-zinc-800 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>

              {/* Status Filter */}
              <div className="relative">
                <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
                <select
                  value={statusFilter}
                  onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
                  className="w-full pl-9 pr-4 py-2 rounded-xl bg-zinc-950 border border-zinc-800 text-xs text-zinc-355 focus:outline-none focus:border-indigo-500 transition-colors appearance-none cursor-pointer capitalize"
                >
                  <option value="">All Statuses</option>
                  <option value="open">Open</option>
                  <option value="in_progress">In Progress</option>
                  <option value="resolved">Resolved</option>
                  <option value="closed">Closed</option>
                </select>
              </div>

              {/* Priority filter */}
              <div className="relative">
                <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
                <select
                  value={priorityFilter}
                  onChange={(e) => { setPriorityFilter(e.target.value); setPage(1); }}
                  className="w-full pl-9 pr-4 py-2 rounded-xl bg-zinc-950 border border-zinc-800 text-xs text-zinc-355 focus:outline-none focus:border-indigo-500 transition-colors appearance-none cursor-pointer capitalize"
                >
                  <option value="">All Priorities</option>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="urgent">Urgent</option>
                </select>
              </div>

              {/* Category filter */}
              <div className="relative">
                <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
                <select
                  value={categoryFilter}
                  onChange={(e) => { setCategoryFilter(e.target.value); setPage(1); }}
                  className="w-full pl-9 pr-4 py-2 rounded-xl bg-zinc-950 border border-zinc-800 text-xs text-zinc-355 focus:outline-none focus:border-indigo-500 transition-colors appearance-none cursor-pointer capitalize"
                >
                  <option value="">All Categories</option>
                  <option value="billing">Billing</option>
                  <option value="technical">Technical</option>
                  <option value="account">Account</option>
                  <option value="general">General</option>
                </select>
              </div>

              {/* Assigned Agent filter */}
              <div className="relative">
                <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
                <select
                  value={agentFilter}
                  onChange={(e) => { setAgentFilter(e.target.value); setPage(1); }}
                  className="w-full pl-9 pr-4 py-2 rounded-xl bg-zinc-950 border border-zinc-800 text-xs text-zinc-355 focus:outline-none focus:border-indigo-500 transition-colors appearance-none cursor-pointer"
                >
                  <option value="">All Agents</option>
                  <option value="">Unassigned</option>
                  {adminsList.map(adm => (
                    <option key={adm.id} value={adm.email}>{adm.full_name}</option>
                  ))}
                </select>
              </div>

            </div>
          </div>

          {/* Table list view */}
          <div className="bg-zinc-900/30 border border-zinc-850 rounded-2xl overflow-hidden shadow-xl shadow-black/25">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-zinc-900/70 border-b border-zinc-850 text-[10px] font-bold text-zinc-500 uppercase tracking-widest">
                    <th className="px-6 py-4">Ticket</th>
                    <th className="px-6 py-4">Customer</th>
                    <th className="px-6 py-4">Status</th>
                    <th className="px-6 py-4">Priority</th>
                    <th className="px-6 py-4">Agent</th>
                    <th className="px-6 py-4 text-center">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-900/60">
                  {loading ? (
                    <tr>
                      <td colSpan={6} className="text-center py-12">
                        <RefreshCw className="h-6 w-6 text-indigo-500 animate-spin mx-auto mb-2" />
                        <span className="text-xs font-semibold text-zinc-500">Retrieving support logs...</span>
                      </td>
                    </tr>
                  ) : tickets.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="text-center py-12 text-xs font-semibold text-zinc-500">
                        No support tickets match active filters.
                      </td>
                    </tr>
                  ) : (
                    tickets.map((t) => (
                      <tr 
                        key={t.id} 
                        className="hover:bg-zinc-900/30 transition-colors group text-zinc-300 text-xs font-medium"
                      >
                        <td className="px-6 py-4">
                          <div>
                            <p className="font-bold text-zinc-200 group-hover:text-indigo-400 transition-colors cursor-pointer" onClick={() => handleOpenDrawer(t.ticket_id)}>
                              {t.subject}
                            </p>
                            <span className="text-[10px] font-bold text-zinc-550 uppercase tracking-wider mt-1 block">
                              ID: {t.ticket_id} &bull; Category: {t.category}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div>
                            <p className="font-bold text-zinc-250">{t.customer_name}</p>
                            <p className="text-[10px] text-zinc-500 font-semibold mt-0.5">{t.customer_email}</p>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span className={`px-2 py-0.5 text-[9px] font-extrabold rounded-full border uppercase ${
                            t.status === "open" ? "bg-indigo-500/10 border-indigo-500/20 text-indigo-400" :
                            t.status === "in_progress" ? "bg-amber-500/10 border-amber-500/20 text-amber-400" :
                            t.status === "resolved" ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400" :
                            "bg-zinc-800/40 border-zinc-700/50 text-zinc-500"
                          }`}>
                            {t.status.replace("_", " ")}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <span className={`px-2 py-0.5 text-[9px] font-extrabold rounded-full border uppercase ${
                            t.priority === "urgent" ? "bg-red-500/10 border-red-500/20 text-red-400 animate-pulse" :
                            t.priority === "high" ? "bg-rose-500/10 border-rose-500/20 text-rose-450" :
                            t.priority === "medium" ? "bg-amber-500/10 border-amber-500/20 text-amber-400" :
                            "bg-zinc-800/40 border-zinc-700/50 text-zinc-500"
                          }`}>
                            {t.priority}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <span className="text-xs font-bold text-zinc-350">
                            {t.assigned_agent ? t.assigned_agent.split("@")[0] : "Unassigned"}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-center">
                          <button
                            onClick={() => handleOpenDrawer(t.ticket_id)}
                            className="p-2 rounded-lg bg-zinc-950 hover:bg-zinc-900 border border-zinc-800 text-indigo-400 hover:text-indigo-300 transition-colors shadow-sm active:scale-95 inline-flex items-center gap-1"
                          >
                            <Eye className="h-3.5 w-3.5" />
                            <span className="text-[10px] font-bold">Manage</span>
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="bg-zinc-950/40 border-t border-zinc-850 p-4 flex items-center justify-between">
              <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">
                Total Tickets: {total}
              </span>
              <div className="flex items-center gap-2">
                <button
                  disabled={page <= 1 || loading}
                  onClick={() => setPage(page - 1)}
                  className="p-1.5 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-200 disabled:opacity-40 disabled:hover:text-zinc-400 transition-colors"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <span className="text-xs text-zinc-400 font-bold px-2">
                  Page {page} of {totalPages}
                </span>
                <button
                  disabled={page >= totalPages || loading}
                  onClick={() => setPage(page + 1)}
                  className="p-1.5 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-200 disabled:opacity-40 disabled:hover:text-zinc-400 transition-colors"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          </div>
        </main>
      </div>

      {/* Side Details Drawer */}
      {selectedTicketId && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex justify-end animate-fade-in font-sans text-xs">
          <div className="w-full max-w-2xl bg-zinc-950 border-l border-zinc-900 p-6 shadow-2xl flex flex-col justify-between h-full relative overflow-y-auto">
            
            {/* Drawer Header */}
            <div>
              <div className="flex items-center justify-between mb-6 pb-4 border-b border-zinc-900">
                <div className="flex items-center gap-2">
                  <Clipboard className="h-5 w-5 text-indigo-400" />
                  <h2 className="text-sm font-bold text-zinc-100">Ticket Manager Console</h2>
                </div>
                <button 
                  onClick={handleCloseDrawer}
                  className="p-1.5 rounded-lg bg-zinc-900 border border-zinc-800 hover:bg-zinc-850 text-zinc-400 hover:text-zinc-200 transition-all active:scale-95"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {drawerLoading ? (
                <div className="text-center py-12">
                  <RefreshCw className="h-6 w-6 text-indigo-500 animate-spin mx-auto mb-2" />
                  <p className="text-xs text-zinc-500 font-semibold">Resolving ticket specifications...</p>
                </div>
              ) : drawerError ? (
                <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl text-xs font-bold flex items-center gap-2">
                  <AlertCircle className="h-4 w-4" />
                  {drawerError}
                </div>
              ) : (
                ticketDetails && (
                  <div className="space-y-6">
                    
                    {/* Ticket Subject Block */}
                    <div className="bg-zinc-900/20 border border-zinc-900 p-4 rounded-xl space-y-2">
                      <div className="flex justify-between items-start gap-4">
                        <h3 className="text-sm font-bold text-zinc-150 leading-relaxed">{ticketDetails.ticket.subject}</h3>
                        <span className="px-2 py-0.5 bg-zinc-950 border border-zinc-900 text-[10px] text-zinc-500 uppercase font-bold tracking-wider rounded shrink-0">
                          {ticketDetails.ticket.ticket_id}
                        </span>
                      </div>
                      <p className="text-zinc-400 leading-relaxed bg-zinc-950/40 border border-zinc-950 p-3 rounded-lg font-medium whitespace-pre-wrap">
                        {ticketDetails.ticket.description}
                      </p>
                    </div>

                    {/* Meta Info Grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      
                      {/* Customer Info */}
                      <div className="bg-zinc-900/20 border border-zinc-900 p-4 rounded-xl space-y-2">
                        <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block">Customer Details</h4>
                        <div>
                          <p className="font-bold text-zinc-200">{ticketDetails.ticket.customer_name}</p>
                          <p className="text-[10px] text-zinc-500 font-semibold mt-0.5 flex items-center gap-1">
                            <Mail className="h-3 w-3 text-zinc-700" />
                            {ticketDetails.ticket.customer_email}
                          </p>
                        </div>
                      </div>

                      {/* Timestamps */}
                      <div className="bg-zinc-900/20 border border-zinc-900 p-4 rounded-xl space-y-2">
                        <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block">Filing Timestamps</h4>
                        <div className="space-y-1 text-[11px] font-semibold text-zinc-400">
                          <div className="flex justify-between">
                            <span>Created:</span>
                            <span className="text-zinc-350">{formatDate(ticketDetails.ticket.created_at)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Last Updated:</span>
                            <span className="text-zinc-350">{formatDate(ticketDetails.ticket.updated_at)}</span>
                          </div>
                        </div>
                      </div>

                    </div>

                    {/* Operational Management controls */}
                    <div className="bg-zinc-900/10 border border-zinc-900 p-4 rounded-xl space-y-4">
                      <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">Operational Directives</h4>
                      
                      <div className="flex flex-wrap gap-4">
                        
                        {/* Status update selector */}
                        <div className="flex items-center gap-2 bg-zinc-950 border border-zinc-900 px-3 py-1.5 rounded-xl text-[11px]">
                          <span className="text-zinc-500 font-semibold">Status:</span>
                          <select
                            disabled={actionLoading}
                            value={ticketDetails.ticket.status}
                            onChange={(e) => handleUpdateStatus(ticketDetails.ticket, e.target.value)}
                            className="bg-transparent border-none text-zinc-200 font-bold focus:outline-none cursor-pointer capitalize"
                          >
                            <option value="open" className="bg-zinc-950">Open</option>
                            <option value="in_progress" className="bg-zinc-950">In Progress</option>
                            <option value="resolved" className="bg-zinc-950">Resolved</option>
                            <option value="closed" className="bg-zinc-950">Closed</option>
                          </select>
                        </div>

                        {/* Priority update selector */}
                        <div className="flex items-center gap-2 bg-zinc-950 border border-zinc-900 px-3 py-1.5 rounded-xl text-[11px]">
                          <span className="text-zinc-500 font-semibold">Priority:</span>
                          <select
                            disabled={actionLoading}
                            value={ticketDetails.ticket.priority}
                            onChange={(e) => handleUpdatePriority(ticketDetails.ticket, e.target.value)}
                            className="bg-transparent border-none text-zinc-200 font-bold focus:outline-none cursor-pointer capitalize"
                          >
                            <option value="low" className="bg-zinc-950">Low</option>
                            <option value="medium" className="bg-zinc-950">Medium</option>
                            <option value="high" className="bg-zinc-950">High</option>
                            <option value="urgent" className="bg-zinc-950">Urgent</option>
                          </select>
                        </div>

                        {/* Assigned agent selector */}
                        <div className="flex items-center gap-2 bg-zinc-950 border border-zinc-900 px-3 py-1.5 rounded-xl text-[11px]">
                          <span className="text-zinc-500 font-semibold">Assigned Agent:</span>
                          <select
                            disabled={actionLoading}
                            value={ticketDetails.ticket.assigned_agent || "unassigned"}
                            onChange={(e) => handleAssignAgent(ticketDetails.ticket, e.target.value)}
                            className="bg-transparent border-none text-zinc-200 font-bold focus:outline-none cursor-pointer"
                          >
                            <option value="unassigned" className="bg-zinc-950">Unassigned</option>
                            {adminsList.map(adm => (
                              <option key={adm.id} value={adm.email} className="bg-zinc-950">{adm.full_name}</option>
                            ))}
                          </select>
                        </div>

                      </div>
                    </div>

                    {/* Chat log transcript */}
                    {ticketDetails.messages.length > 0 && (
                      <div className="space-y-2">
                        <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider flex items-center gap-1.5">
                          <MessageSquare className="h-4 w-4 text-zinc-700" />
                          Chat Conversation Context
                        </h4>
                        <div className="bg-zinc-950/60 border border-zinc-900 p-4 rounded-xl max-h-48 overflow-y-auto space-y-3">
                          {ticketDetails.messages.map((msg, index) => {
                            const isUser = msg.sender === "user" || msg.user_id;
                            return (
                              <div key={msg._id || index} className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
                                <div className={`max-w-[80%] p-3 rounded-2xl text-[11px] leading-relaxed ${
                                  isUser 
                                    ? "bg-indigo-500/10 border border-indigo-500/20 text-zinc-200" 
                                    : "bg-zinc-900 text-zinc-300"
                                }`}>
                                  <span className="text-[9px] font-extrabold uppercase tracking-wide block mb-1 text-zinc-500">
                                    {isUser ? "Customer" : "AI Agent"}
                                  </span>
                                  {msg.content}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {/* Internal Notes composer & logs board */}
                    <div className="space-y-4">
                      <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block">Internal Compliance Notes</h4>
                      
                      {/* Note creator */}
                      <form onSubmit={handleAddNote} className="flex gap-2">
                        <input
                          type="text"
                          required
                          placeholder="Write a private note..."
                          value={newNoteContent}
                          onChange={(e) => setNewNoteContent(e.target.value)}
                          disabled={actionLoading}
                          className="flex-1 px-4 py-2 bg-zinc-950 border border-zinc-850 rounded-xl text-xs placeholder-zinc-650 focus:outline-none focus:border-indigo-500"
                        />
                        <button
                          type="submit"
                          disabled={actionLoading || !newNoteContent.trim()}
                          className="px-4 py-2 bg-indigo-500 hover:bg-indigo-400 text-white font-bold rounded-xl flex items-center gap-1.5 transition-colors disabled:opacity-50 active:scale-95"
                        >
                          <Send className="h-3.5 w-3.5" />
                          <span>Add Note</span>
                        </button>
                      </form>

                      {/* Notes list board */}
                      <div className="space-y-2 max-h-40 overflow-y-auto divide-y divide-zinc-900 border border-zinc-900 rounded-xl p-3 bg-zinc-900/5">
                        {ticketDetails.notes.length === 0 ? (
                          <p className="text-center py-4 text-zinc-600 font-semibold">No internal notes compiled yet.</p>
                        ) : (
                          ticketDetails.notes.map(note => (
                            <div key={note._id} className="pt-2 pb-2 first:pt-0 last:pb-0">
                              <div className="flex justify-between items-center text-[10px] font-bold text-zinc-500 mb-1">
                                <span>{note.admin_name}</span>
                                <span>{formatDate(note.timestamp).split(",")[0]}</span>
                              </div>
                              <p className="text-[11px] text-zinc-300 leading-relaxed font-semibold">{note.content}</p>
                            </div>
                          ))
                        )}
                      </div>
                    </div>

                    {/* Timeline compliance audit trail */}
                    <div className="space-y-3">
                      <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider block">E2E Ticket Operations Timeline</h4>
                      
                      <div className="bg-zinc-950/40 border border-zinc-900 rounded-xl max-h-40 overflow-y-auto p-3 divide-y divide-zinc-900">
                        {ticketDetails.history.length === 0 ? (
                          <p className="text-center py-4 text-zinc-600 font-semibold">No operational updates logged for this ticket.</p>
                        ) : (
                          ticketDetails.history.map(log => (
                            <div key={log._id} className="pt-2 pb-2 first:pt-0 last:pb-0 flex flex-col gap-1 text-[11px]">
                              <div className="flex justify-between items-center font-bold text-zinc-400">
                                <span className="capitalize">{log.action.replace(/_/g, " ")}</span>
                                <span className="text-[10px] text-zinc-500 font-semibold">{formatDate(log.timestamp).split(",")[0]}</span>
                              </div>
                              <p className="text-[10px] text-zinc-500 font-semibold">Admin: {log.admin_id}</p>
                              {(log.previous_value !== undefined || log.new_value !== undefined) && (
                                <div className="text-[10px] text-zinc-450 bg-zinc-900/30 p-1.5 rounded font-mono mt-0.5">
                                  {log.previous_value || "None"} &rarr; {log.new_value || "None"}
                                </div>
                              )}
                            </div>
                          ))
                        )}
                      </div>
                    </div>

                  </div>
                )
              )}
            </div>

            {/* Actions loading blocking layer */}
            {actionLoading && (
              <div className="absolute inset-0 bg-black/30 backdrop-blur-[1px] flex items-center justify-center pointer-events-none">
                <RefreshCw className="h-6 w-6 text-indigo-400 animate-spin" />
              </div>
            )}

          </div>
        </div>
      )}
    </div>
  );
}
