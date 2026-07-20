"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import Navbar from "@/components/layout/Navbar";
import Sidebar from "@/components/layout/Sidebar";
import { api } from "@/services/api";
import { 
  Search, ChevronLeft, ChevronRight, X, FileText, 
  Upload, Trash2, RefreshCw, Calendar, CheckCircle2, 
  ShieldAlert, BookOpen, Info
} from "lucide-react";

interface KBDocument {
  document_id: string;
  filename: string;
  upload_date: string;
  file_type: string;
  chunk_count: number;
  embedding_status: string;
  indexed_status: string;
  file_size: number;
  uploaded_by: string;
  embedding_model: string;
  last_indexed?: string;
}

export default function AdminKnowledgeBasePage() {
  const { currentUser, loading: authLoading } = useAuth();
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Guard routing
  useEffect(() => {
    if (!authLoading && (!currentUser || currentUser.role !== "admin")) {
      router.push("/");
    }
  }, [currentUser, authLoading, router]);

  // Page States
  const [documents, setDocuments] = useState<KBDocument[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(10);
  
  // Search & Filters
  const [search, setSearch] = useState("");
  const [extensionFilter, setExtensionFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Reindexing / Action indicators
  const [actionLoading, setActionLoading] = useState(false);

  // Upload States
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Drawer States
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<KBDocument | null>(null);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [drawerError, setDrawerError] = useState<string | null>(null);

  // Fetch Knowledge Base Documents
  const fetchDocuments = useCallback(async () => {
    if (!currentUser || currentUser.role !== "admin") return;
    setLoading(true);
    setError(null);
    try {
      let url = `/admin/knowledge?page=${page}&limit=${limit}`;
      if (search.trim()) url += `&search=${encodeURIComponent(search)}`;
      if (extensionFilter) url += `&extension=${extensionFilter}`;
      if (statusFilter) url += `&status=${statusFilter}`;
      if (startDate) url += `&start_date=${new Date(startDate).toISOString()}`;
      if (endDate) url += `&end_date=${new Date(endDate).toISOString()}`;

      const res = await api.get(url);
      setDocuments(res.data.documents);
      setTotal(res.data.total);
    } catch (err: unknown) {
      const errorObj = err as { message?: string };
      setError(errorObj.message || "Failed to load knowledge base document logs.");
    } finally {
      setLoading(false);
    }
  }, [currentUser, page, limit, search, extensionFilter, statusFilter, startDate, endDate]);

  useEffect(() => {
    void (async () => {
      await Promise.resolve();
      fetchDocuments();
    })();
  }, [fetchDocuments]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchDocuments();
  };

  // Fetch Detailed View
  const handleOpenDrawer = async (id: string) => {
    setSelectedDocId(id);
    setSelectedDoc(null);
    setDrawerLoading(true);
    setDrawerError(null);
    try {
      const res = await api.get(`/admin/knowledge/${id}`);
      setSelectedDoc(res.data);
    } catch (err: unknown) {
      const errorObj = err as { message?: string };
      setDrawerError(errorObj.message || "Failed to retrieve document specifications.");
    } finally {
      setDrawerLoading(false);
    }
  };

  const handleCloseDrawer = () => {
    setSelectedDocId(null);
    setSelectedDoc(null);
  };

  // Upload File
  const handleFileUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const file = files[0];
    setUploadError(null);
    setSuccessMsg(null);

    // Extension validation
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!ext || !["pdf", "txt", "md", "docx"].includes(ext)) {
      setUploadError("Invalid file type. Allowed files: PDF, TXT, MD, DOCX.");
      return;
    }

    // Size validation (10MB limit)
    const MAX_SIZE = 10 * 1024 * 1024;
    if (file.size > MAX_SIZE) {
      setUploadError("File size exceeds maximum limit of 10MB.");
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      await api.post("/admin/knowledge/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });
      setSuccessMsg(`File "${file.name}" uploaded and indexed successfully.`);
      setPage(1);
      fetchDocuments();
    } catch (err: unknown) {
      const errorObj = err as { response?: { data?: { detail?: string } }; message?: string };
      setUploadError(errorObj.response?.data?.detail || errorObj.message || "File upload failed.");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  // Reindex single document
  const handleReindexDocument = async (id: string, name: string) => {
    setActionLoading(true);
    setSuccessMsg(null);
    setError(null);
    try {
      await api.post(`/admin/knowledge/reindex/${id}`);
      setSuccessMsg(`Document "${name}" successfully re-indexed.`);
      fetchDocuments();
      if (selectedDocId === id) {
        handleOpenDrawer(id);
      }
    } catch (err: unknown) {
      const errorObj = err as { message?: string };
      setError(errorObj.message || "Re-indexing failed.");
    } finally {
      setActionLoading(false);
    }
  };

  // Reindex all documents
  const handleReindexAll = async () => {
    if (!confirm("Are you sure you want to rebuild the entire knowledge base index? This may take some time.")) return;
    setActionLoading(true);
    setSuccessMsg(null);
    setError(null);
    try {
      await api.post("/admin/knowledge/reindex-all");
      setSuccessMsg("Entire knowledge base successfully re-indexed.");
      fetchDocuments();
    } catch (err: unknown) {
      const errorObj = err as { message?: string };
      setError(errorObj.message || "Re-indexing failed.");
    } finally {
      setActionLoading(false);
    }
  };

  // Delete document
  const handleDeleteDocument = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to delete "${name}"? This removes the document and its vector embeddings.`)) return;
    setActionLoading(true);
    setSuccessMsg(null);
    setError(null);
    try {
      await api.delete(`/admin/knowledge/${id}`);
      setSuccessMsg(`Document "${name}" deleted and vector embeddings removed.`);
      handleCloseDrawer();
      fetchDocuments();
    } catch (err: unknown) {
      const errorObj = err as { message?: string };
      setError(errorObj.message || "Deletion failed.");
    } finally {
      setActionLoading(false);
    }
  };

  // Helper size formatter
  const formatBytes = (bytes: number): string => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

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
                Knowledge Base Management
              </h1>
              <p className="text-slate-500 dark:text-slate-400 mt-1">
                Upload, organize, delete, and re-index grounded documents used by the RAG search pipeline.
              </p>
            </div>
            
            <div className="flex flex-wrap gap-2">
              <button
                onClick={handleReindexAll}
                disabled={actionLoading}
                className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-850 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-xl text-sm font-bold flex items-center gap-2 transition-all disabled:opacity-50"
              >
                <RefreshCw className={`h-4 w-4 ${actionLoading ? "animate-spin" : ""}`} />
                Re-index Complete KB
              </button>
              
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                accept=".pdf,.txt,.md,.docx"
                className="hidden"
              />
              
              <button
                onClick={handleFileUploadClick}
                disabled={uploading || actionLoading}
                className="px-4 py-2.5 bg-violet-600 hover:bg-violet-700 active:bg-violet-800 text-white rounded-xl text-sm font-bold flex items-center gap-2 transition-all shadow-md shadow-violet-200 dark:shadow-none disabled:opacity-50"
              >
                <Upload className="h-4 w-4" />
                {uploading ? "Indexing File..." : "Upload Document"}
              </button>
            </div>
          </div>

          {/* Feedback alerts */}
          {successMsg && (
            <div className="bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900/50 text-emerald-700 dark:text-emerald-400 p-4 rounded-xl mb-6 flex gap-3 items-center animate-fadeIn">
              <CheckCircle2 className="h-5 w-5 flex-shrink-0 text-emerald-600" />
              <span className="text-sm font-medium">{successMsg}</span>
            </div>
          )}

          {(error || uploadError) && (
            <div className="bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900/50 text-red-700 dark:text-red-400 p-4 rounded-xl mb-6 flex gap-3 items-center animate-fadeIn">
              <ShieldAlert className="h-5 w-5 flex-shrink-0" />
              <span className="text-sm font-medium">{error || uploadError}</span>
            </div>
          )}

          {/* Filters Area */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 mb-6 shadow-sm">
            <form onSubmit={handleSearchSubmit} className="flex flex-col lg:flex-row gap-4 items-stretch lg:items-end">
              <div className="flex-1">
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Search Filename</label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 h-5 w-5" />
                  <input
                    type="text"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search documents by name..."
                    className="w-full pl-10 pr-4 py-2.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-600 focus:border-transparent transition-all"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 lg:w-2/3">
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">File Extension</label>
                  <select
                    value={extensionFilter}
                    onChange={(e) => setExtensionFilter(e.target.value)}
                    className="w-full px-3 py-2.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-600 transition-all cursor-pointer"
                  >
                    <option value="">All Types</option>
                    <option value="pdf">PDF</option>
                    <option value="txt">TXT</option>
                    <option value="md">Markdown (.md)</option>
                    <option value="docx">DOCX</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Index Status</label>
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="w-full px-3 py-2.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-600 transition-all cursor-pointer"
                  >
                    <option value="">All Statuses</option>
                    <option value="completed">Completed</option>
                    <option value="pending">Pending</option>
                    <option value="failed">Failed</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Upload Start</label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-600 transition-all"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Upload End</label>
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
                    setExtensionFilter("");
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

          {/* Table Container */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden mb-6">
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 bg-slate-50/55 dark:bg-slate-950/30">
                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-400">Filename</th>
                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-400">Size</th>
                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-400">Type</th>
                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-400">Chunks</th>
                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-400">Status</th>
                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-400">Upload Date</th>
                    <th className="px-6 py-4 text-xs font-semibold uppercase tracking-wider text-slate-400 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-150 dark:divide-slate-850">
                  {loading ? (
                    <tr>
                      <td colSpan={7} className="px-6 py-12 text-center">
                        <div className="flex flex-col items-center gap-3">
                          <RefreshCw className="h-8 w-8 text-violet-600 animate-spin" />
                          <span className="text-sm text-slate-500">Querying knowledge base catalog...</span>
                        </div>
                      </td>
                    </tr>
                  ) : documents.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-6 py-16 text-center text-slate-400">
                        <div className="flex flex-col items-center gap-2">
                          <BookOpen className="h-10 w-10 text-slate-300 dark:text-slate-700" />
                          <span className="text-sm">No knowledge documents index catalog files found.</span>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    documents.map((doc) => (
                      <tr 
                        key={doc.document_id}
                        className="hover:bg-slate-50/50 dark:hover:bg-slate-950/20 transition-colors duration-150"
                      >
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="h-9 w-9 bg-slate-100 dark:bg-slate-800 rounded-lg flex items-center justify-center text-slate-600 dark:text-slate-400 flex-shrink-0">
                              <FileText className="h-4 w-4" />
                            </div>
                            <span className="font-semibold text-sm truncate max-w-xs">{doc.filename}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-sm font-medium text-slate-500">
                          {formatBytes(doc.file_size)}
                        </td>
                        <td className="px-6 py-4">
                          <span className="uppercase text-xs font-bold font-mono px-2 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 rounded">
                            {doc.file_type}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-violet-50 dark:bg-violet-950/20 text-violet-700 dark:text-violet-400">
                            {doc.chunk_count} segments
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold ${
                            doc.embedding_status === "completed" ? "bg-green-50 text-green-700 dark:bg-green-950/25 dark:text-green-400" :
                            doc.embedding_status === "pending" ? "bg-amber-50 text-amber-700 dark:bg-amber-950/25 dark:text-amber-400" :
                            "bg-red-55 text-red-700 dark:bg-red-950/25 dark:text-red-400"
                          }`}>
                            <span className={`h-1.5 w-1.5 rounded-full ${
                              doc.embedding_status === "completed" ? "bg-green-500" :
                              doc.embedding_status === "pending" ? "bg-amber-500" :
                              "bg-red-500"
                            }`} />
                            {doc.embedding_status}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-xs text-slate-400 font-medium">
                          <div className="flex items-center gap-1.5">
                            <Calendar className="h-3.5 w-3.5" />
                            {new Date(doc.upload_date).toLocaleString()}
                          </div>
                        </td>
                        <td className="px-6 py-4 text-right">
                          <div className="flex justify-end gap-1.5">
                            <button
                              onClick={() => handleOpenDrawer(doc.document_id)}
                              className="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 rounded-lg text-xs font-bold transition-all"
                            >
                              Details
                            </button>
                            <button
                              onClick={() => handleReindexDocument(doc.document_id, doc.filename)}
                              disabled={actionLoading}
                              className="p-1.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-400 rounded-lg transition-all disabled:opacity-50"
                              title="Re-index this document"
                            >
                              <RefreshCw className="h-3.5 w-3.5" />
                            </button>
                            <button
                              onClick={() => handleDeleteDocument(doc.document_id, doc.filename)}
                              disabled={actionLoading}
                              className="p-1.5 bg-red-50 hover:bg-red-100 dark:bg-red-950/20 dark:hover:bg-red-950/40 text-red-600 rounded-lg transition-all disabled:opacity-50"
                              title="Delete document"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          </div>
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
                  Showing <strong className="text-slate-700 dark:text-slate-300">{((page - 1) * limit) + 1}</strong> to <strong className="text-slate-700 dark:text-slate-300">{Math.min(page * limit, total)}</strong> of <strong className="text-slate-700 dark:text-slate-300">{total}</strong> documents
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

      {/* Document Details Drawer */}
      {selectedDocId && (
        <div className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-800 shadow-2xl flex flex-col transition-all duration-300">
          {/* Header */}
          <div className="px-6 py-5 border-b border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/10 flex justify-between items-center">
            <div>
              <h2 className="text-lg font-bold flex items-center gap-2">
                <Info className="h-5 w-5 text-violet-600" />
                Document Metadata
              </h2>
              <span className="text-xs text-slate-400 font-mono mt-0.5 block">{selectedDocId}</span>
            </div>
            <button
              onClick={handleCloseDrawer}
              className="p-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-750 text-slate-400 hover:text-slate-600 rounded-full transition-all"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {drawerLoading ? (
              <div className="py-20 flex flex-col items-center gap-3">
                <RefreshCw className="h-8 w-8 text-violet-600 animate-spin" />
                <span className="text-sm text-slate-400">Loading document specifications...</span>
              </div>
            ) : drawerError ? (
              <div className="bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900/50 text-red-700 dark:text-red-400 p-4 rounded-xl flex gap-3 items-center">
                <ShieldAlert className="h-5 w-5 flex-shrink-0" />
                <span className="text-sm font-medium">{drawerError}</span>
              </div>
            ) : selectedDoc ? (
              <div className="space-y-6">
                
                {/* Visual card */}
                <div className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-850 p-5 rounded-2xl flex flex-col items-center text-center shadow-sm">
                  <div className="h-16 w-16 bg-violet-100 dark:bg-violet-950/30 rounded-2xl flex items-center justify-center text-violet-600 dark:text-violet-400 mb-3">
                    <FileText className="h-8 w-8" />
                  </div>
                  <h3 className="font-bold text-base max-w-full truncate px-2">{selectedDoc.filename}</h3>
                  <span className="text-xs text-slate-400 font-mono mt-1 uppercase font-bold">{selectedDoc.file_type} format</span>

                  <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold mt-4 ${
                    selectedDoc.embedding_status === "completed" ? "bg-green-50 text-green-700 dark:bg-green-950/20" : "bg-red-55 text-red-700 dark:bg-red-950/20"
                  }`}>
                    <span className={`h-1.5 w-1.5 rounded-full ${selectedDoc.embedding_status === "completed" ? "bg-green-500" : "bg-red-500"}`} />
                    {selectedDoc.embedding_status}
                  </span>
                </div>

                {/* Specs List */}
                <div className="space-y-4">
                  <div className="flex justify-between items-center py-2.5 border-b border-slate-100 dark:border-slate-800">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">File Size</span>
                    <span className="text-sm font-semibold">{formatBytes(selectedDoc.file_size)}</span>
                  </div>

                  <div className="flex justify-between items-center py-2.5 border-b border-slate-100 dark:border-slate-800">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">Chunk Count</span>
                    <span className="text-sm font-semibold">{selectedDoc.chunk_count} document segments</span>
                  </div>

                  <div className="flex justify-between items-center py-2.5 border-b border-slate-100 dark:border-slate-800">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">Embedding Model</span>
                    <span className="text-xs font-mono bg-slate-100 dark:bg-slate-850 px-2 py-0.5 rounded text-slate-600 dark:text-slate-400 max-w-[200px] truncate" title={selectedDoc.embedding_model}>
                      {selectedDoc.embedding_model}
                    </span>
                  </div>

                  <div className="flex justify-between items-center py-2.5 border-b border-slate-100 dark:border-slate-800">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">Uploaded By</span>
                    <span className="text-sm font-semibold text-slate-700 dark:text-slate-300">{selectedDoc.uploaded_by}</span>
                  </div>

                  <div className="flex justify-between items-center py-2.5 border-b border-slate-100 dark:border-slate-800">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">Upload Date</span>
                    <span className="text-xs font-semibold text-slate-500">{new Date(selectedDoc.upload_date).toLocaleString()}</span>
                  </div>

                  <div className="flex justify-between items-center py-2.5 border-b border-slate-100 dark:border-slate-800">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wide">Last Indexed</span>
                    <span className="text-xs font-semibold text-slate-500">
                      {selectedDoc.last_indexed ? new Date(selectedDoc.last_indexed).toLocaleString() : "Never"}
                    </span>
                  </div>
                </div>

                {/* Operations */}
                <div className="pt-4 flex gap-3">
                  <button
                    onClick={() => handleReindexDocument(selectedDoc.document_id, selectedDoc.filename)}
                    disabled={actionLoading}
                    className="flex-1 px-4 py-2.5 bg-slate-100 hover:bg-slate-200 dark:bg-slate-850 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 rounded-xl text-xs font-bold transition-all disabled:opacity-50"
                  >
                    Re-index Document
                  </button>
                  <button
                    onClick={() => handleDeleteDocument(selectedDoc.document_id, selectedDoc.filename)}
                    disabled={actionLoading}
                    className="flex-1 px-4 py-2.5 bg-red-50 hover:bg-red-100 dark:bg-red-950/20 dark:hover:bg-red-950/40 text-red-600 rounded-xl text-xs font-bold transition-all disabled:opacity-50"
                  >
                    Delete Document
                  </button>
                </div>

              </div>
            ) : null}
          </div>
        </div>
      )}

    </div>
  );
}
