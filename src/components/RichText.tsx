import * as React from "react";
import Link from "next/link";
import { Check } from "lucide-react";

/**
 * Tiny formatter for CMS long text (blog articles, case-study write-ups):
 *   **bold**   *italic*   [link text](https://example.com)
 * and, as a whole line, an image:  ![description](/uploads/photo.jpg)
 * Anything else is shown as plain text, so nothing here can inject markup.
 */

const INLINE = /\*\*(.+?)\*\*|\*([^*\s][^*]*?)\*|\[([^\]]+)\]\(([^)\s]+)\)/g;
const IMAGE_LINE = /^!\[([^\]]*)\]\(([^)\s]+)\)$/;

/** Only web, mail, phone and same-site links are allowed. */
function safeHref(href: string): string | null {
  return /^(https?:\/\/|mailto:|tel:|\/|#)/i.test(href) ? href : null;
}

export function RichInline({ text }: { text: string }): React.ReactNode {
  const out: React.ReactNode[] = [];
  let last = 0;
  let key = 0;
  for (const m of text.matchAll(INLINE)) {
    const at = m.index ?? 0;
    if (at > last) out.push(text.slice(last, at));
    if (m[1] !== undefined) {
      out.push(
        <strong key={key++} className="font-semibold text-charcoal">
          <RichInline text={m[1]} />
        </strong>,
      );
    } else if (m[2] !== undefined) {
      out.push(
        <em key={key++}>
          <RichInline text={m[2]} />
        </em>,
      );
    } else {
      const href = safeHref(m[4]);
      const cls = "font-medium text-teal underline underline-offset-4 hover:text-teal-dark";
      if (!href) out.push(m[3]);
      else if (href.startsWith("/") || href.startsWith("#"))
        out.push(
          <Link key={key++} href={href} className={cls}>
            <RichInline text={m[3]} />
          </Link>,
        );
      else
        out.push(
          <a key={key++} href={href} className={cls} target="_blank" rel="noopener noreferrer">
            <RichInline text={m[3]} />
          </a>,
        );
    }
    last = at + m[0].length;
  }
  if (last < text.length) out.push(text.slice(last));
  return <>{out}</>;
}

/** The same text with the **bold**, *italic* and [link](…) markup removed (for schema and meta text). */
export function plainText(text: string): string {
  return text.replace(INLINE, (_m, b, i, l) => b ?? i ?? l ?? "");
}

/** If the whole block is an image line, return its parts. */
export function parseImageLine(block: string): { alt: string; src: string } | null {
  const m = IMAGE_LINE.exec(block.trim());
  if (!m) return null;
  const src = /^(https?:\/\/|\/)/i.test(m[2]) ? m[2] : null;
  return src ? { alt: m[1], src } : null;
}

/** Render CMS long text: "## …" = heading, consecutive "- …" = bullet list, image lines, else paragraph. */
export function ArticleBody({ blocks }: { blocks: string[] }) {
  const out: React.ReactNode[] = [];
  for (let i = 0; i < blocks.length; ) {
    const block = blocks[i];
    const image = parseImageLine(block);
    if (image) {
      out.push(
        <figure key={out.length} className="mt-8">
          {/* Uploaded through the CMS: size is unknown at build time, so a plain <img> is used. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={image.src} alt={image.alt} loading="lazy" className="w-full rounded-[4px] border border-line" />
          {image.alt ? <figcaption className="mt-2 text-sm text-muted">{image.alt}</figcaption> : null}
        </figure>,
      );
      i++;
    } else if (block.startsWith("## ")) {
      out.push(
        <h2 key={out.length} className="mt-10 text-2xl font-bold text-charcoal">
          {block.slice(3)}
        </h2>,
      );
      i++;
    } else if (block.startsWith("- ")) {
      const items: string[] = [];
      while (i < blocks.length && blocks[i].startsWith("- ")) {
        items.push(blocks[i].slice(2));
        i++;
      }
      out.push(
        <ul key={out.length} className="mt-5 space-y-3">
          {items.map((it, j) => (
            <li key={j} className="flex items-start gap-3 text-ink">
              <Check className="mt-1.5 h-4 w-4 shrink-0 text-teal" aria-hidden="true" />
              <span>
                <RichInline text={it} />
              </span>
            </li>
          ))}
        </ul>,
      );
    } else {
      out.push(
        <p key={out.length} className="mt-5 text-[1.0625rem] leading-relaxed text-ink">
          <RichInline text={block} />
        </p>,
      );
      i++;
    }
  }
  return <>{out}</>;
}
