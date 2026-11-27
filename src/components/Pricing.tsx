import { Button } from "@/components/ui/Button";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { RichInline } from "@/components/RichText";
import { home, sections, site } from "@/content/site";

/** Home page: the cost guide, with the price table and the paragraphs under it edited under Home page > Cost block. */
export function Pricing({ ctaHref = `#${site.enquiryFormId}` }: { ctaHref?: string }) {
  const copy = sections.pricing;
  const cost = home.cost;
  const paragraphs = cost.paragraphs.filter((p) => p.trim());
  return (
    <section id="quotations" className="section bg-charcoal text-white">
      <div className="container-site grid gap-12 lg:grid-cols-12 lg:gap-16">
        <div className="lg:col-span-5">
          <SectionHeading tone="dark" eyebrow={copy.eyebrow} title={copy.title} intro={<RichInline text={copy.description} />} />
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
          {cost.rows.length > 0 ? (
            <table className="w-full border-collapse text-left">
              <caption className="pb-4 text-left font-heading text-sm font-semibold uppercase tracking-[0.12em] text-brass">{copy.tableHeading}</caption>
              <thead>
                <tr className="border-y border-line-dark text-sm text-white/60">
                  <th scope="col" className="py-3 pr-4 font-medium">
                    Repair
                  </th>
                  <th scope="col" className="py-3 font-medium">
                    UK guide price
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line-dark border-b border-line-dark">
                {cost.rows.map((row) => (
                  <tr key={row.repair}>
                    <th scope="row" className="py-4 pr-4 font-heading text-[1.0625rem] font-semibold text-white">
                      {row.repair}
                    </th>
                    <td className="py-4 text-[0.9375rem] text-white/80">{row.price}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
          {paragraphs.length > 0 ? (
            <div className="mt-6 space-y-4 text-[0.9375rem] leading-relaxed text-white/75 [&_a]:text-white">
              {paragraphs.map((p) => (
                <p key={p.slice(0, 40)}>
                  <RichInline text={p} />
                </p>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}
