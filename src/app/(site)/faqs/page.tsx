import type { Metadata } from "next";
import { PageHeader } from "@/components/ui/PageHeader";
import { FAQ } from "@/components/FAQ";
import { CtaBand } from "@/components/CtaBand";
import { JsonLd } from "@/components/JsonLd";
import { faqs } from "@/content/faqs";
import { pages, seo, site } from "@/content/site";
import { breadcrumbJsonLd, faqJsonLd } from "@/lib/seo";

export const metadata: Metadata = {
  title: seo.faqs.title,
  description: seo.faqs.description,
  alternates: { canonical: "/faqs" },
  openGraph: { title: `${seo.faqs.title} | ${site.name}`, url: "/faqs" },
};

export default function FaqsPage() {
  const copy = pages.faqs;
  return (
    <>
      <PageHeader eyebrow={copy.eyebrow} title={copy.title} intro={copy.description} crumbs={[{ label: "FAQs" }]} />
      <FAQ items={faqs} showHeading={false} ctaHref={site.enquiryPath} />
      <CtaBand title={copy.ctaTitle} text={copy.ctaDescription} />
      <JsonLd data={[faqJsonLd(faqs), breadcrumbJsonLd([{ name: "FAQs", path: "/faqs" }])]} />
    </>
  );
}
