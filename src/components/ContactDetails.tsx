import { Clock, Mail, MapPin, Phone } from "lucide-react";
import { WhatsAppButton } from "@/components/WhatsAppButton";
import { contact } from "@/content/site";

const telHref = (phone: string) => `tel:${phone.replace(/[^\d+]/g, "")}`;

/** Google Maps embed: a pasted embed address wins, else the map is built from the place or address text. */
export function mapSrc() {
  const url = (contact.mapEmbedUrl || "").trim();
  if (/^https:\/\/(www\.)?google\.[a-z.]+\/maps/i.test(url)) return url;
  const q = (contact.mapQuery || "").trim();
  return q ? `https://www.google.com/maps?q=${encodeURIComponent(q)}&output=embed` : null;
}

/** Contact details, opening hours and the map, on the Contact page. Anything left empty in the CMS is simply not shown. */
export function ContactDetails() {
  const map = mapSrc();
  const address = (contact.address ?? []).filter(Boolean);
  const hours = (contact.hours ?? []).filter(Boolean);
  return (
    <section className="section bg-ivory">
      <div className="container-site grid gap-10 lg:grid-cols-12 lg:gap-16">
        <div className="lg:col-span-5">
          <h2 className="text-3xl font-bold leading-tight md:text-[2.375rem]">{contact.detailsTitle}</h2>
          {contact.detailsIntro ? <p className="mt-4 text-lg leading-relaxed text-muted">{contact.detailsIntro}</p> : null}

          <div className="mt-8">
            <WhatsAppButton className="w-full sm:w-auto" />
          </div>

          <dl className="mt-8 divide-y divide-line border-y border-line">
            {contact.phone ? (
              <div className="flex gap-4 py-4">
                <dt className="flex w-32 shrink-0 items-center gap-2 font-heading text-sm font-semibold text-charcoal">
                  <Phone className="h-4 w-4 text-teal" aria-hidden="true" /> Phone
                </dt>
                <dd>
                  <a href={telHref(contact.phone)} className="text-ink underline decoration-line underline-offset-4 hover:text-teal hover:decoration-teal">
                    {contact.phone}
                  </a>
                </dd>
              </div>
            ) : null}
            {contact.email ? (
              <div className="flex gap-4 py-4">
                <dt className="flex w-32 shrink-0 items-center gap-2 font-heading text-sm font-semibold text-charcoal">
                  <Mail className="h-4 w-4 text-teal" aria-hidden="true" /> Email
                </dt>
                <dd className="min-w-0 break-words">
                  <a href={`mailto:${contact.email}`} className="text-ink underline decoration-line underline-offset-4 hover:text-teal hover:decoration-teal">
                    {contact.email}
                  </a>
                </dd>
              </div>
            ) : null}
            {address.length > 0 ? (
              <div className="flex gap-4 py-4">
                <dt className="flex w-32 shrink-0 items-center gap-2 font-heading text-sm font-semibold text-charcoal">
                  <MapPin className="h-4 w-4 text-teal" aria-hidden="true" /> {contact.addressTitle || "Address"}
                </dt>
                <dd className="text-ink">
                  {address.map((line) => (
                    <span key={line} className="block">
                      {line}
                    </span>
                  ))}
                </dd>
              </div>
            ) : null}
            {hours.length > 0 ? (
              <div className="flex gap-4 py-4">
                <dt className="flex w-32 shrink-0 items-center gap-2 font-heading text-sm font-semibold text-charcoal">
                  <Clock className="h-4 w-4 text-teal" aria-hidden="true" /> {contact.hoursTitle || "Hours"}
                </dt>
                <dd className="text-ink">
                  {hours.map((line) => (
                    <span key={line} className="block">
                      {line}
                    </span>
                  ))}
                </dd>
              </div>
            ) : null}
          </dl>
        </div>

        <div className="lg:col-span-7">
          {map ? (
            <figure>
              <div className="relative aspect-[4/3] overflow-hidden rounded-[4px] border border-line bg-white lg:aspect-[16/11]">
                <iframe
                  src={map}
                  title={contact.mapTitle || "Map"}
                  loading="lazy"
                  allowFullScreen
                  referrerPolicy="no-referrer-when-downgrade"
                  className="absolute inset-0 h-full w-full border-0"
                />
              </div>
              {contact.mapTitle ? <figcaption className="mt-3 text-sm text-muted">{contact.mapTitle}</figcaption> : null}
            </figure>
          ) : null}
        </div>
      </div>
    </section>
  );
}
