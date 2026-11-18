"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { AlertTriangle, Database, ExternalLink, FileText, Loader2, LogOut, Undo2, UploadCloud } from "lucide-react";

import { cn } from "@/lib/utils";
import { LogoMark } from "@/components/Logo";
import { discardDraft, getStatus, logout, publishDraft, type StatusInfo } from "@/components/admin/cms-client";

type NavItem = { id: string; label: string; mode: "object" | "list" };

type Ctx = { status: StatusInfo | null; refresh: () => void };
const StatusContext = React.createContext<Ctx>({ status: null, refresh: () => {} });
export const useCmsStatus = () => React.useContext(StatusContext);

export function AdminShell({ nav, children }: { nav: NavItem[]; children: React.ReactNode }) {
  const pathname = usePathname();
  const [status, setStatus] = React.useState<StatusInfo | null>(null);

  const refresh = React.useCallback(() => {
    getStatus()
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  React.useEffect(() => {
    if (pathname === "/admin/login") return;
    refresh();
  }, [pathname, refresh]);

  // The sign-in page renders without the admin chrome.
  if (pathname === "/admin/login") return <>{children}</>;

  const objects = nav.filter((n) => n.mode === "object");
  const lists = nav.filter((n) => n.mode === "list");

  return (
    <StatusContext.Provider value={{ status, refresh }}>
      <div className="min-h-dvh w-full bg-ivory">
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-brass bg-charcoal px-4 text-white sm:px-6">
          <Link href="/admin" className="flex items-center gap-2.5 font-heading font-bold">
            <LogoMark className="h-7 w-7" />
            <span>Best View Glazing</span>
            <span className="rounded-[3px] bg-white/10 px-1.5 py-0.5 text-[0.65rem] font-semibold uppercase tracking-[0.14em] text-white/80">CMS</span>
          </Link>
          <div className="flex items-center gap-1.5 text-sm">
            {status ? (
              <span className="hidden items-center rounded-[4px] bg-white/10 px-2.5 py-1 text-xs font-semibold text-white/85 sm:inline-flex">
                {status.mode === "github" ? "Live site" : "Local files"}
              </span>
            ) : null}
            <Link href="/" target="_blank" className="inline-flex items-center gap-1.5 rounded-[4px] px-3 py-1.5 font-medium text-white/85 hover:bg-white/10 hover:text-white">
              <ExternalLink className="size-4" /> View site
            </Link>
            <LogoutButton />
          </div>
        </header>

        {status && status.connection && !status.connection.ok ? (
          <div className="border-b border-red-200 bg-red-50 px-4 py-3 sm:px-6">
            <div className="mx-auto flex max-w-7xl items-start gap-2 text-sm text-red-800">
              <AlertTriangle className="mt-0.5 size-4 shrink-0" />
              <div>
                <p className="font-semibold">GitHub connection problem: edits cannot be saved or published yet.</p>
                <p className="mt-0.5">{status.connection.reason}</p>
              </div>
            </div>
          </div>
        ) : null}

        <div className="mx-auto flex max-w-7xl gap-6 px-4 py-6 sm:px-6">
          <aside className="hidden w-56 shrink-0 lg:block">
            <nav className="sticky top-20 space-y-6">
              <Link
                href="/admin"
                className={cn(
                  "block rounded-[4px] px-3 py-2 font-heading text-sm font-semibold",
                  pathname === "/admin" ? "bg-charcoal text-white" : "text-charcoal hover:bg-teal-tint",
                )}
              >
                All sections
              </Link>
              <NavGroup title="Site" icon={<FileText className="size-3.5" />} items={objects} pathname={pathname} />
              <NavGroup title="Lists" icon={<Database className="size-3.5" />} items={lists} pathname={pathname} />
            </nav>
          </aside>

          <main className="min-w-0 flex-1 pb-28">{children}</main>
        </div>

        <PublishBar />
      </div>
    </StatusContext.Provider>
  );
}

function NavGroup({ title, icon, items, pathname }: { title: string; icon: React.ReactNode; items: NavItem[]; pathname: string }) {
  return (
    <div>
      <p className="mb-1.5 flex items-center gap-1.5 px-3 font-heading text-xs font-bold uppercase tracking-[0.12em] text-muted">
        {icon} {title}
      </p>
      <ul className="space-y-0.5">
        {items.map((n) => {
          const active = pathname === `/admin/${n.id}` || pathname.startsWith(`/admin/${n.id}/`);
          return (
            <li key={n.id}>
              <Link
                href={`/admin/${n.id}`}
                className={cn("block rounded-[4px] px-3 py-1.5 text-sm font-medium", active ? "bg-teal-tint text-teal-dark" : "text-ink hover:bg-teal-tint/70")}
              >
                {n.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function LogoutButton() {
  const router = useRouter();
  return (
    <button
      type="button"
      onClick={async () => {
        await logout().catch(() => {});
        router.push("/admin/login");
        router.refresh();
      }}
      className="inline-flex items-center gap-1.5 rounded-[4px] px-3 py-1.5 font-medium text-white/85 hover:bg-white/10 hover:text-white"
    >
      <LogOut className="size-4" /> Sign out
    </button>
  );
}

function PublishBar() {
  const { status, refresh } = useCmsStatus();
  const [busy, setBusy] = React.useState<"publish" | "discard" | null>(null);
  const [msg, setMsg] = React.useState<string | null>(null);

  if (!status || status.mode !== "github" || status.pending <= 0) return null;

  async function run(kind: "publish" | "discard") {
    if (kind === "discard" && !window.confirm("Discard all unpublished changes?")) return;
    setBusy(kind);
    setMsg(null);
    try {
      if (kind === "publish") {
        await publishDraft();
        setMsg("Published. The live site is rebuilding and will update in a minute or two.");
      } else {
        await discardDraft();
        setMsg("Unpublished changes discarded.");
      }
      refresh();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-3 px-4 py-3 sm:flex-row sm:items-center sm:px-6">
        <p className="text-sm text-ink">
          <span className="font-heading font-bold text-teal">{status.pending}</span> unpublished change{status.pending === 1 ? "" : "s"}
          {status.items.length ? <span className="text-muted"> ({status.items.map((i) => i.label).join(", ")})</span> : null}
          {msg ? <span className="ml-2 text-muted">· {msg}</span> : null}
        </p>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => run("discard")}
            disabled={busy !== null}
            className="inline-flex items-center gap-1.5 rounded-[4px] border border-line px-4 py-2 font-heading text-sm font-semibold text-charcoal hover:border-red-700 hover:text-red-700 disabled:opacity-60"
          >
            {busy === "discard" ? <Loader2 className="size-4 animate-spin" /> : <Undo2 className="size-4" />} Discard
          </button>
          <button
            type="button"
            onClick={() => run("publish")}
            disabled={busy !== null}
            className="inline-flex items-center gap-1.5 rounded-[4px] bg-teal px-5 py-2 font-heading text-sm font-semibold text-white hover:bg-teal-dark disabled:opacity-60"
          >
            {busy === "publish" ? <Loader2 className="size-4 animate-spin" /> : <UploadCloud className="size-4" />}
            Publish {status.pending}
          </button>
        </div>
      </div>
    </div>
  );
}
