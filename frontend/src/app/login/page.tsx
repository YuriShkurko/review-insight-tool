"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import AuthForm from "@/components/AuthForm";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { TokenResponse } from "@/lib/types";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();

  async function handleLogin(email: string, password: string) {
    const data = await apiFetch<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    await login(data.access_token);
    router.push("/businesses");
  }

  return (
    <AuthForm
      title="Sign In"
      submitLabel="Sign In"
      onSubmit={handleLogin}
      footer={
        <Link href="/register" className="text-blue-600 hover:underline">
          Don&apos;t have an account? Register
        </Link>
      }
    />
  );
}
