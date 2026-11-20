"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertCircle, ArrowDown, ArrowLeft, ArrowUp, Check, Loader2, Pencil, Plus, Trash2 } from "lucide-react";

import { createEntry, deleteEntry, getContent, reorderEntries, saveEntry, saveObject, type CollectionMeta } from "@/components/admin/cms-client";
import { ObjectForm } from "@/components/admin/fields";
import { slugify } from "@/lib/cms/limits";
import { GuidePanel } from "@/components/admin/guide";
import { useCmsStatus } from "@/components/admin/admin-shell";

type Save = "idle" | "saving" | "saved" | "error";

/** Edits an object collection, or a single entry of a list collection (when `slug` is given). */
export function CollectionEditor({ id, slug }: { id: string; slug?: string }) {
  const router = useRouter();
  const { refresh } = useCmsStatus();
  const [moved, setMoved] = React.useState<{ from: string; to: string }[]>([]);
  const [meta, setMeta] = React.useState<CollectionMeta | null>(null);
  const [value, setValue] = React.useState<Record<string, unknown>>({});
  const [save, setSave] = React.useState<Save>("idle");
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    let active = true;
    getContent(id)
      .then((m) => {
        if (!active) return;
        setMeta(m);
        if (m.mode === "object") {
          setValue((m.data as Record<string, unknown>) ?? {});
        } else {
          const idField = m.idField ?? "slug";
          const entry = (m.data as Record<string, unknown>[]).find((e) => e?.[idField] === slug);
          setValue(entry ?? {});
        }
      })
      .catch((e) => setError(e.message));
    return () => {
      active = false;
    };
  }, [id, slug]);

  async function onSave() {
    if (!meta) return;
    setSave("saving");
    setError(null);
    try {
      let newId: string | null = null;
      if (meta.mode === "object") await saveObject(id, value, meta.sha);
      else {
        const res = await saveEntry(id, value, meta.sha, slug);
        setMoved(res.redirects ?? []);
        if (res.id !== slug) newId = res.id;
      }
      // refresh the sha so the next save does not conflict
      const fresh = await getContent(id);
      setMeta(fresh);
      setSave("saved");
      refresh();
      setTimeout(() => setSave("idle"), 2000);
      // the entry now lives at its new address in the CMS too
      if (newId) router.replace(`/admin/${id}/${encodeURIComponent(newId)}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
      setSave("error");
    }
  }

  if (error && !meta) return <Notice>{error}</Notice>;
  if (!meta) return <Loading />;

  const idField = meta.idField ?? "slug";
  const isList = meta.mode === "list";
  const entryTitle = isList ? String(value[meta.titleField ?? ""] ?? slug) : null;

  return (
    <div className="mx-auto max-w-3xl">
      {isList ? (
        <Link href={`/admin/${id}`} className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-muted hover:text-teal">
          <ArrowLeft className="size-4" /> Back to {meta.label}
        </Link>
      ) : null}

      <div className="mb-6 flex items-end justify-between gap-4">
        <div className="min-w-0">
          <h1 className="font-heading text-2xl font-bold text-charcoal">{isList ? entryTitle : meta.label}</h1>
          <p className="text-sm text-muted">{isList ? `${meta.label} · ${slug}` : meta.description}</p>
        </div>
        <SaveButton state={save} onClick={onSave} />
      </div>

      {error ? <Notice className="mb-4">{error}</Notice> : null}

      {moved.length > 0 ? (
        <div role="status" className="mb-4 rounded-[4px] border border-teal/40 bg-teal-tint px-4 py-3 text-sm text-teal-dark">
          Address changed. A redirect was added under Redirects: {moved.map((m) => `${m.from} \u2192 ${m.to}`).join(", ")}. It goes live with the next Publish.
        </div>
      ) : null}

      {meta.guide ? (
        <div className="mb-4">
          <GuidePanel guide={meta.guide} />
        </div>
      ) : null}

      <div className="rounded-[6px] border border-line bg-white p-6 shadow-card">
        {isList && meta.pathPrefix ? (
          <div className="mb-5">
            <AddressField prefix={meta.pathPrefix} value={String(value[idField] ?? "")} onChange={(v) => setValue({ ...value, [idField]: v })} />
          </div>
        ) : null}
        <ObjectForm fields={meta.fields} value={value} onChange={setValue} hiddenKeys={isList && idField === "slug" ? [idField] : []} />
      </div>

      <div className="mt-6 flex justify-end">
        <SaveButton state={save} onClick={onSave} />
      </div>
    </div>
  );
}

/** Lists the entries of a list collection with New / Edit / Delete and move up / down. */
export function CollectionIndex({ id }: { id: string }) {
  const router = useRouter();
  const { refresh } = useCmsStatus();
  const [meta, setMeta] = React.useState<CollectionMeta | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [busy, setBusy] = React.useState(false);

  const load = React.useCallback(() => {
    getContent(id)
      .then(setMeta)
      .catch((e) => setError(e.message));
  }, [id]);

  React.useEffect(() => load(), [load]);

  async function onNew() {
    setBusy(true);
    try {
      const idField = meta?.idField ?? "slug";
      const question = idField === "from" ? "New redirect: what is the OLD address? (e.g. /services/old-name)" : `New ${meta?.label ?? "entry"}: what is its title?`;
      const title = window.prompt(question)?.trim();
      if (!title) return;
      const { slug } = await createEntry(id, title);
      refresh();
      router.push(`/admin/${id}/${encodeURIComponent(slug)}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  async function onDelete(slug: string, title: string) {
    if (!window.confirm(`Delete "${title}"? Nothing goes live until you press Publish.`)) return;
    try {
      await deleteEntry(id, slug);
      refresh();
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  }

  async function onMove(index: number, direction: -1 | 1) {
    if (!meta) return;
    const idField = meta.idField ?? "slug";
    const ids = ((meta.data as Record<string, unknown>[]) ?? []).map((e) => String(e[idField]));
    const j = index + direction;
    if (j < 0 || j >= ids.length) return;
    [ids[index], ids[j]] = [ids[j], ids[index]];
    setBusy(true);
    try {
      await reorderEntries(id, ids, meta.sha);
      refresh();
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reorder failed");
    } finally {
      setBusy(false);
    }
  }

  if (error && !meta) return <Notice>{error}</Notice>;
  if (!meta) return <Loading />;

  const idField = meta.idField ?? "slug";
  const titleField = meta.titleField ?? meta.fields.find((f) => f.key !== idField)?.key ?? idField;
  const entries = (meta.data as Record<string, unknown>[]) ?? [];

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6 flex items-center justify-between gap-4">
        <div>
          <h1 className="font-heading text-2xl font-bold text-charcoal">{meta.label}</h1>
          <p className="text-sm text-muted">
            {entries.length} {entries.length === 1 ? "entry" : "entries"} · shown on the site in this order
          </p>
        </div>
        <button
          type="button"
          onClick={onNew}
          disabled={busy}
          className="inline-flex items-center gap-1.5 rounded-[4px] bg-teal px-4 py-2 font-heading text-sm font-semibold text-white transition-colors hover:bg-teal-dark disabled:opacity-60"
        >
          {busy ? <Loader2 className="size-4 animate-spin" /> : <Plus className="size-4" />} New
        </button>
      </div>

      {meta.guide ? (
        <div className="mb-4">
          <GuidePanel guide={meta.guide} />
        </div>
      ) : null}

      {error ? <Notice className="mb-4">{error}</Notice> : null}

      <ul className="divide-y divide-line overflow-hidden rounded-[6px] border border-line bg-white shadow-card">
        {entries.map((e, i) => {
          const slug = String(e[idField]);
          const title = String(e[titleField] ?? slug);
          return (
            <li key={slug} className="flex items-center justify-between gap-3 px-4 py-3">
              <div className="flex min-w-0 items-center gap-3">
                <span className="w-6 shrink-0 text-right font-heading text-sm font-bold tabular-nums text-muted">{i + 1}</span>
                <div className="min-w-0">
                  <p className="truncate font-heading font-semibold text-charcoal">{title}</p>
                  <p className="truncate text-xs text-muted">{slug}</p>
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-1.5">
                <IconLink href={`/admin/${id}/${encodeURIComponent(slug)}`} label="Edit">
                  <Pencil className="size-4" />
                </IconLink>
                <IconButton onClick={() => onMove(i, -1)} label="Move up" disabled={busy || i === 0}>
                  <ArrowUp className="size-4" />
                </IconButton>
                <IconButton onClick={() => onMove(i, 1)} label="Move down" disabled={busy || i === entries.length - 1}>
                  <ArrowDown className="size-4" />
                </IconButton>
                <IconButton onClick={() => onDelete(slug, title)} label="Delete" danger>
                  <Trash2 className="size-4" />
                </IconButton>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/** The page address (slug) of a list entry that is a page, shown with its fixed root. */
function AddressField({ prefix, value, onChange }: { prefix: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="block">
      <span className="mb-1.5 flex items-center justify-between gap-2">
        <span className="font-heading text-sm font-semibold text-charcoal">
          Page address <span className="text-teal"> *</span>
        </span>
        <span className="text-xs tabular-nums text-muted">{value.length}/60</span>
      </span>
      <span className="flex items-stretch overflow-hidden rounded-[4px] border border-line bg-white focus-within:border-teal focus-within:ring-2 focus-within:ring-teal/25">
        <span className="flex items-center border-r border-line bg-ivory px-3 text-sm text-muted">{prefix}/</span>
        <input
          className="w-full px-3 py-2 text-sm text-ink outline-none"
          value={value}
          onChange={(e) => onChange(slugify(e.target.value.replace(/\s+$/, "-")))}
          spellCheck={false}
          autoComplete="off"
        />
      </span>
      <span className="mt-1 block text-xs text-muted">
        Lower-case words joined by hyphens. Changing it moves the page: the old address is redirected to the new one automatically and the sitemap updates. Do not change it without a reason, as rankings take time to follow.
      </span>
    </label>
  );
}

const iconCls = "grid size-9 place-items-center rounded-[4px] border border-line bg-white text-charcoal transition-colors hover:border-teal hover:text-teal disabled:opacity-40 disabled:hover:border-line disabled:hover:text-charcoal";

function IconLink({ href, label, children }: { href: string; label: string; children: React.ReactNode }) {
  return (
    <Link href={href} className={iconCls} aria-label={label} title={label}>
      {children}
    </Link>
  );
}

function IconButton({ onClick, label, danger, disabled, children }: { onClick: () => void; label: string; danger?: boolean; disabled?: boolean; children: React.ReactNode }) {
  return (
    <button type="button" onClick={onClick} disabled={disabled} className={`${iconCls} ${danger ? "hover:border-red-700 hover:text-red-700" : ""}`} aria-label={label} title={label}>
      {children}
    </button>
  );
}

function SaveButton({ state, onClick }: { state: Save; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={state === "saving"}
      className="inline-flex shrink-0 items-center gap-2 rounded-[4px] bg-teal px-6 py-2.5 font-heading text-sm font-semibold text-white transition-colors hover:bg-teal-dark disabled:opacity-60"
    >
      {state === "saving" ? (
        <>
          <Loader2 className="size-4 animate-spin" /> Saving…
        </>
      ) : state === "saved" ? (
        <>
          <Check className="size-4" /> Saved
        </>
      ) : (
        "Save"
      )}
    </button>
  );
}

function Notice({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div role="alert" className={`flex items-start gap-2 rounded-[4px] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 ${className ?? ""}`}>
      <AlertCircle className="mt-0.5 size-4 shrink-0" />
      <pre className="whitespace-pre-wrap font-sans">{children}</pre>
    </div>
  );
}

function Loading() {
  return (
    <div className="grid place-items-center py-20 text-muted">
      <Loader2 className="size-6 animate-spin" />
    </div>
  );
}
