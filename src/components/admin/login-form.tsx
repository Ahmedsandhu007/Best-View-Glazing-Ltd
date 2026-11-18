"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";

import { LogoMark } from "@/components/Logo";
import { login } from "@/components/admin/cms-client";

export function LoginForm() {
  const router = useRouter();
  const [password, setPassword] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(password);
      router.push("/admin");
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sign-in failed");
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-dvh w-full place-items-center bg-ivory px-4">
      <form onSubmit={onSubmit} className="w-full max-w-sm rounded-[6px] border border-line border-t-4 border-t-teal bg-white p-8 shadow-card">
        <div className="flex items-center gap-3 text-charcoal">
          <LogoMark className="h-10 w-10" />
          <div className="leading-none">
            <p className="font-heading text-lg font-bold">Best View</p>
            <p className="mt-1 font-heading text-[0.6rem] font-semibold uppercase tracking-[0.16em] text-muted">Glazing Ltd</p>
          </div>
        </div>
        <h1 className="mt-6 font-heading text-2xl font-bold text-charcoal">Website CMS</h1>
        <p className="mt-1 text-sm text-muted">Sign in to edit the website&apos;s text and pictures.</p>

        <label className="mt-6 block font-heading text-sm font-semibold text-charcoal">
          Password
          <input
            type="password"
            autoFocus
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1.5 w-full rounded-[4px] border border-line bg-white px-3 py-2.5 font-sans text-sm font-normal text-ink outline-none focus:border-teal focus:ring-2 focus:ring-teal/25"
          />
        </label>

        {error ? (
          <p role="alert" className="mt-3 whitespace-pre-wrap text-sm text-red-700">
            {error}
          </p>
        ) : null}

        <button
          type="submit"
          disabled={busy || !password}
          className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-[4px] bg-teal px-6 py-2.5 font-heading text-sm font-semibold text-white transition-colors hover:bg-teal-dark disabled:opacity-60"
        >
          {busy ? <Loader2 className="size-4 animate-spin" /> : null}
          Sign in
        </button>
      </form>
    </div>
  );
}
