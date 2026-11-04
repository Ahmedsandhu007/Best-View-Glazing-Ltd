import type { Metadata } from "next";
import { PageHeader } from "@/components/ui/PageHeader";
import { FAQ } from "@/components/FAQ";
import { CtaBand } from "@/components/CtaBand";
import { JsonLd } from "@/components/JsonLd";
import { faqs } from "@/content/faqs";
import { site } from "@/content/site";
import { breadcrumbJsonLd, faqJsonLd } from "@/lib/seo";

export const metadata: Metadata = {
  title: "Frequently Asked Questions – Window & Door Repairs London",
  description:
    "Answers about uPVC, aluminium and sash window repairs, misted double glazing, locks and handles, commercial work, London coverage, quotations and photographs.",
  alternates: { canonical: "/faqs" },
  openGraph: { title: `FAQs | ${site.name}`, url: "/faqs" },
};

export default function FaqsPage() {
  return (
    <>
      <PageHeader
        eyebrow="FAQs"
        title="Frequently Asked Questions"
        intro="Straight answers to the questions customers ask most about window and door repairs in London. If yours is not here, include it in your enquiry and we will answer it with your quotation."
        crumbs={[{ label: "FAQs" }]}
      />
      <FAQ items={faqs} showHeading={false} ctaHref={site.enquiryPath} />
      <CtaBand title="Still have a question?" text="Send it with your enquiry and we will answer it alongside the repair information and quotation." />
      <JsonLd data={[faqJsonLd(faqs), breadcrumbJsonLd([{ name: "FAQs", path: "/faqs" }])]} />
    </>
  );
}
