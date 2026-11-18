# Best View Glazing Ltd – website

Lead-generation website for a fictional London window and door repair company.
Built with Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4 and Lucide icons.

## Run it

```bash
npm install
npm run dev        # http://localhost:3000
```

```bash
npm run build && npm start   # production build
npm run lint                 # ESLint
```

## Connect the enquiry form (required before launch)

The form posts to `/api/enquiry` (`src/app/api/enquiry/route.ts`). The route validates the
submission server-side, checks image signatures, then hands it to `src/lib/enquiry/deliver.ts`,
which picks a backend from environment variables. Copy `.env.example` to `.env.local` and set ONE:

| Backend | Variables |
| --- | --- |
| Webhook (Make, Zapier, n8n, CRM, own server) | `ENQUIRY_WEBHOOK_URL`, optional `ENQUIRY_WEBHOOK_SECRET` |
| Email via Resend | `RESEND_API_KEY`, `ENQUIRY_TO_EMAIL`, `ENQUIRY_FROM_EMAIL` |

Until one is configured the API answers `503` and the form shows an honest "not connected" message.
A success screen is only shown when the backend accepted the enquiry. To add another provider,
implement the `Provider` shape in `deliver.ts`.

Also set `NEXT_PUBLIC_SITE_URL` to the live domain (canonical URLs, Open Graph, sitemap, robots).

## Where things live

```
src/content/      business facts, navigation, services, areas, FAQs, testimonials, image register
src/components/   page sections (Header, Hero, TrustStrip, Introduction, Services, WhyChooseUs,
                  WorkingProcess, AreasWeCover, Testimonials, Pricing, FAQ, QuoteForm, Footer …)
src/components/ui Button, SectionHeading, PageHeader
src/lib/enquiry/  shared validation (client + server) and delivery providers
src/lib/seo.ts    structured-data builders (business, services, FAQ, breadcrumbs)
src/app/          routes: /, /services, /services/[slug], /about, /areas, /areas/[slug],
                  /faqs, /contact, /privacy-policy, /terms, sitemap, robots, icon, OG image
```

No copy or company facts are hard-coded in components; edit `src/content/*`.

## Before going live

- **Testimonials** – `src/content/testimonials.ts` holds clearly labelled placeholder quotes.
  Replace them with genuine, permissioned feedback and set `placeholder: false`. While any entry is
  a placeholder the section shows a "sample content" label and no star ratings.
- **Photography** – `src/content/images.ts` points at Unsplash photographs (free licence) chosen to
  match each subject. Swap any entry for the company's own photos by placing files in `/public` and
  updating `src`. Alt text lives alongside each image.
- **Legal pages** – the privacy policy and terms are sensible defaults for a form-only enquiry site
  and should be checked by the business before launch. No registration numbers, addresses, phone
  numbers, accreditations or opening hours are published anywhere, by design.
- **Structured data** – `HomeAndConstructionBusiness`, `Service`, `FAQPage` and `BreadcrumbList`
  schemas are emitted without address, telephone or coordinates. Add them in `src/lib/seo.ts`
  only once the business is happy to publish them.

## Form behaviour

- Required: name, email, postcode, property type, service, description, preferred contact time, consent.
- Optional: phone, full address, up to three images (JPG/PNG/WebP/HEIC, 5 MB each) with previews.
- UK postcode format validated; a non-blocking notice appears when the postcode looks outside Greater London.
- Client-side validation on blur and on submit, with an error summary, `aria-invalid` and focus management.
- Server-side re-validation, file signature sniffing, honeypot field and a light per-IP rate limit.

## Operations dashboard

The `dashboard/` folder holds the company's operations dashboard (a Python / FastAPI app, separate from the website).
It is not part of the Vercel build; see `dashboard/README.md` to run it and `dashboard/HOSTING.md` to host it.
