import { contact } from "@/content/site";

/** WhatsApp glyph (drawn inline; Lucide carries no brand icons). */
export function WhatsAppIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="currentColor" aria-hidden="true" focusable="false">
      <path d="M12.04 2C6.58 2 2.13 6.45 2.13 11.91c0 1.75.46 3.45 1.32 4.95L2 22l5.25-1.38a9.9 9.9 0 0 0 4.79 1.22c5.46 0 9.91-4.45 9.91-9.91S17.5 2 12.04 2m0 18.15c-1.48 0-2.93-.4-4.2-1.15l-.3-.18-3.12.82.83-3.04-.2-.31a8.2 8.2 0 0 1-1.26-4.38c0-4.54 3.7-8.24 8.25-8.24 4.54 0 8.24 3.7 8.24 8.24s-3.7 8.24-8.24 8.24m4.52-6.16c-.25-.12-1.47-.72-1.69-.81-.23-.08-.39-.12-.56.12-.16.25-.64.81-.78.97-.15.17-.29.19-.54.06-.25-.12-1.05-.39-1.99-1.23-.74-.66-1.23-1.47-1.38-1.72-.14-.25-.02-.38.11-.51.11-.11.25-.29.37-.43.12-.14.16-.25.25-.41.08-.17.04-.31-.02-.43-.06-.12-.56-1.34-.76-1.84-.2-.48-.41-.42-.56-.43h-.48c-.17 0-.43.06-.66.31-.22.25-.86.85-.86 2.07s.89 2.4 1.01 2.56c.12.17 1.75 2.67 4.23 3.74.59.26 1.05.41 1.41.52.59.19 1.13.16 1.56.1.48-.07 1.47-.6 1.67-1.18.21-.58.21-1.07.15-1.18-.07-.1-.23-.16-.48-.27" />
    </svg>
  );
}

/** The wa.me link for the configured number, or null when no number is set. */
export function whatsappHref() {
  const digits = (contact.whatsappNumber || "").replace(/\D/g, "");
  if (!digits) return null;
  const text = contact.whatsappMessage ? `?text=${encodeURIComponent(contact.whatsappMessage)}` : "";
  return `https://wa.me/${digits}${text}`;
}

export function WhatsAppButton({ className = "" }: { className?: string }) {
  const href = whatsappHref();
  if (!href) return null;
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={`inline-flex h-12 items-center justify-center gap-2.5 rounded-[4px] bg-teal px-6 font-heading text-base font-semibold text-white transition-colors hover:bg-teal-dark ${className}`}
    >
      <WhatsAppIcon />
      {contact.whatsappLabel || "Message us on WhatsApp"}
      <span className="sr-only"> (opens in a new tab)</span>
    </a>
  );
}

/** Fixed button in the corner of every page, switched on under Contact details in the CMS. */
export function FloatingWhatsApp() {
  const href = whatsappHref();
  if (!href || !contact.showFloatingButton) return null;
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="floating-corner fixed bottom-5 left-5 z-40 inline-flex h-12 items-center gap-2 rounded-[4px] bg-teal pl-3.5 pr-4 font-heading text-sm font-semibold text-white shadow-raised transition-colors hover:bg-teal-dark"
    >
      <WhatsAppIcon className="h-6 w-6" />
      <span>{contact.floatingLabel || "WhatsApp us"}</span>
      <span className="sr-only"> (opens in a new tab)</span>
    </a>
  );
}
