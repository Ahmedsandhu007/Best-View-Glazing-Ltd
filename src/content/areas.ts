export type AreaGroup = {
  region: string;
  slug: string;
  intro: string;
  areas: { name: string; slug: string }[];
};

const slugify = (s: string) =>
  s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");

const build = (region: string, intro: string, names: string[]): AreaGroup => ({
  region,
  slug: slugify(region),
  intro,
  areas: names.map((name) => ({ name, slug: slugify(name) })),
});

export const areaGroups: AreaGroup[] = [
  build(
    "Central London",
    "Period townhouses, mansion blocks, offices and retail frontages where sash windows, timber doors and heavy commercial glazing all need regular attention.",
    ["Westminster", "Soho", "Mayfair", "Marylebone", "Covent Garden", "Fitzrovia"],
  ),
  build(
    "North London",
    "Victorian and Edwardian terraces, 1930s semis and newer apartment developments with a wide mix of timber, uPVC and aluminium windows.",
    ["Islington", "Camden", "Finchley", "Barnet", "Enfield", "Tottenham"],
  ),
  build(
    "East London",
    "Converted warehouses, high-rise flats, new-build estates and busy commercial units from Hackney through to the Essex border.",
    ["Stratford", "Hackney", "Bow", "Canary Wharf", "Poplar", "Ilford", "Barking", "Romford"],
  ),
  build(
    "South London",
    "Suburban family homes, mansion flats and high-street premises, with a large stock of uPVC and double-glazed units now reaching the age where hardware fails.",
    ["Greenwich", "Lewisham", "Croydon", "Bromley", "Wimbledon", "Sutton", "Streatham"],
  ),
  build(
    "West London",
    "Riverside terraces, Metroland semis, purpose-built blocks and office parks, where aluminium and tilt-and-turn systems are as common as traditional timber.",
    ["Hammersmith", "Ealing", "Acton", "Chiswick", "Richmond", "Hounslow", "Wembley", "Harrow"],
  ),
];

export const allAreas = areaGroups.flatMap((g) =>
  g.areas.map((a) => ({ ...a, region: g.region, regionSlug: g.slug, regionIntro: g.intro })),
);

export function findArea(slug: string) {
  return allAreas.find((a) => a.slug === slug);
}
