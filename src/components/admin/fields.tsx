"use client";

import * as React from "react";
import { ArrowDown, ArrowUp, ImageUp, Loader2, Plus, Trash2 } from "lucide-react";

import { cn } from "@/lib/utils";
import { limitFor } from "@/lib/cms/limits";
import { uploadImage, type FieldSpec } from "@/components/admin/cms-client";
import { GuidePanel } from "@/components/admin/guide";
import { LongTextField } from "@/components/admin/long-text";

const inputCls = "w-full rounded-[4px] border border-line bg-white px-3 py-2 text-sm text-ink outline-none transition-colors focus:border-teal focus:ring-2 focus:ring-teal/25";

/** "primaryCta" -> "Primary cta", "imageAlt" -> "Image alt". */
const humanise = (key: string) => key.replace(/([a-z])([A-Z])/g, "$1 $2").replace(/[-_]/g, " ").replace(/^./, (c) => c.toUpperCase());

function FieldShell({ field, value, children }: { field: FieldSpec; value?: unknown; children: React.ReactNode }) {
  const label = field.label ?? humanise(field.key);
  const max = field.max ?? limitFor(field.key);
  const len = typeof value === "string" ? value.length : null;
  return (
    <label className="block">
      <span className="mb-1.5 flex items-center justify-between gap-2">
        <span className="font-heading text-sm font-semibold text-charcoal">
          {label}
          {field.required ? <span className="text-teal"> *</span> : null}
        </span>
        {len !== null && (field.type === "string" || field.type === "text") ? (
          <span className={cn("text-xs tabular-nums", len > max ? "text-red-700" : "text-muted")}>
            {len}/{max}
          </span>
        ) : null}
      </span>
      {children}
      {field.help ? <span className="mt-1 block text-xs text-muted">{field.help}</span> : null}
    </label>
  );
}

export function FieldInput({ field, value, onChange }: { field: FieldSpec; value: unknown; onChange: (v: unknown) => void }) {
  if (field.type === "string" && field.format === "image") {
    return (
      <FieldShell field={field} value={value}>
        <ImageField value={(value as string) ?? ""} onChange={onChange} />
      </FieldShell>
    );
  }

  switch (field.type) {
    case "string":
      if (field.enum) {
        return (
          <FieldShell field={field} value={value}>
            <select className={inputCls} value={(value as string) ?? ""} onChange={(e) => onChange(e.target.value)}>
              {field.required ? null : <option value="">Default</option>}
              {field.enum.map((o) => (
                <option key={o} value={o}>
                  {o}
                </option>
              ))}
            </select>
          </FieldShell>
        );
      }
      return (
        <FieldShell field={field} value={value}>
          <input className={inputCls} value={(value as string) ?? ""} onChange={(e) => onChange(e.target.value)} />
        </FieldShell>
      );
    case "text":
      return (
        <FieldShell field={field} value={value}>
          <textarea className={cn(inputCls, "min-h-24 resize-y")} value={(value as string) ?? ""} onChange={(e) => onChange(e.target.value)} />
        </FieldShell>
      );
    case "number":
      return (
        <FieldShell field={field} value={value}>
          <input
            type="number"
            className={inputCls}
            min={field.min}
            max={field.max}
            value={value === undefined || value === null ? "" : (value as number)}
            onChange={(e) => onChange(e.target.value === "" ? 0 : Number(e.target.value))}
          />
        </FieldShell>
      );
    case "boolean":
      return (
        <label className="flex items-center gap-2 py-1">
          <input type="checkbox" className="size-4 accent-teal" checked={Boolean(value)} onChange={(e) => onChange(e.target.checked)} />
          <span className="font-heading text-sm font-semibold text-charcoal">{field.label ?? humanise(field.key)}</span>
        </label>
      );
    case "string[]":
      if (field.longText) {
        return (
          <FieldShell field={field}>
            <LongTextField values={(value as string[]) ?? []} onChange={onChange} max={field.max ?? limitFor(field.key)} />
          </FieldShell>
        );
      }
      return (
        <FieldShell field={field}>
          <StringList values={(value as string[]) ?? []} onChange={onChange} max={field.max ?? limitFor(field.key)} multiline={(field.max ?? limitFor(field.key)) > 200} />
        </FieldShell>
      );
    case "object":
      return (
        <fieldset className="rounded-[6px] border border-line bg-ivory/60 p-4">
          <legend className="px-1 font-heading text-sm font-bold text-charcoal">{field.label ?? humanise(field.key)}</legend>
          <div className="grid gap-4 sm:grid-cols-2">
            {(field.fields ?? []).map((sf) => (
              <div key={sf.key} className={sf.type === "object" || sf.type === "object[]" || sf.type === "string[]" || sf.type === "text" ? "sm:col-span-2" : ""}>
                <FieldInput field={sf} value={(value as Record<string, unknown>)?.[sf.key]} onChange={(v) => onChange({ ...((value as object) ?? {}), [sf.key]: v })} />
              </div>
            ))}
          </div>
        </fieldset>
      );
    case "object[]":
      return (
        <FieldShell field={field}>
          <ObjectArray items={(value as Record<string, unknown>[]) ?? []} fields={field.fields ?? []} itemLabel={field.itemLabel ?? "Item"} onChange={onChange} />
        </FieldShell>
      );
    default:
      return null;
  }
}

function StringList({ values, onChange, max, multiline }: { values: string[]; onChange: (v: string[]) => void; max: number; multiline: boolean }) {
  const set = (i: number, v: string) => onChange(values.map((x, j) => (j === i ? v : x)));
  const remove = (i: number) => onChange(values.filter((_, j) => j !== i));
  const move = (i: number, d: number) => {
    const j = i + d;
    if (j < 0 || j >= values.length) return;
    const next = values.slice();
    [next[i], next[j]] = [next[j], next[i]];
    onChange(next);
  };
  return (
    <div className="space-y-2">
      {values.map((v, i) => (
        <div key={i} className="flex items-start gap-1.5">
          {multiline ? (
            <textarea className={cn(inputCls, "min-h-20 resize-y")} value={v} onChange={(e) => set(i, e.target.value)} />
          ) : (
            <input className={inputCls} value={v} maxLength={max + 20} onChange={(e) => set(i, e.target.value)} />
          )}
          <IconBtn onClick={() => move(i, -1)} title="Move up">
            <ArrowUp className="size-4" />
          </IconBtn>
          <IconBtn onClick={() => move(i, 1)} title="Move down">
            <ArrowDown className="size-4" />
          </IconBtn>
          <IconBtn onClick={() => remove(i)} title="Remove" danger>
            <Trash2 className="size-4" />
          </IconBtn>
        </div>
      ))}
      <button
        type="button"
        onClick={() => onChange([...values, ""])}
        className="inline-flex items-center gap-1.5 rounded-[4px] border border-dashed border-line px-3 py-1.5 text-sm font-medium text-charcoal hover:border-teal hover:text-teal"
      >
        <Plus className="size-4" /> Add item
      </button>
    </div>
  );
}

function ObjectArray({
  items,
  fields,
  itemLabel,
  onChange,
}: {
  items: Record<string, unknown>[];
  fields: FieldSpec[];
  itemLabel: string;
  onChange: (v: Record<string, unknown>[]) => void;
}) {
  const blank = () =>
    Object.fromEntries(fields.map((f) => [f.key, f.type === "string[]" || f.type === "object[]" ? [] : f.type === "object" ? {} : f.type === "boolean" ? false : f.type === "number" ? 0 : ""]));
  const setItem = (i: number, v: Record<string, unknown>) => onChange(items.map((x, j) => (j === i ? v : x)));
  const move = (i: number, d: number) => {
    const j = i + d;
    if (j < 0 || j >= items.length) return;
    const next = items.slice();
    [next[i], next[j]] = [next[j], next[i]];
    onChange(next);
  };
  return (
    <div className="space-y-3">
      {items.map((item, i) => (
        <div key={i} className="rounded-[6px] border border-line bg-white p-3">
          <div className="mb-2 flex items-center justify-between">
            <span className="font-heading text-xs font-bold uppercase tracking-[0.1em] text-muted">
              {itemLabel} {i + 1}
            </span>
            <div className="flex gap-1.5">
              <IconBtn onClick={() => move(i, -1)} title="Move up">
                <ArrowUp className="size-4" />
              </IconBtn>
              <IconBtn onClick={() => move(i, 1)} title="Move down">
                <ArrowDown className="size-4" />
              </IconBtn>
              <IconBtn onClick={() => onChange(items.filter((_, j) => j !== i))} title="Remove" danger>
                <Trash2 className="size-4" />
              </IconBtn>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {fields.map((f) => (
              <div key={f.key} className={f.type === "object" || f.type === "object[]" || f.type === "string[]" || f.type === "text" ? "sm:col-span-2" : ""}>
                <FieldInput field={f} value={item[f.key]} onChange={(v) => setItem(i, { ...item, [f.key]: v })} />
              </div>
            ))}
          </div>
        </div>
      ))}
      <button
        type="button"
        onClick={() => onChange([...items, blank()])}
        className="inline-flex items-center gap-1.5 rounded-[4px] border border-dashed border-line px-3 py-1.5 text-sm font-medium text-charcoal hover:border-teal hover:text-teal"
      >
        <Plus className="size-4" /> Add {itemLabel.toLowerCase()}
      </button>
    </div>
  );
}

function ImageField({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [busy, setBusy] = React.useState(false);
  const [err, setErr] = React.useState<string | null>(null);
  // A just-uploaded file is not on the live site until Publish, so preview it from the browser.
  const [preview, setPreview] = React.useState<{ url: string; local: string } | null>(null);
  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setBusy(true);
    setErr(null);
    try {
      const { url } = await uploadImage(file);
      setPreview({ url, local: URL.createObjectURL(file) });
      onChange(url);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3">
        {value ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={preview?.url === value ? preview.local : value} alt="" className="size-16 shrink-0 rounded-[4px] border border-line bg-ivory object-cover" />
        ) : (
          <span className="grid size-16 shrink-0 place-items-center rounded-[4px] border border-dashed border-line text-muted">
            <ImageUp className="size-5" />
          </span>
        )}
        <input className={inputCls} value={value} placeholder="/uploads/… or https://…" onChange={(e) => onChange(e.target.value)} />
      </div>
      <label className="inline-flex cursor-pointer items-center gap-1.5 rounded-[4px] border border-line px-3 py-1.5 text-sm font-medium text-charcoal hover:border-teal hover:text-teal">
        {busy ? <Loader2 className="size-4 animate-spin" /> : <ImageUp className="size-4" />}
        Upload a picture
        <input type="file" accept="image/*" className="sr-only" onChange={onFile} disabled={busy} />
      </label>
      {err ? <p className="text-xs text-red-700">{err}</p> : null}
      {preview?.url === value ? <p className="text-xs text-muted">Uploaded. Press Save, then Publish, and the picture will appear on the live site.</p> : null}
    </div>
  );
}

function IconBtn({ children, onClick, title, danger }: { children: React.ReactNode; onClick: () => void; title: string; danger?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      aria-label={title}
      className={cn(
        "grid size-9 shrink-0 place-items-center rounded-[4px] border border-line bg-white text-charcoal transition-colors hover:border-teal hover:text-teal",
        danger && "hover:border-red-700 hover:text-red-700",
      )}
    >
      {children}
    </button>
  );
}

/** Renders a full set of fields for an object/entry. */
export function ObjectForm({
  fields,
  value,
  onChange,
  hiddenKeys = [],
}: {
  fields: FieldSpec[];
  value: Record<string, unknown>;
  onChange: (v: Record<string, unknown>) => void;
  hiddenKeys?: string[];
}) {
  return (
    <div className="grid gap-5">
      {fields
        .filter((f) => !hiddenKeys.includes(f.key))
        .map((f) => (
          <React.Fragment key={f.key}>
            {f.guide ? <GuidePanel guide={f.guide} /> : null}
            <FieldInput field={f} value={value[f.key]} onChange={(v) => onChange({ ...value, [f.key]: v })} />
          </React.Fragment>
        ))}
    </div>
  );
}
