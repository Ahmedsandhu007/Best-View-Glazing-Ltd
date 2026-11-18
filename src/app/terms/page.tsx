import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "@/components/ui/PageHeader";
import { site } from "@/content/site";

export const metadata: Metadata = {
  title: "Terms & Conditions",
  description: `Terms governing the use of the ${site.name} website and the quotations and repair services it describes.`,
  alternates: { canonical: "/terms" },
};

const sections = [
  {
    heading: "Use of this website",
    body: [
      "This website is provided by " + site.name + " for information about our window and door repair services and to allow you to request a quotation. By using the site you agree to these terms. If you do not agree, please do not use the site.",
      "You must not use the enquiry form to send unlawful, offensive or misleading content, or to attempt to interfere with the operation of the site.",
    ],
  },
  {
    heading: "Enquiries and quotations",
    body: [
      "Submitting an enquiry does not create a contract. We review each enquiry and, where we are able to help, respond with repair information and a quotation. A quotation is based on the information you provide and may be revised if the fault, the parts required or the access arrangements turn out to be different from what was described.",
      "Quotations are valid for the period stated on them. A contract for repair work is formed only when you accept a quotation and we confirm the arrangement in writing.",
    ],
  },
  {
    heading: "Carrying out the work",
    body: [
      "We will carry out agreed work with reasonable skill and care using appropriate parts and materials. Where a part is obsolete we will fit a suitable compatible equivalent and tell you so. Some repairs require a return visit once parts have been manufactured or sourced.",
      "You are responsible for providing safe access to the window or door and for telling us about anything at the property that could affect the work, such as asbestos, fragile surfaces or restrictions on working hours.",
    ],
  },
  {
    heading: "Service area",
    body: ["Our services are provided within Greater London only. We may decline enquiries for properties outside that area."],
  },
  {
    heading: "Accuracy of information",
    body: [
      "We take care to keep the information on this site accurate and up to date, but it is general in nature and is not a substitute for an assessment of your particular window or door. Descriptions of repairs are illustrative and the appropriate repair for your property will be set out in your quotation.",
    ],
  },
  {
    heading: "Liability",
    body: [
      "Nothing in these terms limits or excludes our liability for death or personal injury caused by negligence, for fraud, or for anything else that cannot be limited or excluded by law. Subject to that, we are not liable for any loss that was not a foreseeable result of our breaking these terms, or for business losses where you use our services as a consumer.",
    ],
  },
  {
    heading: "Intellectual property",
    body: ["The content, design and branding of this website belong to " + site.name + " or its licensors and may not be copied or reused without permission."],
  },
  {
    heading: "Governing law",
    body: ["These terms are governed by the law of England and Wales and any dispute will be dealt with by the courts of England and Wales."],
  },
];

export default function TermsPage() {
  return (
    <>
      <PageHeader eyebrow="Legal" title="Terms & Conditions" intro="The terms that apply to your use of this website and to the quotations and repair services it describes." crumbs={[{ label: "Terms & Conditions" }]} />
      <section className="section bg-white">
        <div className="container-site max-w-3xl">
          <p className="text-sm text-muted">Last updated: November 2026</p>
          {sections.map((s) => (
            <div key={s.heading} className="mt-10">
              <h2 className="text-2xl font-bold">{s.heading}</h2>
              <div className="prose-site mt-4 text-[1.0625rem] leading-relaxed text-ink">
                {s.body.map((p) => (
                  <p key={p.slice(0, 30)}>{p}</p>
                ))}
              </div>
            </div>
          ))}
          <p className="mt-12 border-t border-line pt-6 text-[0.9375rem] text-muted">
            See also our{" "}
            <Link href="/privacy-policy" className="font-medium text-teal underline underline-offset-4">
              Privacy Policy
            </Link>
            .
          </p>
        </div>
      </section>
    </>
  );
}
