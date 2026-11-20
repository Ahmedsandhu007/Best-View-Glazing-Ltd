import regionsData from "./regions.json";
import areaPagesData from "./area-pages.json";

/** A region on the Areas page, edited under "Areas we cover" in the CMS. */
export type Region = { region: string; slug: string; intro: string };

export type AreaSection = {
  heading: string;
  paragraphs: string[];
  image?: string;
  imageAlt?: string;
  /** Which side the photo sits on at desktop width. */
  imageSide?: "right" | "left";
};

export type AreaFaq = { question: string; answer: string };

/** A district / town page, edited under "Area pages" in the CMS. */
export type District = {
  slug: string;
  name: string;
  /** The region's slug from "Areas we cover". */
  regionSlug: string;
  /** "Publish page" switch. Off (the default) = no page, no links to it, not in the sitemap, old address redirects to /areas. */
  published?: boolean;
  /** Page heading; empty = "Window & Door Repairs in <name>". */
  h1?: string;
  /** Banner intro; empty = a standard sentence. */
  intro?: string;
  image?: string;
  imageAlt?: string;
  sections?: AreaSection[];
  /** Nearby places named on the page; a name that matches a published district becomes a link. */
  nearby?: string[];
  faqs?: AreaFaq[];
  seoTitle?: string;
  seoDescription?: string;
};

export type AreaGroup = Region & { areas: District[] };

export const regions = regionsData as Region[];
const districts = areaPagesData as District[];

/** Regions with their districts (in the order of the Area pages list), the shape the Areas page and footer use. */
export const areaGroups: AreaGroup[] = regions.map((r) => ({ ...r, areas: districts.filter((d) => d.regionSlug === r.slug) }));

/** Every district, published or not, with its region (used for the redirect of unpublished addresses). */
export const allAreas = districts.map((d) => {
  const r = regions.find((x) => x.slug === d.regionSlug);
  return { ...d, region: r?.region ?? d.regionSlug, regionIntro: r?.intro ?? "" };
});

/** Districts with a live page: linked, in the sitemap and rendered. */
export const publishedAreas = allAreas.filter((a) => a.published === true);

export function isPublishedArea(slug: string) {
  return publishedAreas.some((a) => a.slug === slug);
}

/** A district whose page is live, or undefined. */
export function findArea(slug: string) {
  return publishedAreas.find((a) => a.slug === slug);
}
