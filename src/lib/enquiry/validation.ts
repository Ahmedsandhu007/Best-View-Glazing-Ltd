/**
 * Enquiry form rules shared by the browser (instant feedback) and the API
 * route (authoritative check). No dependencies so it can run anywhere.
 */
import { contactTimeOptions, propertyTypeOptions, serviceFormOptions } from "@/content/services";

export const enquiryFieldNames = [
  "fullName",
  "email",
  "phone",
  "postcode",
  "address",
  "propertyType",
  "service",
  "description",
  "contactTime",
  "consent",
] as const;

export type EnquiryFieldName = (typeof enquiryFieldNames)[number];
export type EnquiryFields = Record<EnquiryFieldName, string>;
export type EnquiryErrors = Partial<Record<EnquiryFieldName | "files" | "form", string>>;

export const fileRules = {
  maxFiles: 3,
  maxBytes: 5 * 1024 * 1024,
  /** MIME types accepted from the browser. The server also checks file signatures. */
  mimeTypes: ["image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"],
  extensions: [".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"],
  get accept() {
    return [...this.mimeTypes, ...this.extensions].join(",");
  },
} as const;

export const limits = {
  fullName: 80,
  email: 160,
  phone: 30,
  postcode: 10,
  address: 240,
  descriptionMin: 20,
  descriptionMax: 2000,
} as const;

/** Standard UK postcode pattern (case-insensitive, optional space). */
export const UK_POSTCODE_RE =
  /^(GIR ?0AA|[A-PR-UWYZ]([0-9]{1,2}|([A-HK-Y][0-9]([0-9ABEHMNPRV-Y])?)|[0-9][A-HJKPS-UW]) ?[0-9][ABD-HJLNP-UW-Z]{2})$/i;

/** London postal districts plus the outer postcode areas that fall within Greater London. */
const LONDON_AREAS = ["EC", "WC", "NW", "SE", "SW", "E", "N", "W", "BR", "CR", "DA", "EN", "HA", "IG", "KT", "RM", "SM", "TW", "UB", "WD"];

export function normalisePostcode(value: string) {
  const compact = value.toUpperCase().replace(/\s+/g, "");
  if (compact.length < 5) return compact;
  return `${compact.slice(0, -3)} ${compact.slice(-3)}`;
}

/** Soft check used for an informational notice only; never blocks submission. */
export function isLikelyLondonPostcode(value: string) {
  const area = value.toUpperCase().replace(/\s+/g, "").match(/^[A-Z]{1,2}/)?.[0];
  if (!area) return true;
  return LONDON_AREAS.includes(area);
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const PHONE_RE = /^[+()\d\s-]{7,30}$/;

export function validateEnquiry(fields: EnquiryFields): EnquiryErrors {
  const errors: EnquiryErrors = {};
  const v = (k: EnquiryFieldName) => (fields[k] ?? "").trim();

  if (!v("fullName")) errors.fullName = "Please enter your full name.";
  else if (v("fullName").length > limits.fullName) errors.fullName = `Please keep your name under ${limits.fullName} characters.`;

  if (!v("email")) errors.email = "Please enter your email address.";
  else if (!EMAIL_RE.test(v("email")) || v("email").length > limits.email)
    errors.email = "Please enter a valid email address, for example name@example.co.uk.";

  if (v("phone") && !PHONE_RE.test(v("phone"))) errors.phone = "Please enter a valid phone number or leave this blank.";

  if (!v("postcode")) errors.postcode = "Please enter the property postcode.";
  else if (!UK_POSTCODE_RE.test(v("postcode"))) errors.postcode = "Please enter a valid UK postcode, for example SW1A 1AA.";

  if (v("address").length > limits.address) errors.address = `Please keep the address under ${limits.address} characters.`;

  if (!v("propertyType")) errors.propertyType = "Please select the property type.";
  else if (!(propertyTypeOptions as readonly string[]).includes(v("propertyType"))) errors.propertyType = "Please choose a property type from the list.";

  if (!v("service")) errors.service = "Please select the service you need.";
  else if (!(serviceFormOptions as readonly string[]).includes(v("service"))) errors.service = "Please choose a service from the list.";

  if (!v("description")) errors.description = "Please describe the problem so we can assess it.";
  else if (v("description").length < limits.descriptionMin)
    errors.description = `Please give a little more detail (at least ${limits.descriptionMin} characters).`;
  else if (v("description").length > limits.descriptionMax)
    errors.description = `Please keep the description under ${limits.descriptionMax} characters.`;

  if (!v("contactTime")) errors.contactTime = "Please tell us when you would prefer to be contacted.";
  else if (!(contactTimeOptions as readonly string[]).includes(v("contactTime"))) errors.contactTime = "Please choose a contact time from the list.";

  if (v("consent") !== "yes") errors.consent = "Please confirm you have read the privacy notice.";

  return errors;
}

export function validateFileList(files: { name: string; size: number; type: string }[]): string | undefined {
  if (files.length > fileRules.maxFiles) return `You can attach up to ${fileRules.maxFiles} images.`;
  for (const f of files) {
    const ext = f.name.toLowerCase().slice(f.name.lastIndexOf("."));
    const typeOk = (fileRules.mimeTypes as readonly string[]).includes(f.type) || (fileRules.extensions as readonly string[]).includes(ext);
    if (!typeOk) return `"${f.name}" is not a supported image. Please use JPG, PNG, WebP or HEIC files.`;
    if (f.size > fileRules.maxBytes) return `"${f.name}" is larger than 5 MB. Please choose a smaller image.`;
    if (f.size === 0) return `"${f.name}" appears to be empty.`;
  }
  return undefined;
}
