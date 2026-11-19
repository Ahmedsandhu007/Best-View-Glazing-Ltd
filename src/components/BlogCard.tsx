import Image from "next/image";
import Link from "next/link";
import { ArrowRight, CalendarDays, Clock } from "lucide-react";
import type { Post } from "@/content/posts";

export function BlogCard({ post, headingLevel = "h3" }: { post: Post; headingLevel?: "h2" | "h3" }) {
  const Heading = headingLevel;
  return (
    <article className="group relative flex h-full flex-col overflow-hidden rounded-[4px] border border-line bg-white transition-colors hover:border-teal/50 focus-within:border-teal">
      <div className="relative aspect-[16/10] overflow-hidden border-b border-line bg-ivory">
        <Image
          src={post.image}
          alt={post.imageAlt}
          fill
          loading="lazy"
          sizes="(min-width: 1024px) 380px, (min-width: 640px) 50vw, 100vw"
          className="object-cover transition-transform duration-300 group-hover:scale-[1.02]"
        />
      </div>
      <div className="flex flex-1 flex-col p-6">
        <p className="eyebrow text-[0.75rem]">{post.category}</p>
        <Heading className="mt-2 font-heading text-[1.125rem] font-semibold leading-snug text-charcoal">
          <Link href={`/blog/${post.slug}`} className="after:absolute after:inset-0 after:content-[''] group-hover:text-teal focus-visible:outline-none">
            {post.title}
          </Link>
        </Heading>
        <p className="mt-2.5 text-[0.9375rem] leading-relaxed text-muted">{post.excerpt}</p>
        <div className="mt-auto flex flex-wrap items-center gap-x-4 gap-y-1 pt-5 text-sm text-muted">
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
          <span className="ml-auto inline-flex items-center gap-1.5 font-heading font-semibold text-teal">
            Read
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
          </span>
        </div>
      </div>
    </article>
  );
}
