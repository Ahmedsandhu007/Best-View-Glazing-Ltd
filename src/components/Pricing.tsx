import { Button } from "@/components/ui/Button";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { quoteFactors, sections, site } from "@/content/site";

export function Pricing({ ctaHref = `#${site.enquiryFormId}` }: { ctaHref?: string }) {
  const copy = sections.pricing;
  return (
    <section id="quotations" className="section bg-charcoal text-white">
      <div className="container-site grid gap-12 lg:grid-cols-12 lg:gap-16">
        <div className="lg:col-span-5">
          <SectionHeading tone="dark" eyebrow={copy.eyebrow} title={copy.title} intro={copy.description} />
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Button href={ctaHref} variant="light" size="lg">
              {copy.primaryLabel}
            </Button>
            <Button href="/faqs" variant="outlineLight" size="lg">
              {copy.secondaryLabel}
            </Button>
          </div>
        </div>
        <div className="lg:col-span-7">
          <h3 className="font-heading text-sm font-semibold uppercase tracking-[0.12em] text-brass">{copy.factorsHeading}</h3>
          <ol className="mt-5 divide-y divide-line-dark border-y border-line-dark">
            {quoteFactors.map((factor, i) => (
              <li key={factor.slug} className="grid gap-1 py-5 sm:grid-cols-[3rem_1fr] sm:gap-4">
                <span className="font-heading text-lg font-bold tabular-nums text-brass" aria-hidden="true">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <div>
                  <p className="font-heading text-[1.0625rem] font-semibold text-white">{factor.title}</p>
                  <p className="mt-1 text-[0.9375rem] leading-relaxed text-white/70">{factor.text}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
