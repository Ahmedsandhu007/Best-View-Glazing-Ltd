import { QuoteForm } from "@/components/QuoteForm";
import { processSteps, site } from "@/content/site";

type Props = {
  defaultService?: string;
  headingLevel?: "h1" | "h2";
  tone?: "ivory" | "white";
};

export function QuoteSection({ defaultService, headingLevel = "h2", tone = "ivory" }: Props) {
  const Heading = headingLevel;
  return (
    <section id={site.enquiryFormId} className={`section ${tone === "ivory" ? "bg-ivory" : "bg-white"}`} aria-labelledby="quote-heading">
      <div className="container-site grid gap-12 lg:grid-cols-12 lg:gap-16">
        <div className="lg:col-span-5">
          <p className="eyebrow">Request a quote</p>
          <Heading id="quote-heading" className="mt-3 text-3xl font-bold leading-tight md:text-[2.375rem]">
            Request a Window or Door Repair Quote
          </Heading>
          <p className="mt-4 text-lg leading-relaxed text-muted">
            Tell us a little about the repair you need and our team will review your enquiry.
          </p>
          <div className="mt-8 border-t border-line pt-6">
            <h3 className="font-heading text-sm font-semibold uppercase tracking-[0.12em] text-teal">What happens next</h3>
            <ol className="mt-4 space-y-4">
              {processSteps.map((step, i) => (
                <li key={step.title} className="flex gap-4">
                  <span className="font-heading text-lg font-bold tabular-nums text-teal" aria-hidden="true">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <div>
                    <p className="font-heading font-semibold text-charcoal">{step.title}</p>
                    <p className="mt-0.5 text-sm leading-relaxed text-muted">{step.text}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>
          <p className="mt-8 text-sm leading-relaxed text-muted">
            This form is our only enquiry channel. Keeping every request in one place means nothing is lost and each enquiry is
            reviewed by someone who understands window and door hardware.
          </p>
        </div>
        <div className="lg:col-span-7">
          <QuoteForm defaultService={defaultService} />
        </div>
      </div>
    </section>
  );
}
