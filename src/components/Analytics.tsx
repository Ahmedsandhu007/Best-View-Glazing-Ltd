"use client";

import Script from "next/script";
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";
import { contactEventFor, trackEvent } from "@/lib/analytics";

/**
 * Loads GA4 when a Measurement ID is set in Site settings, sends a page_view on every
 * route change, and records phone, WhatsApp and email clicks anywhere on the site.
 * The quote form sends its own generate_lead event on success.
 */
export function Analytics({ measurementId }: { measurementId: string }) {
  const pathname = usePathname();
  const id = measurementId.trim();
  const lastTracked = useRef<string | null>(null);

  // One page_view per route (the config call below has send_page_view off; the ref stops a repeat on the same path).
  useEffect(() => {
    if (!id || lastTracked.current === pathname) return;
    lastTracked.current = pathname;
    trackEvent("page_view", { page_path: pathname, page_location: window.location.href, page_title: document.title });
  }, [id, pathname]);

  // Contact clicks: one listener for every tel:, mailto: and WhatsApp link, wherever it is rendered.
  useEffect(() => {
    if (!id) return;
    const onClick = (e: MouseEvent) => {
      const link = (e.target as Element | null)?.closest?.("a[href]");
      if (!link) return;
      const href = link.getAttribute("href") ?? "";
      const name = contactEventFor(href);
      if (!name) return;
      trackEvent(name, { link_url: href, link_text: (link.textContent ?? "").trim().slice(0, 80), page_path: window.location.pathname });
    };
    document.addEventListener("click", onClick, true);
    return () => document.removeEventListener("click", onClick, true);
  }, [id]);

  if (!id) return null;
  return (
    <>
      <Script src={`https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(id)}`} strategy="afterInteractive" />
      <Script id="ga4-init" strategy="afterInteractive">
        {`window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
window.gtag = gtag;
gtag('js', new Date());
gtag('config', ${JSON.stringify(id)}, { send_page_view: false });`}
      </Script>
    </>
  );
}
