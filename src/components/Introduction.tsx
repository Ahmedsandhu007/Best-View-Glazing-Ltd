import Image from "next/image";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { images } from "@/content/images";
import { home } from "@/content/site";

export function Introduction() {
  const img = images.intro;
  const intro = home.intro;
  return (
    <section className="section bg-white">
      <div className="container-site grid items-center gap-12 lg:grid-cols-12 lg:gap-16">
        <div className="order-2 lg:order-1 lg:col-span-5">
          <div className="relative aspect-[4/3] overflow-hidden rounded-[4px] border border-line bg-ivory">
            <Image src={img.src} alt={img.alt} fill loading="lazy" sizes="(min-width: 1024px) 460px, 100vw" className="object-cover" />
          </div>
        </div>
        <div className="order-1 lg:order-2 lg:col-span-7">
          <p className="eyebrow">{intro.eyebrow}</p>
          <h2 className="mt-3 text-3xl font-bold leading-tight md:text-[2.375rem]">{intro.title}</h2>
          <div className="prose-site mt-6 text-[1.0625rem] leading-relaxed text-ink">
            {intro.paragraphs.map((p) => (
              <p key={p.slice(0, 40)}>{p}</p>
            ))}
          </div>
          {intro.quickLinks.length > 0 && (
            <ul className="mt-7 grid gap-x-8 gap-y-2 sm:grid-cols-2">
              {intro.quickLinks.map((l) => (
                <li key={l.href + l.label}>
                  <Link
                    href={l.href}
                    className="inline-flex items-center gap-2 text-[0.9375rem] font-medium text-charcoal underline decoration-line underline-offset-4 hover:text-teal hover:decoration-teal"
                  >
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          )}
          <div className="mt-8">
            <Button href={intro.cta.href} variant="secondary">
              {intro.cta.label}
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}
