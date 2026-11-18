import Image from "next/image";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { images } from "@/content/images";

const quickLinks = [
  { label: "uPVC window repairs", href: "/services/upvc-window-repairs" },
  { label: "Aluminium window repairs", href: "/services/aluminium-window-repairs" },
  { label: "Sash window repairs", href: "/services/sash-window-repairs" },
  { label: "Double glazing repairs", href: "/services/double-glazing-repairs" },
  { label: "Window lock and handle repairs", href: "/services/window-lock-and-handle-repairs" },
  { label: "Door lock and mechanism repairs", href: "/services/door-lock-and-handle-repairs" },
];

export function Introduction() {
  const img = images.intro;
  return (
    <section className="section bg-white">
      <div className="container-site grid items-center gap-12 lg:grid-cols-12 lg:gap-16">
        <div className="order-2 lg:order-1 lg:col-span-5">
          <div className="relative aspect-[4/3] overflow-hidden rounded-[4px] border border-line bg-ivory">
            <Image src={img.src} alt={img.alt} fill loading="lazy" sizes="(min-width: 1024px) 460px, 100vw" className="object-cover" />
          </div>
        </div>
        <div className="order-1 lg:order-2 lg:col-span-7">
          <p className="eyebrow">Who we are</p>
          <h2 className="mt-3 text-3xl font-bold leading-tight md:text-[2.375rem]">Window &amp; Door Repair Specialists in London</h2>
          <div className="prose-site mt-6 text-[1.0625rem] leading-relaxed text-ink">
            <p>
              Windows and doors do a great deal of quiet work. They keep a property secure, warm, dry and ventilated, and
              most people only notice them when a handle snaps, a sash drops or condensation appears between the panes.
              Left alone, a small mechanical fault tends to become a larger and more expensive one.
            </p>
            <p>
              Best View Glazing Ltd repairs the common mechanical and glazing problems that affect uPVC,
              aluminium, timber and sash windows, together with the locks, hinges and mechanisms on external and internal
              doors. We replace failed hinges, handles, locks and gaskets, re-glaze misted or broken sealed units, free
              jammed sashes and repair damaged frames, keeping the original window wherever that is the sensible option.
            </p>
            <p>
              We work for homeowners, tenants and landlords, for letting agencies and property management companies, and
              for offices, shops and other commercial premises. Whatever the property, the approach is the same: understand
              the fault, propose a practical repair and quote for it clearly. We cover the whole of Greater London.
            </p>
          </div>
          <ul className="mt-7 grid gap-x-8 gap-y-2 sm:grid-cols-2">
            {quickLinks.map((l) => (
              <li key={l.href}>
                <Link href={l.href} className="inline-flex items-center gap-2 text-[0.9375rem] font-medium text-charcoal underline decoration-line underline-offset-4 hover:text-teal hover:decoration-teal">
                  {l.label}
                </Link>
              </li>
            ))}
          </ul>
          <div className="mt-8">
            <Button href="/about" variant="secondary">
              More about how we work
            </Button>
          </div>
        </div>
      </div>
    </section>
  );
}
