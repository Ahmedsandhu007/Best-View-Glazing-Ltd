/**
 * Enquiry delivery.
 * ------------------------------------------------------------------
 * The API route validates the submission and hands it to `deliverEnquiry`.
 * Which backend receives it is decided purely by environment variables,
 * so connecting a real inbox or CRM never touches the UI:
 *
 *   ENQUIRY_WEBHOOK_URL      POST the enquiry as JSON to any endpoint
 *                            (Make, Zapier, n8n, a CRM, your own server).
 *   ENQUIRY_WEBHOOK_SECRET   Optional; sent as the `X-Enquiry-Secret` header.
 *
 *   RESEND_API_KEY           Send the enquiry by email through Resend's REST API.
 *   ENQUIRY_TO_EMAIL         Inbox that receives enquiries.
 *   ENQUIRY_FROM_EMAIL       Verified sender, e.g. "Best View Glazing Website <enquiries@yourdomain.co.uk>".
 *
 * If neither backend is configured the route returns 503 and the form shows
 * an honest "not connected" message. A success state is never shown unless
 * the backend accepted the enquiry.
 */
import type { EnquiryFields } from "./validation";

export type EnquiryAttachment = { filename: string; contentType: string; base64: string; size: number };

export type EnquiryPayload = {
  reference: string;
  receivedAt: string;
  fields: EnquiryFields;
  attachments: EnquiryAttachment[];
  meta: { page: string | null; userAgent: string | null };
};

export type DeliveryResult = { ok: true; provider: string } | { ok: false; code: "not_configured" | "provider_error"; detail?: string };

type Provider = { name: string; send: (payload: EnquiryPayload) => Promise<void> };

const fieldLabels: Record<keyof EnquiryFields, string> = {
  fullName: "Full name",
  email: "Email address",
  phone: "Phone number",
  postcode: "Postcode",
  address: "Property address",
  propertyType: "Property type",
  service: "Service required",
  description: "Description of the problem",
  contactTime: "Preferred contact time",
  consent: "Privacy consent",
};

function escapeHtml(s: string) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c] as string);
}

export function renderEnquiryText(p: EnquiryPayload) {
  const lines = [
    `New website enquiry ${p.reference}`,
    `Received: ${p.receivedAt}`,
    "",
    ...(Object.keys(fieldLabels) as (keyof EnquiryFields)[]).map((k) => `${fieldLabels[k]}: ${p.fields[k] || "-"}`),
    "",
    `Attachments: ${p.attachments.length ? p.attachments.map((a) => `${a.filename} (${Math.round(a.size / 1024)} KB)`).join(", ") : "none"}`,
    `Page: ${p.meta.page ?? "-"}`,
  ];
  return lines.join("\n");
}

export function renderEnquiryHtml(p: EnquiryPayload) {
  const rows = (Object.keys(fieldLabels) as (keyof EnquiryFields)[])
    .map(
      (k) =>
        `<tr><th align="left" style="padding:6px 12px 6px 0;color:#667176;font-weight:600;vertical-align:top;white-space:nowrap">${fieldLabels[k]}</th><td style="padding:6px 0;color:#273238;white-space:pre-wrap">${escapeHtml(p.fields[k] || "-")}</td></tr>`,
    )
    .join("");
  const attachments = p.attachments.length
    ? `<p style="color:#667176">Attachments: ${p.attachments.map((a) => escapeHtml(a.filename)).join(", ")}</p>`
    : "";
  return `<div style="font-family:Inter,Arial,sans-serif;font-size:15px;line-height:1.5;color:#273238"><h2 style="margin:0 0 4px;color:#202C30">New website enquiry</h2><p style="margin:0 0 16px;color:#667176">Reference ${p.reference} · ${p.receivedAt}</p><table cellspacing="0" cellpadding="0">${rows}</table>${attachments}</div>`;
}

function webhookProvider(): Provider | null {
  const url = process.env.ENQUIRY_WEBHOOK_URL;
  if (!url) return null;
  return {
    name: "webhook",
    send: async (payload) => {
      const res = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(process.env.ENQUIRY_WEBHOOK_SECRET ? { "X-Enquiry-Secret": process.env.ENQUIRY_WEBHOOK_SECRET } : {}),
        },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(15_000),
      });
      if (!res.ok) throw new Error(`Webhook responded ${res.status}`);
    },
  };
}

function resendProvider(): Provider | null {
  const key = process.env.RESEND_API_KEY;
  const to = process.env.ENQUIRY_TO_EMAIL;
  const from = process.env.ENQUIRY_FROM_EMAIL;
  if (!key || !to || !from) return null;
  return {
    name: "resend",
    send: async (payload) => {
      const res = await fetch("https://api.resend.com/emails", {
        method: "POST",
        headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          from,
          to: to.split(",").map((s) => s.trim()),
          ...(payload.fields.email ? { reply_to: payload.fields.email } : {}),
          subject: `Website enquiry ${payload.reference} – ${payload.fields.service} (${payload.fields.postcode})`,
          text: renderEnquiryText(payload),
          html: renderEnquiryHtml(payload),
          attachments: payload.attachments.map((a) => ({ filename: a.filename, content: a.base64 })),
        }),
        signal: AbortSignal.timeout(15_000),
      });
      if (!res.ok) throw new Error(`Resend responded ${res.status}: ${(await res.text()).slice(0, 200)}`);
    },
  };
}

export function getProvider(): Provider | null {
  return webhookProvider() ?? resendProvider();
}

export async function deliverEnquiry(payload: EnquiryPayload): Promise<DeliveryResult> {
  const provider = getProvider();
  if (!provider) return { ok: false, code: "not_configured" };
  try {
    await provider.send(payload);
    return { ok: true, provider: provider.name };
  } catch (err) {
    return { ok: false, code: "provider_error", detail: err instanceof Error ? err.message : String(err) };
  }
}
