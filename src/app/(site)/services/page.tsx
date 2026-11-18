import type { Metadata } from "next";
import { PageHeader } from "@/components/ui/PageHeader";
import { Services } from "@/components/Services";
import { Pricing } from "@/components/Pricing";
import { WorkingProcess } from "@/components/WorkingProcess";
import { CtaBand } from "@/components/CtaBand";
import { JsonLd } from "@/components/JsonLd";
import { breadcrumbJsonLd } from "@/lib/seo";
import { pages, seo, site } from "@/content/site";

export const metadata: Metadata = {
  title: seo.services.title,
  description: seo.services.description,
  alternates: { canonical: "/services" },
  openGraph: { title: seo.services.title, url: "/services" },
};

export default function ServicesPage() {
  const banner = pages.services;
  return (
    <>
      <PageHeader eyebrow={banner.eyebrow} title={banner.title} intro={banner.description} crumbs={[{ label: "Our Services" }]} />
      <Services compact headingLevel="h2" />
      <WorkingProcess tone="white" />
      <Pricing ctaHref={site.enquiryPath} />
      <CtaBand />
      <JsonLd data={breadcrumbJsonLd([{ name: "Our Services", path: "/services" }])} />
    </>
  );
}
