import { readCollection, writeCollection } from "@/lib/cms/store";
import { applyRename, type Redirect, type Rename } from "@/lib/redirects";

const REDIRECTS_FILE = "src/content/redirects.json";

/** Write the moved addresses into the Redirects list (one draft commit), collapsing chains. */
export async function recordRenames(renames: Rename[], label: string): Promise<void> {
  if (renames.length === 0) return;
  const { data, sha } = await readCollection<Redirect[]>(REDIRECTS_FILE);
  let list = Array.isArray(data) ? data : [];
  const stamp = new Date().toISOString().slice(0, 10);
  for (const r of renames) list = applyRename(list, r.from, r.to, `Address changed in the CMS (${label}) on ${stamp}`);
  const summary = renames.map((r) => `${r.from} -> ${r.to}`).join(", ");
  await writeCollection(REDIRECTS_FILE, list, sha, `CMS: redirect ${summary}`);
}
