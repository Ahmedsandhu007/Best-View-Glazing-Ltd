import { NextResponse } from "next/server";
import { deliverEnquiry, type EnquiryAttachment } from "@/lib/enquiry/deliver";
import {
  enquiryFieldNames,
  fileRules,
  normalisePostcode,
  validateEnquiry,
  validateFileList,
  type EnquiryFields,
} from "@/lib/enquiry/validation";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/* ---- light in-memory rate limit (per server instance) ---- */
const WINDOW_MS = 15 * 60 * 1000;
const MAX_PER_WINDOW = 6;
const hits = new Map<string, number[]>();

function rateLimited(ip: string) {
  const now = Date.now();
  const recent = (hits.get(ip) ?? []).filter((t) => now - t < WINDOW_MS);
  recent.push(now);
  hits.set(ip, recent);
  if (hits.size > 5000) hits.clear();
  return recent.length > MAX_PER_WINDOW;
}

/* ---- file signature checks (never trust the declared MIME type) ---- */
function sniffImageType(bytes: Uint8Array): string | null {
  if (bytes.length < 12) return null;
  if (bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) return "image/jpeg";
  if (bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e && bytes[3] === 0x47) return "image/png";
  const ascii = (from: number, to: number) => String.fromCharCode(...bytes.slice(from, to));
  if (ascii(0, 4) === "RIFF" && ascii(8, 12) === "WEBP") return "image/webp";
  if (ascii(4, 8) === "ftyp") {
    const brand = ascii(8, 12).toLowerCase();
    if (["heic", "heix", "hevc", "hevx", "mif1", "msf1", "heif"].includes(brand)) return "image/heic";
  }
  return null;
}

function safeFilename(name: string) {
  const base = name.split(/[\\/]/).pop() ?? "image";
  return base.replace(/[^\w.\-]+/g, "_").slice(0, 80) || "image";
}

function makeReference() {
  const time = Date.now().toString(36).toUpperCase();
  const rand = Math.random().toString(36).slice(2, 6).toUpperCase();
  return `BVG-${time}-${rand}`;
}

export async function POST(req: Request) {
  const ip = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "unknown";
  if (rateLimited(ip)) {
    return NextResponse.json({ ok: false, message: "Too many enquiries have been sent from this connection. Please try again later." }, { status: 429 });
  }

  let form: FormData;
  try {
    form = await req.formData();
  } catch {
    return NextResponse.json({ ok: false, message: "The enquiry could not be read. Please try again." }, { status: 400 });
  }

  // Honeypot: real users never see this field. Bots that fill it are dropped quietly.
  if (typeof form.get("company_website") === "string" && (form.get("company_website") as string).length > 0) {
    return NextResponse.json({ ok: false, message: "Submission rejected." }, { status: 400 });
  }

  const fields = Object.fromEntries(
    enquiryFieldNames.map((k) => {
      const raw = form.get(k);
      return [k, typeof raw === "string" ? raw.trim() : ""];
    }),
  ) as EnquiryFields;
  fields.postcode = normalisePostcode(fields.postcode);

  const errors = validateEnquiry(fields);
  if (Object.keys(errors).length > 0) {
    return NextResponse.json({ ok: false, message: "Please correct the highlighted fields.", errors }, { status: 422 });
  }

  const files = form.getAll("images").filter((f): f is File => f instanceof File && f.size > 0);
  const fileError = validateFileList(files.map((f) => ({ name: f.name, size: f.size, type: f.type })));
  if (fileError) {
    return NextResponse.json({ ok: false, message: fileError, errors: { files: fileError } }, { status: 422 });
  }

  const attachments: EnquiryAttachment[] = [];
  for (const file of files.slice(0, fileRules.maxFiles)) {
    const buffer = Buffer.from(await file.arrayBuffer());
    const detected = sniffImageType(new Uint8Array(buffer.subarray(0, 16)));
    if (!detected) {
      const msg = `"${file.name}" does not appear to be a valid image file.`;
      return NextResponse.json({ ok: false, message: msg, errors: { files: msg } }, { status: 422 });
    }
    attachments.push({ filename: safeFilename(file.name), contentType: detected, base64: buffer.toString("base64"), size: buffer.length });
  }

  const payload = {
    reference: makeReference(),
    receivedAt: new Date().toISOString(),
    fields,
    attachments,
    meta: {
      page: typeof form.get("page") === "string" ? (form.get("page") as string).slice(0, 200) : null,
      userAgent: req.headers.get("user-agent")?.slice(0, 200) ?? null,
    },
  };

  const result = await deliverEnquiry(payload);

  if (result.ok) {
    return NextResponse.json({ ok: true, reference: payload.reference });
  }

  if (result.code === "not_configured") {
    console.error("[enquiry] No delivery backend configured. Set ENQUIRY_WEBHOOK_URL or RESEND_API_KEY + ENQUIRY_TO_EMAIL + ENQUIRY_FROM_EMAIL.");
    return NextResponse.json(
      {
        ok: false,
        code: "not_configured",
        message: "The enquiry service is not connected yet, so your message has not been sent. Please try again later.",
      },
      { status: 503 },
    );
  }

  console.error("[enquiry] Delivery failed:", result.detail);
  return NextResponse.json(
    { ok: false, code: "provider_error", message: "We could not send your enquiry just now. Please try again in a few minutes." },
    { status: 502 },
  );
}
