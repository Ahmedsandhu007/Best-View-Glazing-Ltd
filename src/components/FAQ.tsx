"use client";

import { useId, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { SectionHeading } from "@/components/ui/SectionHeading";
import type { Faq } from "@/content/faqs";
import { sections, site } from "@/content/site";

export function FaqAccordion({ items }: { items: Faq[] }) {
  const prefix = useId();
  const [openItems, setOpenItems] = useState<Set<number>>(() => new Set());
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);

  const toggle = (i: number) =>
    setOpenItems((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });

  // Arrow / Home / End move focus between question buttons (WAI-ARIA accordion pattern).
  const onKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>, i: number) => {
    const count = items.length;
    let target: number | null = null;
    if (e.key === "ArrowDown") target = (i + 1) % count;
    else if (e.key === "ArrowUp") target = (i - 1 + count) % count;
    else if (e.key === "Home") target = 0;
    else if (e.key === "End") target = count - 1;
    if (target !== null) {
      e.preventDefault();
      buttons.current[target]?.focus();
    }
  };

  return (
    <div className="divide-y divide-line border-y border-line">
      {items.map((faq, i) => {
        const expanded = openItems.has(i);
        const qid = `${prefix}-q-${i}`;
        const aid = `${prefix}-a-${i}`;
        return (
          <div key={faq.slug ?? faq.question}>
            <h3 className="m-0">
              <button
                ref={(el) => {
                  buttons.current[i] = el;
                }}
                id={qid}
                type="button"
                aria-expanded={expanded}
                aria-controls={aid}
                onClick={() => toggle(i)}
                onKeyDown={(e) => onKeyDown(e, i)}
                className="flex w-full items-center justify-between gap-6 py-5 text-left font-heading text-[1.0625rem] font-semibold text-charcoal transition-colors hover:text-teal"
              >
                <span>{faq.question}</span>
                <ChevronDown
                  className={`h-5 w-5 shrink-0 text-muted transition-transform duration-200 ${expanded ? "rotate-180" : ""}`}
                  aria-hidden="true"
                />
              </button>
            </h3>
            <div
              id={aid}
              role="region"
              aria-labelledby={qid}
              inert={!expanded}
              className={`grid transition-[grid-template-rows] duration-200 ease-out ${expanded ? "grid-rows-[1fr]" : "grid-rows-[0fr]"}`}
            >
              <div className="overflow-hidden">
                <p className="pb-6 pr-2 text-[0.9375rem] leading-relaxed text-muted sm:pr-12">{faq.answer}</p>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

type Props = { items: Faq[]; ctaHref?: string; showHeading?: boolean };

export function FAQ({ items, ctaHref = `#${site.enquiryFormId}`, showHeading = true }: Props) {
  const copy = sections.faq;
  return (
    <section id="faqs" className="section bg-white">
      <div className="container-site grid gap-12 lg:grid-cols-12 lg:gap-16">
        {showHeading && (
          <div className="lg:col-span-4">
            <div className="lg:sticky lg:top-28">
              <SectionHeading eyebrow={copy.eyebrow} title={copy.title} intro={copy.description} />
              <div className="mt-8">
                <Button href={ctaHref} variant="secondary">
                  {copy.buttonLabel}
                </Button>
              </div>
            </div>
          </div>
        )}
        <div className={showHeading ? "lg:col-span-8" : "lg:col-span-12"}>
          <FaqAccordion items={items} />
        </div>
      </div>
    </section>
  );
}
