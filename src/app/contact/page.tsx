import type { Metadata } from "next";
import { PageHeader } from "@/components/ui/PageHeader";
import { QuoteSection } from "@/components/QuoteSection";
import { JsonLd } from "@/components/JsonLd";
import { site } from "@/content/site";
import { breadcrumbJsonLd } from "@/lib/seo";

export const metadata: Metadata = {
  title: "Request a Free Quote – Window & Door Repairs London",
  description:
    "Request a free window or door repair quotation anywhere in Greater London. Tell us about the fault, attach photographs and our team will review your enquiry.",
  alternates: { canonical: "/contact" },
  openGraph: { title: `Request a Free Quote | ${site.name}`, url: "/contact" },
};

export default function ContactPage() {
  return (
    <>
      <PageHeader
        eyebrow="Contact us"
        title="Request a Free Quote"
        intro="The enquiry form below is the way to reach us. It takes a couple of minutes, lets you attach photographs of the problem, and makes sure your request goes straight to the people who will assess it."
        crumbs={[{ label: "Contact" }]}
      />
      <QuoteSection tone="white" />
      <JsonLd data={breadcrumbJsonLd([{ name: "Contact", path: "/contact" }])} />
    </>
  );
}
