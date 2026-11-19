import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, CalendarDays, Clock } from "lucide-react";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/Button";
import { ArticleBody } from "@/components/RichText";
import { BlogCard } from "@/components/BlogCard";
import { CtaBand } from "@/components/CtaBand";
import { JsonLd } from "@/components/JsonLd";
import { findPost, posts } from "@/content/posts";
import { site } from "@/content/site";
import { blogPostingJsonLd, breadcrumbJsonLd } from "@/lib/seo";

type Params = { slug: string };

export function generateStaticParams(): Params[] {
  return posts.map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({ params }: { params: Promise<Params> }): Promise<Metadata> {
  const { slug } = await params;
  const post = findPost(slug);
  if (!post) return {};
  const title = post.seoTitle?.trim() || post.title;
  const description = post.seoDescription?.trim() || post.excerpt;
  return {
    title,
    description,
    alternates: { canonical: `/blog/${post.slug}` },
    openGraph: { type: "article", title: `${title} | ${site.name}`, description, url: `/blog/${post.slug}`, images: [{ url: post.image, alt: post.imageAlt }] },
  };
}

export default async function BlogPostPage({ params }: { params: Promise<Params> }) {
  const { slug } = await params;
  const post = findPost(slug);
  if (!post) notFound();
  const related = posts.filter((p) => p.slug !== slug).slice(0, 3);

  return (
    <>
      <PageHeader eyebrow={post.category} title={post.title} intro={post.excerpt} crumbs={[{ label: "Blog", href: "/blog" }, { label: post.title }]} />

      <article className="section bg-white">
        <div className="container-site max-w-3xl">
          <div className="relative aspect-[16/9] overflow-hidden rounded-[4px] border border-line bg-ivory">
            <Image src={post.image} alt={post.imageAlt} fill priority sizes="(min-width: 1024px) 760px, 100vw" className="object-cover" />
          </div>
          <div className="mt-6 flex flex-wrap items-center gap-x-5 gap-y-2 border-b border-line pb-5 text-sm text-muted">
            {post.date ? (
              <span className="inline-flex items-center gap-1.5">
                <CalendarDays className="h-4 w-4" aria-hidden="true" /> {post.date}
              </span>
            ) : null}
            {post.readingTime ? (
              <span className="inline-flex items-center gap-1.5">
                <Clock className="h-4 w-4" aria-hidden="true" /> {post.readingTime}
              </span>
            ) : null}
            <span>By the {site.name} team</span>
          </div>

          <div className="prose-site">
            {post.body.length ? <ArticleBody blocks={post.body} /> : <p className="mt-5 text-[1.0625rem] leading-relaxed text-ink">{post.excerpt}</p>}
          </div>

          <div className="mt-12 flex flex-col gap-3 border-t border-line pt-8 sm:flex-row sm:items-center sm:justify-between">
            <Link href="/blog" className="inline-flex items-center gap-1.5 font-heading text-[0.9375rem] font-semibold text-charcoal hover:text-teal">
              <ArrowLeft className="h-4 w-4" aria-hidden="true" /> All articles
            </Link>
            <Button href={site.enquiryPath}>Request a Free Quote</Button>
          </div>
        </div>
      </article>

      {related.length > 0 && (
        <section className="section bg-ivory" aria-labelledby="related-posts">
          <div className="container-site">
            <h2 id="related-posts" className="text-2xl font-bold md:text-3xl">
              Keep reading
            </h2>
            <ul className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {related.map((p) => (
                <li key={p.slug}>
                  <BlogCard post={p} />
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}

      <CtaBand />
      <JsonLd
        data={[
          blogPostingJsonLd(post),
          breadcrumbJsonLd([
            { name: "Blog", path: "/blog" },
            { name: post.title, path: `/blog/${post.slug}` },
          ]),
        ]}
      />
    </>
  );
}
