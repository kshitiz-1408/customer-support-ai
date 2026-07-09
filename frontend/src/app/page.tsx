"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { api } from "@/services/api";
import { Ticket, TicketCreate, TicketUpdate, KBSearchResult, TicketStatus, TicketPriority, TicketCategory } from "@/types";
import Navbar from "@/components/layout/Navbar";
import Sidebar from "@/components/layout/Sidebar";
import { 
  Search, 
  Loader2, 
  CheckCircle2, 
  Clock, 
  AlertCircle, 
  BookOpen, 
  User, 
  Folder, 
  ChevronRight, 
  Filter, 
  Sparkles, 
  Trash2,
  Check,
  AlertTriangle,
  MessageSquare,
  ArrowRight
} from "lucide-react";

export default function SupportDashboard() {
  // Tickets state
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selectedTicket, setSelectedTicket] = useState<Ticket | null>(null);
  const [ticketsFilter, setTicketsFilter] = useState<string>("all");
  const [ticketsLoading, setTicketsLoading] = useState<boolean>(true);
  const [ticketsError, setTicketsError] = useState<string | null>(null);

  // KB state
  const [kbQuery, setKbQuery] = useState<string>("");
  const [kbResults, setKbResults] = useState<KBSearchResult[]>([]);
  const [kbLoading, setKbLoading] = useState<boolean>(false);

  // New ticket form state
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [newTicket, setNewTicket] = useState<TicketCreate>({
    customer_name: "",
    customer_email: "",
    subject: "",
    description: "",
    priority: "medium",
    category: "general"
  });
  const [formSubmitting, setFormSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Inspector edit state
  const [inspectorNotes, setInspectorNotes] = useState<string>("");
  const [inspectorStatus, setInspectorStatus] = useState<TicketStatus>("open");
  const [inspectorAgent, setInspectorAgent] = useState<string>("");
  const [updatingTicketId, setUpdatingTicketId] = useState<number | null>(null);





  const fetchTickets = async (statusFilter?: string) => {
    try {
      setTicketsLoading(true);
      setTicketsError(null);
      let endpoint = "/tickets/";
      if (statusFilter && statusFilter !== "all") {
        endpoint += `?status=${statusFilter}`;
      }
      const response = await api.get<Ticket[]>(endpoint);
      setTickets(response.data);
      
      if (selectedTicket) {
        const updatedSelected = response.data.find(t => t.id === selectedTicket.id);
        if (updatedSelected) {
          setSelectedTicket(updatedSelected);
        } else {
          setSelectedTicket(null);
        }
      }
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (err: any) {
      setTicketsError(err.message || "Failed to load tickets");
    } finally {
      setTicketsLoading(false);
    }
  };

  const fetchKB = async (query = "") => {
    try {
      setKbLoading(true);
      const endpoint = query ? `/kb/search?q=${encodeURIComponent(query)}` : "/kb/search";
      const response = await api.get<KBSearchResult[]>(endpoint);
      setKbResults(response.data);
    } catch (err) {
      console.error("Failed to fetch knowledge base", err);
    } finally {
      setKbLoading(false);
    }
  };

  // Load tickets on mount
  useEffect(() => {
    setTimeout(() => {
      fetchTickets();
      fetchKB();
    }, 0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Search KB when query changes
  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      fetchKB(kbQuery);
    }, 300);

    return () => clearTimeout(delayDebounceFn);
  }, [kbQuery]);

  // Sync inspector inputs when selected ticket changes
  useEffect(() => {
    if (selectedTicket) {
      setTimeout(() => {
        setInspectorNotes(selectedTicket.resolution_notes || "");
        setInspectorStatus(selectedTicket.status);
        setInspectorAgent(selectedTicket.assigned_agent || "");
      }, 0);
    }
  }, [selectedTicket]);

  const handleFilterChange = (filter: string) => {
    setTicketsFilter(filter);
    fetchTickets(filter);
  };

  const handleCreateTicket = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormSubmitting(true);
    setFormError(null);

    try {
      await api.post<Ticket>("/tickets/", newTicket);
      setNewTicket({
        customer_name: "",
        customer_email: "",
        subject: "",
        description: "",
        priority: "medium",
        category: "general"
      });
      setIsModalOpen(false);
      fetchTickets(ticketsFilter);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (err: any) {
      setFormError(err.message || "Failed to create ticket.");
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleUpdateTicket = async (id: number) => {
    setUpdatingTicketId(id);
    try {
      const updateData: TicketUpdate = {
        status: inspectorStatus,
        assigned_agent: inspectorAgent || undefined,
        resolution_notes: inspectorNotes || undefined
      };
      
      const response = await api.put<Ticket>(`/tickets/${id}`, updateData);
      setTickets(prev => prev.map(t => t.id === id ? response.data : t));
      setSelectedTicket(response.data);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (err: any) {
      alert(`Update failed: ${err.message}`);
    } finally {
      setUpdatingTicketId(null);
    }
  };

  const handleDeleteTicket = async (id: number) => {
    if (!confirm("Are you sure you want to delete this ticket?")) return;
    
    try {
      await api.delete(`/tickets/${id}`);
      if (selectedTicket?.id === id) {
        setSelectedTicket(null);
      }
      setTickets(prev => prev.filter(t => t.id !== id));
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  const getPriorityStyles = (priority: TicketPriority) => {
    switch (priority) {
      case "urgent": return "bg-rose-500/10 text-rose-400 border border-rose-500/20";
      case "high": return "bg-amber-500/10 text-amber-400 border border-amber-500/20";
      case "medium": return "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20";
      case "low": return "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
    }
  };

  const getStatusStyles = (status: TicketStatus) => {
    switch (status) {
      case "open": return "bg-sky-500/15 text-sky-400 border border-sky-500/30";
      case "in_progress": return "bg-violet-500/15 text-violet-400 border border-violet-500/30";
      case "resolved": return "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30";
      case "closed": return "bg-zinc-500/15 text-zinc-400 border border-zinc-500/30";
    }
  };

  const openCount = tickets.filter(t => t.status === "open").length;
  const inProgressCount = tickets.filter(t => t.status === "in_progress").length;
  const resolvedCount = tickets.filter(t => t.status === "resolved").length;

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col selection:bg-indigo-500/30">
      
      {/* Background Neon Gradients */}
      <div className="absolute top-0 left-1/4 -translate-x-1/2 w-96 h-96 bg-indigo-500/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute top-1/3 right-1/4 w-96 h-96 bg-violet-600/5 rounded-full blur-[150px] pointer-events-none" />
      
      {/* Shared Header Navigation */}
      <Navbar />

      <div className="flex-1 flex max-w-7xl mx-auto w-full relative">
        {/* Navigation Sidebar */}
        <Sidebar />

        {/* Dashboard Workspace */}
        <main className="flex-grow p-6 space-y-6">
          
          {/* Hero Section Banner linking to Chat */}
          <section className="relative overflow-hidden rounded-2xl border border-indigo-500/30 bg-gradient-to-r from-indigo-950/40 via-zinc-900/50 to-zinc-900/40 p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 backdrop-blur-md">
            <div className="absolute top-0 right-0 w-48 h-48 bg-gradient-to-br from-indigo-500/10 to-violet-500/10 rounded-full blur-2xl pointer-events-none" />
            <div className="space-y-1.5 z-10">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-indigo-400 animate-pulse" />
                Diagnostic Chat Assistance Active
              </h2>
              <p className="text-xs text-zinc-400 max-w-xl leading-relaxed">
                Connect with the AI virtual agent to query endpoints, perform automated database validations, and trace logs in real-time.
              </p>
            </div>
            <Link 
              href="/chat"
              className="z-10 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold py-2.5 px-4 rounded-lg flex items-center gap-1.5 shadow-lg shadow-indigo-500/15 hover:shadow-indigo-500/25 transition-all duration-200 transform active:scale-95 cursor-pointer hover:translate-x-0.5 shrink-0"
            >
              <MessageSquare className="h-4.5 w-4.5" />
              Launch Chat Session
              <ArrowRight className="h-4 w-4" />
            </Link>
          </section>

          {/* Metric Cards */}
          <section className="grid grid-cols-1 sm:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl backdrop-blur-md bg-zinc-900/40 border border-zinc-850 flex items-center justify-between">
              <div>
                <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">Open Cases</p>
                <h3 className="text-xl font-bold mt-0.5 text-sky-400">{openCount}</h3>
              </div>
              <div className="h-8 w-8 rounded-lg bg-sky-500/10 flex items-center justify-center text-sky-400 border border-sky-500/20">
                <AlertCircle className="h-4.5 w-4.5" />
              </div>
            </div>

            <div className="p-4 rounded-xl backdrop-blur-md bg-zinc-900/40 border border-zinc-850 flex items-center justify-between">
              <div>
                <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">In Progress</p>
                <h3 className="text-xl font-bold mt-0.5 text-violet-400">{inProgressCount}</h3>
              </div>
              <div className="h-8 w-8 rounded-lg bg-violet-500/10 flex items-center justify-center text-violet-400 border border-violet-500/20">
                <Clock className="h-4.5 w-4.5" />
              </div>
            </div>

            <div className="p-4 rounded-xl backdrop-blur-md bg-zinc-900/40 border border-zinc-850 flex items-center justify-between">
              <div>
                <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">Resolved</p>
                <h3 className="text-xl font-bold mt-0.5 text-emerald-400">{resolvedCount}</h3>
              </div>
              <div className="h-8 w-8 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400 border border-emerald-500/20">
                <CheckCircle2 className="h-4.5 w-4.5" />
              </div>
            </div>

            <div className="p-4 rounded-xl backdrop-blur-md bg-zinc-900/40 border border-zinc-850 flex items-center justify-between">
              <div>
                <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider">KB Articles</p>
                <h3 className="text-xl font-bold mt-0.5 text-indigo-400">{kbResults.length}</h3>
              </div>
              <div className="h-8 w-8 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400 border border-indigo-500/20">
                <BookOpen className="h-4.5 w-4.5" />
              </div>
            </div>
          </section>

          {/* Core Content Queue */}
          <section className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            
            {/* Left Queue */}
            <div className="lg:col-span-7 space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-bold text-zinc-200 flex items-center gap-2">
                  <Filter className="h-4 w-4 text-zinc-400" />
                  Tickets Workspace
                </h2>
                
                <div className="flex rounded-lg bg-zinc-900 p-1 border border-zinc-800">
                  {["all", "open", "in_progress", "resolved"].map((tab) => (
                    <button
                      key={tab}
                      onClick={() => handleFilterChange(tab)}
                      className={`px-2.5 py-1 text-[11px] font-bold capitalize rounded-md transition-all cursor-pointer ${
                        ticketsFilter === tab 
                          ? "bg-zinc-800 text-white shadow-sm" 
                          : "text-zinc-400 hover:text-zinc-200"
                      }`}
                    >
                      {tab.replace("_", " ")}
                    </button>
                  ))}
                </div>
              </div>

              {ticketsError && (
                <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex gap-2.5 items-center">
                  <AlertTriangle className="h-4.5 w-4.5 shrink-0" />
                  <span>Ensure the FastAPI backend is running locally.</span>
                </div>
              )}

              <div className="space-y-3">
                {ticketsLoading ? (
                  <div className="py-12 flex flex-col items-center justify-center gap-3 border border-zinc-900 rounded-xl">
                    <Loader2 className="h-6 w-6 animate-spin text-indigo-500" />
                    <p className="text-xs text-zinc-500">Loading cases...</p>
                  </div>
                ) : tickets.length === 0 ? (
                  <div className="py-12 flex flex-col items-center justify-center gap-2 border border-zinc-900 rounded-xl text-center">
                    <CheckCircle2 className="h-7 w-7 text-zinc-650" />
                    <h4 className="text-zinc-400 text-xs font-bold mt-2">All Clear</h4>
                    <p className="text-[11px] text-zinc-500">No cases match filters.</p>
                  </div>
                ) : (
                  tickets.map((ticket) => (
                    <div
                      key={ticket.id}
                      onClick={() => setSelectedTicket(ticket)}
                      className={`p-4 rounded-xl border transition-all cursor-pointer text-left ${
                        selectedTicket?.id === ticket.id
                          ? "bg-indigo-500/5 border-indigo-500/40 shadow-sm"
                          : "bg-zinc-900/30 border-zinc-850 hover:border-zinc-700"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="space-y-1">
                          <span className={`text-[9px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full ${getPriorityStyles(ticket.priority)}`}>
                            {ticket.priority}
                          </span>
                          <h4 className="font-bold text-zinc-200 text-xs mt-1.5">
                            {ticket.subject}
                          </h4>
                        </div>
                        <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full ${getStatusStyles(ticket.status)}`}>
                          {ticket.status.replace("_", " ")}
                        </span>
                      </div>
                      <p className="text-[11px] text-zinc-400 mt-2 line-clamp-2">
                        {ticket.description}
                      </p>
                      <div className="mt-4 pt-3 border-t border-zinc-900 flex items-center justify-between text-[10px] text-zinc-500">
                        <div className="flex items-center gap-1.5">
                          <User className="h-3 w-3" />
                          <span className="font-bold text-zinc-400">{ticket.customer_name}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <Folder className="h-3 w-3" />
                          <span className="capitalize font-bold">{ticket.category}</span>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Right Queue */}
            <div className="lg:col-span-5 space-y-6">
              
              {/* Case Inspector */}
              <div className="p-4 rounded-xl border border-zinc-850 bg-zinc-900/20 backdrop-blur-md">
                <h3 className="text-xs font-bold text-zinc-200 border-b border-zinc-900 pb-3 mb-4 flex items-center gap-1.5">
                  <ChevronRight className="h-4 w-4 text-indigo-500 rotate-95" />
                  Details Inspector
                </h3>

                {!selectedTicket ? (
                  <div className="py-12 text-center text-zinc-500">
                    <AlertCircle className="h-6 w-6 mx-auto mb-2 text-zinc-700" />
                    <p className="text-[11px]">Select a case to inspect detail workflows.</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div>
                      <h4 className="text-sm font-bold text-white">{selectedTicket.subject}</h4>
                      <p className="text-[10px] text-indigo-400 font-bold mt-0.5">ID: #{selectedTicket.id}</p>
                    </div>

                    <div className="p-3 bg-zinc-900/50 border border-zinc-850 rounded-lg space-y-2 text-[11px]">
                      <div className="flex justify-between">
                        <span className="text-zinc-500 font-medium">Customer:</span>
                        <span className="text-zinc-300 font-bold">{selectedTicket.customer_name}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-zinc-500 font-medium">Category:</span>
                        <span className="text-zinc-300 font-bold capitalize">{selectedTicket.category}</span>
                      </div>
                    </div>

                    <p className="text-[11px] text-zinc-300 bg-zinc-900/30 p-3 border border-zinc-900 rounded-lg">
                      {selectedTicket.description}
                    </p>

                    <form onSubmit={(e) => { e.preventDefault(); handleUpdateTicket(selectedTicket.id); }} className="space-y-4 pt-3 border-t border-zinc-900">
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="text-[9px] font-bold text-zinc-500 block mb-1">Status</label>
                          <select
                            value={inspectorStatus}
                            onChange={(e) => setInspectorStatus(e.target.value as TicketStatus)}
                            className="w-full text-xs font-semibold rounded-lg bg-zinc-900 border border-zinc-800 p-2 text-zinc-300 focus:outline-none"
                          >
                            <option value="open">Open</option>
                            <option value="in_progress">In Progress</option>
                            <option value="resolved">Resolved</option>
                            <option value="closed">Closed</option>
                          </select>
                        </div>
                        <div>
                          <label className="text-[9px] font-bold text-zinc-500 block mb-1">Agent</label>
                          <input
                            type="text"
                            placeholder="Name..."
                            value={inspectorAgent}
                            onChange={(e) => setInspectorAgent(e.target.value)}
                            className="w-full text-xs font-semibold rounded-lg bg-zinc-900 border border-zinc-800 p-2 text-zinc-300 focus:outline-none"
                          />
                        </div>
                      </div>

                      <div className="flex gap-2">
                        <button
                          type="submit"
                          disabled={updatingTicketId === selectedTicket.id}
                          className="flex-grow py-2.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-white text-xs font-bold transition-all flex items-center justify-center gap-1.5 border border-zinc-750 cursor-pointer"
                        >
                          {updatingTicketId === selectedTicket.id ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            <Check className="h-3.5 w-3.5 text-indigo-400" />
                          )}
                          Update Case
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteTicket(selectedTicket.id)}
                          className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 cursor-pointer hover:bg-rose-500/15"
                        >
                          <Trash2 className="h-4.5 w-4.5" />
                        </button>
                      </div>
                    </form>
                  </div>
                )}
              </div>

              {/* Knowledge Base */}
              <div className="p-4 rounded-xl border border-zinc-850 bg-zinc-900/20 backdrop-blur-md">
                <h3 className="text-xs font-bold text-zinc-200 border-b border-zinc-900 pb-3 mb-4 flex items-center gap-1.5">
                  <BookOpen className="h-4 w-4 text-indigo-500" />
                  Knowledge Base Lookup
                </h3>

                <div className="relative mb-4">
                  <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-zinc-500" />
                  <input
                    type="text"
                    placeholder="Search docs..."
                    value={kbQuery}
                    onChange={(e) => setKbQuery(e.target.value)}
                    className="w-full text-xs font-semibold rounded-lg bg-zinc-950 border border-zinc-850 pl-8 pr-3 py-2 text-zinc-300 focus:outline-none"
                  />
                </div>

                <div className="space-y-2.5 max-h-[220px] overflow-y-auto pr-0.5">
                  {kbLoading ? (
                    <div className="py-6 flex justify-center">
                      <Loader2 className="h-5 w-5 animate-spin text-indigo-500" />
                    </div>
                  ) : kbResults.length === 0 ? (
                    <p className="text-center text-[11px] text-zinc-650 py-4">No results</p>
                  ) : (
                    kbResults.map(({ article, score }) => (
                      <div key={article.id} className="p-2.5 rounded-lg bg-zinc-900/30 border border-zinc-850 text-left">
                        <div className="flex justify-between items-center gap-2">
                          <h4 className="text-[11px] font-bold text-zinc-300">{article.title}</h4>
                          <span className="text-[8px] text-zinc-500 font-mono">Score: {score.toFixed(1)}</span>
                        </div>
                        <p className="text-[10px] text-zinc-450 mt-1 line-clamp-2 leading-relaxed">
                          {article.content}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </div>

            </div>

          </section>

        </main>
      </div>

      {/* Creation Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-zinc-950/80 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-md rounded-xl bg-zinc-900 border border-zinc-800 shadow-2xl p-6 relative">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3 mb-4">
              <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
                <Sparkles className="h-4.5 w-4.5 text-indigo-400" />
                Submit New Support Case
              </h3>
              <button 
                onClick={() => setIsModalOpen(false)}
                className="text-zinc-400 hover:text-zinc-200 text-xs p-1 cursor-pointer"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateTicket} className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[9px] font-bold text-zinc-500 block mb-1">Customer Name</label>
                  <input
                    type="text" required placeholder="Alice Cooper"
                    value={newTicket.customer_name}
                    onChange={(e) => setNewTicket(prev => ({ ...prev, customer_name: e.target.value }))}
                    className="w-full text-xs font-semibold rounded-lg bg-zinc-950 border border-zinc-800 p-2.5 text-zinc-350 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-[9px] font-bold text-zinc-500 block mb-1">Customer Email</label>
                  <input
                    type="email" required placeholder="alice@email.com"
                    value={newTicket.customer_email}
                    onChange={(e) => setNewTicket(prev => ({ ...prev, customer_email: e.target.value }))}
                    className="w-full text-xs font-semibold rounded-lg bg-zinc-950 border border-zinc-800 p-2.5 text-zinc-350 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="text-[9px] font-bold text-zinc-500 block mb-1">Subject</label>
                <input
                  type="text" required placeholder="Subject..."
                  value={newTicket.subject}
                  onChange={(e) => setNewTicket(prev => ({ ...prev, subject: e.target.value }))}
                  className="w-full text-xs font-semibold rounded-lg bg-zinc-950 border border-zinc-800 p-2.5 text-zinc-350 focus:outline-none"
                />
              </div>

              <div>
                <label className="text-[9px] font-bold text-zinc-500 block mb-1">Description</label>
                <textarea
                  rows={3} required placeholder="Description details..."
                  value={newTicket.description}
                  onChange={(e) => setNewTicket(prev => ({ ...prev, description: e.target.value }))}
                  className="w-full text-xs font-semibold rounded-lg bg-zinc-950 border border-zinc-800 p-2.5 text-zinc-350 focus:outline-none resize-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[9px] font-bold text-zinc-500 block mb-1">Priority</label>
                  <select
                    value={newTicket.priority}
                    onChange={(e) => setNewTicket(prev => ({ ...prev, priority: e.target.value as TicketPriority }))}
                    className="w-full text-xs font-semibold rounded-lg bg-zinc-950 border border-zinc-800 p-2.5 text-zinc-350 focus:outline-none"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </div>
                <div>
                  <label className="text-[9px] font-bold text-zinc-500 block mb-1">Category</label>
                  <select
                    value={newTicket.category}
                    onChange={(e) => setNewTicket(prev => ({ ...prev, category: e.target.value as TicketCategory }))}
                    className="w-full text-xs font-semibold rounded-lg bg-zinc-950 border border-zinc-800 p-2.5 text-zinc-350 focus:outline-none"
                  >
                    <option value="general">General</option>
                    <option value="billing">Billing</option>
                    <option value="technical">Technical</option>
                    <option value="account">Account</option>
                  </select>
                </div>
              </div>

              {formError && (
                <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-450 text-[10px] font-bold">
                  {formError}
                </div>
              )}

              <div className="flex gap-2 pt-3 border-t border-zinc-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="flex-1 py-2 rounded-lg bg-zinc-950 border border-zinc-850 hover:bg-zinc-900 text-zinc-400 text-xs font-bold cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="flex-1 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold transition-all flex items-center justify-center gap-1.5 cursor-pointer shadow-lg shadow-indigo-500/10"
                >
                  {formSubmitting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <span>Submit</span>}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
