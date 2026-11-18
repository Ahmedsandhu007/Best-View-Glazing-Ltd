import { notFound } from "next/navigation";

/** Any address that matches no page renders the site's 404 inside the site layout (header and footer included). */
export default function CatchAll() {
  notFound();
}
