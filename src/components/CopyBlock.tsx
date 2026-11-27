import Image from "next/image";
import { RichInline } from "@/components/RichText";
import { images } from "@/content/images";

type Props = {
  heading: string;
  paragraphs: string[];
  /** A picture from the Photographs section shown beside the text (optional). */
  image?: keyof typeof images;
  imageSide?: "left" | "right";
  tone?: "ivory" | "white";
  id?: string;
};

/** A heading and a few paragraphs (links allowed), with an optional photo beside them. Hidden when there is no text. */
export function CopyBlock({ heading, paragraphs, image, imageSide = "right", tone = "white", id }: Props) {
  const text = paragraphs.filter((p) => p.trim());
  if (!heading.trim() || text.length === 0) return null;
  const img = image ? images[image] : null;
  return (
    <section id={id} className={`section ${tone === "ivory" ? "bg-ivory" : "bg-white"}`}>
      <div className={`container-site ${img ? "grid items-center gap-12 lg:grid-cols-12 lg:gap-16" : ""}`}>
        <div className={img ? `lg:col-span-7 ${imageSide === "left" ? "order-1 lg:order-2" : ""}` : "max-w-3xl"}>
          <h2 className="text-3xl font-bold leading-tight text-charcoal md:text-[2.375rem]">{heading}</h2>
          <div className="mt-6 space-y-5 text-[1.0625rem] leading-relaxed text-ink">
            {text.map((p) => (
              <p key={p.slice(0, 40)}>
                <RichInline text={p} />
              </p>
            ))}
          </div>
        </div>
        {img ? (
          <div className={`lg:col-span-5 ${imageSide === "left" ? "order-2 lg:order-1" : ""}`}>
            <div className="relative aspect-[4/3] overflow-hidden rounded-[4px] border border-line bg-ivory">
              <Image src={img.src} alt={img.alt} fill loading="lazy" sizes="(min-width: 1024px) 460px, 100vw" className="object-cover" />
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}
