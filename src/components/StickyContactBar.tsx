import { Phone } from "lucide-react";
import { contact } from "@/content/site";
import { WhatsAppIcon, whatsappHref } from "@/components/WhatsAppButton";

/**
 * Call / WhatsApp bar fixed to the bottom of phone screens (hidden from lg up).
 * Shown on service pages when switched on; hidden when neither number is set.
 * The floating corner buttons move up above it (see globals.css).
 */
export function StickyContactBar({ callLabel, whatsappLabel }: { callLabel: string; whatsappLabel: string }) {
  const tel = contact.phone ? `tel:${contact.phone.replace(/[^\d+]/g, "")}` : null;
  const wa = whatsappHref();
  if (!tel && !wa) return null;
  const cell = "flex h-[60px] items-center justify-center gap-2 font-heading text-[0.9375rem] font-semibold";
  return (
    <>
      <div aria-hidden="true" className="h-[60px] lg:hidden" />
      <nav aria-label="Call or message us" className="sticky-contact-bar fixed inset-x-0 bottom-0 z-40 grid border-t border-line bg-white shadow-raised lg:hidden" style={{ gridTemplateColumns: tel && wa ? "1fr 1fr" : "1fr" }}>
        {tel ? (
          <a href={tel} className={`${cell} text-charcoal ${wa ? "border-r border-line" : ""}`}>
            <Phone className="h-[18px] w-[18px]" aria-hidden="true" />
            {callLabel}
          </a>
        ) : null}
        {wa ? (
          <a href={wa} target="_blank" rel="noopener noreferrer" className={`${cell} bg-teal text-white`}>
            <WhatsAppIcon className="h-[18px] w-[18px]" />
            {whatsappLabel}
            <span className="sr-only"> (opens in a new tab)</span>
          </a>
        ) : null}
      </nav>
    </>
  );
}
