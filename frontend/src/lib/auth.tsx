"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import api, { authApi } from "./api";

interface User {
  id: string;
  username: string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem("quantbot_token");
    if (stored) {
      setToken(stored);
      api.defaults.headers.common["Authorization"] = `Bearer ${stored}`;
      authApi.me()
        .then((res) => setUser(res.data))
        .catch(() => {
          localStorage.removeItem("quantbot_token");
          setToken(null);
          delete api.defaults.headers.common["Authorization"];
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, []);

  const login = async (username: string, password: string) => {
    const res = await authApi.login({ username, password });
    const t = res.data.access_token;
    localStorage.setItem("quantbot_token", t);
    api.defaults.headers.common["Authorization"] = `Bearer ${t}`;
    setToken(t);
    const me = await authApi.me();
    setUser(me.data);
  };

  const register = async (username: string, email: string, password: string) => {
    await authApi.register({ username, email, password });
    await login(username, password);
  };

  const logout = () => {
    localStorage.removeItem("quantbot_token");
    setToken(null);
    setUser(null);
    delete api.defaults.headers.common["Authorization"];
  };

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
