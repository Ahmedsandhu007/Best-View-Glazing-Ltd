import type { MetadataRoute } from "next";
import { site } from "@/content/site";
import { services } from "@/content/services";
import { publishedAreas } from "@/content/areas";
import { posts } from "@/content/posts";
import { caseStudies } from "@/content/case-studies";
import redirectsData from "@/content/redirects.json";
import { buildRedirectMap, type Redirect } from "@/lib/redirects";

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();
  const url = (path: string) => new URL(path, site.url).toString();
  const statics: MetadataRoute.Sitemap = [
    { url: url("/"), lastModified: now, changeFrequency: "weekly", priority: 1 },
    { url: url("/services"), lastModified: now, changeFrequency: "monthly", priority: 0.9 },
    { url: url("/about"), lastModified: now, changeFrequency: "monthly", priority: 0.6 },
    { url: url("/areas"), lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: url("/case-studies"), lastModified: now, changeFrequency: "monthly", priority: 0.7 },
    { url: url("/blog"), lastModified: now, changeFrequency: "weekly", priority: 0.7 },
    { url: url("/faqs"), lastModified: now, changeFrequency: "monthly", priority: 0.6 },
    { url: url("/contact"), lastModified: now, changeFrequency: "monthly", priority: 0.9 },
    { url: url("/privacy-policy"), lastModified: now, changeFrequency: "yearly", priority: 0.2 },
    { url: url("/terms"), lastModified: now, changeFrequency: "yearly", priority: 0.2 },
  ];
  // An address with a redirect rule is no longer a page of its own.
  const redirected = buildRedirectMap(redirectsData as Redirect[]);
  const live = (entry: MetadataRoute.Sitemap[number]) => !redirected.has(new URL(entry.url).pathname.replace(/\/$/, "") || "/");
  return [
    ...statics,
    ...services.map((s) => ({ url: url(`/services/${s.slug}`), lastModified: now, changeFrequency: "monthly" as const, priority: 0.8 })),
    ...publishedAreas.map((a) => ({ url: url(`/areas/${a.slug}`), lastModified: now, changeFrequency: "monthly" as const, priority: 0.6 })),
    ...caseStudies.map((c) => ({ url: url(`/case-studies/${c.slug}`), lastModified: now, changeFrequency: "monthly" as const, priority: 0.5 })),
    ...posts.map((p) => ({ url: url(`/blog/${p.slug}`), lastModified: now, changeFrequency: "monthly" as const, priority: 0.5 })),
  ].filter(live);
}
