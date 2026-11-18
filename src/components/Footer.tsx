import Link from "next/link";
import { Logo } from "@/components/Logo";
import { footer, legalLinks, navigation, site } from "@/content/site";
import { services } from "@/content/services";
import { areaGroups } from "@/content/areas";

const linkClass = "text-[0.9375rem] text-white/75 transition-colors hover:text-white";
const headingClass = "font-heading text-sm font-semibold uppercase tracking-[0.12em] text-brass";

export function Footer() {
  return (
    <footer className="bg-charcoal text-white">
      <div className="container-site py-14 md:py-16">
        <div className="grid gap-12 lg:grid-cols-12">
          <div className="lg:col-span-4">
            <Logo variant="light" />
            <p className="mt-5 max-w-sm text-[0.9375rem] leading-relaxed text-white/75">{footer.intro}</p>
            <Link
              href={site.enquiryPath}
              className="mt-6 inline-flex items-center gap-2 border-b border-brass pb-1 font-heading text-[0.9375rem] font-semibold text-white hover:border-white"
            >
              {footer.quoteLinkLabel}
            </Link>
          </div>

          <div className="grid gap-10 sm:grid-cols-3 lg:col-span-8">
            <div>
              <h2 className={headingClass}>{footer.navigationHeading}</h2>
              <ul className="mt-4 space-y-2.5">
                {navigation.map((item) => (
                  <li key={item.href}>
                    <Link href={item.href} className={linkClass}>
                      {item.label}
                    </Link>
                  </li>
                ))}
                <li>
                  <Link href={site.enquiryPath} className={linkClass}>
                    Request a Quote
                  </Link>
                </li>
              </ul>
            </div>
            <div>
              <h2 className={headingClass}>{footer.servicesHeading}</h2>
              <ul className="mt-4 space-y-2.5">
                {services.map((s) => (
                  <li key={s.slug}>
                    <Link href={`/services/${s.slug}`} className={linkClass}>
                      {s.title}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h2 className={headingClass}>{footer.areasHeading}</h2>
              <ul className="mt-4 space-y-2.5">
                {areaGroups.map((g) => (
                  <li key={g.slug}>
                    <Link href={`/areas#${g.slug}`} className={linkClass}>
                      {g.region}
                    </Link>
                  </li>
                ))}
                <li>
                  <Link href="/areas" className={linkClass}>
                    All areas we cover
                  </Link>
                </li>
              </ul>
              <h2 className={`mt-8 ${headingClass}`}>{footer.legalHeading}</h2>
              <ul className="mt-4 space-y-2.5">
                {legalLinks.map((item) => (
                  <li key={item.href}>
                    <Link href={item.href} className={linkClass}>
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
      <div className="border-t border-line-dark">
        <div className="container-site flex flex-col gap-3 py-5 text-sm text-white/60 sm:flex-row sm:items-center sm:justify-between">
          <p>{site.legalLine}</p>
          <p>{footer.bottomLine}</p>
        </div>
      </div>
    </footer>
  );
}
