/**
 * Single source of truth for field length limits + format checks.
 * Used by server-side validation AND the editor's live character counters,
 * so the UI and the server always agree.
 */

export const TEXT_LIMITS: Record<string, number> = {
  slug: 60,
  name: 80,
  shortName: 40,
  title: 160,
  label: 80,
  eyebrow: 60,
  heading: 140,
  bodyTitle: 140,
  subtitle: 400,
  summary: 220,
  description: 1200,
  text: 600,
  intro: 600,
  quote: 600,
  answer: 1500,
  question: 180,
  body: 1500,
  faults: 120,
  paragraphs: 1500,
  reassurance: 120,
  location: 80,
  region: 60,
  legalLine: 120,
  tagline: 160,
  note: 400,
  imageCaption: 200,
  src: 400,
  image: 400,
  alt: 200,
  imageAlt: 200,
  href: 200,
  url: 200,
  seoTitle: 90,
  formLabel: 60,
  icon: 40,
  updated: 40,
  keywords: 60,
  factorsHeading: 80,
  stepsHeading: 80,
  buttonLabel: 60,
  primaryLabel: 60,
  secondaryLabel: 60,
  submitLabel: 60,
  privacyLine: 160,
  placeholderNotice: 200,
  quoteLinkLabel: 60,
  bottomLine: 200,
  navigationHeading: 40,
  servicesHeading: 40,
  areasHeading: 40,
  legalHeading: 40,
  captionOne: 120,
  captionTwo: 120,
  ctaTitle: 120,
  ctaDescription: 300,
  category: 40,
  date: 40,
  readingTime: 24,
  excerpt: 280,
  tags: 40,
  value: 24,
  seoDescription: 220,
  phone: 30,
  email: 120,
  whatsappNumber: 20,
  whatsappLabel: 40,
  whatsappMessage: 200,
  mapQuery: 160,
  mapEmbedUrl: 400,
  hours: 80,
  address: 80,
  ga4MeasurementId: 20,
  gtmId: 20,
  ahrefsKey: 60,
  googleSiteVerification: 120,
  bingSiteVerification: 120,
  from: 200,
  to: 200,
  postcodeHint: 160,
  outsideAreaNotice: 300,
  coverageLine: 200,
  openingHoursSchema: 40,
  sameAs: 200,
  h1: 120,
  regionSlug: 60,
  nearby: 60,
  imageSide: 10,
  mode: 10,
  enabled: 10,
  areaPages: 60,
  faqsHeading: 140,
  callLabel: 30,
  items: 400,
};

export const limitFor = (key: string) => TEXT_LIMITS[key] ?? 400;

/* ── Format checkers ─────────────────────────────────────── */
export const isEmail = (v: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
export const isUrl = (v: string) => /^https?:\/\/\S+$/.test(v);
export const isSlug = (v: string) => /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(v);
export const isHexColor = (v: string) => /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(v);
/** A site path ("/uploads/x.jpg") or an https image address. */
export const isImageRef = (v: string) => /^\/[^\s]*$/.test(v) || /^https:\/\/\S+$/.test(v);

/** Make a URL-safe slug from arbitrary text. */
export function slugify(input: string): string {
  return input
    .toLowerCase()
    .trim()
    .replace(/&/g, "and")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, TEXT_LIMITS.slug);
}
