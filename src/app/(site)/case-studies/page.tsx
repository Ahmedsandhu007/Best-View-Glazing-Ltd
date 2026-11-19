import type { Metadata } from "next";
import { PageHeader } from "@/components/ui/PageHeader";
import { CaseStudiesGrid } from "@/components/CaseStudiesGrid";
import { Testimonials } from "@/components/Testimonials";
import { CtaBand } from "@/components/CtaBand";
import { JsonLd } from "@/components/JsonLd";
import { caseStudies, hasPlaceholderCaseStudies } from "@/content/case-studies";
import { pages, sections, seo, site } from "@/content/site";
import { breadcrumbJsonLd } from "@/lib/seo";

export const metadata: Metadata = {
  title: seo.caseStudies.title,
  description: seo.caseStudies.description,
  alternates: { canonical: "/case-studies" },
  openGraph: { title: `${seo.caseStudies.title} | ${site.name}`, url: "/case-studies" },
};

export default function CaseStudiesPage() {
  const copy = pages.caseStudies;
  return (
    <>
      <PageHeader eyebrow={copy.eyebrow} title={copy.title} intro={copy.description} crumbs={[{ label: "Case Studies" }]} />
      <section className="section bg-white">
        <div className="container-site">
          {hasPlaceholderCaseStudies && (
            <p className="mb-8 inline-block rounded-[4px] border border-brass/60 bg-ivory px-3 py-1.5 text-sm text-ink">{sections.caseStudies.placeholderNotice}</p>
          )}
          {caseStudies.length === 0 ? <p className="text-muted">No case studies yet.</p> : <CaseStudiesGrid studies={caseStudies} />}
        </div>
      </section>
      <Testimonials />
      <CtaBand title={copy.ctaTitle} text={copy.ctaDescription} />
      <JsonLd data={breadcrumbJsonLd([{ name: "Case Studies", path: "/case-studies" }])} />
    </>
  );
}
