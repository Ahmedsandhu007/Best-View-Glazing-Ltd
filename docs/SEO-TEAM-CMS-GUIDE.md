# Best View Glazing CMS: SEO team guide

As of 19 November 2026. The shareable copy with the publish-flow drawing is the Claude doc of the same name; this file is the version kept with the code.

## What the CMS is and where to find it

The CMS is the editing screen built into the website itself, at the site's address followed by `/admin`. Every piece of text and every picture on the site is a field in one of its sections, so nothing needs a developer.

- Address: `https://<the live domain>/admin`.
- Sign-in: one shared password, set by the site owner in Vercel as `ADMIN_PASSWORD`. Ask the owner for it.
- A session lasts 12 hours, then you sign in again.
- Each section opens with a small picture of the page showing where its fields appear. Read it the first time.
- Every text field shows a character counter such as `48/120`. Over the limit, Save is refused with a message naming the field.
- `View site` opens the live site in a new tab. `Sign out` ends the session.

## How a change reaches the live site

Saving never changes the live site. Only Publish does, and the site then rebuilds for a minute or two.

Edit a section → Save (draft, nothing live) → Publish (sends every draft) → Vercel builds (1 to 2 minutes) → live site. Discard drops every draft and returns to what is live.

- **Save**: stores the section as a draft. Save as often as you like.
- **Unpublished changes bar** (bottom of the screen): counts the drafts and names the sections they are in.
- **Publish**: sends every saved draft at once. Finish all open edits first. Allow one to two minutes, then refresh.
- **Discard**: throws away every unpublished draft. It asks for confirmation. No undo.
- Drafts are shared between editors; whoever presses Publish sends everyone's drafts. Agree who publishes.

## The sections and where each one shows

| Section | What it holds | Where it shows |
| --- | --- | --- |
| Site settings | Company name, short name, tagline, site description, service area name, live address, copyright line, profile links (sameAs), GA4 Measurement ID, GTM container ID, Ahrefs key, Search Console and Bing verification codes | Page titles, social previews, footer, structured data, tracking tags |
| Home page | Hero label, headline, text, two buttons, ticked lines, photo caption; introduction block | Home page, first two screens |
| Section headings | Label, title, intro line and button text for every block of the home page, the enquiry-form section and the teal call-to-action band | Home page and the band on inner pages |
| Page banners & copy | Dark banner of each inner page; About and Areas body text; FAQ, Blog and Case Studies closing banners | Top of the inner pages |
| Photographs | Home hero and intro photos, About photos, Areas photo, each with alt text | Those pages |
| Contact details | Phone, WhatsApp number and message, email, address, opening hours (shown and in Google's format), map, floating WhatsApp button | Contact page, footer, every page, structured data |
| Enquiry form | The dropdown choices: property type, service required, contact time; the line under Postcode; the optional outside-area notice | The enquiry form |
| Page banners & copy > Services page | Banner plus the line above the area links on every service page | Service pages |
| SEO titles & descriptions | Title and meta description per page; site keywords | Search results and browser tabs |
| Footer | Paragraph under the logo, column headings, bottom line | Every page |
| Legal pages | Privacy Policy and Terms text, dated sections | /privacy-policy, /terms |
| Services (list) | 14 services: card title, H1, summary, card photo, content sections (own H2s and photos), common faults, optional blocks, questions and answers, area links, form label, SEO title, meta description | Home grid, /services, one page per service |
| Service page blocks | Site-wide defaults for the quote form in the banner, the phone Call / WhatsApp bar and the optional blocks | Every service page |
| Areas we cover (list) | The regions (columns on the Areas page) | Home, /areas |
| Area pages (list) | One entry per town or district: region, Publish page switch, H1, intro, photo, content sections, nearby places, FAQs, SEO title and meta description | /areas, one page per town switched on |
| Blog articles (list) | Title, category, date, reading time, summary, picture, article, SEO fields | /blog, one page per article, three newest on the home page |
| Case studies (list) | Title, category, location, summary, description, picture, tags, results, write-up, sample flag | /case-studies, one page each, first three on the home page |
| FAQs (list) | Question and answer | Home page and /faqs |
| Testimonials (list) | Name, location, quote, stars, sample flag | Home page and /case-studies |
| Trust strip, Why choose us, How it works, Quotation factors (lists) | Short titled points in order | Home page blocks of the same name |
| Redirects (list) | Old address, new address, note | Visitors and search engines reaching an old address |

List order is site order: the Move up and Move down arrows change what visitors see.

## SEO fields, and what the site does on its own

**Page titles and meta descriptions** live in `SEO titles & descriptions`, one pair per page. Service pages take their SEO title from each entry in `Services`; blog articles have their own SEO fields at the bottom of each entry.

- The site adds ` | Best View Glazing Ltd` after every title except the home page's, so write titles without the company name. Aim for 50 to 60 characters before the suffix.
- Meta descriptions: 140 to 160 characters, a plain sentence with the service and the area in it.
- `Site keywords` feed the keywords meta tag only. Keep the list short and honest.

**Page addresses (slugs).** Every service, article, case study and district has a `Page address`, set from the title when it is created. Changing it moves the page, updates the sitemap and every generated link, and adds a rule under `Redirects` so the old address sends visitors to the new one in one hop. Links typed by hand inside article text still point at the old address; they work through the redirect, but update them when you can. Change an address of a live, indexed page only with a reason: rankings take time to follow.

**Headings.** The banner title is the H1. Section titles and `## ` lines inside an article are H2s. Do not type "H1" or "H2" into the text.

**Alt text.** Fill the description beside every picture in one plain phrase, for example `Timber sash windows on a Victorian terrace in Islington`. No keyword lists.

**Internal links.** In articles and write-ups, link with `[words](/services/sash-window-repairs)`. Same-site paths start with `/`; outside links start with `https://` and open in a new tab.

**Automatic, nothing to do:** sitemap and robots, canonical URLs, Open Graph and Twitter tags, structured data (business, services, FAQs, breadcrumbs, BlogPosting), `noindex` on `/admin`, and one address per page (upper-case paths, trailing slashes and the vercel.app address all redirect to the www address in one hop).

**Tracking.** Paste the GA4 Measurement ID, the Google Tag Manager container ID, the Ahrefs Web Analytics key and the Search Console and Bing verification codes into `Site settings` and publish. If the GTM container sends GA4 page views itself, leave the Measurement ID empty so views are not counted twice. GA4 then records page views, `phone_click`, `whatsapp_click`, `email_click` and `generate_lead` (quote form sent). Mark `generate_lead` as a key event in GA4.

## Publishing a blog article, step by step

1. Open `Blog articles` and press `New`. Type the final title: it becomes the slug.
2. Fill `Category`, `Date` (`19 November 2026`), `Reading time` (`5 min read`), `Summary`.
3. Add the picture (upload or an `https://` address) and its description.
4. Paste the article into the `Article` box from Google Docs or Word. Headings, bullets, bold, italics and links are kept. By hand: `## ` heading, `- ` bullet, `**bold**`, `*italic*`, `[words](link)`. For pictures inside the article, place the cursor and press `Insert image`. Keep paragraphs under 1,500 characters.
5. Fill `SEO title` and `Meta description` if the title or summary are not what search results should show.
6. Save, then check `/blog/<slug>` through `View site` on a phone-sized window.
7. Publish. Wait one to two minutes and check the live address.

The home page shows the first three entries, so keep the newest at the top with `Move up`. To unpublish, delete the entry and publish.

## Case studies, services, areas, testimonials, contact details

**Case studies.** `Category` is a fixed choice and doubles as the filter button. `Summary` goes on the card, `Description` at the top of the page, the optional `Full write-up` below. `Results` are up to three number-and-label pairs. The list ships empty: the home-page section, the Blog menu column and the /case-studies grid appear as soon as the first entry is saved. Add only verified projects, state only figures the company can stand behind, and use `Sample content` only for a draft you do not want to look real yet.

**Services.** `Card title` is the card and menu name; `H1` the page heading (empty = card title plus the service area); `Summary` the card text and banner intro. `Content sections` are the body, each with its own H2, paragraphs and an optional photo on the left or right. `Common faults` is the ticked list (empty = hidden). `Optional blocks` switch Why choose us, Benefits, Our process, What affects the cost, the banner quote form and the phone bar on or off for this service, and can override the site-wide heading, intro or points; the site-wide settings live under `Service page blocks`, where `{service}` in a heading becomes the service name. `Questions and answers` show with FAQ schema. `Where we carry out this work` takes the page addresses of published area pages (empty = block hidden). `Form label` must match a `Service required` choice in `Enquiry form` exactly. `Meta description` is per service; empty = built from the summary.

**Areas we cover and Area pages.** Regions are the columns on the Areas page and may be outside London. Each town or district is an entry under `Area pages`, a plain name on the Areas page until its `Publish page` switch is on. Off (the default): no page, no links, not in the sitemap, and the old `/areas/<slug>` address redirects to `/areas`. On: the page is live and linked on the next publish. Write the page first: `H1`, `Banner intro`, `Content sections` (each with its own H2, paragraphs and an optional photo), `Nearby places` (a name that matches another published area page becomes a link), `Questions and answers` (adds FAQ schema), `Photo`, `SEO title` and `Meta description`. All 35 London districts are off since 20 November 2026; switch one on only once it has unique content.

**Service FAQs.** Each service has its own `Questions and answers` list at the bottom of its entry. Filled in, they show on the service page with FAQ schema; empty, nothing shows.

**Testimonials.** The list ships empty and the section is hidden until the first entry is saved. Add verified reviews only. Tick `Sample content` on anything that is not a real review; stars are hidden and a notice shows until it is unticked.

**Contact details.** Phone, WhatsApp number (digits with country code), WhatsApp message, email, address, hours, map (an address or a Google Maps embed link), floating button. Empty values are hidden; an empty WhatsApp number removes every WhatsApp button. The shipped phone, WhatsApp, email, hours and map are placeholders. `Opening hours for Google` takes the same hours in Google's format (`Mo-Fr 08:00-18:00`) and feeds the structured data.

**Coverage wording.** No "Greater London only" text is fixed in the templates any more: the service area name is in `Site settings`, the line under the Postcode box is in `Enquiry form`, and the line above the area links on service pages is in `Page banners & copy > Services page`. The outside-area notice on the form is off while its field is empty.

## Pictures

- `Upload a picture` takes JPG, PNG, WebP, AVIF or SVG up to 4 MB; large photos are shrunk to 2,000 px and converted to WebP in the browser.
- Or paste an `https://` image address the company has rights to.
- Service cards are shown 16:10, case studies 4:3, blog cards 16:10, article headers 16:9. Landscape photos crop best.
- Fill the description beside every picture.
- Uploads appear on the live site after Save and Publish; they are kept forever, so name files sensibly before uploading.

## Before you press Publish

- [ ] Every section you touched is saved, with no red error under a field.
- [ ] No slug of a live page was changed.
- [ ] New articles and case studies have a picture, its description, a summary and a category.
- [ ] SEO title and meta description are set for any new page, within 60 and 160 characters.
- [ ] Links inside the text point at real pages and work in the preview.
- [ ] Nothing promises what the company has not agreed to: no guarantees, response times, prices, accreditations or review scores.
- [ ] Sample content is unticked only on genuinely real entries.
- [ ] You checked the page on `View site` on a phone-sized window.
- [ ] Nobody else has unpublished drafts they are not ready to send.

What not to do: do not edit `slug` on existing entries; do not delete the only entry in a list the home page relies on; do not paste whole web pages as an article; do not put the company name in page titles.

## When something looks wrong

| What you see | What it means | What to do |
| --- | --- | --- |
| Red banner: "GitHub connection problem" | The CMS cannot reach the site's code store | Tell the site owner; it is a host setting |
| "Content changed since you loaded it" | Someone else saved the same section | Reload, redo the edit, save |
| "… is too long (max 120)" | A limit was passed; nothing saved | Shorten and save again |
| Sign-in page appears while working | The 12-hour session ended | Sign in again; saved drafts are kept |
| Published, live page unchanged | Build takes 1 to 2 minutes; browser cache | Wait, then reload with Ctrl+F5 |
| Still unchanged after 5 minutes | Build failed or did not start | Tell the site owner (Vercel dashboard, repo Actions tab) |
| Picture upload refused | Over 4 MB, not an image, or an SVG with scripts | Export a smaller JPG or PNG |
| New district or article missing | Not published, or a bad slug | Check the unpublished-changes bar; slugs are lower-case words joined by hyphens |

A mistake can always be fixed by editing again and publishing, or by Discard before publishing. Site owner for anything outside the CMS: Ahmed (Alpha Digital Solutions).
