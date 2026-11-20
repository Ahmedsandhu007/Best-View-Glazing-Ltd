"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";
import { ChevronDown, Menu, X } from "lucide-react";
import { Logo } from "@/components/Logo";
import { Button } from "@/components/ui/Button";
import { MenuPanelContent } from "@/components/MegaMenus";
import { navigation, site, type NavItem } from "@/content/site";

function isActive(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

function groupActive(pathname: string, item: NavItem) {
  return isActive(pathname, item.href) || (item.children ?? []).some((c) => isActive(pathname, c.href));
}

const topLink = (active: boolean) =>
  `relative inline-flex items-center gap-1 whitespace-nowrap py-2 text-[0.9375rem] font-medium transition-colors hover:text-teal ${
    active ? "text-teal" : "text-ink"
  } after:absolute after:inset-x-0 after:-bottom-[25px] after:h-[2px] after:bg-teal after:transition-opacity ${active ? "after:opacity-100" : "after:opacity-0"}`;

export function Header() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false); // mobile drawer
  const [openMenu, setOpenMenu] = useState<string | null>(null); // desktop dropdown, keyed by the item href
  const panelId = useId();
  const toggleRef = useRef<HTMLButtonElement>(null);
  const navRef = useRef<HTMLElement>(null);

  // On the home page the form is on the page itself; elsewhere go to the contact page.
  const quoteHref = pathname === "/" ? `#${site.enquiryFormId}` : site.enquiryPath;

  // Close the drawer and any dropdown whenever the route changes (state adjusted during render, per React guidance).
  const [lastPathname, setLastPathname] = useState(pathname);
  if (lastPathname !== pathname) {
    setLastPathname(pathname);
    setOpen(false);
    setOpenMenu(null);
  }

  // Drawer: Escape closes; lock scroll while open.
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

  // Dropdown: Escape closes (focus returns to the menu label); a click or tap outside the nav closes.
  useEffect(() => {
    if (!openMenu) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      const nav = navRef.current;
      if (nav && nav.contains(document.activeElement)) {
        nav.querySelector<HTMLAnchorElement>(`a[href="${openMenu}"]`)?.focus();
      }
      setOpenMenu(null);
    };
    const onPointerDown = (e: PointerEvent) => {
      if (navRef.current && !navRef.current.contains(e.target as Node)) setOpenMenu(null);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointerDown);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointerDown);
    };
  }, [openMenu]);

  const closeMenu = () => setOpenMenu(null);

  return (
    <header className="sticky top-0 z-50 border-b border-line bg-white">
      <div className="container-site relative flex h-[72px] items-center justify-between gap-6">
        <Logo />

        <nav ref={navRef} aria-label="Primary" className="hidden self-stretch lg:block">
          <ul className="flex h-full items-center gap-6 xl:gap-8">
            {navigation.map((item) => {
              const active = groupActive(pathname, item);
              if (!item.children) {
                return (
                  <li key={item.href}>
                    <Link href={item.href} aria-current={isActive(pathname, item.href) ? "page" : undefined} className={topLink(active)}>
                      {item.label}
                    </Link>
                  </li>
                );
              }
              // A dropdown: the label opens its own page; hovering or focusing shows a panel.
              // It is state-driven so it closes on link click, route change, Escape, mouse-leave and clicks outside.
              // The li spans the full header height so the pointer never leaves it on the way down.
              // With a picture panel the menu is as wide as the header content; otherwise a plain list.
              const isOpen = openMenu === item.href;
              const dropdownClass = `z-50 transition-opacity ${isOpen ? "visible opacity-100" : "invisible opacity-0"}`;
              return (
                <li
                  key={item.href}
                  className={`flex h-full items-center ${item.panel ? "" : "relative"}`}
                  onMouseEnter={() => setOpenMenu(item.href)}
                  onMouseLeave={closeMenu}
                  onFocus={() => setOpenMenu(item.href)}
                  onBlur={(e) => {
                    if (!e.currentTarget.contains(e.relatedTarget as Node | null)) closeMenu();
                  }}
                  onClick={(e) => {
                    if ((e.target as Element).closest("a")) closeMenu();
                  }}
                >
                  <Link
                    href={item.href}
                    aria-current={isActive(pathname, item.href) ? "page" : undefined}
                    aria-expanded={isOpen}
                    className={topLink(active)}
                  >
                    {item.label}
                    <ChevronDown className={`h-4 w-4 text-muted transition-transform ${isOpen ? "rotate-180" : ""}`} aria-hidden="true" />
                  </Link>
                  {item.panel ? (
                    <div className={`absolute inset-x-0 top-full ${dropdownClass}`} aria-label={`${item.label} pages`}>
                      <div className="max-h-[calc(100vh-72px)] overflow-y-auto rounded-b-[4px] border border-t-0 border-line bg-white shadow-raised">
                        <MenuPanelContent panel={item.panel} />
                      </div>
                    </div>
                  ) : (
                    <div className={`absolute left-1/2 top-full -translate-x-1/2 ${dropdownClass}`}>
                      <ul className="min-w-[13rem] rounded-[4px] border border-line bg-white p-1.5 shadow-raised" aria-label={`${item.label} pages`}>
                        {item.children.map((child) => {
                          const childActive = isActive(pathname, child.href);
                          return (
                            <li key={child.href}>
                              <Link
                                href={child.href}
                                aria-current={childActive ? "page" : undefined}
                                className={`block rounded-[3px] px-3.5 py-2.5 text-[0.9375rem] font-medium transition-colors hover:bg-teal-tint hover:text-teal-dark ${
                                  childActive ? "bg-teal-tint text-teal-dark" : "text-ink"
                                }`}
                              >
                                {child.label}
                              </Link>
                            </li>
                          );
                        })}
                      </ul>
                    </div>
                  )}
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

      {/* Mobile navigation drawer: a group shows its own page, then its children indented. Every link closes it. */}
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
                  {item.children && (
                    <ul className="mb-2 border-l-2 border-line pl-4">
                      {item.children.map((child) => {
                        const childActive = isActive(pathname, child.href);
                        return (
                          <li key={child.href}>
                            <Link
                              href={child.href}
                              aria-current={childActive ? "page" : undefined}
                              className={`block py-2.5 text-[0.9375rem] ${childActive ? "font-medium text-teal" : "text-muted"}`}
                              onClick={() => setOpen(false)}
                            >
                              {child.label}
                            </Link>
                          </li>
                        );
                      })}
                    </ul>
                  )}
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
