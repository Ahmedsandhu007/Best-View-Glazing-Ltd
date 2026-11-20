"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { CheckCircle2, CircleAlert } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { serviceFormOptions } from "@/content/services";
import { UK_POSTCODE_RE, limits } from "@/lib/enquiry/validation";
import { trackEvent } from "@/lib/analytics";

type Copy = { title: string; intro: string; buttonLabel: string; note: string };
type Fields = { fullName: string; phone: string; postcode: string; service: string; description: string };
type Errors = Partial<Record<keyof Fields | "form", string>>;

const PHONE_RE = /^[+()\d\s-]{7,30}$/;

function validate(f: Fields): Errors {
  const e: Errors = {};
  if (!f.fullName.trim()) e.fullName = "Please enter your name.";
  else if (f.fullName.trim().length > limits.fullName) e.fullName = `Please keep your name under ${limits.fullName} characters.`;
  if (!f.phone.trim()) e.phone = "Please enter a phone number so we can call you back.";
  else if (!PHONE_RE.test(f.phone.trim())) e.phone = "Please enter a valid phone number.";
  if (!f.postcode.trim()) e.postcode = "Please enter the property postcode.";
  else if (!UK_POSTCODE_RE.test(f.postcode.trim())) e.postcode = "Please enter a valid UK postcode, for example SW1A 1AA.";
  if (!f.service) e.service = "Please choose a service.";
  if (f.description.length > limits.descriptionMax) e.description = `Please keep the message under ${limits.descriptionMax} characters.`;
  return e;
}

const inputClass =
  "w-full rounded-[4px] border border-line bg-white px-3 py-2.5 text-[0.9375rem] text-ink placeholder:text-muted/80 focus:border-teal focus:outline-none focus:ring-2 focus:ring-teal/25";
const labelClass = "block font-heading text-[0.8125rem] font-semibold text-charcoal";

/** The short quote form in the hero of a service page: name, phone, postcode, service (pre-selected), message. */
export function HeroQuoteForm({ defaultService, copy }: { defaultService: string; copy: Copy }) {
  const [fields, setFields] = useState<Fields>({ fullName: "", phone: "", postcode: "", service: defaultService, description: "" });
  const [errors, setErrors] = useState<Errors>({});
  const [status, setStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [reference, setReference] = useState("");
  const [serverMessage, setServerMessage] = useState("");
  const formRef = useRef<HTMLFormElement>(null);

  const set = (k: keyof Fields, v: string) => setFields((f) => ({ ...f, [k]: v }));

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const errs = validate(fields);
    setErrors(errs);
    if (Object.keys(errs).length) {
      formRef.current?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus();
      return;
    }
    setStatus("submitting");
    setServerMessage("");
    const body = new FormData();
    body.append("form", "short");
    (Object.keys(fields) as (keyof Fields)[]).forEach((k) => body.append(k, fields[k]));
    body.append("page", window.location.pathname);
    const honeypot = formRef.current?.elements.namedItem("company_website") as HTMLInputElement | null;
    body.append("company_website", honeypot?.value ?? "");
    try {
      const res = await fetch("/api/enquiry", { method: "POST", body });
      const data = (await res.json().catch(() => ({}))) as { ok?: boolean; reference?: string; message?: string; errors?: Errors };
      if (res.ok && data.ok && data.reference) {
        setReference(data.reference);
        setStatus("success");
        trackEvent("generate_lead", { form_id: "hero-form", page_path: window.location.pathname, service: fields.service });
        return;
      }
      if (data.errors) setErrors(data.errors);
      setServerMessage(data.message || "We could not send your enquiry just now. Please try again in a few minutes.");
      setStatus("error");
    } catch {
      setServerMessage("Your enquiry could not be sent because the connection failed. Please check your internet connection and try again.");
      setStatus("error");
    }
  }

  if (status === "success") {
    return (
      <div role="status" className="rounded-[4px] bg-white p-7 text-ink shadow-raised">
        <CheckCircle2 className="h-9 w-9 text-teal" strokeWidth={1.75} aria-hidden="true" />
        <h2 className="mt-3 font-heading text-xl font-bold text-charcoal">Thank you. Your enquiry has been received.</h2>
        <p className="mt-2 text-[0.9375rem]">
          Your reference is <strong className="font-semibold">{reference}</strong>. We will call you on the number you gave with the repair information and a
          quotation, or a few questions first.
        </p>
      </div>
    );
  }

  const err = (k: keyof Fields) => (errors[k] ? <p className="mt-1 text-sm text-red-700">{errors[k]}</p> : null);

  return (
    <form ref={formRef} onSubmit={onSubmit} noValidate aria-label="Quick quote form" className="rounded-[4px] bg-white p-6 text-ink shadow-raised sm:p-7">
      <h2 className="font-heading text-xl font-bold text-charcoal">{copy.title}</h2>
      {copy.intro ? <p className="mt-1.5 text-sm leading-relaxed text-muted">{copy.intro}</p> : null}
      {status === "error" && serverMessage ? (
        <p role="alert" className="mt-4 flex items-start gap-2 rounded-[4px] border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          {serverMessage}
        </p>
      ) : null}
      <div className="mt-4 grid gap-3.5 sm:grid-cols-2">
        <div>
          <label htmlFor="hq-name" className={labelClass}>
            Name
          </label>
          <input id="hq-name" name="fullName" autoComplete="name" className={`${inputClass} mt-1`} value={fields.fullName} onChange={(e) => set("fullName", e.target.value)} aria-invalid={Boolean(errors.fullName)} />
          {err("fullName")}
        </div>
        <div>
          <label htmlFor="hq-phone" className={labelClass}>
            Phone
          </label>
          <input id="hq-phone" name="phone" type="tel" autoComplete="tel" className={`${inputClass} mt-1`} value={fields.phone} onChange={(e) => set("phone", e.target.value)} aria-invalid={Boolean(errors.phone)} />
          {err("phone")}
        </div>
        <div>
          <label htmlFor="hq-postcode" className={labelClass}>
            Postcode
          </label>
          <input
            id="hq-postcode"
            name="postcode"
            autoComplete="postal-code"
            placeholder="e.g. SW1A 1AA"
            className={`${inputClass} mt-1 uppercase`}
            value={fields.postcode}
            onChange={(e) => set("postcode", e.target.value.toUpperCase())}
            aria-invalid={Boolean(errors.postcode)}
          />
          {err("postcode")}
        </div>
        <div>
          <label htmlFor="hq-service" className={labelClass}>
            Service
          </label>
          <select id="hq-service" name="service" className={`${inputClass} mt-1`} value={fields.service} onChange={(e) => set("service", e.target.value)} aria-invalid={Boolean(errors.service)}>
            <option value="">Choose a service</option>
            {serviceFormOptions.map((o) => (
              <option key={o} value={o}>
                {o}
              </option>
            ))}
          </select>
          {err("service")}
        </div>
        <div className="sm:col-span-2">
          <label htmlFor="hq-message" className={labelClass}>
            What is the problem? <span className="font-normal text-muted">(optional)</span>
          </label>
          <textarea id="hq-message" name="description" rows={2} className={`${inputClass} mt-1 resize-y`} value={fields.description} onChange={(e) => set("description", e.target.value)} aria-invalid={Boolean(errors.description)} />
          {err("description")}
        </div>
      </div>
      <div className="hidden" aria-hidden="true">
        <label htmlFor="hq-company-website">Company website</label>
        <input id="hq-company-website" name="company_website" tabIndex={-1} autoComplete="off" />
      </div>
      <Button type="submit" size="lg" disabled={status === "submitting"} aria-busy={status === "submitting"} className="mt-5 w-full">
        {status === "submitting" ? "Sending…" : copy.buttonLabel}
      </Button>
      <p className="mt-3 text-xs leading-relaxed text-muted">
        {copy.note} By sending this form you agree to our{" "}
        <Link href="/privacy-policy" className="underline underline-offset-2 hover:text-teal">
          privacy policy
        </Link>
        .
      </p>
    </form>
  );
}
