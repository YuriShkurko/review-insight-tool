"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";

export default function NavBar() {
  const { user, logout, isLoading } = useAuth();

  if (isLoading || !user) return null;

  return (
    <nav className="bg-white border-b border-gray-200">
      <div className="max-w-3xl mx-auto px-4 h-14 flex items-center justify-between">
        <Link href="/businesses" className="font-semibold text-lg">
          Review Insight
        </Link>
        <div className="flex items-center gap-4 text-sm">
          <span className="text-gray-500">{user.email}</span>
          <button
            onClick={logout}
            className="text-red-600 hover:underline font-medium"
          >
            Logout
          </button>
        </div>
      </div>
    </nav>
  );
}
