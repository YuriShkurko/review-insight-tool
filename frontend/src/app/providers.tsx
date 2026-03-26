"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import { AuthProvider } from "@/lib/auth";
import NavBar from "@/components/NavBar";
import { isTrailEnabled, trailEvent } from "@/lib/debugTrail";
import DebugPanel from "@/components/DebugPanel";
import { mountDebugSelector } from "@/lib/debugSelector";

function RouteWatcher() {
  const pathname = usePathname();
  const prevRef = useRef<string | null>(null);

  useEffect(() => {
    const prev = prevRef.current;
    if (prev !== null && prev !== pathname) {
      trailEvent("route:change", { from: prev, to: pathname });
    }
    prevRef.current = pathname;
  }, [pathname]);

  return null;
}

function DebugSelectorMount() {
  useEffect(() => mountDebugSelector(), []);
  return null;
}

export function Providers({ children }: { children: ReactNode }) {
  const debugEnabled = isTrailEnabled();

  return (
    <AuthProvider>
      {debugEnabled && <RouteWatcher />}
      {debugEnabled && <DebugSelectorMount />}
      <NavBar />
      <main>{children}</main>
      {debugEnabled && <DebugPanel />}
    </AuthProvider>
  );
}
