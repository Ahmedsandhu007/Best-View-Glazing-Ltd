/**
 * Site-wide content, read from the JSON files the CMS edits.
 * Components import from here, so a content change never touches a component.
 */
import settingsData from "./settings.json";
import homeData from "./home.json";
import sectionsData from "./sections.json";
import pagesData from "./pages.json";
import footerData from "./footer.json";
import seoData from "./seo.json";
import legalData from "./legal.json";
import trustData from "./trust-points.json";
import whyData from "./why-us.json";
import processData from "./process.json";
import factorsData from "./quote-factors.json";
import contactData from "./contact.json";

export const site = {
  ...settingsData,
  /** Public URL of the deployed site. NEXT_PUBLIC_SITE_URL wins over the CMS value. */
  url: process.env.NEXT_PUBLIC_SITE_URL ?? settingsData.url,
  /** The only enquiry channel is the website form. */
  enquiryPath: "/contact",
  enquiryFormId: "quote-form",
};

export const navigation = [
  { label: "Home", href: "/" },
  { label: "Services", href: "/services" },
  { label: "About", href: "/about" },
  { label: "Areas", href: "/areas" },
  { label: "Case Studies", href: "/case-studies" },
  { label: "Blog", href: "/blog" },
  { label: "FAQs", href: "/faqs" },
  { label: "Contact", href: "/contact" },
] as const;

export const legalLinks = [
  { label: "Privacy Policy", href: "/privacy-policy" },
  { label: "Terms & Conditions", href: "/terms" },
] as const;

export type TrustIcon = "building" | "wrench" | "file" | "map";
export type TrustPoint = { slug: string; title: string; text: string; icon: TrustIcon };
export const trustPoints = trustData as TrustPoint[];

export type WhyUsIcon = "search" | "building" | "hammer" | "file" | "map" | "message";
export type WhyUsPoint = { slug: string; title: string; text: string; icon?: WhyUsIcon };
export const whyChooseUs = whyData as WhyUsPoint[];

export type ProcessStep = { slug: string; title: string; text: string };
export const processSteps = processData as ProcessStep[];

export type QuoteFactor = { slug: string; title: string; text: string };
export const quoteFactors = factorsData as QuoteFactor[];

export const home = homeData;
export const sections = sectionsData;
export const pages = pagesData;
export const footer = footerData;
export const seo = seoData;
export const legal = legalData;

/** Phone, WhatsApp, email, address, opening hours and the map, edited under "Contact details" in the CMS. Empty values hide their lines. */
export const contact = contactData;

export type LegalDoc = { updated: string; sections: { title: string; body: string[] }[] };
