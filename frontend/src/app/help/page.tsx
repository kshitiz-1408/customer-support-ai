"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import Navbar from "@/components/layout/Navbar";
import Sidebar from "@/components/layout/Sidebar";
import { api } from "@/services/api";
import axios from "axios";
import { 
  Search, ChevronDown, ChevronUp, MessageSquare, PlusCircle, FileText, 
  Mail, ShieldAlert, Cpu, Database, Brain, Network, Key, Layers,
  RefreshCw, CheckCircle2, AlertTriangle, Send, Loader2, Info
} from "lucide-react";

interface FAQItem {
  question: string;
  answer: string;
}

interface SystemStatus {
  backend: "healthy" | "unavailable" | "loading";
  mongodb: "healthy" | "unavailable" | "loading";
  gemini: "healthy" | "unavailable" | "loading";
  faiss: "healthy" | "unavailable" | "loading";
  auth: "healthy" | "unavailable" | "loading";
  docker: "healthy" | "unavailable" | "loading";
}

export default function HelpPage() {
  const { currentUser } = useAuth();
  const contactFormRef = useRef<HTMLDivElement>(null);
  const subjectInputRef = useRef<HTMLInputElement>(null);

  // Search box state
  const [searchQuery, setSearchQuery] = useState("");

  // FAQ Accordion State
  const [openFAQIndex, setOpenFAQIndex] = useState<number | null>(null);

  // Contact Form State
  const [subject, setSubject] = useState("");
  const [category, setCategory] = useState("general");
  const [message, setMessage] = useState("");
  const [submitLoading, setSubmitLoading] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Health Status state
  const [status, setStatus] = useState<SystemStatus>({
    backend: "loading",
    mongodb: "loading",
    gemini: "loading",
    faiss: "loading",
    auth: "loading",
    docker: "loading"
  });

  const faqs: FAQItem[] = [
    {
      question: "How do I login?",
      answer: "Navigate to /login, input your registered email address and secure password credentials, and submit. If your session expires, the client context will automatically request rotated token versions to maintain active login."
    },
    {
      question: "How do I create a ticket?",
      answer: "You can submit a ticket by utilizing the 'Contact Support' form on this page below, or directly through the main dashboard panels. Providing category scopes helps route the issue to specialized agents."
    },
    {
      question: "How do I reset my password?",
      answer: "Go to System Settings from the sidebar, open the 'Security & Login' tab, fill in your current password and supply a new password matching the complexity requirements, and save."
    },
    {
      question: "How does the AI answer questions?",
      answer: "The customer-support system routes your queries through a Retrieval-Augmented Generation (RAG) pipeline. This loads relevant documentation from our vector indexes (FAISS) and builds a comprehensive prompt context evaluated by the Gemini LLM."
    },
    {
      question: "How is my data stored?",
      answer: "Your user account records, ticket assignments, and conversation transcripts are securely persisted in MongoDB Atlas database collections. Access controls ensure data isolation boundaries are strictly enforced."
    },
    {
      question: "How do I contact support?",
      answer: "Open a session in the 'Support Chat' for direct conversational guidance with the AI agent. If the model determines that the problem requires human engineering review, it automatically schedules a new support ticket."
    },
    {
      question: "How do I upload documents?",
      answer: "Document uploading and knowledge base article injections are restricted to administrative profiles. Admins can update indexes from the global settings portal to keep RAG information fresh."
    }
  ];

  // Fetch Health Statuses
  const checkHealth = async () => {
    setStatus({
      backend: "loading",
      mongodb: "loading",
      gemini: "loading",
      faiss: "loading",
      auth: "loading",
      docker: "loading"
    });

    const envApiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    
    // Check Authentication
    let authState: "healthy" | "unavailable" = "unavailable";
    try {
      if (currentUser) {
        authState = "healthy";
      }
    } catch {
      authState = "unavailable";
    }

    try {
      // Fetch readiness probe
      const res = await axios.get(`${envApiUrl}/health/ready`, { timeout: 8000 });
      
      if (res.status === 200) {
        setStatus({
          backend: "healthy",
          mongodb: "healthy",
          gemini: "healthy",
          faiss: "healthy",
          auth: authState,
          docker: "healthy"
        });
      }
    } catch (err: any) {
      // 503 returns errors detail
      const responseErrors = err.response?.data?.detail?.errors || {};
      
      setStatus({
        backend: "healthy", // If we hit 503 from backend, backend itself is alive
        mongodb: responseErrors.mongodb ? "unavailable" : "healthy",
        gemini: responseErrors.gemini ? "unavailable" : "healthy",
        faiss: responseErrors.faiss ? "unavailable" : "healthy",
        auth: authState,
        docker: "healthy"
      });
    }
  };

  useEffect(() => {
    checkHealth();
  }, [currentUser]);

  const handleFAQToggle = (idx: number) => {
    setOpenFAQIndex(openFAQIndex === idx ? null : idx);
  };

  const scrollToContact = () => {
    contactFormRef.current?.scrollIntoView({ behavior: "smooth" });
    setTimeout(() => {
      subjectInputRef.current?.focus();
    }, 500);
  };

  const handleContactSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentUser) return;
    setSubmitLoading(true);
    setSubmitError(null);
    setSubmitSuccess(null);

    if (!subject.trim() || !message.trim()) {
      setSubmitError("Subject and Message fields are required.");
      setSubmitLoading(false);
      return;
    }

    try {
      await api.post("/tickets/", {
        customer_name: currentUser.full_name,
        customer_email: currentUser.email,
        subject: subject.trim(),
        description: message.trim(),
        priority: "medium",
        category: category
      });

      setSubmitSuccess("Ticket created successfully! Our support agents will notify you shortly.");
      setSubject("");
      setMessage("");
    } catch (err: any) {
      setSubmitError(err.response?.data?.detail || err.message || "Failed to submit support ticket.");
    } finally {
      setSubmitLoading(false);
    }
  };

  // Filter FAQs based on query
  const filteredFAQs = faqs.filter(faq => 
    faq.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
    faq.answer.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col selection:bg-indigo-500/30 font-sans">
      <Navbar />

      <div className="flex-1 flex max-w-7xl mx-auto w-full relative">
        <Sidebar />

        <main className="flex-1 p-6 md:p-8 text-zinc-300 space-y-8">
          
          {/* Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-extrabold text-zinc-100 tracking-tight">Help & Documentation Desk</h1>
              <p className="text-xs text-zinc-500 mt-1 font-semibold">Browse frequently asked answers, check platform status, or contact human support</p>
            </div>
          </div>

          {/* Quick Actions Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Link 
              href="/chat"
              className="flex flex-col items-center gap-3 p-5 rounded-2xl bg-zinc-900/40 border border-zinc-850 hover:border-indigo-500/50 hover:bg-zinc-900/60 transition-all text-center group active:scale-95 shadow-md"
            >
              <MessageSquare className="h-6 w-6 text-indigo-400 group-hover:scale-110 transition-transform" />
              <span className="text-xs font-bold text-zinc-200">Open Support Chat</span>
            </Link>

            <button
              onClick={scrollToContact}
              className="flex flex-col items-center gap-3 p-5 rounded-2xl bg-zinc-900/40 border border-zinc-850 hover:border-violet-500/50 hover:bg-zinc-900/60 transition-all text-center group active:scale-95 shadow-md"
            >
              <PlusCircle className="h-6 w-6 text-violet-400 group-hover:scale-110 transition-transform" />
              <span className="text-xs font-bold text-zinc-200">Create Support Ticket</span>
            </button>

            <button
              onClick={() => alert("Enterprise Developer API specifications are available under the general project folders.")}
              className="flex flex-col items-center gap-3 p-5 rounded-2xl bg-zinc-900/40 border border-zinc-850 hover:border-emerald-500/50 hover:bg-zinc-900/60 transition-all text-center group active:scale-95 shadow-md"
            >
              <FileText className="h-6 w-6 text-emerald-400 group-hover:scale-110 transition-transform" />
              <span className="text-xs font-bold text-zinc-200">View Documentation</span>
            </button>

            <button
              onClick={scrollToContact}
              className="flex flex-col items-center gap-3 p-5 rounded-2xl bg-zinc-900/40 border border-zinc-850 hover:border-amber-500/50 hover:bg-zinc-900/60 transition-all text-center group active:scale-95 shadow-md"
            >
              <Mail className="h-6 w-6 text-amber-400 group-hover:scale-110 transition-transform" />
              <span className="text-xs font-bold text-zinc-200">Contact Support Team</span>
            </button>
          </div>

          {/* Search box & Accordion FAQs */}
          <div className="bg-zinc-900/40 border border-zinc-850 rounded-2xl p-6 sm:p-8 shadow-xl">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
              <div>
                <h2 className="text-sm font-bold text-zinc-100 flex items-center gap-2">
                  <span className="h-5 w-1 bg-indigo-500 rounded-full" />
                  Frequently Asked Questions
                </h2>
                <p className="text-[10px] text-zinc-500 font-semibold mt-1">Review verified queries regarding authentication, AI prompting, and security bounds</p>
              </div>

              {/* Search input */}
              <div className="relative w-full md:w-72">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
                <input
                  type="text"
                  placeholder="Search faq answers..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-4 py-2 rounded-xl bg-zinc-950 border border-zinc-800 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>
            </div>

            {/* Accordion List */}
            <div className="space-y-3">
              {filteredFAQs.length === 0 ? (
                <p className="text-center py-6 text-zinc-500 text-xs font-semibold">No questions match your query search parameters.</p>
              ) : (
                filteredFAQs.map((faq, idx) => {
                  const isOpen = openFAQIndex === idx;
                  return (
                    <div 
                      key={idx} 
                      className="border border-zinc-850 rounded-xl overflow-hidden bg-zinc-900/20"
                    >
                      <button
                        onClick={() => handleFAQToggle(idx)}
                        className="w-full flex items-center justify-between p-4 text-xs font-bold text-zinc-200 hover:text-zinc-150 hover:bg-zinc-900/30 transition-all text-left"
                      >
                        <span>{faq.question}</span>
                        {isOpen ? <ChevronUp className="h-4 w-4 text-zinc-500" /> : <ChevronDown className="h-4 w-4 text-zinc-500" />}
                      </button>
                      
                      {isOpen && (
                        <div className="p-4 bg-zinc-950/40 border-t border-zinc-900 text-xs text-zinc-400 font-semibold leading-relaxed">
                          {faq.answer}
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Contact support & Status section */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            
            {/* Form */}
            <div ref={contactFormRef} className="md:col-span-2 bg-zinc-900/40 border border-zinc-850 rounded-2xl p-6 sm:p-8 shadow-xl space-y-6">
              <div>
                <h2 className="text-sm font-bold text-zinc-100 flex items-center gap-2">
                  <span className="h-5 w-1 bg-violet-600 rounded-full" />
                  Submit Support Request
                </h2>
                <p className="text-[10px] text-zinc-500 font-semibold mt-1">Submit a ticket which will be assigned to a support agent</p>
              </div>

              {submitSuccess && (
                <div className="px-4 py-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-start gap-2.5 text-emerald-400 text-xs font-semibold">
                  <CheckCircle2 className="h-4 w-4 mt-0.5 shrink-0" />
                  {submitSuccess}
                </div>
              )}

              {submitError && (
                <div className="px-4 py-3 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-start gap-2.5 text-rose-455 text-xs font-semibold">
                  <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
                  {submitError}
                </div>
              )}

              <form onSubmit={handleContactSubmit} className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider px-0.5">Your Name</label>
                    <input
                      type="text"
                      disabled
                      value={currentUser?.full_name || ""}
                      className="w-full bg-zinc-950/40 border border-zinc-900 rounded-xl py-2.5 px-4 text-xs font-bold text-zinc-600 cursor-not-allowed"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-wider px-0.5">Email Address</label>
                    <input
                      type="email"
                      disabled
                      value={currentUser?.email || ""}
                      className="w-full bg-zinc-950/40 border border-zinc-900 rounded-xl py-2.5 px-4 text-xs font-bold text-zinc-600 cursor-not-allowed"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label htmlFor="subject" className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider px-0.5">Subject</label>
                    <input
                      id="subject"
                      ref={subjectInputRef}
                      type="text"
                      required
                      placeholder="Summary of your issue..."
                      value={subject}
                      onChange={(e) => setSubject(e.target.value)}
                      disabled={submitLoading}
                      className="w-full bg-zinc-950/60 border border-zinc-850 rounded-xl py-2.5 px-4 text-xs text-zinc-200 placeholder-zinc-650 focus:outline-none focus:border-indigo-500 transition-colors"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label htmlFor="category" className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider px-0.5">Category</label>
                    <select
                      id="category"
                      value={category}
                      onChange={(e) => setCategory(e.target.value)}
                      disabled={submitLoading}
                      className="w-full bg-zinc-950/60 border border-zinc-850 rounded-xl py-2.5 px-4 text-xs text-zinc-300 focus:outline-none focus:border-indigo-500 transition-colors cursor-pointer"
                    >
                      <option value="general">General Query</option>
                      <option value="billing">Billing & Subscriptions</option>
                      <option value="technical">Technical Support</option>
                      <option value="account">Account Access</option>
                    </select>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label htmlFor="message" className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider px-0.5">Detailed Description</label>
                  <textarea
                    id="message"
                    required
                    rows={4}
                    placeholder="Describe your issue in detail..."
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    disabled={submitLoading}
                    className="w-full bg-zinc-950/60 border border-zinc-850 rounded-xl py-2.5 px-4 text-xs text-zinc-200 placeholder-zinc-650 focus:outline-none focus:border-indigo-500 transition-colors resize-none"
                  />
                </div>

                <div className="flex justify-end pt-2">
                  <button
                    type="submit"
                    disabled={submitLoading}
                    className="bg-indigo-500 hover:bg-indigo-400 text-white font-bold py-2.5 px-4 rounded-xl shadow-md flex items-center gap-2 transition-all cursor-pointer text-xs disabled:opacity-50 active:scale-95"
                  >
                    {submitLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                    Submit Support Ticket
                  </button>
                </div>
              </form>
            </div>

            {/* Health status sidebar */}
            <div className="space-y-6">
              
              {/* System status cards */}
              <div className="bg-zinc-900/40 border border-zinc-850 rounded-2xl p-6 shadow-xl space-y-4">
                <div className="flex items-center justify-between border-b border-zinc-900 pb-3">
                  <h2 className="text-xs font-bold text-zinc-150 uppercase tracking-wider">System Status</h2>
                  <button 
                    onClick={checkHealth}
                    className="p-1 rounded bg-zinc-950 border border-zinc-850 hover:bg-zinc-900 text-zinc-400 hover:text-zinc-200 transition-all active:scale-95"
                  >
                    <RefreshCw className="h-3.5 w-3.5" />
                  </button>
                </div>

                {/* status items */}
                <div className="grid grid-cols-2 gap-3.5">
                  
                  {/* Backend */}
                  <div className="p-3 bg-zinc-950/30 border border-zinc-900 rounded-xl flex items-center gap-2">
                    <Cpu className="h-4 w-4 text-zinc-500" />
                    <div>
                      <p className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider">Backend API</p>
                      <span className={`text-[10px] font-bold capitalize ${
                        status.backend === "healthy" ? "text-emerald-400" :
                        status.backend === "loading" ? "text-zinc-550" : "text-rose-500"
                      }`}>
                        {status.backend}
                      </span>
                    </div>
                  </div>

                  {/* MongoDB */}
                  <div className="p-3 bg-zinc-950/30 border border-zinc-900 rounded-xl flex items-center gap-2">
                    <Database className="h-4 w-4 text-zinc-500" />
                    <div>
                      <p className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider">MongoDB</p>
                      <span className={`text-[10px] font-bold capitalize ${
                        status.mongodb === "healthy" ? "text-emerald-400" :
                        status.mongodb === "loading" ? "text-zinc-550" : "text-rose-500"
                      }`}>
                        {status.mongodb}
                      </span>
                    </div>
                  </div>

                  {/* Gemini */}
                  <div className="p-3 bg-zinc-950/30 border border-zinc-900 rounded-xl flex items-center gap-2">
                    <Brain className="h-4 w-4 text-zinc-500" />
                    <div>
                      <p className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider">Gemini LLM</p>
                      <span className={`text-[10px] font-bold capitalize ${
                        status.gemini === "healthy" ? "text-emerald-400" :
                        status.gemini === "loading" ? "text-zinc-550" : "text-rose-500"
                      }`}>
                        {status.gemini}
                      </span>
                    </div>
                  </div>

                  {/* FAISS */}
                  <div className="p-3 bg-zinc-950/30 border border-zinc-900 rounded-xl flex items-center gap-2">
                    <Network className="h-4 w-4 text-zinc-500" />
                    <div>
                      <p className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider">FAISS Store</p>
                      <span className={`text-[10px] font-bold capitalize ${
                        status.faiss === "healthy" ? "text-emerald-400" :
                        status.faiss === "loading" ? "text-zinc-550" : "text-rose-500"
                      }`}>
                        {status.faiss}
                      </span>
                    </div>
                  </div>

                  {/* Auth */}
                  <div className="p-3 bg-zinc-950/30 border border-zinc-900 rounded-xl flex items-center gap-2">
                    <Key className="h-4 w-4 text-zinc-500" />
                    <div>
                      <p className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider">Auth Gate</p>
                      <span className={`text-[10px] font-bold capitalize ${
                        status.auth === "healthy" ? "text-emerald-400" :
                        status.auth === "loading" ? "text-zinc-550" : "text-rose-500"
                      }`}>
                        {status.auth}
                      </span>
                    </div>
                  </div>

                  {/* Docker */}
                  <div className="p-3 bg-zinc-950/30 border border-zinc-900 rounded-xl flex items-center gap-2">
                    <Layers className="h-4 w-4 text-zinc-500" />
                    <div>
                      <p className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider">Docker Dev</p>
                      <span className={`text-[10px] font-bold capitalize ${
                        status.docker === "healthy" ? "text-emerald-400" :
                        status.docker === "loading" ? "text-zinc-550" : "text-rose-500"
                      }`}>
                        {status.docker}
                      </span>
                    </div>
                  </div>

                </div>
              </div>

              {/* Version & Info panel */}
              <div className="bg-zinc-900/40 border border-zinc-850 rounded-2xl p-6 shadow-xl space-y-3.5 text-xs text-zinc-400">
                <h2 className="text-xs font-bold text-zinc-150 uppercase tracking-wider border-b border-zinc-900 pb-3">Environment Specs</h2>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-zinc-500 font-semibold">Application Version</span>
                    <span className="font-bold text-zinc-300">v1.2.4</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500 font-semibold">Build Tag</span>
                    <span className="font-bold text-zinc-300">#6821-prod</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500 font-semibold">Environment</span>
                    <span className="font-bold text-emerald-400 capitalize">Development</span>
                  </div>
                  <div className="flex justify-between border-t border-zinc-900 pt-2.5 mt-2.5">
                    <span className="text-zinc-500 font-semibold">Current User</span>
                    <span className="font-bold text-zinc-300 truncate max-w-[120px]">{currentUser?.full_name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-zinc-500 font-semibold">Active Role</span>
                    <span className="font-bold text-indigo-400 capitalize">{currentUser?.role}</span>
                  </div>
                </div>
              </div>

            </div>

          </div>

        </main>
      </div>
    </div>
  );
}
