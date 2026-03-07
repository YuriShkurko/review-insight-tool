"use client";

import type { ReactNode } from "react";
import { AuthProvider } from "@/lib/auth";
import NavBar from "@/components/NavBar";

export function Providers({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <NavBar />
      <main>{children}</main>
    </AuthProvider>
  );
}
