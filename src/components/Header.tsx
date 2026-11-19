"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";
import { Menu, X } from "lucide-react";
import { Logo } from "@/components/Logo";
import { Button } from "@/components/ui/Button";
import { navigation, site } from "@/content/site";

function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Header() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const panelId = useId();
  const toggleRef = useRef<HTMLButtonElement>(null);

  // On the home page the form is on the page itself; elsewhere go to the contact page.
  const quoteHref = pathname === "/" ? `#${site.enquiryFormId}` : site.enquiryPath;

  // Close the drawer whenever the route changes (state adjusted during render, per React guidance).
  const [lastPathname, setLastPathname] = useState(pathname);
  if (lastPathname !== pathname) {
    setLastPathname(pathname);
    setOpen(false);
  }

  // Escape closes; lock scroll while open.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        toggleRef.current?.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
    };
  }, [open]);

  return (
    <header className="sticky top-0 z-50 border-b border-line bg-white">
      <div className="container-site flex h-[72px] items-center justify-between gap-6">
        <Logo />

        <nav aria-label="Primary" className="hidden lg:block">
          <ul className="flex items-center gap-5 xl:gap-7">
            {navigation.map((item) => {
              const active = isActive(pathname, item.href);
              return (
                <li key={item.href} className={item.href === "/" ? "hidden xl:block" : ""}>
                  <Link
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={`relative whitespace-nowrap py-2 text-[0.9375rem] font-medium transition-colors hover:text-teal ${
                      active ? "text-teal" : "text-ink"
                    } after:absolute after:inset-x-0 after:-bottom-[25px] after:h-[2px] after:bg-teal after:transition-opacity ${
                      active ? "after:opacity-100" : "after:opacity-0"
                    }`}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="flex items-center gap-3">
          <div className="hidden sm:block">
            <Button href={quoteHref}>Request a Free Quote</Button>
          </div>
          <button
            ref={toggleRef}
            type="button"
            className="inline-flex h-11 w-11 items-center justify-center rounded-[4px] border border-line text-charcoal hover:bg-ivory lg:hidden"
            aria-expanded={open}
            aria-controls={panelId}
            aria-label={open ? "Close menu" : "Open menu"}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? <X className="h-5 w-5" aria-hidden="true" /> : <Menu className="h-5 w-5" aria-hidden="true" />}
          </button>
        </div>
      </div>

      {/* Mobile navigation drawer */}
      <div
        id={panelId}
        hidden={!open}
        className="absolute inset-x-0 top-full max-h-[calc(100dvh-72px)] overflow-y-auto border-b border-line bg-white shadow-raised lg:hidden"
      >
        <nav aria-label="Mobile" className="container-site py-4">
          <ul className="divide-y divide-line">
            {navigation.map((item) => {
              const active = isActive(pathname, item.href);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={`flex items-center justify-between py-3.5 text-base font-medium ${active ? "text-teal" : "text-ink"}`}
                    onClick={() => setOpen(false)}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
          <div className="mt-4 pb-2">
            <Button href={quoteHref} size="lg" className="w-full" onClick={() => setOpen(false)}>
              Request a Free Quote
            </Button>
          </div>
        </nav>
      </div>
      {open && (
        <button
          type="button"
          aria-label="Close menu"
          tabIndex={-1}
          className="fixed inset-0 top-[72px] -z-10 bg-charcoal/40 lg:hidden"
          onClick={() => setOpen(false)}
        />
      )}
    </header>
  );
}
