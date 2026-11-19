import type { Metadata } from "next";
import { PageHeader } from "@/components/ui/PageHeader";
import { ContactDetails } from "@/components/ContactDetails";
import { QuoteSection } from "@/components/QuoteSection";
import { JsonLd } from "@/components/JsonLd";
import { pages, seo, site } from "@/content/site";
import { breadcrumbJsonLd } from "@/lib/seo";

export const metadata: Metadata = {
  title: seo.contact.title,
  description: seo.contact.description,
  alternates: { canonical: "/contact" },
  openGraph: { title: `${seo.contact.title} | ${site.name}`, url: "/contact" },
};

export default function ContactPage() {
  const copy = pages.contact;
  return (
    <>
      <PageHeader eyebrow={copy.eyebrow} title={copy.title} intro={copy.description} crumbs={[{ label: "Contact" }]} />
      <ContactDetails />
      <QuoteSection tone="white" />
      <JsonLd data={breadcrumbJsonLd([{ name: "Contact", path: "/contact" }])} />
    </>
  );
}
