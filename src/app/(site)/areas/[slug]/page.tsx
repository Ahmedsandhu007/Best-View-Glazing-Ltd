import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/Button";
import { QuoteSection } from "@/components/QuoteSection";
import { JsonLd } from "@/components/JsonLd";
import { FaqAccordion } from "@/components/FAQ";
import { findArea, publishedAreas } from "@/content/areas";
import { services } from "@/content/services";
import { site } from "@/content/site";
import { breadcrumbJsonLd, faqJsonLd } from "@/lib/seo";

type Params = { slug: string };

export function generateStaticParams(): Params[] {
  return publishedAreas.map((a) => ({ slug: a.slug }));
}

const defaultIntro = (name: string, region: string) =>
  `Repairs to uPVC, aluminium, timber and sash windows, double glazing, locks, handles, hinges and door mechanisms for homes and commercial premises in ${name} and the surrounding parts of ${region}.`;

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { slug } = await params;
  const area = findArea(slug);
  if (!area) return {};
  const path = `/areas/${area.slug}`;
  const title = area.seoTitle?.trim() || `Window & Door Repairs ${area.name}`;
  const description =
    area.seoDescription?.trim() ||
    `uPVC, aluminium, timber and sash window repairs, double glazing, locks, hinges and door repairs in ${area.name}, ${area.region}. Residential and commercial. Request a free quote.`;
  return {
    title,
    description,
    alternates: { canonical: path },
    openGraph: { title: `${title} | ${site.name}`, url: path, ...(area.image ? { images: [{ url: area.image, alt: area.imageAlt ?? "" }] } : {}) },
  };
}

export default async function AreaPage({ params }: { params: Promise<Params> }) {
  const { slug } = await params;
  const area = findArea(slug);
  if (!area) notFound();

  const title = area.h1?.trim() || `Window & Door Repairs in ${area.name}`;
  const intro = area.intro?.trim() || defaultIntro(area.name, area.region);
  const sections = (area.sections ?? []).filter((s) => s.heading?.trim() || (s.paragraphs ?? []).some((p) => p.trim()));
  const nearby = (area.nearby ?? []).map((n) => n.trim()).filter(Boolean);
  const faqs = (area.faqs ?? []).filter((f) => f.question?.trim() && f.answer?.trim());
  const neighbours = publishedAreas.filter((a) => a.regionSlug === area.regionSlug && a.slug !== area.slug);
  const linkFor = (name: string) => publishedAreas.find((a) => a.name.toLowerCase() === name.toLowerCase() && a.slug !== area.slug);

  return (
    <>
      <PageHeader eyebrow={area.region} title={title} intro={intro} crumbs={[{ label: "Areas We Cover", href: "/areas" }, { label: area.name }]}>
        <Button href={`#${site.enquiryFormId}`} variant="light" size="lg">
          Request a Free Quote
        </Button>
      </PageHeader>

      <section className="section bg-white">
        <div className="container-site grid gap-12 lg:grid-cols-12 lg:gap-16">
          <div className="lg:col-span-7">
            {area.image ? (
              <div className="relative mb-10 aspect-[16/9] overflow-hidden rounded-[4px] border border-line bg-ivory">
                <Image src={area.image} alt={area.imageAlt ?? ""} fill priority sizes="(min-width: 1024px) 680px, 100vw" className="object-cover" />
              </div>
            ) : null}

            {sections.length > 0 ? (
              <div className="flex flex-col gap-12">
                {sections.map((s, i) => {
                  const hasImage = Boolean(s.image);
                  const imageLeft = s.imageSide === "left";
                  return (
                    <div key={`${s.heading}-${i}`} className={hasImage ? "grid gap-6 md:grid-cols-12 md:items-start" : ""}>
                      {hasImage ? (
                        <div className={`relative aspect-[4/3] overflow-hidden rounded-[4px] border border-line bg-ivory md:col-span-5 ${imageLeft ? "md:order-first" : "md:order-last"}`}>
                          <Image src={s.image as string} alt={s.imageAlt ?? ""} fill sizes="(min-width: 768px) 320px, 100vw" className="object-cover" />
                        </div>
                      ) : null}
                      <div className={hasImage ? "md:col-span-7" : ""}>
                        {s.heading?.trim() ? <h2 className="text-2xl font-bold md:text-3xl">{s.heading}</h2> : null}
                        <div className="prose-site mt-5 text-[1.0625rem] leading-relaxed text-ink">
                          {(s.paragraphs ?? [])
                            .filter((p) => p.trim())
                            .map((p, j) => (
                              <p key={j}>{p}</p>
                            ))}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <>
                <h2 className="text-2xl font-bold md:text-3xl">Window and door repairs for {area.name} properties</h2>
                <div className="prose-site mt-5 text-[1.0625rem] leading-relaxed text-ink">
                  <p>
                    {area.name} sits within our {area.region} coverage. {area.regionIntro}
                  </p>
                  <p>
                    Whatever the age or style of the property, the faults tend to be familiar: windows that have dropped on worn hinges, handles and locks
                    that no longer engage, sealed units that have misted, sashes that stick or rattle, and doors that need lifting to lock. We diagnose
                    the cause, propose a practical repair and quote for it clearly before any work is agreed.
                  </p>
                  <p>
                    We work for homeowners, tenants and landlords in {area.name} as well as for letting agents, property managers and commercial
                    occupiers. Enquiries are made through the website form, which lets you attach photographs of the problem and tell us when you would
                    prefer to be contacted.
                  </p>
                </div>
              </>
            )}

            <h2 className="mt-12 text-2xl font-bold md:text-3xl">Services available in {area.name}</h2>
            <ul className="mt-5 grid gap-x-8 gap-y-2.5 sm:grid-cols-2">
              {services.map((s) => (
                <li key={s.slug}>
                  <Link
                    href={`/services/${s.slug}`}
                    className="inline-flex items-center gap-2 text-[0.9375rem] font-medium text-charcoal underline decoration-line underline-offset-4 hover:text-teal hover:decoration-teal"
                  >
                    {s.title}
                  </Link>
                </li>
              ))}
            </ul>

            {nearby.length > 0 && (
              <>
                <h2 className="mt-12 text-2xl font-bold md:text-3xl">Nearby places we also cover</h2>
                <ul className="mt-5 flex flex-wrap gap-2">
                  {nearby.map((n) => {
                    const target = linkFor(n);
                    const cls = "inline-flex items-center rounded-[4px] border border-line px-3 py-1.5 text-sm font-medium text-charcoal";
                    return (
                      <li key={n}>
                        {target ? (
                          <Link href={`/areas/${target.slug}`} className={`${cls} transition-colors hover:border-teal hover:text-teal`}>
                            {n}
                          </Link>
                        ) : (
                          <span className={cls}>{n}</span>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </>
            )}

            {faqs.length > 0 && (
              <>
                <h2 className="mt-12 text-2xl font-bold md:text-3xl">Questions about repairs in {area.name}</h2>
                <div className="mt-5">
                  <FaqAccordion items={faqs.map((f, i) => ({ slug: `faq-${i}`, question: f.question, answer: f.answer }))} />
                </div>
              </>
            )}
          </div>

          <aside className="lg:col-span-5">
            <div className="rounded-[4px] border border-line bg-ivory p-6">
              <h2 className="font-heading text-lg font-semibold text-charcoal">Other areas in {area.region}</h2>
              {neighbours.length > 0 && (
                <ul className="mt-4 space-y-2">
                  {neighbours.map((n) => (
                    <li key={n.slug}>
                      <Link href={`/areas/${n.slug}`} className="text-[0.9375rem] text-ink underline decoration-line underline-offset-4 hover:text-teal hover:decoration-teal">
                        Window &amp; door repairs in {n.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
              <Link href="/areas" className="mt-5 inline-flex items-center gap-1.5 font-heading text-[0.9375rem] font-semibold text-teal">
                All areas we cover
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
            <div className="mt-6 rounded-[4px] border border-line bg-white p-6">
              <h2 className="font-heading text-lg font-semibold text-charcoal">No local branch, no middleman</h2>
              <p className="mt-2 text-[0.9375rem] leading-relaxed text-muted">
                We do not have an office in {area.name}; every enquiry is handled by our central team and the repair is carried out at your property.
              </p>
            </div>
          </aside>
        </div>
      </section>

      <QuoteSection />
      <JsonLd
        data={[
          breadcrumbJsonLd([
            { name: "Areas We Cover", path: "/areas" },
            { name: area.name, path: `/areas/${area.slug}` },
          ]),
          ...(faqs.length > 0 ? [faqJsonLd(faqs)] : []),
        ]}
      />
    </>
  );
}
