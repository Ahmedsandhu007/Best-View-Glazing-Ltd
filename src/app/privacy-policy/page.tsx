import type { Metadata } from "next";
import Link from "next/link";
import { PageHeader } from "@/components/ui/PageHeader";
import { site } from "@/content/site";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: `How ${site.name} collects and uses the personal information you provide through this website.`,
  alternates: { canonical: "/privacy-policy" },
  robots: { index: true, follow: true },
};

const sections = [
  {
    heading: "Who we are",
    body: [
      `${site.name} ("we", "us") provides window and door repair services across Greater London. This policy explains how we handle personal information collected through this website.`,
    ],
  },
  {
    heading: "What we collect",
    body: [
      "When you submit the enquiry form we collect the details you enter: your name, email address, postcode, property type, the service you need, a description of the problem, your preferred contact time and, if you choose to provide them, your phone number, property address and photographs of the window or door.",
      "We also record the date and time of the enquiry, the page it was sent from and basic technical information such as the browser type, which helps us prevent misuse of the form.",
    ],
  },
  {
    heading: "Why we collect it and our lawful basis",
    body: [
      "We use this information to assess your enquiry, prepare and send a quotation, and arrange and carry out any repair you agree to. Our lawful basis is that the processing is necessary to take steps at your request before entering into a contract, and to perform that contract once work is agreed.",
      "We do not use your details for marketing and we do not sell or rent personal information to anyone.",
    ],
  },
  {
    heading: "Who we share it with",
    body: [
      "Your enquiry is delivered to us by the email or form-processing provider connected to this website, which processes it on our behalf under contract. Where a repair requires parts from a supplier we share only the technical details needed to source them, never your contact information.",
      "We may disclose information where the law requires it.",
    ],
  },
  {
    heading: "How long we keep it",
    body: [
      "Enquiries that do not lead to work are kept for up to 12 months so that we can respond to follow-up questions, then deleted. Records relating to work we have carried out are kept for the period required for accounting and warranty purposes, after which they are deleted or anonymised.",
    ],
  },
  {
    heading: "Photographs you upload",
    body: [
      "Images are used solely to understand the fault and prepare your quotation. Please avoid including people, documents or anything unrelated to the window or door in your photographs.",
    ],
  },
  {
    heading: "Cookies and analytics",
    body: [
      "This website does not set advertising or tracking cookies. If analytics or similar tools are introduced in future, this policy will be updated and any consent required will be requested before they are used.",
    ],
  },
  {
    heading: "Your rights",
    body: [
      "You have the right to access the personal information we hold about you, to have it corrected or deleted, to restrict or object to its processing, and to data portability where applicable. You also have the right to complain to the Information Commissioner's Office (ico.org.uk).",
      "To exercise any of these rights, send a request through the website enquiry form and we will respond within one month.",
    ],
  },
  {
    heading: "Changes to this policy",
    body: ["We may update this policy from time to time. The date of the latest revision is shown below."],
  },
];

export default function PrivacyPolicyPage() {
  return (
    <>
      <PageHeader eyebrow="Legal" title="Privacy Policy" intro="How we collect, use and protect the personal information you provide through this website." crumbs={[{ label: "Privacy Policy" }]} />
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
            Questions about this policy can be sent through the{" "}
            <Link href={site.enquiryPath} className="font-medium text-teal underline underline-offset-4">
              enquiry form
            </Link>
            .
          </p>
        </div>
      </section>
    </>
  );
}
