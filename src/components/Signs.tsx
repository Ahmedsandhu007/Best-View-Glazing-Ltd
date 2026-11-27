import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { RichInline } from "@/components/RichText";
import { home } from "@/content/site";

/** Home page: the symptoms a customer can see, what usually causes each one, and the service page that fixes it. */
export function Signs() {
  const copy = home.signs;
  if (!copy.heading.trim() || copy.items.length === 0) return null;
  return (
    <section id="signs" className="section bg-ivory">
      <div className="container-site">
        <div className="max-w-2xl">
          <h2 className="text-3xl font-bold leading-tight text-charcoal md:text-[2.375rem]">{copy.heading}</h2>
          {copy.intro ? <p className="mt-4 text-lg leading-relaxed text-muted">{copy.intro}</p> : null}
        </div>
        <ul className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {copy.items.map((item) => (
            <li key={item.symptom} className="flex flex-col rounded-[4px] border border-line bg-white p-6">
              <h3 className="font-heading text-[1.0625rem] font-semibold leading-snug text-charcoal">{item.symptom}</h3>
              <p className="mt-2 flex-1 text-[0.9375rem] leading-relaxed text-muted">{item.cause}</p>
              {item.href && item.linkLabel ? (
                <Link href={item.href} className="mt-4 inline-flex items-center gap-1.5 font-heading text-sm font-semibold text-teal hover:text-teal-dark">
                  {item.linkLabel}
                  <ArrowRight className="h-4 w-4" aria-hidden="true" />
                </Link>
              ) : null}
            </li>
          ))}
        </ul>
        {copy.outro ? (
          <p className="mt-10 max-w-3xl text-[1.0625rem] leading-relaxed text-ink">
            <RichInline text={copy.outro} />
          </p>
        ) : null}
      </div>
    </section>
  );
}
