import { Button } from "@/components/ui/Button";
import { sections, site } from "@/content/site";

type Props = { title?: string; text?: string; href?: string };

export function CtaBand({ title, text, href = site.enquiryPath }: Props) {
  const copy = sections.cta;
  return (
    <section className="bg-teal text-white">
      <div className="container-site flex flex-col gap-6 py-12 md:flex-row md:items-center md:justify-between md:py-14">
        <div className="max-w-2xl">
          <h2 className="font-heading text-2xl font-bold text-white md:text-3xl">{title ?? copy.title}</h2>
          <p className="mt-2 text-[1.0625rem] leading-relaxed text-white/85">{text ?? copy.description}</p>
        </div>
        <Button href={href} variant="light" size="lg" className="shrink-0">
          {copy.buttonLabel}
        </Button>
      </div>
    </section>
  );
}
