/**
 * Redirect rules, pure helpers shared by the proxy, the sitemap and the CMS.
 * The list itself lives in src/content/redirects.json, edited under "Redirects"
 * in the CMS and extended automatically when a page address (slug) changes.
 */
export type Redirect = {
  /** Old address on this site, e.g. /services/old-name. Lower-case, no trailing slash. */
  from: string;
  /** New address: a path on this site (/...) or a full https:// address. */
  to: string;
  /** Free text, e.g. who changed it and why. */
  note?: string;
};

/** Lower-case and without a trailing slash, the form every path takes on the site. */
export function normalizePath(path: string) {
  let p = path.trim().toLowerCase();
  if (!p.startsWith("/")) p = `/${p}`;
  if (p.length > 1 && p.endsWith("/")) p = p.slice(0, -1);
  return p;
}

const isExternal = (to: string) => /^https?:\/\//i.test(to);

export function buildRedirectMap(list: Redirect[]) {
  const map = new Map<string, string>();
  for (const r of list) {
    if (!r || typeof r.from !== "string" || typeof r.to !== "string") continue;
    const from = normalizePath(r.from);
    const to = isExternal(r.to) ? r.to.trim() : normalizePath(r.to);
    if (from !== to) map.set(from, to);
  }
  return map;
}

/** Follow the rules from `path` until they stop (at most 5 steps, loops cut), so a visitor is sent in ONE hop. */
export function resolveRedirect(map: Map<string, string>, path: string): string | null {
  let current = normalizePath(path);
  const seen = new Set<string>([current]);
  let target: string | null = null;
  for (let i = 0; i < 5; i++) {
    const next = map.get(current);
    if (!next) break;
    target = next;
    if (isExternal(next) || seen.has(next)) break;
    seen.add(next);
    current = next;
  }
  return target;
}

/**
 * Record that `from` moved to `to`:
 * - every rule that pointed at `from` now points at `to` (no chains),
 * - a rule starting at `to` is dropped (the address is a live page again),
 * - the new rule is added, replacing any older rule for `from`.
 */
export function applyRename(list: Redirect[], from: string, to: string, note?: string): Redirect[] {
  const f = normalizePath(from);
  const t = isExternal(to) ? to.trim() : normalizePath(to);
  if (f === t) return list;
  const next: Redirect[] = [];
  for (const r of list) {
    const rFrom = normalizePath(r.from);
    const rTo = isExternal(r.to) ? r.to.trim() : normalizePath(r.to);
    if (rFrom === f || rFrom === t) continue; // replaced below / live again
    next.push(rTo === f ? { ...r, to: t } : r);
  }
  next.push(note ? { from: f, to: t, note } : { from: f, to: t });
  return next;
}

export type Rename = { from: string; to: string };

/**
 * Compare a list entry before and after a save and return the page addresses that moved.
 * `pathPrefix` is the collection's page root (/services, /blog, /case-studies).
 * A region entry (Areas we cover) is compared district by district: a district keeps
 * its position in the list (or its name) while its address changes.
 */
export function detectRenames(
  opts: { pathPrefix?: string; idField: string; districtPrefix?: string },
  before: Record<string, unknown> | null,
  after: Record<string, unknown>,
): Rename[] {
  const renames: Rename[] = [];
  if (!before) return renames;

  if (opts.pathPrefix) {
    const oldId = before[opts.idField];
    const newId = after[opts.idField];
    if (typeof oldId === "string" && typeof newId === "string" && oldId !== newId) {
      renames.push({ from: `${opts.pathPrefix}/${oldId}`, to: `${opts.pathPrefix}/${newId}` });
    }
  }

  if (opts.districtPrefix) {
    type District = { name?: unknown; slug?: unknown };
    const oldList = (Array.isArray(before.areas) ? before.areas : []) as District[];
    const newList = (Array.isArray(after.areas) ? after.areas : []) as District[];
    const oldSlugs = new Set(oldList.map((d) => d.slug));
    const newSlugs = new Set(newList.map((d) => d.slug));
    oldList.forEach((old, i) => {
      if (typeof old.slug !== "string" || newSlugs.has(old.slug)) return; // unchanged or still there
      const samePlace = newList[i];
      let match: District | undefined;
      if (samePlace && typeof samePlace.slug === "string" && !oldSlugs.has(samePlace.slug)) match = samePlace;
      else {
        const byName = newList.filter((d) => typeof d.slug === "string" && !oldSlugs.has(d.slug) && d.name === old.name);
        if (byName.length === 1) match = byName[0];
      }
      if (match) renames.push({ from: `${opts.districtPrefix}/${old.slug}`, to: `${opts.districtPrefix}/${match.slug}` });
    });
  }

  return renames;
}
