"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import Navbar from "@/components/layout/Navbar";
import Sidebar from "@/components/layout/Sidebar";
import { api } from "@/services/api";
import { 
  Search, Filter, ChevronLeft, ChevronRight, X, MessageSquare, 
  User, Mail, Calendar, Eye, FileText, Bot, Compass, CheckCircle2,
  AlertCircle, ShieldAlert, Tag, ShieldCheck, RefreshCw, Layers
} from "lucide-react";

interface ConversationItem {
  conversation_id: string;
  user_id?: string;
  user_email?: string;
  user_name?: string;
  title?: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  ticket_id?: string;
  ticket_status?: string;
}

interface ParticipantInfo {
  user_id?: string;
  email?: string;
  full_name?: string;
}

interface TicketAssociation {
  ticket_id: string;
  subject: string;
  status: string;
  priority: string;
  category: string;
  created_at: string;
}

interface MessageItem {
  message_id: string;
  role: string;
  content: string;
  intent?: string;
  agent?: string;
  sources?: Array<{
    source: string;
    page: number;
    type: string;
  }>;
  confidence_score?: number;
  created_at: string;
}

interface ConversationDetails {
  conversation_id: string;
  session_id?: string;
  title?: string;
  created_at: string;
  updated_at: string;
  participant?: ParticipantInfo;
  ticket?: TicketAssociation;
  messages: MessageItem[];
}

export default function AdminConversationsPage() {
  const { currentUser, loading: authLoading } = useAuth();
  const router = useRouter();

  // Guard routing
  useEffect(() => {
    if (!authLoading && (!currentUser || currentUser.role !== "admin")) {
      router.push("/");
    }
  }, [currentUser, authLoading, router]);

  // Page States
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(10);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Drawer States
  const [selectedConvId, setSelectedConvId] = useState<string | null>(null);
  const [details, setDetails] = useState<ConversationDetails | null>(null);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [drawerError, setDrawerError] = useState<string | null>(null);

  // Fetch Conversation List
  const fetchConversations = async () => {
    if (!currentUser || currentUser.role !== "admin") return;
    setLoading(true);
    setError(null);
    try {
      let url = `/admin/conversations?page=${page}&limit=${limit}`;
      if (search.trim()) {
        url += `&search=${encodeURIComponent(search)}`;
      }
      if (statusFilter) {
        url += `&status=${statusFilter}`;
      }
      if (startDate) {
        url += `&start_date=${new Date(startDate).toISOString()}`;
      }
      if (endDate) {
        url += `&end_date=${new Date(endDate).toISOString()}`;
      }

      const res = await api.get(url);
      setConversations(res.data.conversations);
      setTotal(res.data.total);
    } catch (err: any) {
      setError(err.message || "Failed to load conversation logs.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConversations();
  }, [page, statusFilter, startDate, endDate, currentUser]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchConversations();
  };

  // Fetch Detailed View
  const fetchDetails = async (id: string) => {
    setDrawerLoading(true);
    setDrawerError(null);
    try {
      const res = await api.get(`/admin/conversations/${id}`);
      setDetails(res.data);
    } catch (err: any) {
      setDrawerError(err.message || "Failed to retrieve conversation details.");
    } finally {
      setDrawerLoading(false);
    }
  };

  const handleOpenDrawer = (id: string) => {
    setSelectedConvId(id);
    setDetails(null);
    fetchDetails(id);
  };

  const handleCloseDrawer = () => {
    setSelectedConvId(null);
    setDetails(null);
  };

  // Pagination bounds
  const totalPages = Math.ceil(total / limit) || 1;

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
              <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-violet-600 via-indigo-600 to-blue-600 bg-clip-text text-transparent">
                Conversation Inspector
              </h1>
              <p className="text-slate-500 dark:text-slate-400 mt-1">
                Inspect support logs, RAG triggers, and agent actions for quality assurance.
              </p>
            </div>
          </div>

          {/* Filters Area */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 mb-6 shadow-sm">
            <form onSubmit={handleSearchSubmit} className="flex flex-col lg:flex-row gap-4 items-stretch lg:items-end">
              <div className="flex-1">
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Search Conversations</label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 h-5 w-5" />
                  <input
                    type="text"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search by ID, User Email, Name, or Ticket ID..."
                    className="w-full pl-10 pr-4 py-2.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-600 focus:border-transparent transition-all"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 lg:w-3/5">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Ticket Status</label>
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="w-full px-3 py-2.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-600 transition-all cursor-pointer"
                  >
                    <option value="">All Statuses</option>
                    <option value="open">Open</option>
                    <option value="in_progress">In Progress</option>
                    <option value="resolved">Resolved</option>
                    <option value="closed">Closed</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Start Date</label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-600 transition-all"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">End Date</label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-600 transition-all"
                  />
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  type="submit"
                  className="px-5 py-2.5 bg-violet-600 hover:bg-violet-700 active:bg-violet-800 text-white rounded-xl text-sm font-semibold transition-all shadow-md shadow-violet-200 dark:shadow-none"
                >
                  Apply
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setSearch("");
                    setStatusFilter("");
                    setStartDate("");
                    setEndDate("");
                    setPage(1);
                  }}
                  className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-850 dark:hover:bg-slate-800 rounded-xl text-sm font-semibold transition-all"
                >
                  Reset
                </button>
              </div>
            </form>
          </div>

          {/* Main Error */}
          {error && (
            <div className="bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900/50 text-red-700 dark:text-red-400 p-4 rounded-xl mb-6 flex gap-3 items-center">
              <ShieldAlert className="h-5 w-5 flex-shrink-0" />
              <span className="text-sm font-medium">{error}</span>
            </div>
          )}

          {/* Table Container */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden mb-6">
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/55 dark:bg-slate-950/30">
                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-400">User / Customer</th>
                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-400">Conversation ID</th>
                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-400">Title</th>
                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-400">Messages</th>
                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-400">Ticket Assoc.</th>
                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-400">Last Active</th>
                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-400 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-150 dark:divide-slate-850">
                  {loading ? (
                    <tr>
                      <td colSpan={7} className="px-6 py-12 text-center">
                        <div className="flex flex-col items-center gap-3">
                          <RefreshCw className="h-8 w-8 text-violet-600 animate-spin" />
                          <span className="text-sm text-slate-500">Querying conversation logs...</span>
                        </div>
                      </td>
                    </tr>
                  ) : conversations.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-6 py-16 text-center text-slate-400">
                        <div className="flex flex-col items-center gap-2">
                          <MessageSquare className="h-10 w-10 text-slate-300 dark:text-slate-700" />
                          <span className="text-sm">No conversation history meets specified search metrics.</span>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    conversations.map((c) => (
                      <tr 
                        key={c.conversation_id}
                        className="hover:bg-slate-50/50 dark:hover:bg-slate-950/20 transition-colors duration-150"
                      >
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="h-9 w-9 bg-slate-100 dark:bg-slate-800 rounded-full flex items-center justify-center text-slate-600 dark:text-slate-400">
                              <User className="h-4 w-4" />
                            </div>
                            <div>
                              <div className="font-semibold text-sm">
                                {c.user_name || "Guest Customer"}
                              </div>
                              {c.user_email && (
                                <div className="text-xs text-slate-400 flex items-center gap-1 mt-0.5">
                                  <Mail className="h-3 w-3" />
                                  {c.user_email}
                                </div>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <code className="text-xs px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded font-mono text-slate-600 dark:text-slate-400">
                            {c.conversation_id.slice(0, 8)}...
                          </code>
                        </td>
                        <td className="px-6 py-4 max-w-xs truncate font-medium text-sm">
                          {c.title}
                        </td>
                        <td className="px-6 py-4">
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-violet-50 dark:bg-violet-950/20 text-violet-700 dark:text-violet-400">
                            {c.message_count} messages
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          {c.ticket_id ? (
                            <div className="flex flex-col gap-1">
                              <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                                {c.ticket_id}
                              </span>
                              <span className={`inline-block text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded border self-start ${
                                c.ticket_status === "open" ? "bg-red-55 dark:bg-red-950/20 text-red-600 border-red-200 dark:border-red-900/30" :
                                c.ticket_status === "in_progress" ? "bg-yellow-55 dark:bg-yellow-950/20 text-yellow-600 border-yellow-200 dark:border-yellow-900/30" :
                                c.ticket_status === "resolved" ? "bg-green-55 dark:bg-green-950/20 text-green-600 border-green-200 dark:border-green-900/30" :
                                "bg-slate-50 dark:bg-slate-950 text-slate-500 border-slate-200 dark:border-slate-800"
                              }`}>
                                {c.ticket_status}
                              </span>
                            </div>
                          ) : (
                            <span className="text-xs text-slate-400 italic">No associated ticket</span>
                          )}
                        </td>
                        <td className="px-6 py-4 text-xs text-slate-400 font-medium">
                          <div className="flex items-center gap-1.5">
                            <Calendar className="h-3.5 w-3.5" />
                            {new Date(c.updated_at).toLocaleString()}
                          </div>
                        </td>
                        <td className="px-6 py-4 text-right">
                          <button
                            onClick={() => handleOpenDrawer(c.conversation_id)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg text-xs font-semibold transition-all"
                          >
                            <Eye className="h-3.5 w-3.5" />
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
            {!loading && total > 0 && (
              <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between">
                <span className="text-xs text-slate-400 font-medium">
                  Showing <strong className="text-slate-700 dark:text-slate-300">{((page - 1) * limit) + 1}</strong> to <strong className="text-slate-700 dark:text-slate-300">{Math.min(page * limit, total)}</strong> of <strong className="text-slate-700 dark:text-slate-300">{total}</strong> conversations
                </span>
                <div className="flex gap-2">
                  <button
                    disabled={page === 1}
                    onClick={() => setPage(p => p - 1)}
                    className="p-1.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 rounded-lg text-slate-500 disabled:opacity-40 disabled:pointer-events-none transition-all"
                  >
                    <ChevronLeft className="h-5 w-5" />
                  </button>
                  <button
                    disabled={page === totalPages}
                    onClick={() => setPage(p => p + 1)}
                    className="p-1.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 rounded-lg text-slate-500 disabled:opacity-40 disabled:pointer-events-none transition-all"
                  >
                    <ChevronRight className="h-5 w-5" />
                  </button>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>

      {/* Conversations Detail Inspector Drawer */}
      {selectedConvId && (
        <div className="fixed inset-y-0 right-0 z-50 w-full max-w-3xl bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 shadow-2xl flex flex-col transition-all duration-300">
          {/* Header */}
          <div className="px-6 py-5 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/10 flex justify-between items-center">
            <div>
              <h2 className="text-lg font-bold flex items-center gap-2">
                <MessageSquare className="h-5 w-5 text-violet-600" />
                Conversation Spec Audit
              </h2>
              <span className="text-xs text-slate-400 font-mono mt-0.5 block">{selectedConvId}</span>
            </div>
            <button
              onClick={handleCloseDrawer}
              className="p-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-750 text-slate-400 hover:text-slate-600 rounded-full transition-all"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Main Body */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {drawerLoading ? (
              <div className="py-20 flex flex-col items-center gap-3">
                <RefreshCw className="h-8 w-8 text-violet-600 animate-spin" />
                <span className="text-sm text-slate-400">Loading conversation specifications...</span>
              </div>
            ) : drawerError ? (
              <div className="bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900/50 text-red-700 dark:text-red-400 p-4 rounded-xl flex gap-3 items-center">
                <ShieldAlert className="h-5 w-5 flex-shrink-0" />
                <span className="text-sm font-medium">{drawerError}</span>
              </div>
            ) : details ? (
              <>
                {/* Metadata cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Participant Card */}
                  <div className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-850 p-4 rounded-xl">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-1.5">
                      <User className="h-3.5 w-3.5 text-violet-600" />
                      Client Profile
                    </h3>
                    {details.participant ? (
                      <div className="space-y-2">
                        <div className="text-sm font-semibold">{details.participant.full_name || "Guest Customer"}</div>
                        <div className="text-xs text-slate-500 flex items-center gap-1.5">
                          <Mail className="h-3.5 w-3.5" />
                          {details.participant.email}
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono">
                          ID: {details.participant.user_id}
                        </div>
                      </div>
                    ) : (
                      <span className="text-xs text-slate-400 italic">Anonymous/Guest Client</span>
                    )}
                  </div>

                  {/* Associated Ticket Card */}
                  <div className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-850 p-4 rounded-xl">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-1.5">
                      <FileText className="h-3.5 w-3.5 text-violet-600" />
                      Ticket Association
                    </h3>
                    {details.ticket ? (
                      <div className="space-y-2">
                        <div className="text-sm font-semibold flex justify-between items-center">
                          <span>{details.ticket.ticket_id}</span>
                          <span className={`text-[9px] uppercase font-bold tracking-wider px-1.5 rounded border ${
                            details.ticket.status === "open" ? "bg-red-50 text-red-600 border-red-200" :
                            details.ticket.status === "in_progress" ? "bg-yellow-50 text-yellow-600 border-yellow-200" :
                            "bg-green-50 text-green-600 border-green-200"
                          }`}>
                            {details.ticket.status}
                          </span>
                        </div>
                        <div className="text-xs font-medium text-slate-600 dark:text-slate-300 truncate">
                          {details.ticket.subject}
                        </div>
                        <div className="flex gap-2 text-[10px]">
                          <span className="px-1.5 py-0.5 bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400 rounded">
                            {details.ticket.priority} priority
                          </span>
                          <span className="px-1.5 py-0.5 bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400 rounded">
                            {details.ticket.category}
                          </span>
                        </div>
                      </div>
                    ) : (
                      <span className="text-xs text-slate-400 italic">No registered support tickets associated.</span>
                    )}
                  </div>
                </div>

                {/* Timeline */}
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-4 flex items-center gap-1.5">
                    <Layers className="h-3.5 w-3.5 text-violet-600" />
                    Chronological Message Timeline
                  </h3>
                  <div className="space-y-6">
                    {details.messages.length === 0 ? (
                      <div className="text-center py-10 text-xs text-slate-400 italic">
                        Empty conversation history log.
                      </div>
                    ) : (
                      details.messages.map((msg, i) => (
                        <div 
                          key={msg.message_id || i}
                          className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}
                        >
                          <div className="text-[10px] text-slate-400 font-medium mb-1 px-1">
                            {msg.role === "user" ? "Customer" : "AI Agent"} • {new Date(msg.created_at).toLocaleString()}
                          </div>

                          <div className={`p-4 rounded-2xl max-w-xl text-sm leading-relaxed shadow-sm border ${
                            msg.role === "user" 
                              ? "bg-violet-600 border-violet-500 text-white rounded-tr-none" 
                              : "bg-slate-50 dark:bg-slate-950 border-slate-200 dark:border-slate-850 rounded-tl-none text-slate-800 dark:text-slate-200"
                          }`}>
                            {msg.content}
                          </div>

                          {/* Metadata logs */}
                          {msg.role === "user" && msg.intent && (
                            <div className="mt-1.5 flex gap-1.5 text-[10px] font-semibold text-slate-500">
                              <span className="flex items-center gap-1 px-2 py-0.5 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-800 rounded-md">
                                <Tag className="h-3 w-3 text-violet-600" />
                                Intent: {msg.intent}
                              </span>
                            </div>
                          )}

                          {msg.role === "assistant" && (msg.agent || msg.sources || msg.confidence_score) && (
                            <div className="mt-1.5 flex flex-wrap gap-1.5 text-[10px] font-semibold text-slate-500">
                              {msg.agent && (
                                <span className="flex items-center gap-1 px-2 py-0.5 bg-slate-150 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-850 rounded-md">
                                  <Bot className="h-3 w-3 text-indigo-500" />
                                  Agent: {msg.agent}
                                </span>
                              )}
                              {msg.confidence_score !== undefined && msg.confidence_score !== null && (
                                <span className="flex items-center gap-1 px-2 py-0.5 bg-slate-150 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-850 rounded-md">
                                  <ShieldCheck className="h-3 w-3 text-green-500" />
                                  Conf: {(msg.confidence_score * 100).toFixed(0)}%
                                </span>
                              )}
                              {msg.sources && msg.sources.length > 0 && (
                                <div className="w-full mt-1.5 space-y-1 pl-1">
                                  <div className="text-[9px] uppercase font-bold text-slate-400 flex items-center gap-1">
                                    <Compass className="h-3 w-3 text-blue-500" />
                                    Knowledge Sources Retrieved
                                  </div>
                                  <div className="flex flex-wrap gap-1 mt-1">
                                    {msg.sources.map((s, idx) => (
                                      <span key={idx} className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-50 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-900/30 text-blue-600 dark:text-blue-400 rounded-md text-[9px] font-medium">
                                        {s.source} (Page {s.page})
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
