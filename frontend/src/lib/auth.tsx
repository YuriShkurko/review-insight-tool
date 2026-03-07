"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { useRouter, usePathname } from "next/navigation";
import { apiFetch, setOnUnauthorized } from "./api";
import type { User } from "./types";

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (token: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

const PUBLIC_PATHS = ["/login", "/register"];

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  const clearAuth = useCallback(() => {
    localStorage.removeItem("token");
    setUser(null);
    setToken(null);
  }, []);

  const logout = useCallback(() => {
    clearAuth();
    router.push("/login");
  }, [clearAuth, router]);

  useEffect(() => {
    setOnUnauthorized(logout);
  }, [logout]);

  const fetchUser = useCallback(
    async (t: string) => {
      try {
        localStorage.setItem("token", t);
        const me = await apiFetch<User>("/auth/me");
        setUser(me);
        setToken(t);
      } catch {
        clearAuth();
      }
    },
    [clearAuth]
  );

  useEffect(() => {
    const stored = localStorage.getItem("token");
    if (stored) {
      fetchUser(stored).finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, [fetchUser]);

  const login = useCallback(
    async (newToken: string) => {
      await fetchUser(newToken);
    },
    [fetchUser]
  );

  const isPublicPage = PUBLIC_PATHS.includes(pathname);

  if (isLoading && !isPublicPage) {
    return (
      <AuthContext.Provider
        value={{ user, token, isLoading, login, logout }}
      >
        <div className="flex justify-center items-center min-h-screen">
          <div className="text-center">
            <div className="inline-block h-6 w-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mb-3" />
            <p className="text-gray-400 text-sm">Loading...</p>
          </div>
        </div>
      </AuthContext.Provider>
    );
  }

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export function useRequireAuth() {
  const auth = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!auth.isLoading && !auth.user) {
      router.replace("/login");
    }
  }, [auth.isLoading, auth.user, router]);

  return auth;
}
