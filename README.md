# Best View Glazing Ltd – website and CMS

Lead-generation website for a London window and door repair company, with a built-in content
management system (CMS) at `/admin` so the company can edit every page's text and pictures.
Built with Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4 and Lucide icons.

## Run it

```bash
npm install
npm run dev        # http://localhost:3000  (CMS at /admin)
```

```bash
npm run build && npm start   # production build
npm run lint                 # ESLint
```

## The CMS (/admin)

Editors sign in at `/admin` with the password set in `ADMIN_PASSWORD`. Every piece of text and every
picture on the site is a field in one of the CMS sections; each section shows a small picture of where
its content appears on the page.

- **Site sections**: Site settings, Home page, Section headings, Page banners & copy, Photographs,
  Enquiry form, SEO titles & descriptions, Footer, Legal pages.
- **Lists** (add, edit, delete, reorder): Services, Areas we cover, Blog articles, Case studies, FAQs,
  Testimonials, Trust strip, Why choose us, How it works, Quotation factors.
- **Blog articles and case-study write-ups** use one big text box: paste from Google Docs or Word and
  headings, bullets, bold, italics and links are kept; "Insert image" uploads a picture into the text.
  By hand: `## ` heading, `- ` bullet, `**bold**`, `*italic*`, `[text](link)`.

How it saves:

- **Live site (GitHub mode)**, when `GITHUB_TOKEN` and `GITHUB_REPO` are set: each Save commits to the
  `cms-draft` branch (not built, see `vercel.json`). The **Publish** bar merges the draft into `main`,
  which Vercel rebuilds; **Discard** throws the drafts away. Uploaded pictures go to `public/uploads/`.
- **Local mode**, with no GitHub variables: Save writes straight to the JSON files in `src/content/`.
  Handy when editing on a PC; commit the result as usual.

The code: `src/lib/cms/registry.ts` (the sections and their fields), `validate.ts` and `limits.ts`
(the rules), `store.ts` + `src/lib/github.ts` (where content is read and written), `src/lib/adminAuth.ts`
and `src/proxy.ts` (sign-in and the gate on `/admin`), `src/app/api/admin/*` (the API),
`src/app/admin/*` and `src/components/admin/*` (the screens).

## Environment variables

Copy `.env.example` to `.env.local` locally; on Vercel add them under Project → Settings → Environment Variables.

| Variable | Needed for |
| --- | --- |
| `NEXT_PUBLIC_SITE_URL` | Canonical URLs, Open Graph, sitemap, robots |
| `ADMIN_PASSWORD`, `ADMIN_SESSION_SECRET` | CMS sign-in (both required) |
| `GITHUB_TOKEN`, `GITHUB_REPO` (+ optional `GITHUB_BRANCH`, `GITHUB_DRAFT_BRANCH`) | CMS publishing on the live site |
| `ENQUIRY_WEBHOOK_URL` (+ optional `ENQUIRY_WEBHOOK_SECRET`) | Enquiry form delivery, option A |
| `RESEND_API_KEY`, `ENQUIRY_TO_EMAIL`, `ENQUIRY_FROM_EMAIL` | Enquiry form delivery, option B |

Until a form backend is set the enquiry form shows an honest "not connected" message and never fakes success.

## Where things live

```
src/content/      JSON content the CMS edits, plus small loader modules the components import
src/components/   page sections (Header, Hero, TrustStrip, Introduction, Services, WhyChooseUs,
                  WorkingProcess, AreasWeCover, Testimonials, Pricing, FAQ, QuoteForm, Footer …)
src/components/admin  the CMS screens
src/lib/enquiry/  enquiry form validation (client + server) and delivery providers
src/lib/seo.ts    structured-data builders (business, services, FAQ, breadcrumbs)
src/app/(site)/   public routes: /, /services, /services/[slug], /about, /areas, /areas/[slug],
                  /case-studies, /case-studies/[slug], /blog, /blog/[slug], /faqs, /contact,
                  /privacy-policy, /terms
src/app/admin/    the CMS;  src/app/api/  the enquiry and CMS APIs
```

## Before going live

- **Testimonials** are sample content: edit them in the CMS and untick "Sample content" once genuine.
- **Photography** is Unsplash stock chosen to match each subject; replace through the CMS (upload or paste an image address).
- **Legal pages** are sensible defaults for a form-only enquiry site; the business should check them.
- No addresses, phone numbers, accreditations or opening hours are published anywhere, by design.
