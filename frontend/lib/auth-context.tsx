"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";

interface AuthContextValue {
  token: string | null;
  isReady: boolean;
  signIn: (token: string) => void;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);
const STORAGE_KEY = "illusions_access_token";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    setToken(window.localStorage.getItem(STORAGE_KEY));
    setIsReady(true);
  }, []);

  function signIn(newToken: string) {
    window.localStorage.setItem(STORAGE_KEY, newToken);
    setToken(newToken);
  }

  function signOut() {
    window.localStorage.removeItem(STORAGE_KEY);
    setToken(null);
  }

  return (
    <AuthContext.Provider value={{ token, isReady, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
