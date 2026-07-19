"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { api } from "@/services/api";
import { Loader2 } from "lucide-react";
import axios from "axios";

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at?: string;
  last_login?: string;
}

interface AuthContextType {
  currentUser: User | null;
  user: User | null; // Kept for backward compatibility
  accessToken: string | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (fullName: string, email: string, password: string, confirmPassword: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const router = useRouter();
  const pathname = usePathname();

  const refresh = async (): Promise<string | null> => {
    const storedRefreshToken = localStorage.getItem("refreshToken");
    if (!storedRefreshToken) return null;
    try {
      const envApiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const refreshRes = await axios.post(`${envApiUrl}/api/v1/auth/refresh`, {
        refresh_token: storedRefreshToken
      });
      const newAccess = refreshRes.data.access_token;
      localStorage.setItem("accessToken", newAccess);
      setAccessToken(newAccess);
      return newAccess;
    } catch (err) {
      setUser(null);
      setAccessToken(null);
      localStorage.removeItem("accessToken");
      localStorage.removeItem("refreshToken");
      throw err;
    }
  };

  // 1. Session restoration on mount
  useEffect(() => {
    const restoreSession = async () => {
      const storedAccessToken = localStorage.getItem("accessToken");
      const storedRefreshToken = localStorage.getItem("refreshToken");

      if (storedAccessToken && storedRefreshToken) {
        try {
          setAccessToken(storedAccessToken);
          const response = await api.get<User>("/auth/me");
          setUser(response.data);
        } catch {
          // If profile fetch fails, the access token might be expired. Let's attempt to restore via refresh.
          try {
            const newAccess = await refresh();
            if (newAccess) {
              // Wait briefly to allow request interceptor headers to update
              api.defaults.headers.common["Authorization"] = `Bearer ${newAccess}`;
              const meRes = await api.get<User>("/auth/me");
              setUser(meRes.data);
            } else {
              throw new Error("No refresh token available");
            }
          } catch {
            // Clear credentials on session recovery failure
            localStorage.removeItem("accessToken");
            localStorage.removeItem("refreshToken");
            setUser(null);
            setAccessToken(null);
          }
        }
      }
      setLoading(false);
    };

    restoreSession();
  }, []);

  // 2. Interceptor logout sync
  useEffect(() => {
    const handleLogoutEvent = () => {
      setUser(null);
      setAccessToken(null);
      localStorage.removeItem("accessToken");
      localStorage.removeItem("refreshToken");
      router.push("/login");
    };

    window.addEventListener("auth-logout", handleLogoutEvent);
    return () => window.removeEventListener("auth-logout", handleLogoutEvent);
  }, [router]);

  // 3. Client-side Route Guard
  useEffect(() => {
    if (!loading) {
      const publicPaths = ["/login", "/register"];
      const isPublicPath = publicPaths.includes(pathname);
      
      if (!user && !isPublicPath) {
        router.push("/login");
      } else if (user && isPublicPath) {
        router.push("/");
      }
    }
  }, [user, loading, pathname, router]);

  const login = async (email: string, password: string) => {
    setLoading(true);
    try {
      const res = await api.post("/auth/login", { email, password });
      const { access_token, refresh_token } = res.data;
      
      localStorage.setItem("accessToken", access_token);
      localStorage.setItem("refreshToken", refresh_token);
      setAccessToken(access_token);

      // Fetch user profile info
      const meRes = await api.get<User>("/auth/me");
      setUser(meRes.data);
      router.push("/");
    } catch (err) {
      setLoading(false);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const register = async (fullName: string, email: string, password: string, confirmPassword: string) => {
    setLoading(true);
    try {
      await api.post("/auth/register", {
        full_name: fullName,
        email,
        password,
        confirm_password: confirmPassword,
      });
      
      // Auto login after registration
      await login(email, password);
    } catch (err) {
      setLoading(false);
      throw err;
    }
  };

  const logout = async () => {
    setLoading(true);
    try {
      await api.post("/auth/logout");
    } catch (err) {
      console.error("Logout request failed:", err);
    } finally {
      setUser(null);
      setAccessToken(null);
      localStorage.removeItem("accessToken");
      localStorage.removeItem("refreshToken");
      setLoading(false);
      router.push("/login");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 flex flex-col items-center justify-center text-zinc-400 gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
        <p className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">Restoring Session...</p>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ 
      currentUser: user, 
      user, 
      accessToken, 
      loading, 
      isAuthenticated: !!user, 
      login, 
      register, 
      logout, 
      refresh 
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
