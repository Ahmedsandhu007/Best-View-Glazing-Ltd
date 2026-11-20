/**
 * Google Analytics 4 helpers. The Measurement ID comes from Site settings in the CMS;
 * with no ID nothing loads and these calls are no-ops.
 */
declare global {
  interface Window {
    dataLayer?: unknown[];
    gtag?: (...args: unknown[]) => void;
  }
}

export type LeadEvent = "generate_lead";
export type ClickEvent = "phone_click" | "whatsapp_click" | "email_click";

export function trackEvent(name: LeadEvent | ClickEvent | "page_view", params: Record<string, unknown> = {}) {
  if (typeof window === "undefined" || typeof window.gtag !== "function") return;
  window.gtag("event", name, params);
}

/** Which contact event a link href stands for, or null for an ordinary link. */
export function contactEventFor(href: string): ClickEvent | null {
  const h = href.trim().toLowerCase();
  if (h.startsWith("tel:")) return "phone_click";
  if (h.startsWith("mailto:")) return "email_click";
  if (h.includes("wa.me/") || h.includes("api.whatsapp.com/") || h.startsWith("whatsapp:")) return "whatsapp_click";
  return null;
}
