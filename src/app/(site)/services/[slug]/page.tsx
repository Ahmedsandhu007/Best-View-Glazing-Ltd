import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowRight, Check } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/Button";
import { ServiceCard } from "@/components/Services";
import { QuoteSection } from "@/components/QuoteSection";
import { JsonLd } from "@/components/JsonLd";
import { findService, services } from "@/content/services";
import { areaGroups } from "@/content/areas";
import { site } from "@/content/site";
import { breadcrumbJsonLd, serviceJsonLd } from "@/lib/seo";

type Params = { slug: string };

export function generateStaticParams(): Params[] {
  return services.map((s) => ({ slug: s.slug }));
}

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { slug } = await params;
  const service = findService(slug);
  if (!service) return {};
  const path = `/services/${service.slug}`;
  return {
    title: service.seoTitle,
    description: `${service.summary} Residential and commercial ${service.title.toLowerCase()} across Greater London. Request a free quotation.`,
    alternates: { canonical: path },
    openGraph: { title: `${service.seoTitle} | ${site.name}`, url: path, images: [{ url: service.image, alt: service.imageAlt }] },
  };
}

export default async function ServicePage({ params }: { params: Promise<Params> }) {
  const { slug } = await params;
  const service = findService(slug);
  if (!service) notFound();
  const related = services.filter((s) => s.slug !== service.slug).slice(0, 3);

  return (
    <>
      <PageHeader
        eyebrow="Repair service"
        title={`${service.title} in London`}
        intro={service.summary}
        crumbs={[{ label: "Our Services", href: "/services" }, { label: service.title }]}
      >
        <Button href={`#${site.enquiryFormId}`} variant="light" size="lg">
          Request a Free Quote
        </Button>
      </PageHeader>

      <section className="section bg-white">
        <div className="container-site grid gap-12 lg:grid-cols-12 lg:gap-16">
          <div className="lg:col-span-7">
            <h2 className="text-2xl font-bold md:text-3xl">About our {service.title.toLowerCase()}</h2>
            <div className="prose-site mt-5 text-[1.0625rem] leading-relaxed text-ink">
              {service.body.map((p) => (
                <p key={p.slice(0, 40)}>{p}</p>
              ))}
            </div>

            {service.faults.length > 0 && (
              <>
                <h2 className="mt-12 text-2xl font-bold md:text-3xl">Common faults we repair</h2>
                <ul className="mt-5 grid gap-3 sm:grid-cols-2">
                  {service.faults.map((fault) => (
                    <li key={fault} className="flex items-start gap-3 rounded-[4px] border border-line bg-ivory px-4 py-3 text-[0.9375rem] text-ink">
                      <Check className="mt-1 h-4 w-4 shrink-0 text-teal" aria-hidden="true" />
                      {fault}
                    </li>
                  ))}
                </ul>
              </>
            )}

            <h2 className="mt-12 text-2xl font-bold md:text-3xl">Where we carry out this work</h2>
            <p className="mt-4 text-[1.0625rem] leading-relaxed text-ink">
              {service.title} are available to residential and commercial customers throughout Greater London, including:
            </p>
            <ul className="mt-5 flex flex-wrap gap-2">
              {areaGroups.map((g) => (
                <li key={g.slug}>
                  <Link
                    href={`/areas#${g.slug}`}
                    className="inline-flex items-center rounded-[4px] border border-line px-3 py-1.5 text-sm font-medium text-charcoal transition-colors hover:border-teal hover:text-teal"
                  >
                    {g.region}
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

          <aside className="lg:col-span-5">
            <div className="lg:sticky lg:top-28">
              <div className="relative aspect-[4/3] overflow-hidden rounded-[4px] border border-line bg-ivory">
                <Image src={service.image} alt={service.imageAlt} fill priority sizes="(min-width: 1024px) 460px, 100vw" className="object-cover" />
              </div>
              <div className="mt-6 rounded-[4px] border border-line bg-ivory p-6">
                <h2 className="font-heading text-lg font-semibold text-charcoal">Request a quotation</h2>
                <p className="mt-2 text-[0.9375rem] leading-relaxed text-muted">
                  Describe the fault, add a photograph if you can, and we will respond with the repair information and a clear
                  quotation.
                </p>
                <Button href={`#${site.enquiryFormId}`} className="mt-5 w-full">
                  Go to the enquiry form
                </Button>
              </div>
            </div>
          </aside>
        </div>
      </section>

      <section className="section bg-ivory" aria-labelledby="related-heading">
        <div className="container-site">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
            <h2 id="related-heading" className="text-2xl font-bold md:text-3xl">
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
      <JsonLd
        data={[
          serviceJsonLd(service),
          breadcrumbJsonLd([
            { name: "Our Services", path: "/services" },
            { name: service.title, path: `/services/${service.slug}` },
          ]),
        ]}
      />
    </>
  );
}
