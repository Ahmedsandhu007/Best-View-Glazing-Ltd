import caseStudiesData from "./case-studies.json";

export const caseStudyCategories = ["Sash windows", "uPVC", "Aluminium", "Double glazing", "Doors", "Commercial"] as const;
export type CaseStudyCategory = (typeof caseStudyCategories)[number];

/** A case study, edited under "Case studies" in the CMS. `placeholder` marks sample content the site labels as such. */
export type CaseStudy = {
  slug: string;
  title: string;
  category: string;
  location: string;
  excerpt: string;
  description: string;
  image: string;
  imageAlt: string;
  tags: string[];
  results: { label: string; value: string }[];
  body?: string[];
  placeholder?: boolean;
};

export const caseStudies = caseStudiesData as CaseStudy[];

export const hasPlaceholderCaseStudies = caseStudies.some((c) => c.placeholder);

export function findCaseStudy(slug: string) {
  return caseStudies.find((c) => c.slug === slug);
}
