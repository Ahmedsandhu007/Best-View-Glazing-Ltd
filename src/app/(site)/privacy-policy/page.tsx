import type { Metadata } from "next";
import { PageHeader } from "@/components/ui/PageHeader";
import { LegalDocument } from "@/components/LegalDocument";
import { legal, pages, seo, site } from "@/content/site";

export const metadata: Metadata = {
  title: seo.privacy.title,
  description: seo.privacy.description,
  alternates: { canonical: "/privacy-policy" },
};

export default function PrivacyPolicyPage() {
  const copy = pages.privacy;
  return (
    <>
      <PageHeader eyebrow={copy.eyebrow} title={copy.title} intro={copy.description} crumbs={[{ label: "Privacy Policy" }]} />
      <LegalDocument doc={legal.privacy} footer={{ text: "Questions about this policy can be sent through the", linkLabel: "enquiry form", href: site.enquiryPath }} />
    </>
  );
}
