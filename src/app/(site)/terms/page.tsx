import type { Metadata } from "next";
import { PageHeader } from "@/components/ui/PageHeader";
import { LegalDocument } from "@/components/LegalDocument";
import { legal, pages, seo } from "@/content/site";

export const metadata: Metadata = {
  title: seo.terms.title,
  description: seo.terms.description,
  alternates: { canonical: "/terms" },
};

export default function TermsPage() {
  const copy = pages.terms;
  return (
    <>
      <PageHeader eyebrow={copy.eyebrow} title={copy.title} intro={copy.description} crumbs={[{ label: "Terms & Conditions" }]} />
      <LegalDocument doc={legal.terms} footer={{ text: "See also our", linkLabel: "Privacy Policy", href: "/privacy-policy" }} />
    </>
  );
}
