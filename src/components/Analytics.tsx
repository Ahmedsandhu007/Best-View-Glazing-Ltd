"use client";

import Script from "next/script";
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";
import { contactEventFor, trackEvent } from "@/lib/analytics";

type Props = {
  /** GA4 Measurement ID (G-…), Site settings. */
  measurementId: string;
  /** Google Tag Manager container ID (GTM-…), Site settings. */
  gtmId: string;
  /** Ahrefs Web Analytics key, Site settings. */
  ahrefsKey: string;
};

/**
 * Site-wide tracking, every value set under Site settings in the CMS (empty = not loaded):
 * - Google Tag Manager container and/or GA4 tag, sharing one dataLayer and gtag();
 * - a page_view per route change, and phone / WhatsApp / email click events, pushed through gtag();
 * - Ahrefs Web Analytics.
 * The quote forms send their own generate_lead event on success.
 */
export function Analytics({ measurementId, gtmId, ahrefsKey }: Props) {
  const pathname = usePathname();
  const ga = measurementId.trim();
  const gtm = gtmId.trim();
  const ahrefs = ahrefsKey.trim();
  const google = Boolean(ga || gtm);
  const lastTracked = useRef<string | null>(null);

  // One page_view per route (the GA4 config below has send_page_view off; the ref stops a repeat on the same path).
  useEffect(() => {
    if (!google || lastTracked.current === pathname) return;
    lastTracked.current = pathname;
    trackEvent("page_view", { page_path: pathname, page_location: window.location.href, page_title: document.title });
  }, [google, pathname]);

  // Contact clicks: one listener for every tel:, mailto: and WhatsApp link, wherever it is rendered.
  useEffect(() => {
    if (!google) return;
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
  }, [google]);

  if (!google && !ahrefs) return null;

  const init = [
    "window.dataLayer = window.dataLayer || [];",
    "function gtag(){dataLayer.push(arguments);}",
    "window.gtag = gtag;",
    "gtag('js', new Date());",
    ga ? `gtag('config', ${JSON.stringify(ga)}, { send_page_view: false });` : "",
  ]
    .filter(Boolean)
    .join("\n");

  return (
    <>
      {gtm ? <Script src={`https://www.googletagmanager.com/gtm.js?id=${encodeURIComponent(gtm)}`} strategy="afterInteractive" /> : null}
      {ga ? <Script src={`https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(ga)}`} strategy="afterInteractive" /> : null}
      {google ? (
        <Script id="google-tag-init" strategy="afterInteractive">
          {init}
        </Script>
      ) : null}
      {ahrefs ? <Script src="https://analytics.ahrefs.com/analytics.js" data-key={ahrefs} strategy="afterInteractive" /> : null}
    </>
  );
}
