"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { CheckCircle2, CircleAlert, ImagePlus, Info, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { contactTimeOptions, propertyTypeOptions, serviceFormOptions } from "@/content/services";
import {
  fileRules,
  isLikelyLondonPostcode,
  limits,
  UK_POSTCODE_RE,
  validateEnquiry,
  validateFileList,
  type EnquiryErrors,
  type EnquiryFieldName,
  type EnquiryFields,
} from "@/lib/enquiry/validation";

const ENDPOINT = "/api/enquiry";

type Status = "idle" | "submitting" | "success" | "error";

const emptyFields: EnquiryFields = {
  fullName: "",
  email: "",
  phone: "",
  postcode: "",
  address: "",
  propertyType: "",
  service: "",
  description: "",
  contactTime: "",
  consent: "",
};

const inputClass =
  "block w-full rounded-[4px] border border-line bg-white px-3.5 py-3 text-base text-ink placeholder:text-muted/60 transition-colors focus:border-teal focus:outline-none focus:ring-2 focus:ring-teal/25 aria-[invalid=true]:border-red-700";
const labelClass = "block font-heading text-[0.9375rem] font-semibold text-charcoal";

function Required() {
  return (
    <span className="text-red-700" aria-hidden="true">
      {" "}
      *
    </span>
  );
}

function FieldError({ id, message }: { id: string; message?: string }) {
  if (!message) return null;
  return (
    <p id={id} className="mt-1.5 flex items-start gap-1.5 text-sm text-red-700">
      <CircleAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      {message}
    </p>
  );
}

type Props = { defaultService?: string };

export function QuoteForm({ defaultService }: Props) {
  const [fields, setFields] = useState<EnquiryFields>({
    ...emptyFields,
    service: defaultService && (serviceFormOptions as readonly string[]).includes(defaultService) ? defaultService : "",
  });
  const [touched, setTouched] = useState<Partial<Record<EnquiryFieldName, boolean>>>({});
  const [errors, setErrors] = useState<EnquiryErrors>({});
  const [files, setFiles] = useState<File[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [serverMessage, setServerMessage] = useState<string>("");
  const [reference, setReference] = useState<string>("");
  const [submitAttempted, setSubmitAttempted] = useState(false);
  const formRef = useRef<HTMLFormElement>(null);
  const summaryRef = useRef<HTMLDivElement>(null);
  const successRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const previews = useMemo(
    () => files.map((f) => (f.type.startsWith("image/") && !/hei[cf]/.test(f.type) ? URL.createObjectURL(f) : null)),
    [files],
  );
  useEffect(() => () => previews.forEach((u) => u && URL.revokeObjectURL(u)), [previews]);

  const visibleErrors: EnquiryErrors = useMemo(() => {
    if (submitAttempted) return errors;
    const shown: EnquiryErrors = {};
    (Object.keys(errors) as (keyof EnquiryErrors)[]).forEach((k) => {
      if (k === "files" || k === "form" || touched[k as EnquiryFieldName]) shown[k] = errors[k];
    });
    return shown;
  }, [errors, touched, submitAttempted]);

  const update = (name: EnquiryFieldName, value: string) => {
    const next = { ...fields, [name]: value };
    setFields(next);
    if (touched[name] || submitAttempted) setErrors((prev) => ({ ...validateEnquiry(next), files: prev.files }));
  };

  const blur = (name: EnquiryFieldName) => {
    setTouched((t) => ({ ...t, [name]: true }));
    setErrors((prev) => ({ files: prev.files, ...validateEnquiry(fields) }));
  };

  const postcodeNotice =
    fields.postcode && UK_POSTCODE_RE.test(fields.postcode.trim()) && !isLikelyLondonPostcode(fields.postcode)
      ? "This postcode looks like it may be outside Greater London. We only carry out repairs within Greater London, but you can still send the enquiry and we will confirm whether we can help."
      : null;

  const addFiles = (list: FileList | null) => {
    if (!list) return;
    const merged = [...files, ...Array.from(list)].slice(0, fileRules.maxFiles);
    const err = validateFileList(merged.map((f) => ({ name: f.name, size: f.size, type: f.type })));
    setErrors((prev) => ({ ...prev, files: err }));
    setFiles(err ? files : merged);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const removeFile = (i: number) => {
    const next = files.filter((_, idx) => idx !== i);
    setFiles(next);
    setErrors((prev) => ({ ...prev, files: validateFileList(next.map((f) => ({ name: f.name, size: f.size, type: f.type }))) }));
  };

  const errorId = (name: string) => `quote-${name}-error`;
  const describedBy = (name: EnquiryFieldName, extra?: string) =>
    [visibleErrors[name] ? errorId(name) : null, extra].filter(Boolean).join(" ") || undefined;

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitAttempted(true);
    const fieldErrors = validateEnquiry(fields);
    const fileError = validateFileList(files.map((f) => ({ name: f.name, size: f.size, type: f.type })));
    const all: EnquiryErrors = { ...fieldErrors, ...(fileError ? { files: fileError } : {}) };
    setErrors(all);
    if (Object.keys(all).length > 0) {
      setStatus("idle");
      requestAnimationFrame(() => {
        const first = formRef.current?.querySelector<HTMLElement>('[aria-invalid="true"]');
        (first ?? summaryRef.current)?.focus();
        summaryRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
      });
      return;
    }

    setStatus("submitting");
    setServerMessage("");
    const body = new FormData();
    (Object.keys(fields) as EnquiryFieldName[]).forEach((k) => body.append(k, fields[k]));
    files.forEach((f) => body.append("images", f, f.name));
    body.append("page", window.location.pathname);
    const honeypot = formRef.current?.elements.namedItem("company_website") as HTMLInputElement | null;
    body.append("company_website", honeypot?.value ?? "");

    try {
      const res = await fetch(ENDPOINT, { method: "POST", body });
      const data = (await res.json().catch(() => ({}))) as { ok?: boolean; reference?: string; message?: string; errors?: EnquiryErrors };
      if (res.ok && data.ok && data.reference) {
        setReference(data.reference);
        setStatus("success");
        requestAnimationFrame(() => successRef.current?.focus());
        return;
      }
      if (data.errors) setErrors(data.errors);
      setServerMessage(data.message || "We could not send your enquiry just now. Please try again in a few minutes.");
      setStatus("error");
      requestAnimationFrame(() => summaryRef.current?.focus());
    } catch {
      setServerMessage("Your enquiry could not be sent because the connection failed. Please check your internet connection and try again.");
      setStatus("error");
      requestAnimationFrame(() => summaryRef.current?.focus());
    }
  }

  const reset = () => {
    setFields({ ...emptyFields, service: fields.service });
    setFiles([]);
    setErrors({});
    setTouched({});
    setSubmitAttempted(false);
    setStatus("idle");
    setReference("");
    setServerMessage("");
  };

  if (status === "success") {
    return (
      <div ref={successRef} tabIndex={-1} role="status" className="rounded-[4px] border border-line bg-white p-8 focus:outline-none md:p-10">
        <CheckCircle2 className="h-10 w-10 text-teal" strokeWidth={1.75} aria-hidden="true" />
        <h3 className="mt-4 font-heading text-2xl font-bold text-charcoal">Thank you. Your enquiry has been received.</h3>
        <p className="mt-3 text-ink">
          Your reference is <strong className="font-semibold">{reference}</strong>. Our team will review the details you have
          provided and respond to <strong className="font-semibold">{fields.email}</strong> with the relevant repair
          information and a quotation.
        </p>
        <p className="mt-3 text-[0.9375rem] text-muted">
          If you remember something useful, such as the make of the window or a better photograph, you are welcome to send a
          second enquiry quoting the reference above.
        </p>
        <div className="mt-6">
          <Button variant="secondary" onClick={reset}>
            Send another enquiry
          </Button>
        </div>
      </div>
    );
  }

  const summaryErrors = Object.entries(visibleErrors).filter(([, v]) => v);
  const showSummary = (submitAttempted && summaryErrors.length > 0) || status === "error";

  return (
    <form ref={formRef} onSubmit={onSubmit} noValidate className="rounded-[4px] border border-line bg-white p-6 sm:p-8 md:p-10" aria-describedby="quote-form-note">
      <p id="quote-form-note" className="text-sm text-muted">
        Fields marked <span className="text-red-700">*</span> are required.
      </p>

      <div
        ref={summaryRef}
        tabIndex={-1}
        role="alert"
        aria-live="assertive"
        className={`mt-5 rounded-[4px] border px-4 py-3 text-sm focus:outline-none ${showSummary ? "border-red-200 bg-red-50 text-red-800" : "hidden"}`}
      >
        {status === "error" && serverMessage ? (
          <p className="font-medium">{serverMessage}</p>
        ) : (
          <>
            <p className="font-medium">Please check the following before sending:</p>
            <ul className="mt-1.5 list-disc space-y-0.5 pl-5">
              {summaryErrors.map(([k, v]) => (
                <li key={k}>{v}</li>
              ))}
            </ul>
          </>
        )}
      </div>

      <div className="mt-6 grid gap-5 sm:grid-cols-2">
        <div>
          <label htmlFor="quote-fullName" className={labelClass}>
            Full name
            <Required />
          </label>
          <input
            id="quote-fullName"
            name="fullName"
            type="text"
            autoComplete="name"
            maxLength={limits.fullName}
            required
            value={fields.fullName}
            onChange={(e) => update("fullName", e.target.value)}
            onBlur={() => blur("fullName")}
            aria-invalid={Boolean(visibleErrors.fullName)}
            aria-describedby={describedBy("fullName")}
            className={`${inputClass} mt-1.5`}
          />
          <FieldError id={errorId("fullName")} message={visibleErrors.fullName} />
        </div>
        <div>
          <label htmlFor="quote-email" className={labelClass}>
            Email address
            <Required />
          </label>
          <input
            id="quote-email"
            name="email"
            type="email"
            autoComplete="email"
            inputMode="email"
            maxLength={limits.email}
            required
            value={fields.email}
            onChange={(e) => update("email", e.target.value)}
            onBlur={() => blur("email")}
            aria-invalid={Boolean(visibleErrors.email)}
            aria-describedby={describedBy("email")}
            className={`${inputClass} mt-1.5`}
          />
          <FieldError id={errorId("email")} message={visibleErrors.email} />
        </div>
        <div>
          <label htmlFor="quote-phone" className={labelClass}>
            Phone number <span className="font-normal text-muted">(optional)</span>
          </label>
          <input
            id="quote-phone"
            name="phone"
            type="tel"
            autoComplete="tel"
            inputMode="tel"
            maxLength={limits.phone}
            value={fields.phone}
            onChange={(e) => update("phone", e.target.value)}
            onBlur={() => blur("phone")}
            aria-invalid={Boolean(visibleErrors.phone)}
            aria-describedby={describedBy("phone")}
            className={`${inputClass} mt-1.5`}
          />
          <FieldError id={errorId("phone")} message={visibleErrors.phone} />
        </div>
        <div>
          <label htmlFor="quote-postcode" className={labelClass}>
            Postcode
            <Required />
          </label>
          <input
            id="quote-postcode"
            name="postcode"
            type="text"
            autoComplete="postal-code"
            maxLength={limits.postcode}
            placeholder="e.g. SW1A 1AA"
            required
            value={fields.postcode}
            onChange={(e) => update("postcode", e.target.value.toUpperCase())}
            onBlur={() => blur("postcode")}
            aria-invalid={Boolean(visibleErrors.postcode)}
            aria-describedby={describedBy("postcode", "quote-postcode-hint")}
            className={`${inputClass} mt-1.5 uppercase`}
          />
          <p id="quote-postcode-hint" className="mt-1.5 text-sm text-muted">
            We carry out repairs within Greater London only.
          </p>
          <FieldError id={errorId("postcode")} message={visibleErrors.postcode} />
          {postcodeNotice && !visibleErrors.postcode && (
            <p className="mt-2 flex items-start gap-1.5 rounded-[4px] border border-brass/50 bg-ivory px-3 py-2 text-sm text-ink" role="note">
              <Info className="mt-0.5 h-4 w-4 shrink-0 text-brass" aria-hidden="true" />
              {postcodeNotice}
            </p>
          )}
        </div>
        <div className="sm:col-span-2">
          <label htmlFor="quote-address" className={labelClass}>
            Full property address <span className="font-normal text-muted">(optional)</span>
          </label>
          <input
            id="quote-address"
            name="address"
            type="text"
            autoComplete="street-address"
            maxLength={limits.address}
            value={fields.address}
            onChange={(e) => update("address", e.target.value)}
            onBlur={() => blur("address")}
            aria-invalid={Boolean(visibleErrors.address)}
            aria-describedby={describedBy("address")}
            className={`${inputClass} mt-1.5`}
          />
          <FieldError id={errorId("address")} message={visibleErrors.address} />
        </div>
        <div>
          <label htmlFor="quote-propertyType" className={labelClass}>
            Property type
            <Required />
          </label>
          <select
            id="quote-propertyType"
            name="propertyType"
            required
            value={fields.propertyType}
            onChange={(e) => update("propertyType", e.target.value)}
            onBlur={() => blur("propertyType")}
            aria-invalid={Boolean(visibleErrors.propertyType)}
            aria-describedby={describedBy("propertyType")}
            className={`${inputClass} mt-1.5`}
          >
            <option value="">Select property type</option>
            {propertyTypeOptions.map((o) => (
              <option key={o} value={o}>
                {o}
              </option>
            ))}
          </select>
          <FieldError id={errorId("propertyType")} message={visibleErrors.propertyType} />
        </div>
        <div>
          <label htmlFor="quote-service" className={labelClass}>
            Service required
            <Required />
          </label>
          <select
            id="quote-service"
            name="service"
            required
            value={fields.service}
            onChange={(e) => update("service", e.target.value)}
            onBlur={() => blur("service")}
            aria-invalid={Boolean(visibleErrors.service)}
            aria-describedby={describedBy("service")}
            className={`${inputClass} mt-1.5`}
          >
            <option value="">Select a service</option>
            {serviceFormOptions.map((o) => (
              <option key={o} value={o}>
                {o}
              </option>
            ))}
          </select>
          <FieldError id={errorId("service")} message={visibleErrors.service} />
        </div>
        <div className="sm:col-span-2">
          <label htmlFor="quote-description" className={labelClass}>
            Description of the problem
            <Required />
          </label>
          <textarea
            id="quote-description"
            name="description"
            rows={5}
            minLength={limits.descriptionMin}
            maxLength={limits.descriptionMax}
            placeholder="For example: the handle on a uPVC bedroom window turns but the window will not lock, and the sash has dropped on one side."
            required
            value={fields.description}
            onChange={(e) => update("description", e.target.value)}
            onBlur={() => blur("description")}
            aria-invalid={Boolean(visibleErrors.description)}
            aria-describedby={describedBy("description", "quote-description-hint")}
            className={`${inputClass} mt-1.5 resize-y`}
          />
          <p id="quote-description-hint" className="mt-1.5 text-sm text-muted">
            Include the window or door type, how many units are affected and which floor they are on if you know.
          </p>
          <FieldError id={errorId("description")} message={visibleErrors.description} />
        </div>
        <div>
          <label htmlFor="quote-contactTime" className={labelClass}>
            Preferred contact time
            <Required />
          </label>
          <select
            id="quote-contactTime"
            name="contactTime"
            required
            value={fields.contactTime}
            onChange={(e) => update("contactTime", e.target.value)}
            onBlur={() => blur("contactTime")}
            aria-invalid={Boolean(visibleErrors.contactTime)}
            aria-describedby={describedBy("contactTime")}
            className={`${inputClass} mt-1.5`}
          >
            <option value="">Select a time</option>
            {contactTimeOptions.map((o) => (
              <option key={o} value={o}>
                {o}
              </option>
            ))}
          </select>
          <FieldError id={errorId("contactTime")} message={visibleErrors.contactTime} />
        </div>

        <div className="sm:col-span-2">
          <p className={labelClass} id="quote-images-label">
            Photographs of the window or door <span className="font-normal text-muted">(optional)</span>
          </p>
          <p id="quote-images-hint" className="mt-1 text-sm text-muted">
            Up to {fileRules.maxFiles} images, JPG, PNG, WebP or HEIC, 5 MB each. A photo of the fault and one of the whole unit is ideal.
          </p>
          <label
            htmlFor="quote-images"
            className="mt-2.5 flex cursor-pointer items-center justify-center gap-3 rounded-[4px] border border-dashed border-charcoal/30 bg-ivory px-4 py-6 text-[0.9375rem] text-ink transition-colors hover:border-teal hover:bg-teal-tint/50 focus-within:border-teal focus-within:ring-2 focus-within:ring-teal/25"
          >
            <ImagePlus className="h-5 w-5 text-teal" aria-hidden="true" />
            <span>
              <span className="font-heading font-semibold text-teal">Choose images</span> or drag them here
            </span>
            <input
              ref={fileInputRef}
              id="quote-images"
              name="images"
              type="file"
              multiple
              accept={fileRules.accept}
              onChange={(e) => addFiles(e.target.files)}
              disabled={files.length >= fileRules.maxFiles}
              aria-labelledby="quote-images-label"
              aria-describedby={visibleErrors.files ? `${errorId("files")} quote-images-hint` : "quote-images-hint"}
              aria-invalid={Boolean(visibleErrors.files)}
              className="sr-only"
            />
          </label>
          <FieldError id={errorId("files")} message={visibleErrors.files} />
          {files.length > 0 && (
            <ul className="mt-4 grid gap-3 xs:grid-cols-2 sm:grid-cols-3" aria-label="Selected images">
              {files.map((f, i) => (
                <li key={`${f.name}-${f.size}-${i}`} className="relative overflow-hidden rounded-[4px] border border-line bg-ivory">
                  {previews[i] ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={previews[i] as string} alt="" className="aspect-[4/3] w-full object-cover" />
                  ) : (
                    <div className="flex aspect-[4/3] items-center justify-center px-3 text-center text-sm text-muted">Preview not available for this format</div>
                  )}
                  <div className="flex items-center justify-between gap-2 px-2.5 py-2 text-xs text-ink">
                    <span className="truncate" title={f.name}>
                      {f.name}
                    </span>
                    <span className="shrink-0 text-muted">{Math.max(1, Math.round(f.size / 1024))} KB</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeFile(i)}
                    aria-label={`Remove ${f.name}`}
                    className="absolute right-1.5 top-1.5 inline-flex h-8 w-8 items-center justify-center rounded-[4px] bg-white/95 text-charcoal shadow-card hover:bg-white"
                  >
                    <X className="h-4 w-4" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="sm:col-span-2">
          <div className="flex items-start gap-3">
            <input
              id="quote-consent"
              name="consent"
              type="checkbox"
              required
              checked={fields.consent === "yes"}
              onChange={(e) => update("consent", e.target.checked ? "yes" : "")}
              onBlur={() => blur("consent")}
              aria-invalid={Boolean(visibleErrors.consent)}
              aria-describedby={describedBy("consent")}
              className="mt-1 h-5 w-5 shrink-0 rounded-[3px] border-line text-teal accent-teal focus:ring-teal"
            />
            <label htmlFor="quote-consent" className="text-[0.9375rem] leading-relaxed text-ink">
              I have read the{" "}
              <Link href="/privacy-policy" target="_blank" rel="noopener" className="font-medium text-teal underline underline-offset-4">
                Privacy Policy<span className="sr-only"> (opens in a new tab)</span>
              </Link>{" "}
              and agree to Best View Glazing Ltd storing the details I have provided in order to respond to my enquiry.
              <Required />
            </label>
          </div>
          <FieldError id={errorId("consent")} message={visibleErrors.consent} />
        </div>
      </div>

      {/* Honeypot: hidden from people, tempting to bots. */}
      <div className="hidden" aria-hidden="true">
        <label htmlFor="quote-company-website">Company website</label>
        <input id="quote-company-website" name="company_website" type="text" tabIndex={-1} autoComplete="off" defaultValue="" />
      </div>

      <div className="mt-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <Button type="submit" size="lg" disabled={status === "submitting"} aria-busy={status === "submitting"} className="w-full sm:w-auto">
          {status === "submitting" ? "Sending your enquiry…" : "Send my enquiry"}
        </Button>
        <p className="text-sm text-muted">Your details are used only to respond to this enquiry.</p>
      </div>
    </form>
  );
}
