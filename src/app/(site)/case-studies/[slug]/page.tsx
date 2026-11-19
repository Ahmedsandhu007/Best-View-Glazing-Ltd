import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, MapPin } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/Button";
import { ArticleBody } from "@/components/RichText";
import { CaseStudyCard } from "@/components/CaseStudyCard";
import { CtaBand } from "@/components/CtaBand";
import { JsonLd } from "@/components/JsonLd";
import { caseStudies, findCaseStudy } from "@/content/case-studies";
import { sections, site } from "@/content/site";
import { breadcrumbJsonLd } from "@/lib/seo";

type Params = { slug: string };

export function generateStaticParams(): Params[] {
  return caseStudies.map((c) => ({ slug: c.slug }));
}

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { slug } = await params;
  const study = findCaseStudy(slug);
  if (!study) return {};
  return {
    title: `${study.title} – Case Study`,
    description: study.excerpt,
    alternates: { canonical: `/case-studies/${study.slug}` },
    openGraph: { title: `${study.title} | ${site.name}`, description: study.excerpt, url: `/case-studies/${study.slug}`, images: [{ url: study.image, alt: study.imageAlt }] },
  };
}

export default async function CaseStudyPage({ params }: { params: Promise<Params> }) {
  const { slug } = await params;
  const study = findCaseStudy(slug);
  if (!study) notFound();
  const related = caseStudies.filter((c) => c.slug !== slug).slice(0, 3);

  return (
    <>
      <PageHeader eyebrow={study.category} title={study.title} intro={study.excerpt} crumbs={[{ label: "Case Studies", href: "/case-studies" }, { label: study.title }]} />

      <article className="section bg-white">
        <div className="container-site grid gap-12 lg:grid-cols-12 lg:gap-16">
          <div className="lg:col-span-7">
            {study.placeholder && (
              <p className="mb-6 inline-block rounded-[4px] border border-brass/60 bg-ivory px-3 py-1.5 text-sm text-ink">{sections.caseStudies.placeholderNotice}</p>
            )}
            <p className="inline-flex items-center gap-1.5 text-sm text-muted">
              <MapPin className="h-4 w-4" aria-hidden="true" /> {study.location}
            </p>
            <p className="mt-4 text-[1.0625rem] leading-relaxed text-ink">{study.description}</p>
            {study.body && study.body.length > 0 && (
              <div className="prose-site">
                <ArticleBody blocks={study.body} />
              </div>
            )}
            {study.tags.length > 0 && (
              <ul className="mt-8 flex flex-wrap gap-2" aria-label="Work carried out">
                {study.tags.map((t) => (
                  <li key={t} className="rounded-[4px] border border-line px-3 py-1 text-sm text-charcoal">
                    {t}
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-10 flex flex-col gap-3 border-t border-line pt-8 sm:flex-row sm:items-center sm:justify-between">
              <Link href="/case-studies" className="inline-flex items-center gap-1.5 font-heading text-[0.9375rem] font-semibold text-charcoal hover:text-teal">
                <ArrowLeft className="h-4 w-4" aria-hidden="true" /> All case studies
              </Link>
              <Button href={site.enquiryPath}>Request a Free Quote</Button>
            </div>
          </div>
          <aside className="lg:col-span-5">
            <div className="lg:sticky lg:top-28">
              <div className="relative aspect-[4/3] overflow-hidden rounded-[4px] border border-line bg-ivory">
                <Image src={study.image} alt={study.imageAlt} fill priority sizes="(min-width: 1024px) 460px, 100vw" className="object-cover" />
              </div>
              {study.results.length > 0 && (
                <dl className="mt-6 grid grid-cols-3 gap-3">
                  {study.results.map((r) => (
                    <div key={r.label} className="rounded-[4px] border border-line bg-ivory p-4">
                      <dd className="font-heading text-2xl font-bold text-charcoal">{r.value}</dd>
                      <dt className="mt-1 text-xs uppercase tracking-[0.08em] text-muted">{r.label}</dt>
                    </div>
                  ))}
                </dl>
              )}
            </div>
          </aside>
        </div>
      </article>

      {related.length > 0 && (
        <section className="section bg-ivory" aria-labelledby="related-studies">
          <div className="container-site">
            <h2 id="related-studies" className="text-2xl font-bold md:text-3xl">
              More case studies
            </h2>
            <ul className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {related.map((c) => (
                <li key={c.slug}>
                  <CaseStudyCard study={c} />
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}

      <CtaBand />
      <JsonLd
        data={breadcrumbJsonLd([
          { name: "Case Studies", path: "/case-studies" },
          { name: study.title, path: `/case-studies/${study.slug}` },
        ])}
      />
    </>
  );
}
