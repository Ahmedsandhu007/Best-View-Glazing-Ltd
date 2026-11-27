import { SectionHeading } from "@/components/ui/SectionHeading";
import { Button } from "@/components/ui/Button";
import { BlogCard } from "@/components/BlogCard";
import { posts } from "@/content/posts";
import { sections } from "@/content/site";

/** Home page: the four most recent articles (the first four entries; the list is kept newest first in the CMS). */
export function BlogTeasers() {
  const copy = sections.blog;
  const latest = posts.slice(0, 4);
  if (latest.length === 0) return null;
  return (
    <section className="section bg-white">
      <div className="container-site">
        <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
          <SectionHeading eyebrow={copy.eyebrow} title={copy.title} intro={copy.description} />
          <Button href="/blog" variant="secondary" className="shrink-0">
            {copy.buttonLabel}
          </Button>
        </div>
        <ul className={`mt-10 grid gap-6 sm:grid-cols-2 ${latest.length > 3 ? "lg:grid-cols-4" : "lg:grid-cols-3"}`}>
          {latest.map((p) => (
            <li key={p.slug}>
              <BlogCard post={p} />
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
