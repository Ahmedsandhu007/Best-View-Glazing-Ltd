import servicesData from "./services.json";
import formData from "./form.json";

export type ServiceSection = { heading: string; paragraphs: string[]; image?: string; imageAlt?: string; imageSide?: "right" | "left" };
export type TitledPoint = { title: string; text: string };
/** "default" follows the site-wide switch under Service page blocks; "on" / "off" override it for this service. */
export type ServiceBlockMode = "default" | "on" | "off";
export type ServiceBlocks = {
  heroForm?: ServiceBlockMode;
  stickyBar?: ServiceBlockMode;
  whyUs?: { mode?: ServiceBlockMode; heading?: string; items?: TitledPoint[] };
  benefits?: { mode?: ServiceBlockMode; heading?: string; items?: string[] };
  process?: { mode?: ServiceBlockMode; heading?: string; items?: TitledPoint[] };
  cost?: { mode?: ServiceBlockMode; heading?: string; intro?: string; items?: TitledPoint[] };
  faqsHeading?: string;
};

export type Service = {
  slug: string;
  title: string;
  /** Page heading; empty = "<title> in <service area>". */
  h1?: string;
  /** Short name used in the enquiry form select. */
  formLabel: string;
  /** One-line summary for cards and metadata. */
  summary: string;
  /** Content sections of the service page, each with its own H2. */
  sections?: ServiceSection[];
  /** Per-service switches and overrides for the optional blocks. */
  blocks?: ServiceBlocks;
  /** Published area pages linked under "Where we carry out this work" (their slugs). Empty = block hidden. */
  areaPages?: string[];
  /** Typical faults handled under this service. */
  faults: string[];
  /** Photo: a site path (/uploads/…) or an https image URL. */
  image: string;
  imageAlt: string;
  /** Lucide icon name used where a photo is not appropriate. */
  icon: string;
  /** SEO keyword phrase used in the page title. */
  seoTitle: string;
  /** Meta description; empty = built from the summary. */
  seoDescription?: string;
  /** Questions and answers shown on the service page (FAQPage schema). */
  faqs?: { question: string; answer: string }[];
};

export const services = servicesData as Service[];

export function findService(slug: string) {
  return services.find((s) => s.slug === slug);
}

/** Options for the enquiry form, edited under "Enquiry form" in the CMS. */
export const serviceFormOptions: readonly string[] = formData.serviceOptions;
export const propertyTypeOptions: readonly string[] = formData.propertyTypeOptions;
export const contactTimeOptions: readonly string[] = formData.contactTimeOptions;

/** Wording on the enquiry form, edited under "Enquiry form" in the CMS. Empty = the line is not shown. */
export const formCopy = {
  postcodeHint: (formData as { postcodeHint?: string }).postcodeHint ?? "",
  outsideAreaNotice: (formData as { outsideAreaNotice?: string }).outsideAreaNotice ?? "",
};
