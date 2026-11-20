import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowRight, Check, ChevronRight } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/Button";
import { ServiceCard } from "@/components/Services";
import { QuoteSection } from "@/components/QuoteSection";
import { HeroQuoteForm } from "@/components/HeroQuoteForm";
import { StickyContactBar } from "@/components/StickyContactBar";
import { FaqAccordion } from "@/components/FAQ";
import { JsonLd } from "@/components/JsonLd";
import { findService, services } from "@/content/services";
import { publishedAreas } from "@/content/areas";
import { pages, site, trustPoints } from "@/content/site";
import { resolveServicePage } from "@/lib/service-page";
import { breadcrumbJsonLd, faqJsonLd, serviceJsonLd } from "@/lib/seo";

type Params = { slug: string };

export function generateStaticParams(): Params[] {
  return services.map((s) => ({ slug: s.slug }));
}

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { slug } = await params;
  const service = findService(slug);
  if (!service) return {};
  const path = `/services/${service.slug}`;
  const description =
    service.seoDescription?.trim() ||
    `${service.summary} Residential and commercial ${service.title.toLowerCase()} across ${site.region}. Request a free quotation.`;
  return {
    title: service.seoTitle,
    description,
    alternates: { canonical: path },
    openGraph: { title: `${service.seoTitle} | ${site.name}`, url: path, images: [{ url: service.image, alt: service.imageAlt }] },
  };
}

const h2 = "text-2xl font-bold md:text-3xl";

export default async function ServicePage({ params }: { params: Promise<Params> }) {
  const { slug } = await params;
  const service = findService(slug);
  if (!service) notFound();
  const page = resolveServicePage(service);
  const related = services.filter((s) => s.slug !== service.slug).slice(0, 3);
  const title = service.h1?.trim() || `${service.title} in ${site.region}`;
  const sections = (service.sections ?? []).filter((s) => s.heading?.trim() || (s.paragraphs ?? []).some((p) => p.trim()));
  const faqs = (service.faqs ?? []).filter((f) => f.question?.trim() && f.answer?.trim());
  const areas = (service.areaPages ?? []).map((a) => publishedAreas.find((p) => p.slug === a)).filter((a): a is (typeof publishedAreas)[number] => Boolean(a));
  const crumbs = [
    { label: "Our Services", href: "/services" },
    { label: service.title },
  ];

  return (
    <>
      {page.heroForm ? (
        <section className="bg-charcoal text-white">
          <div className="container-site py-12 md:py-16">
            <nav aria-label="Breadcrumb" className="mb-6">
              <ol className="flex flex-wrap items-center gap-1.5 text-sm text-white/65">
                <li>
                  <Link href="/" className="hover:text-white">
                    Home
                  </Link>
                </li>
                {crumbs.map((c) => (
                  <li key={c.label} className="flex items-center gap-1.5">
                    <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
                    {c.href ? (
                      <Link href={c.href} className="hover:text-white">
                        {c.label}
                      </Link>
                    ) : (
                      <span aria-current="page" className="text-white/90">
                        {c.label}
                      </span>
                    )}
                  </li>
                ))}
              </ol>
            </nav>
            <div className="grid gap-10 lg:grid-cols-12 lg:gap-12">
              <div className="lg:col-span-7">
                <p className="eyebrow text-brass">Repair service</p>
                <h1 className="mt-3 text-4xl font-bold leading-[1.1] text-white md:text-5xl">{title}</h1>
                <p className="mt-5 max-w-2xl text-lg leading-relaxed text-white/80">{service.summary}</p>
                <div className="mt-8 flex flex-wrap items-center gap-4">
                  <Button href="#hero-quote-form" variant="light" size="lg">
                    Request a Free Quote
                  </Button>
                  {faqs.length > 0 ? (
                    <Link href="#service-faqs" className="font-heading text-[0.9375rem] font-semibold text-white underline-offset-4 hover:underline">
                      Read the questions and answers
                    </Link>
                  ) : null}
                </div>
                <ul className="mt-8 grid gap-2.5 text-[0.9375rem] text-white/85">
                  {trustPoints.slice(0, 3).map((t) => (
                    <li key={t.slug} className="flex items-start gap-2.5">
                      <Check className="mt-1 h-4 w-4 shrink-0 text-brass" aria-hidden="true" />
                      {t.title}
                    </li>
                  ))}
                </ul>
              </div>
              <div id="hero-quote-form" className="scroll-mt-24 lg:col-span-5">
                <HeroQuoteForm defaultService={service.formLabel} copy={page.heroForm} />
              </div>
            </div>
          </div>
        </section>
      ) : (
        <PageHeader eyebrow="Repair service" title={title} intro={service.summary} crumbs={crumbs}>
          <Button href={`#${site.enquiryFormId}`} variant="light" size="lg">
            Request a Free Quote
          </Button>
        </PageHeader>
      )}

      {/* Content sections written in the CMS, each with its own H2 and optional photo */}
      {(sections.length > 0 || service.faults.length > 0) && (
        <section className="section bg-white">
          <div className="container-site flex flex-col gap-14">
            {sections.map((s, i) => {
              const hasImage = Boolean(s.image);
              const imageLeft = s.imageSide === "left";
              return (
                <div key={`${s.heading}-${i}`} className={hasImage ? "grid gap-8 lg:grid-cols-12 lg:items-center lg:gap-14" : "max-w-3xl"}>
                  {hasImage ? (
                    <div className={`relative aspect-[4/3] overflow-hidden rounded-[4px] border border-line bg-ivory lg:col-span-5 ${imageLeft ? "lg:order-first" : "lg:order-last"}`}>
                      <Image src={s.image as string} alt={s.imageAlt ?? ""} fill priority={i === 0} sizes="(min-width: 1024px) 460px, 100vw" className="object-cover" />
                    </div>
                  ) : null}
                  <div className={hasImage ? "lg:col-span-7" : ""}>
                    {s.heading?.trim() ? <h2 className={h2}>{s.heading}</h2> : null}
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

            {service.faults.length > 0 && (
              <div className="max-w-3xl">
                <h2 className={h2}>Common faults we repair</h2>
                <ul className="mt-5 grid gap-3 sm:grid-cols-2">
                  {service.faults.map((fault) => (
                    <li key={fault} className="flex items-start gap-3 rounded-[4px] border border-line bg-ivory px-4 py-3 text-[0.9375rem] text-ink">
                      <Check className="mt-1 h-4 w-4 shrink-0 text-teal" aria-hidden="true" />
                      {fault}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </section>
      )}

      {page.whyUs && (
        <section className="section bg-ivory" aria-labelledby="service-why-heading">
          <div className="container-site">
            <h2 id="service-why-heading" className={h2}>
              {page.whyUs.heading}
            </h2>
            <ul className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {page.whyUs.items.map((p, i) => (
                <li key={`${p.title}-${i}`} className="rounded-[4px] border border-line bg-white p-6">
                  <h3 className="font-heading text-[1.0625rem] font-semibold text-charcoal">{p.title}</h3>
                  <p className="mt-2 text-[0.9375rem] leading-relaxed text-muted">{p.text}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}

      {page.benefits && (
        <section className="section bg-white" aria-labelledby="service-benefits-heading">
          <div className="container-site">
            <h2 id="service-benefits-heading" className={h2}>
              {page.benefits.heading}
            </h2>
            <ul className="mt-7 grid gap-x-8 gap-y-3.5 sm:grid-cols-2 lg:grid-cols-3">
              {page.benefits.items.map((b, i) => (
                <li key={`${b}-${i}`} className="flex items-start gap-3 text-[0.9375rem] leading-relaxed text-ink">
                  <Check className="mt-1 h-4 w-4 shrink-0 text-teal" aria-hidden="true" />
                  {b}
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}

      {page.process && (
        <section className="section bg-charcoal text-white" aria-labelledby="service-process-heading">
          <div className="container-site">
            <h2 id="service-process-heading" className={h2}>
              {page.process.heading}
            </h2>
            <ol className="mt-8 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
              {page.process.items.map((step, i) => (
                <li key={`${step.title}-${i}`}>
                  <div className="font-heading text-3xl font-extrabold text-brass">{i + 1}</div>
                  <h3 className="mt-2 font-heading text-[1.0625rem] font-semibold">{step.title}</h3>
                  <p className="mt-1.5 text-[0.9375rem] leading-relaxed text-white/75">{step.text}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>
      )}

      {page.cost && (
        <section className="section bg-white" aria-labelledby="service-cost-heading">
          <div className="container-site grid gap-10 lg:grid-cols-12 lg:gap-14">
            <div className="lg:col-span-5">
              <h2 id="service-cost-heading" className={h2}>
                {page.cost.heading}
              </h2>
              {page.cost.intro ? <p className="mt-4 text-[1.0625rem] leading-relaxed text-muted">{page.cost.intro}</p> : null}
            </div>
            <ol className="grid gap-3 lg:col-span-7">
              {page.cost.items.map((f, i) => (
                <li key={`${f.title}-${i}`} className="flex gap-4 rounded-[4px] border border-line bg-white px-5 py-4">
                  <span className="font-heading text-lg font-extrabold text-teal">{String(i + 1).padStart(2, "0")}</span>
                  <div>
                    <h3 className="font-heading text-base font-semibold text-charcoal">{f.title}</h3>
                    <p className="mt-1 text-[0.9375rem] leading-relaxed text-muted">{f.text}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </section>
      )}

      {faqs.length > 0 && (
        <section id="service-faqs" className="section scroll-mt-24 bg-ivory" aria-labelledby="service-faq-heading">
          <div className="container-site grid gap-10 lg:grid-cols-12 lg:gap-16">
            <div className="lg:col-span-4">
              <p className="eyebrow">Questions</p>
              <h2 id="service-faq-heading" className={`mt-3 ${h2}`}>
                {page.faqsHeading}
              </h2>
            </div>
            <div className="lg:col-span-8">
              <FaqAccordion items={faqs.map((f, i) => ({ slug: `faq-${i}`, question: f.question, answer: f.answer }))} />
            </div>
          </div>
        </section>
      )}

      {areas.length > 0 && (
        <section className="section bg-white" aria-labelledby="service-areas-heading">
          <div className="container-site">
            <h2 id="service-areas-heading" className={h2}>
              {page.coverageHeading}
            </h2>
            <p className="mt-4 max-w-3xl text-[1.0625rem] leading-relaxed text-ink">{pages.services.coverageLine}</p>
            <ul className="mt-5 flex flex-wrap items-center gap-2">
              {areas.map((a) => (
                <li key={a.slug}>
                  <Link
                    href={`/areas/${a.slug}`}
                    className="inline-flex items-center rounded-[4px] border border-line px-3 py-1.5 text-sm font-medium text-charcoal transition-colors hover:border-teal hover:text-teal"
                  >
                    {a.name}
                  </Link>
                </li>
              ))}
              <li>
                <Link href="/areas" className="inline-flex items-center gap-1 px-2 py-1.5 text-sm font-semibold text-teal">
                  All areas
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Link>
              </li>
            </ul>
          </div>
        </section>
      )}

      <section className="section bg-ivory" aria-labelledby="related-heading">
        <div className="container-site">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <h2 id="related-heading" className={h2}>
              Related repair services
            </h2>
            <Link href="/services" className="inline-flex items-center gap-1.5 font-heading text-[0.9375rem] font-semibold text-teal">
              View all services
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </div>
          <ul className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {related.map((s) => (
              <li key={s.slug}>
                <ServiceCard service={s} />
              </li>
            ))}
          </ul>
        </div>
      </section>

      <QuoteSection defaultService={service.formLabel} tone="white" />
      {page.stickyBar ? <StickyContactBar callLabel={page.stickyBar.callLabel} whatsappLabel={page.stickyBar.whatsappLabel} /> : null}
      <JsonLd
        data={[
          serviceJsonLd(service),
          ...(faqs.length > 0 ? [faqJsonLd(faqs)] : []),
          breadcrumbJsonLd([
            { name: "Our Services", path: "/services" },
            { name: service.title, path: `/services/${service.slug}` },
          ]),
        ]}
      />
    </>
  );
}
