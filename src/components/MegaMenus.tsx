import Image from "next/image";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { services } from "@/content/services";
import { areaGroups } from "@/content/areas";
import { images } from "@/content/images";
import { posts } from "@/content/posts";
import { caseStudies } from "@/content/case-studies";

import type { MenuPanel } from "@/content/site";

function PanelHeading({ title, href, linkLabel }: { title: string; href: string; linkLabel: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-line pb-3">
      <p className="font-heading text-[0.8125rem] font-semibold uppercase tracking-[0.12em] text-charcoal">{title}</p>
      <Link href={href} className="inline-flex items-center gap-1.5 font-heading text-sm font-semibold text-teal hover:text-teal-dark">
        {linkLabel}
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
      </Link>
    </div>
  );
}

/** Services dropdown: every service with its photo, plus the areas column. */
export function ServicesMenu() {
  return (
    <div className="grid gap-8 p-7 xl:grid-cols-12">
      <div className="xl:col-span-9">
        <PanelHeading title="Our Services" href="/services" linkLabel="View all services" />
        <ul className="mt-4 grid gap-x-6 gap-y-0.5 sm:grid-cols-2 xl:grid-cols-3">
          {services.map((s) => (
            <li key={s.slug}>
              <Link href={`/services/${s.slug}`} className="group/item -mx-2 flex items-center gap-3.5 rounded-[4px] p-2 transition-colors hover:bg-ivory">
                <span className="relative h-14 w-[4.5rem] shrink-0 overflow-hidden rounded-[3px] bg-ivory">
                  <Image src={s.image} alt="" fill sizes="96px" className="object-cover" />
                </span>
                <span className="min-w-0">
                  <span className="block font-heading text-[0.9375rem] font-semibold leading-snug text-charcoal transition-colors group-hover/item:text-teal">
                    {s.title}
                  </span>
                  <span className="mt-0.5 block truncate text-[0.8125rem] text-muted">{s.summary}</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
      <div className="xl:col-span-3 xl:border-l xl:border-line xl:pl-8">
        <PanelHeading title="Areas We Cover" href="/areas" linkLabel="All areas" />
        <Link href="/areas" className="relative mt-4 block aspect-[16/10] overflow-hidden rounded-[4px] bg-ivory">
          <Image src={images.areas.src} alt={images.areas.alt} fill sizes="320px" className="object-cover" />
        </Link>
        <ul className="mt-3 space-y-0.5">
          {areaGroups.map((g) => (
            <li key={g.slug}>
              <Link
                href={`/areas#${g.slug}`}
                className="-mx-2 flex items-center justify-between gap-3 rounded-[3px] px-2 py-1.5 text-[0.9375rem] font-medium text-ink transition-colors hover:bg-ivory hover:text-teal"
              >
                {g.region}
                <span className="text-xs text-muted">{g.areas.length} areas</span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function PictureTile({ href, image, label, title, meta }: { href: string; image: string; label: string; title: string; meta?: string }) {
  return (
    <Link href={href} className="group/item block">
      <span className="relative block aspect-[16/10] overflow-hidden rounded-[4px] bg-ivory">
        <Image src={image} alt="" fill sizes="240px" className="object-cover transition-transform duration-300 group-hover/item:scale-[1.03]" />
      </span>
      <span className="mt-3 block truncate text-[0.75rem] font-medium uppercase tracking-[0.1em] text-teal">{label}</span>
      <span className="mt-1 line-clamp-2 block font-heading text-[0.9375rem] font-semibold leading-snug text-charcoal transition-colors group-hover/item:text-teal">
        {title}
      </span>
      {meta ? <span className="mt-1 block truncate text-[0.8125rem] text-muted">{meta}</span> : null}
    </Link>
  );
}

/** Blog dropdown: the three newest articles and case studies with their pictures. */
export function BlogMenu() {
  return (
    <div className="grid gap-8 p-7 lg:grid-cols-2">
      <div>
        <PanelHeading title="Articles" href="/blog" linkLabel="All articles" />
        <ul className="mt-4 grid grid-cols-3 gap-5">
          {posts.slice(0, 3).map((p) => (
            <li key={p.slug}>
              <PictureTile href={`/blog/${p.slug}`} image={p.image} label={p.category} title={p.title} />
            </li>
          ))}
        </ul>
      </div>
      <div className="lg:border-l lg:border-line lg:pl-8">
        <PanelHeading title="Case Studies" href="/case-studies" linkLabel="All case studies" />
        <ul className="mt-4 grid grid-cols-3 gap-5">
          {caseStudies.slice(0, 3).map((c) => (
            <li key={c.slug}>
              <PictureTile href={`/case-studies/${c.slug}`} image={c.image} label={c.category} title={c.title} meta={c.location} />
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export function MenuPanelContent({ panel }: { panel: MenuPanel }) {
  return panel === "services" ? <ServicesMenu /> : <BlogMenu />;
}
