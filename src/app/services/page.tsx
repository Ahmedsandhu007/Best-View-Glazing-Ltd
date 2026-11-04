import type { Metadata } from "next";
import { PageHeader } from "@/components/ui/PageHeader";
import { Services } from "@/components/Services";
import { Pricing } from "@/components/Pricing";
import { WorkingProcess } from "@/components/WorkingProcess";
import { CtaBand } from "@/components/CtaBand";
import { JsonLd } from "@/components/JsonLd";
import { breadcrumbJsonLd } from "@/lib/seo";
import { site } from "@/content/site";

export const metadata: Metadata = {
  title: "Window & Door Repair Services London",
  description:
    "uPVC, aluminium, timber, sash and tilt and turn window repairs, double glazing, locks, handles, hinges, seals, frames and door repairs across Greater London.",
  alternates: { canonical: "/services" },
  openGraph: { title: "Window & Door Repair Services London", url: "/services" },
};

export default function ServicesPage() {
  return (
    <>
      <PageHeader
        eyebrow="Our services"
        title="Window & Door Repair Services in London"
        intro="Fourteen core services covering the mechanical, glazing and frame faults that affect windows and doors in London homes and commercial buildings. Choose a service to read what the repair involves, or go straight to the enquiry form."
        crumbs={[{ label: "Our Services" }]}
      />
      <Services compact headingLevel="h2" />
      <WorkingProcess tone="white" />
      <Pricing ctaHref={site.enquiryPath} />
      <CtaBand />
      <JsonLd data={breadcrumbJsonLd([{ name: "Our Services", path: "/services" }])} />
    </>
  );
}
