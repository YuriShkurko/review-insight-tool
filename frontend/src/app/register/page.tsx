"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import AuthForm from "@/components/AuthForm";
import { apiFetch } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { TokenResponse } from "@/lib/types";

export default function RegisterPage() {
  const { login } = useAuth();
  const router = useRouter();

  async function handleRegister(email: string, password: string) {
    const data = await apiFetch<TokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    await login(data.access_token);
    router.push("/businesses");
  }

  return (
    <AuthForm
      title="Create Account"
      submitLabel="Register"
      onSubmit={handleRegister}
      footer={
        <Link href="/login" className="text-blue-600 hover:underline">
          Already have an account? Sign in
        </Link>
      }
    />
  );
}
