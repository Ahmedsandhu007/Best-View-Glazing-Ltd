import { NextResponse } from "next/server";

import { getCollection, type Collection } from "@/lib/cms/registry";
import { type FieldSpec, validateCollection, type ValidationResult } from "@/lib/cms/validate";
import { readCollection, writeCollection } from "@/lib/cms/store";
import { slugify } from "@/lib/cms/limits";
import { GitHubConfigError, GitHubConflictError } from "@/lib/github";
import { detectRenames, normalizePath } from "@/lib/redirects";
import { recordRenames } from "@/lib/cms/renames";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type Params = { params: Promise<{ file: string }> };

const json = (data: unknown, status = 200) => NextResponse.json(data, { status });

function handle(err: unknown) {
  if (err instanceof GitHubConflictError) return json({ error: err.message }, 409);
  if (err instanceof GitHubConfigError) return json({ error: err.message }, 503);
  return json({ error: err instanceof Error ? err.message : "Unexpected error" }, 500);
}

const PLACEHOLDER_IMAGE = "/images/placeholder.svg";

/** Fields with their `enumFrom` choices filled from the other collection's current (draft) entries. */
async function resolvedFields(col: Collection): Promise<FieldSpec[]> {
  if (!col.fields.some((f) => f.enumFrom)) return col.fields;
  return Promise.all(
    col.fields.map(async (f) => {
      if (!f.enumFrom) return f;
      const source = getCollection(f.enumFrom.collection);
      if (!source) return f;
      const { data } = await readCollection<Record<string, unknown>[]>(source.file);
      const options = (Array.isArray(data) ? data : []).map((e) => String(e?.[f.enumFrom!.valueField] ?? "")).filter(Boolean);
      return { ...f, enum: options };
    }),
  );
}

/** Validate with the resolved fields plus the collection's own checks. */
function validateWith(col: Collection, fields: FieldSpec[], data: unknown): ValidationResult {
  const base = validateCollection({ mode: col.mode, idField: col.idField ?? "slug", fields }, data);
  const extra = col.check ? col.check(data) : [];
  if (extra.length === 0) return base;
  return { ok: false, errors: [...(base.ok ? [] : base.errors), ...extra] };
}

/** Build a minimal entry that satisfies the collection's required fields. */
function defaultValue(f: FieldSpec): unknown {
  switch (f.type) {
    case "string":
    case "text":
      if (f.format === "image") return f.required ? PLACEHOLDER_IMAGE : "";
      if (f.format === "path") return "/contact";
      if (f.format === "slug") return "";
      return f.enum ? f.enum[0] : f.required ? "Untitled" : "";
    case "number":
      return 0;
    case "boolean":
      return false;
    case "string[]":
      return f.required ? ["Untitled"] : [];
    case "object":
      return Object.fromEntries((f.fields ?? []).map((sf) => [sf.key, defaultValue(sf)]));
    case "object[]":
      return [];
    default:
      return "";
  }
}

export async function GET(_req: Request, { params }: Params) {
  const col = getCollection((await params).file);
  if (!col) return json({ error: "unknown_collection" }, 404);
  try {
    const { data, sha } = await readCollection(col.file);
    const fields = await resolvedFields(col);
    return json({ data, sha, mode: col.mode, idField: col.idField, titleField: col.titleField, fields, label: col.label, description: col.description, guide: col.guide, pathPrefix: col.pathPrefix });
  } catch (e) {
    return handle(e);
  }
}

export async function PUT(req: Request, { params }: Params) {
  const col = getCollection((await params).file);
  if (!col) return json({ error: "unknown_collection" }, 404);
  const body = await req.json().catch(() => null);
  if (!body) return json({ error: "invalid_json" }, 400);

  try {
    const fields = await resolvedFields(col);
    if (col.mode === "object") {
      const v = validateWith(col, fields, body.data);
      if (!v.ok) return json({ errors: v.errors }, 422);
      await writeCollection(col.file, body.data, body.sha ?? null, `CMS: update ${col.label}`);
      return json({ ok: true });
    }

    // list mode: replace (or append) the entry matched by idField, or reorder the whole list
    const idField = col.idField ?? "slug";
    const { data } = await readCollection<Record<string, unknown>[]>(col.file);
    const current = Array.isArray(data) ? data.slice() : [];

    if (Array.isArray(body.order)) {
      const order = body.order as string[];
      const byId = new Map(current.map((e) => [String(e?.[idField]), e]));
      if (order.length !== current.length || order.some((id) => !byId.has(id))) return json({ error: "The list changed since you loaded it. Reload and try again." }, 409);
      const reordered = order.map((id) => byId.get(id)!);
      const v = validateWith(col, fields, reordered);
      if (!v.ok) return json({ errors: v.errors }, 422);
      await writeCollection(col.file, reordered, body.sha ?? null, `CMS: reorder ${col.label}`);
      return json({ ok: true });
    }

    const entry = body.entry as Record<string, unknown> | undefined;
    if (!entry || typeof entry[idField] !== "string") return json({ error: "missing_entry" }, 400);
    // `id` is the address the entry was opened with; it differs from entry[idField] when the editor changed the address.
    const originalId = typeof body.id === "string" && body.id ? (body.id as string) : (entry[idField] as string);
    const idx = current.findIndex((e) => e?.[idField] === originalId);
    if (entry[idField] !== originalId && current.some((e, i) => i !== idx && e?.[idField] === entry[idField])) {
      return json({ errors: [`The address "${entry[idField]}" is already used by another entry.`] }, 422);
    }
    const before = idx >= 0 ? current[idx] : null;
    if (idx >= 0) current[idx] = entry;
    else current.push(entry);

    const v = validateWith(col, fields, current);
    if (!v.ok) return json({ errors: v.errors }, 422);
    await writeCollection(col.file, current, body.sha ?? null, `CMS: update ${col.label}/${entry[idField]}`);

    // A moved page address gets a redirect from the old one (services, blog, case studies, districts).
    const renames = detectRenames({ pathPrefix: col.pathPrefix, idField }, before, entry);
    await recordRenames(renames, col.label);
    return json({ ok: true, id: entry[idField], redirects: renames });
  } catch (e) {
    return handle(e);
  }
}

export async function POST(req: Request, { params }: Params) {
  const col = getCollection((await params).file);
  if (!col || col.mode !== "list") return json({ error: "unsupported" }, 400);
  const body = await req.json().catch(() => ({}));
  const idField = col.idField ?? "slug";
  const title = String((body as { title?: string }).title || "New entry").slice(0, 120);

  try {
    const { data } = await readCollection<Record<string, unknown>[]>(col.file);
    const arr = Array.isArray(data) ? data.slice() : [];

    // the server owns the unique id: a slug from the title, or for Redirects the old address itself
    const base = idField === "from" ? normalizePath(title.startsWith("/") ? title : `/${slugify(title)}`) : slugify(title) || "entry";
    let slug = base;
    let n = 1;
    while (arr.some((e) => e?.[idField] === slug)) slug = `${base}-${++n}`;

    const fields = await resolvedFields(col);
    const entry: Record<string, unknown> = {};
    for (const f of fields) entry[f.key] = defaultValue(f);
    entry[idField] = slug;
    if (col.titleField && col.titleField !== idField) entry[col.titleField] = title;

    arr.push(entry);
    const v = validateWith(col, fields, arr);
    if (!v.ok) return json({ errors: v.errors }, 422);
    await writeCollection(col.file, arr, null, `CMS: create ${col.label}/${slug}`);
    return json({ ok: true, slug });
  } catch (e) {
    return handle(e);
  }
}

export async function DELETE(req: Request, { params }: Params) {
  const col = getCollection((await params).file);
  if (!col || col.mode !== "list") return json({ error: "unsupported" }, 400);
  const slug = new URL(req.url).searchParams.get("slug");
  if (!slug) return json({ error: "missing_slug" }, 400);
  const idField = col.idField ?? "slug";

  try {
    const { data } = await readCollection<Record<string, unknown>[]>(col.file);
    const arr = (Array.isArray(data) ? data : []).filter((e) => e?.[idField] !== slug);
    const v = validateWith(col, await resolvedFields(col), arr);
    if (!v.ok) return json({ errors: v.errors }, 422);
    await writeCollection(col.file, arr, null, `CMS: delete ${col.label}/${slug}`);
    return json({ ok: true });
  } catch (e) {
    return handle(e);
  }
}
