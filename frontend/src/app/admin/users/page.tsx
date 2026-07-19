"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import Navbar from "@/components/layout/Navbar";
import Sidebar from "@/components/layout/Sidebar";
import { api } from "@/services/api";
import { 
  Search, Filter, ChevronLeft, ChevronRight, X, ShieldAlert,
  User, CheckCircle, AlertTriangle, RefreshCw, Eye, ShieldCheck, Mail, Calendar, Key, AlertCircle
} from "lucide-react";

interface UserItem {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
  last_login?: string;
}

interface UserDetails extends UserItem {
  conversation_count: number;
  ticket_count: number;
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

export default function AdminUsersPage() {
  const { currentUser, loading: authLoading } = useAuth();
  const router = useRouter();

  // Guard routing
  useEffect(() => {
    if (!authLoading && (!currentUser || currentUser.role !== "admin")) {
      router.push("/");
    }
  }, [currentUser, authLoading, router]);

  // Page States
  const [users, setUsers] = useState<UserItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(10);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sortBy, setSortBy] = useState("created_at");
  const [sortOrder, setSortOrder] = useState("desc");
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Drawer States
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [userDetails, setUserDetails] = useState<UserDetails | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [drawerError, setDrawerError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Load User List
  const fetchUsers = async () => {
    if (!currentUser || currentUser.role !== "admin") return;
    setLoading(true);
    setError(null);
    try {
      let url = `/admin/users?page=${page}&limit=${limit}&sort_by=${sortBy}&sort_order=${sortOrder}`;
      if (search.trim()) url += `&search=${encodeURIComponent(search)}`;
      if (roleFilter) url += `&role=${roleFilter}`;
      if (statusFilter === "active") url += `&is_active=true`;
      if (statusFilter === "inactive") url += `&is_active=false`;
      if (statusFilter === "verified") url += `&is_verified=true`;
      if (statusFilter === "unverified") url += `&is_verified=false`;

      const res = await api.get(url);
      setUsers(res.data.users);
      setTotal(res.data.total);
    } catch (err: any) {
      setError(err.message || "Failed to load user directories.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [page, search, roleFilter, statusFilter, sortBy, sortOrder, currentUser]);

  // Load Drawer Details
  const fetchDetails = async (id: string) => {
    setDrawerLoading(true);
    setDrawerError(null);
    try {
      const detailRes = await api.get(`/admin/users/${id}`);
      setUserDetails(detailRes.data);

      const logsRes = await api.get(`/admin/users/${id}/audit-logs`);
      setAuditLogs(logsRes.data);
    } catch (err: any) {
      setDrawerError(err.message || "Failed to load user specifications.");
    } finally {
      setDrawerLoading(false);
    }
  };

  const handleOpenDrawer = (id: string) => {
    setSelectedUserId(id);
    setUserDetails(null);
    setAuditLogs([]);
    fetchDetails(id);
  };

  const handleCloseDrawer = () => {
    setSelectedUserId(null);
    setUserDetails(null);
    setAuditLogs([]);
  };

  // Administrative Actions
  const handleToggleActivation = async (user: UserItem) => {
    setActionLoading(true);
    setSuccessMsg(null);
    setDrawerError(null);
    try {
      const endpoint = user.is_active ? "deactivate" : "activate";
      const res = await api.patch(`/admin/users/${user.id}/${endpoint}`);
      
      setSuccessMsg(`User status updated to ${user.is_active ? "Inactive" : "Active"}.`);
      fetchUsers();
      // Reload details if active in drawer
      if (selectedUserId === user.id) {
        fetchDetails(user.id);
      }
    } catch (err: any) {
      setDrawerError(err.response?.data?.detail || err.message || "Action rejected.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleToggleVerification = async (user: UserItem) => {
    setActionLoading(true);
    setSuccessMsg(null);
    setDrawerError(null);
    try {
      const endpoint = user.is_verified ? "unverify" : "verify";
      const res = await api.patch(`/admin/users/${user.id}/${endpoint}`);
      
      setSuccessMsg(`User verification status updated successfully.`);
      fetchUsers();
      if (selectedUserId === user.id) {
        fetchDetails(user.id);
      }
    } catch (err: any) {
      setDrawerError(err.response?.data?.detail || err.message || "Action rejected.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleChangeRole = async (user: UserItem, newRole: string) => {
    setActionLoading(true);
    setSuccessMsg(null);
    setDrawerError(null);
    try {
      await api.patch(`/admin/users/${user.id}/role`, { role: newRole });
      
      setSuccessMsg(`User role updated to ${newRole.toUpperCase()}.`);
      fetchUsers();
      if (selectedUserId === user.id) {
        fetchDetails(user.id);
      }
    } catch (err: any) {
      setDrawerError(err.response?.data?.detail || err.message || "Action rejected.");
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
                <ShieldAlert className="h-5 w-5 text-amber-500" />
                <h1 className="text-xl font-extrabold text-zinc-100 tracking-tight">Admin Console</h1>
              </div>
              <p className="text-xs text-zinc-500 font-semibold mt-1">Manage portal directories, modify roles, and audit security actions</p>
            </div>

            {/* Notification Bar */}
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

          {/* Table Filters & Actions */}
          <div className="bg-zinc-900/40 border border-zinc-850 rounded-2xl p-5 mb-6 backdrop-blur-md shadow-xl">
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
              
              {/* Search Bar */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
                <input
                  type="text"
                  placeholder="Search name or email..."
                  value={search}
                  onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                  className="w-full pl-9 pr-4 py-2 rounded-xl bg-zinc-950 border border-zinc-800 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>

              {/* Role filter */}
              <div className="relative">
                <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
                <select
                  value={roleFilter}
                  onChange={(e) => { setRoleFilter(e.target.value); setPage(1); }}
                  className="w-full pl-9 pr-4 py-2 rounded-xl bg-zinc-950 border border-zinc-800 text-xs text-zinc-300 focus:outline-none focus:border-indigo-500 transition-colors appearance-none cursor-pointer"
                >
                  <option value="">All Roles</option>
                  <option value="admin">Administrator</option>
                  <option value="user">User Account</option>
                </select>
              </div>

              {/* Status filter */}
              <div className="relative">
                <Filter className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
                <select
                  value={statusFilter}
                  onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
                  className="w-full pl-9 pr-4 py-2 rounded-xl bg-zinc-950 border border-zinc-800 text-xs text-zinc-300 focus:outline-none focus:border-indigo-500 transition-colors appearance-none cursor-pointer"
                >
                  <option value="">All Statuses</option>
                  <option value="active">Active Accounts</option>
                  <option value="inactive">Deactivated</option>
                  <option value="verified">Verified Profile</option>
                  <option value="unverified">Unverified Profile</option>
                </select>
              </div>

              {/* Sorting filter */}
              <div className="relative">
                <select
                  value={`${sortBy}-${sortOrder}`}
                  onChange={(e) => {
                    const [field, order] = e.target.value.split("-");
                    setSortBy(field);
                    setSortOrder(order);
                    setPage(1);
                  }}
                  className="w-full px-4 py-2 rounded-xl bg-zinc-950 border border-zinc-800 text-xs text-zinc-300 focus:outline-none focus:border-indigo-500 transition-colors appearance-none cursor-pointer"
                >
                  <option value="created_at-desc">Newest Registered</option>
                  <option value="created_at-asc">Oldest Registered</option>
                  <option value="full_name-asc">Name (A-Z)</option>
                  <option value="full_name-desc">Name (Z-A)</option>
                </select>
              </div>

            </div>
          </div>

          {/* User Table Grid */}
          <div className="bg-zinc-900/30 border border-zinc-850 rounded-2xl overflow-hidden shadow-xl shadow-black/25">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-zinc-900/70 border-b border-zinc-850 text-[10px] font-bold text-zinc-500 uppercase tracking-widest">
                    <th className="px-6 py-4">User</th>
                    <th className="px-6 py-4">Role</th>
                    <th className="px-6 py-4">Status</th>
                    <th className="px-6 py-4">Verified</th>
                    <th className="px-6 py-4">Joined Date</th>
                    <th className="px-6 py-4 text-center">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-900/60">
                  {loading ? (
                    <tr>
                      <td colSpan={6} className="text-center py-12">
                        <RefreshCw className="h-6 w-6 text-indigo-500 animate-spin mx-auto mb-2" />
                        <span className="text-xs font-semibold text-zinc-500">Retrieving Accounts...</span>
                      </td>
                    </tr>
                  ) : users.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="text-center py-12 text-xs font-semibold text-zinc-500">
                        No registered users match active filters.
                      </td>
                    </tr>
                  ) : (
                    users.map((u) => (
                      <tr 
                        key={u.id} 
                        className="hover:bg-zinc-900/30 transition-colors group text-zinc-300 text-xs font-medium"
                      >
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-indigo-500/20 to-violet-500/20 text-indigo-400 font-extrabold flex items-center justify-center">
                              {u.full_name.charAt(0).toUpperCase()}
                            </div>
                            <div>
                              <p className="font-bold text-zinc-200 group-hover:text-zinc-100 transition-colors">{u.full_name}</p>
                              <p className="text-[10px] text-zinc-500 font-semibold mt-0.5">{u.email}</p>
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span className={`px-2 py-0.5 text-[10px] font-bold rounded-full border capitalize ${
                            u.role === "admin" 
                              ? "bg-amber-500/10 border-amber-500/20 text-amber-400"
                              : "bg-zinc-800/40 border-zinc-700/50 text-zinc-400"
                          }`}>
                            {u.role}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <span className={`inline-flex items-center gap-1 text-[10px] font-bold ${
                            u.is_active ? "text-emerald-400" : "text-zinc-500"
                          }`}>
                            <span className={`h-1.5 w-1.5 rounded-full ${u.is_active ? "bg-emerald-400" : "bg-zinc-600"}`} />
                            {u.is_active ? "Active" : "Deactivated"}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <span className={`inline-flex items-center gap-1.5 text-[10px] font-bold ${
                            u.is_verified ? "text-indigo-400" : "text-zinc-500"
                          }`}>
                            {u.is_verified ? <ShieldCheck className="h-4 w-4" /> : <User className="h-4 w-4" />}
                            {u.is_verified ? "Verified" : "Standard"}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-zinc-500 font-semibold">
                          {formatDate(u.created_at).split(",")[0]}
                        </td>
                        <td className="px-6 py-4 text-center">
                          <button
                            onClick={() => handleOpenDrawer(u.id)}
                            className="p-2 rounded-lg bg-zinc-950 hover:bg-zinc-900 border border-zinc-800 text-indigo-400 hover:text-indigo-300 transition-colors shadow-sm active:scale-95 inline-flex items-center gap-1"
                          >
                            <Eye className="h-3.5 w-3.5" />
                            <span className="text-[10px] font-bold">Details</span>
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            <div className="bg-zinc-950/40 border-t border-zinc-850 p-4 flex items-center justify-between">
              <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">
                Total Records: {total}
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
      {selectedUserId && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex justify-end animate-fade-in font-sans">
          <div className="w-full max-w-lg bg-zinc-950 border-l border-zinc-900 p-6 shadow-2xl flex flex-col justify-between h-full relative overflow-y-auto">
            
            {/* Drawer Header */}
            <div>
              <div className="flex items-center justify-between mb-6 pb-4 border-b border-zinc-900">
                <div className="flex items-center gap-2">
                  <User className="h-5 w-5 text-indigo-400" />
                  <h2 className="text-base font-bold text-zinc-100">User Audit Details</h2>
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
                  <p className="text-xs text-zinc-500 font-semibold">Resolving detailed records...</p>
                </div>
              ) : drawerError ? (
                <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl text-xs font-bold flex items-center gap-2">
                  <AlertCircle className="h-4 w-4" />
                  {drawerError}
                </div>
              ) : (
                userDetails && (
                  <div className="space-y-6">
                    
                    {/* Main User Card */}
                    <div className="flex items-center gap-4 bg-zinc-900/20 border border-zinc-900 p-4 rounded-xl">
                      <div className="h-12 w-12 rounded-xl bg-gradient-to-tr from-indigo-500 to-violet-500 text-white font-extrabold flex items-center justify-center shadow-lg">
                        {userDetails.full_name.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <p className="text-sm font-bold text-zinc-200">{userDetails.full_name}</p>
                        <p className="text-xs text-zinc-500 font-semibold">{userDetails.email}</p>
                        <span className="inline-block px-1.5 py-0.5 bg-zinc-800 text-[9px] text-zinc-400 rounded mt-1.5 uppercase font-bold tracking-wide">
                          ID: {userDetails.id}
                        </span>
                      </div>
                    </div>

                    {/* Stats counters */}
                    <div className="grid grid-cols-2 gap-4">
                      <div className="p-4 bg-zinc-900/30 border border-zinc-900 rounded-xl text-center">
                        <p className="text-xl font-extrabold text-indigo-400">{userDetails.conversation_count}</p>
                        <p className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold mt-1">Conversations</p>
                      </div>
                      <div className="p-4 bg-zinc-900/30 border border-zinc-900 rounded-xl text-center">
                        <p className="text-xl font-extrabold text-amber-400">{userDetails.ticket_count}</p>
                        <p className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold mt-1">Tickets Filed</p>
                      </div>
                    </div>

                    {/* Meta Fields */}
                    <div className="space-y-3 bg-zinc-900/20 border border-zinc-900 p-4 rounded-xl text-xs">
                      <div className="flex justify-between">
                        <span className="text-zinc-500 font-semibold">Current Privilege Role</span>
                        <span className="font-bold text-zinc-200 capitalize">{userDetails.role}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-zinc-500 font-semibold">User Verification State</span>
                        <span className={`font-bold ${userDetails.is_verified ? "text-indigo-400" : "text-zinc-500"}`}>
                          {userDetails.is_verified ? "Verified Professional" : "Standard Registration"}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-zinc-500 font-semibold">Connection Status</span>
                        <span className={`font-bold ${userDetails.is_active ? "text-emerald-400" : "text-red-400"}`}>
                          {userDetails.is_active ? "Active" : "Deactivated"}
                        </span>
                      </div>
                      <div className="flex justify-between border-t border-zinc-900 pt-2.5 mt-2.5">
                        <span className="text-zinc-500 font-semibold flex items-center gap-1"><Calendar className="h-3.5 w-3.5 text-zinc-600" /> Registered</span>
                        <span className="font-bold text-zinc-400">{formatDate(userDetails.created_at)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-zinc-500 font-semibold flex items-center gap-1"><Key className="h-3.5 w-3.5 text-zinc-600" /> Last Login</span>
                        <span className="font-bold text-zinc-400">{formatDate(userDetails.last_login)}</span>
                      </div>
                    </div>

                    {/* Operational controls */}
                    <div>
                      <h3 className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-3">Admin Actions</h3>
                      <div className="flex flex-wrap gap-2.5">
                        
                        {/* Role selector dropdown */}
                        <div className="relative flex items-center gap-2 bg-zinc-900/40 border border-zinc-800 px-3 py-1.5 rounded-xl text-xs">
                          <span className="text-zinc-500 font-semibold">Role:</span>
                          <select
                            disabled={actionLoading || userDetails.id === currentUser.id}
                            value={userDetails.role}
                            onChange={(e) => handleChangeRole(userDetails, e.target.value)}
                            className="bg-transparent border-none text-zinc-200 font-bold focus:outline-none cursor-pointer disabled:opacity-50"
                          >
                            <option value="user" className="bg-zinc-950">User</option>
                            <option value="admin" className="bg-zinc-950">Admin</option>
                          </select>
                        </div>

                        {/* Promote/Demote Action Buttons */}
                        {userDetails.role === "user" ? (
                          <button
                            type="button"
                            disabled={actionLoading}
                            onClick={() => handleChangeRole(userDetails, "admin")}
                            className="px-4 py-2 text-xs font-bold rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 hover:bg-indigo-500/20 transition-all active:scale-95 disabled:opacity-50"
                          >
                            Promote to Admin
                          </button>
                        ) : (
                          <button
                            type="button"
                            disabled={actionLoading || userDetails.id === currentUser.id}
                            onClick={() => handleChangeRole(userDetails, "user")}
                            className="px-4 py-2 text-xs font-bold rounded-xl bg-zinc-800/40 border border-zinc-700/50 text-zinc-400 hover:bg-zinc-800 transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
                          >
                            Demote to User
                          </button>
                        )}

                        {/* Toggle active button */}
                        <button
                          disabled={actionLoading || userDetails.id === currentUser.id}
                          onClick={() => handleToggleActivation(userDetails)}
                          className={`px-4 py-2 text-xs font-bold rounded-xl border transition-all active:scale-95 disabled:opacity-50 ${
                            userDetails.is_active 
                              ? "bg-red-500/10 border-red-500/20 text-red-400 hover:bg-red-500/20"
                              : "bg-emerald-500/10 border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20"
                          }`}
                        >
                          {userDetails.is_active ? "Deactivate Account" : "Activate Account"}
                        </button>

                        {/* Toggle verify button */}
                        <button
                          disabled={actionLoading}
                          onClick={() => handleToggleVerification(userDetails)}
                          className={`px-4 py-2 text-xs font-bold rounded-xl border transition-all active:scale-95 disabled:opacity-50 ${
                            userDetails.is_verified 
                              ? "bg-zinc-900 border-zinc-800 text-zinc-400 hover:bg-zinc-850"
                              : "bg-indigo-500/10 border-indigo-500/20 text-indigo-400 hover:bg-indigo-500/20"
                          }`}
                        >
                          {userDetails.is_verified ? "Unverify User" : "Verify Profile"}
                        </button>

                      </div>
                    </div>

                    {/* Audit Logs list */}
                    <div>
                      <h3 className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-3">Security Audit Trail</h3>
                      <div className="bg-zinc-900/20 border border-zinc-900 rounded-xl overflow-hidden divide-y divide-zinc-900/60 max-h-48 overflow-y-auto">
                        {auditLogs.length === 0 ? (
                          <p className="text-center py-6 text-zinc-500 text-xs font-semibold">No operational updates logged for this account.</p>
                        ) : (
                          auditLogs.map((log) => (
                            <div key={log._id} className="p-3 text-xs flex flex-col gap-1 hover:bg-zinc-900/10">
                              <div className="flex justify-between items-center">
                                <span className="font-bold text-zinc-300 capitalize">{log.action.replace(/_/g, " ")}</span>
                                <span className="text-[10px] text-zinc-500 font-semibold">{formatDate(log.timestamp).split(",")[0]}</span>
                              </div>
                              <p className="text-[10px] text-zinc-500 font-semibold">Admin: {log.admin_id}</p>
                              {(log.previous_value !== undefined || log.new_value !== undefined) && (
                                <div className="text-[10px] text-zinc-400 bg-zinc-950/60 p-1.5 rounded mt-1 font-mono">
                                  {log.previous_value} &rarr; {log.new_value}
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

            {/* Actions loading indicator */}
            {actionLoading && (
              <div className="absolute inset-0 bg-black/30 backdrop-blur-[2px] flex items-center justify-center pointer-events-none">
                <RefreshCw className="h-6 w-6 text-indigo-400 animate-spin" />
              </div>
            )}

          </div>
        </div>
      )}
    </div>
  );
}
