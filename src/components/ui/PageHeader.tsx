import Link from "next/link";
import { ChevronRight } from "lucide-react";
import type { ReactNode } from "react";

type Crumb = { label: string; href?: string };

type Props = {
  eyebrow?: string;
  title: string;
  intro?: ReactNode;
  crumbs?: Crumb[];
  children?: ReactNode;
};

/** Standard inner-page banner: charcoal band with breadcrumb, H1 and intro. */
export function PageHeader({ eyebrow, title, intro, crumbs, children }: Props) {
  return (
    <section className="bg-charcoal text-white">
      <div className="container-site py-14 md:py-20">
        {crumbs && crumbs.length > 0 && (
          <nav aria-label="Breadcrumb" className="mb-6">
            <ol className="flex flex-wrap items-center gap-1.5 text-sm text-white/65">
              <li>
                <Link href="/" className="hover:text-white">
                  Home
                </Link>
              </li>
              {crumbs.map((c) => (
                <li key={c.label} className="flex items-center gap-1.5">
                  <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
                  {c.href ? (
                    <Link href={c.href} className="hover:text-white">
                      {c.label}
                    </Link>
                  ) : (
                    <span aria-current="page" className="text-white/90">
                      {c.label}
                    </span>
                  )}
                </li>
              ))}
            </ol>
          </nav>
        )}
        <div className="max-w-3xl">
          {eyebrow && <p className="eyebrow text-brass">{eyebrow}</p>}
          <h1 className="mt-3 text-4xl font-bold leading-[1.1] text-white md:text-5xl">{title}</h1>
          {intro && <div className="mt-5 text-lg leading-relaxed text-white/80">{intro}</div>}
          {children && <div className="mt-8">{children}</div>}
        </div>
      </div>
    </section>
  );
}
