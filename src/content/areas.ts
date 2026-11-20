import regionsData from "./regions.json";

export type District = {
  name: string;
  slug: string;
  /** "Publish page" switch in the CMS. Off (the default) = no page, no links to it, not in the sitemap, old address redirects to /areas. */
  published?: boolean;
};

export type AreaGroup = {
  region: string;
  slug: string;
  intro: string;
  areas: District[];
};

export const areaGroups = regionsData as AreaGroup[];

/** Every district, published or not (used for the redirect of unpublished addresses). */
export const allAreas = areaGroups.flatMap((g) =>
  g.areas.map((a) => ({ ...a, region: g.region, regionSlug: g.slug, regionIntro: g.intro })),
);

/** Districts with a live page: these are linked, listed in the sitemap and rendered. */
export const publishedAreas = allAreas.filter((a) => a.published === true);

export function isPublishedArea(slug: string) {
  return publishedAreas.some((a) => a.slug === slug);
}

/** A district whose page is live, or undefined. */
export function findArea(slug: string) {
  return publishedAreas.find((a) => a.slug === slug);
}
