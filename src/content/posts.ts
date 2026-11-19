import postsData from "./posts.json";

/** A blog article, edited under "Blog articles" in the CMS. Body blocks: "## " heading, "- " bullet, "![alt](src)" image, else paragraph. */
export type Post = {
  slug: string;
  title: string;
  category: string;
  date?: string;
  readingTime?: string;
  excerpt: string;
  image: string;
  imageAlt: string;
  body: string[];
  seoTitle?: string;
  seoDescription?: string;
};

export const posts = postsData as Post[];

export function findPost(slug: string) {
  return posts.find((p) => p.slug === slug);
}
