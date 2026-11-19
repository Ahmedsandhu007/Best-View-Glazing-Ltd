import type { Metadata } from "next";
import { PageHeader } from "@/components/ui/PageHeader";
import { BlogCard } from "@/components/BlogCard";
import { CtaBand } from "@/components/CtaBand";
import { JsonLd } from "@/components/JsonLd";
import { posts } from "@/content/posts";
import { pages, seo, site } from "@/content/site";
import { breadcrumbJsonLd } from "@/lib/seo";

export const metadata: Metadata = {
  title: seo.blog.title,
  description: seo.blog.description,
  alternates: { canonical: "/blog" },
  openGraph: { title: `${seo.blog.title} | ${site.name}`, url: "/blog" },
};

export default function BlogIndexPage() {
  const copy = pages.blog;
  return (
    <>
      <PageHeader eyebrow={copy.eyebrow} title={copy.title} intro={copy.description} crumbs={[{ label: "Blog" }]} />
      <section className="section bg-white">
        <div className="container-site">
          {posts.length === 0 ? (
            <p className="text-muted">No articles yet.</p>
          ) : (
            <ul className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {posts.map((p) => (
                <li key={p.slug}>
                  <BlogCard post={p} headingLevel="h2" />
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
      <CtaBand title={copy.ctaTitle} text={copy.ctaDescription} />
      <JsonLd data={breadcrumbJsonLd([{ name: "Blog", path: "/blog" }])} />
    </>
  );
}
