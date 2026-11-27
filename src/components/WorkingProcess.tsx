import { SectionHeading } from "@/components/ui/SectionHeading";
import { processSteps, sections } from "@/content/site";

export function WorkingProcess({ tone = "ivory" }: { tone?: "ivory" | "white" }) {
  const copy = sections.process;
  return (
    <section className={`section ${tone === "ivory" ? "bg-ivory" : "bg-white"}`}>
      <div className="container-site">
        <SectionHeading eyebrow={copy.eyebrow} title={copy.title} intro={copy.description || undefined} />
        <ol className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {processSteps.map((step, i) => (
            <li key={step.slug} className={`flex flex-col rounded-[4px] border border-line p-6 ${tone === "ivory" ? "bg-white" : "bg-ivory"}`}>
              <span className="font-heading text-3xl font-bold tabular-nums text-teal" aria-hidden="true">
                {String(i + 1).padStart(2, "0")}
              </span>
              <h3 className="mt-4 font-heading text-[1.0625rem] font-semibold text-charcoal">
                <span className="sr-only">Step {i + 1}: </span>
                {step.title}
              </h3>
              <p className="mt-2 text-[0.9375rem] leading-relaxed text-muted">{step.text}</p>
            </li>
          ))}
        </ol>
        {copy.note ? <p className="mt-8 max-w-3xl text-[1.0625rem] leading-relaxed text-ink">{copy.note}</p> : null}
      </div>
    </section>
  );
}
