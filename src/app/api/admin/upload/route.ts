import { NextResponse } from "next/server";

import { writeBinary } from "@/lib/cms/store";
import { slugify } from "@/lib/cms/limits";
import { GitHubConfigError } from "@/lib/github";

export const runtime = "nodejs";

const MAX_BYTES = 4 * 1024 * 1024; // 4 MB (the host rejects request bodies over 4.5 MB)
const ALLOWED: Record<string, string> = {
  "image/jpeg": "jpg",
  "image/png": "png",
  "image/webp": "webp",
  "image/svg+xml": "svg",
  "image/avif": "avif",
};

/** Check the bytes really are the image type claimed (SVG is text, so it is checked by its opening tag). */
function looksLike(type: string, bytes: Uint8Array): boolean {
  const ascii = (from: number, to: number) => String.fromCharCode(...bytes.slice(from, to));
  switch (type) {
    case "image/jpeg":
      return bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff;
    case "image/png":
      return bytes[0] === 0x89 && ascii(1, 4) === "PNG";
    case "image/webp":
      return ascii(0, 4) === "RIFF" && ascii(8, 12) === "WEBP";
    case "image/avif":
      return ascii(4, 8) === "ftyp";
    case "image/svg+xml":
      return /<svg[\s>]/i.test(new TextDecoder().decode(bytes.slice(0, 2048)));
    default:
      return false;
  }
}

export async function POST(req: Request) {
  try {
    const form = await req.formData();
    const file = form.get("file");
    if (!(file instanceof File)) return NextResponse.json({ error: "No file provided." }, { status: 400 });
    if (file.size > MAX_BYTES) return NextResponse.json({ error: "File must be under 4 MB." }, { status: 422 });

    const ext = ALLOWED[file.type];
    if (!ext) return NextResponse.json({ error: "Unsupported image type. Use JPG, PNG, WebP, AVIF or SVG." }, { status: 422 });

    const buffer = Buffer.from(await file.arrayBuffer());
    if (!looksLike(file.type, new Uint8Array(buffer.subarray(0, 2048)))) {
      return NextResponse.json({ error: "That file does not look like a valid image." }, { status: 422 });
    }
    if (ext === "svg" && /<script[\s>]|on\w+\s*=/i.test(buffer.toString("utf8"))) {
      return NextResponse.json({ error: "SVG files with scripts are not allowed." }, { status: 422 });
    }

    const base = slugify(file.name.replace(/\.[^.]+$/, "")) || "upload";
    const stamp = Math.abs(hashString(`${file.name}:${file.size}:${Date.now()}`)).toString(36).slice(0, 6);
    const path = `public/uploads/${base}-${stamp}.${ext}`;

    await writeBinary(path, buffer.toString("base64"), `CMS: upload ${base}.${ext}`);

    // Public URL (strip the leading "public")
    return NextResponse.json({ ok: true, url: path.replace(/^public/, "") });
  } catch (e) {
    if (e instanceof GitHubConfigError) return NextResponse.json({ error: e.message }, { status: 503 });
    return NextResponse.json({ error: e instanceof Error ? e.message : "Upload failed" }, { status: 500 });
  }
}

function hashString(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (Math.imul(31, h) + s.charCodeAt(i)) | 0;
  return h;
}
