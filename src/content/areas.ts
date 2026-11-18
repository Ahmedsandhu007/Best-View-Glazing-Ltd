import regionsData from "./regions.json";

export type AreaGroup = {
  region: string;
  slug: string;
  intro: string;
  areas: { name: string; slug: string }[];
};

export const areaGroups = regionsData as AreaGroup[];

export const allAreas = areaGroups.flatMap((g) =>
  g.areas.map((a) => ({ ...a, region: g.region, regionSlug: g.slug, regionIntro: g.intro })),
);

export function findArea(slug: string) {
  return allAreas.find((a) => a.slug === slug);
}
