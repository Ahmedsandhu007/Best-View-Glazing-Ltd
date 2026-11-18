import Link from "next/link";
import type { LegalDoc } from "@/content/site";

/** Renders a legal document from the CMS: dated sections of paragraphs; a paragraph starting with "- " becomes a bullet. */
export function LegalDocument({ doc, footer }: { doc: LegalDoc; footer: { text: string; linkLabel: string; href: string } }) {
  return (
    <section className="section bg-white">
      <div className="container-site max-w-3xl">
        <p className="text-sm text-muted">Last updated: {doc.updated}</p>
        {doc.sections.map((s) => {
          const bullets = s.body.filter((p) => p.startsWith("- "));
          const paragraphs = s.body.filter((p) => !p.startsWith("- "));
          return (
            <div key={s.title} className="mt-10">
              <h2 className="text-2xl font-bold">{s.title}</h2>
              <div className="prose-site mt-4 text-[1.0625rem] leading-relaxed text-ink">
                {paragraphs.map((p) => (
                  <p key={p.slice(0, 40)}>{p}</p>
                ))}
                {bullets.length > 0 && (
                  <ul>
                    {bullets.map((b) => (
                      <li key={b.slice(0, 40)}>{b.slice(2)}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          );
        })}
        <p className="mt-12 border-t border-line pt-6 text-[0.9375rem] text-muted">
          {footer.text}{" "}
          <Link href={footer.href} className="font-medium text-teal underline underline-offset-4">
            {footer.linkLabel}
          </Link>
          .
        </p>
      </div>
    </section>
  );
}
