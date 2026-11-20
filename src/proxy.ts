import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { ADMIN_COOKIE, verifySessionToken } from "@/lib/adminAuth";
import settings from "@/content/settings.json";
import { allAreas, isPublishedArea } from "@/content/areas";
import redirectsData from "@/content/redirects.json";
import { buildRedirectMap, resolveRedirect, type Redirect } from "@/lib/redirects";

/**
 * Runs on every request except Next's static assets:
 * 1. URL hygiene: one address per page. A *.vercel.app host, an upper-case path or a
 *    trailing slash is sent to the canonical https://www host, lower-case, in ONE 308.
 *    The Redirects list (CMS) is applied next, chains already joined, then a district page
 *    switched off in the CMS ("Publish page") goes to /areas, all in the same hop.
 * 2. CMS gate: every /admin page and /api/admin route needs a valid session.
 */
export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon\\.ico).*)"],
};

/** Host of the live site: NEXT_PUBLIC_SITE_URL wins over the CMS "Live site address". */
function canonicalHost() {
  try {
    return new URL(process.env.NEXT_PUBLIC_SITE_URL ?? settings.url).host.toLowerCase();
  } catch {
    return "";
  }
}

const redirectMap = buildRedirectMap(redirectsData as Redirect[]);

/** Paths that keep their case and slash: uploads, Next internals, the API and files with an extension. */
function keepsCase(pathname: string) {
  return (
    pathname.startsWith("/uploads/") || pathname.startsWith("/_next/") || pathname.startsWith("/api/") || /\.[a-z0-9]+$/i.test(pathname)
  );
}

export async function proxy(req: NextRequest) {
  const url = req.nextUrl;
  const { pathname } = url;

  // --- 1. URL hygiene -------------------------------------------------------------------
  const host = (req.headers.get("host") ?? url.host).toLowerCase();
  const canonical = canonicalHost();
  const wantHost = host.endsWith(".vercel.app") && canonical && !canonical.endsWith(".vercel.app") ? canonical : host;

  let wantPath = pathname;
  if (!keepsCase(pathname)) {
    wantPath = pathname.toLowerCase();
    if (wantPath.length > 1 && wantPath.endsWith("/")) wantPath = wantPath.slice(0, -1);
  }
  const moved = resolveRedirect(redirectMap, wantPath);
  if (moved && /^https?:\/\//i.test(moved)) return NextResponse.redirect(new URL(moved), 308);
  if (moved) wantPath = moved;
  const district = wantPath.startsWith("/areas/") ? wantPath.slice("/areas/".length) : "";
  if (district && !district.includes("/") && !isPublishedArea(district) && allAreas.some((a) => a.slug === district)) {
    wantPath = "/areas";
  }

  if (wantHost !== host || wantPath !== pathname) {
    const target = new URL(url.toString());
    target.pathname = wantPath;
    if (wantHost !== host) {
      const want = new URL(`https://${wantHost}`);
      target.protocol = "https:";
      target.hostname = want.hostname;
      target.port = want.port;
    }
    return NextResponse.redirect(target, 308);
  }

  // --- 2. CMS gate ----------------------------------------------------------------------
  if (!pathname.startsWith("/admin") && !pathname.startsWith("/api/admin")) return NextResponse.next();

  // Always let the sign-in page and the auth endpoints through.
  if (pathname === "/admin/login" || pathname === "/api/admin/login" || pathname === "/api/admin/logout") {
    return NextResponse.next();
  }

  const authed = await verifySessionToken(req.cookies.get(ADMIN_COOKIE)?.value);
  if (authed) return NextResponse.next();

  if (pathname.startsWith("/api/")) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  return NextResponse.redirect(new URL("/admin/login", req.url));
}
