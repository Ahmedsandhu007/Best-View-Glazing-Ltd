import { Quote, Star } from "lucide-react";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { hasPlaceholderTestimonials, testimonials } from "@/content/testimonials";

export function Testimonials() {
  return (
    <section className="section bg-ivory">
      <div className="container-site">
        <SectionHeading
          eyebrow="Customer feedback"
          title="What customers say about the work"
          intro="Feedback from the homeowners, landlords and businesses we have carried out repairs for across London."
        />
        {hasPlaceholderTestimonials && (
          <p className="mt-6 inline-block rounded-[4px] border border-brass/60 bg-white px-3 py-1.5 text-sm text-ink">
            Sample content: these example quotes will be replaced with genuine customer feedback before launch.
          </p>
        )}
        <ul className="mt-10 grid gap-6 md:grid-cols-3">
          {testimonials.map((t, i) => (
            <li key={i} className="flex h-full flex-col rounded-[4px] border border-line bg-white p-7">
              <Quote className="h-6 w-6 text-brass" strokeWidth={1.75} aria-hidden="true" />
              {!t.placeholder && t.rating ? (
                <div className="mt-4 flex items-center gap-0.5" aria-label={`${t.rating} out of 5 stars`}>
                  {Array.from({ length: 5 }).map((_, s) => (
                    <Star key={s} className={`h-4 w-4 ${s < t.rating! ? "fill-brass text-brass" : "text-line"}`} aria-hidden="true" />
                  ))}
                </div>
              ) : null}
              <blockquote className="mt-4 flex-1 text-[0.9375rem] leading-relaxed text-ink">
                <p>“{t.quote}”</p>
              </blockquote>
              <footer className="mt-6 border-t border-line pt-4 text-sm">
                <p className="font-heading font-semibold text-charcoal">{t.name}</p>
                <p className="text-muted">{t.location}</p>
              </footer>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
