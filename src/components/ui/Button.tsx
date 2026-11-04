import Link from "next/link";
import type { ComponentPropsWithoutRef, ReactNode } from "react";

type Variant = "primary" | "secondary" | "light" | "outlineLight";
type Size = "md" | "lg";

const base =
  "inline-flex items-center justify-center gap-2 rounded-[4px] font-heading font-semibold leading-none transition-colors duration-150 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 disabled:cursor-not-allowed disabled:opacity-60";

const variants: Record<Variant, string> = {
  primary: "bg-teal text-white hover:bg-teal-dark focus-visible:outline-teal",
  secondary: "border border-charcoal/25 bg-white text-charcoal hover:border-charcoal hover:bg-ivory focus-visible:outline-charcoal",
  light: "bg-white text-charcoal hover:bg-ivory focus-visible:outline-white",
  outlineLight: "border border-white/40 text-white hover:border-white hover:bg-white/10 focus-visible:outline-white",
};

const sizes: Record<Size, string> = {
  md: "h-11 px-5 text-[0.9375rem]",
  lg: "h-12 px-6 text-base",
};

type CommonProps = { variant?: Variant; size?: Size; className?: string; children: ReactNode };
type LinkProps = CommonProps & { href: string } & Omit<ComponentPropsWithoutRef<typeof Link>, "href" | "className">;
type NativeProps = CommonProps & { href?: undefined } & ComponentPropsWithoutRef<"button">;

function omit<T extends object, K extends keyof T>(obj: T, keys: readonly K[]): Omit<T, K> {
  const copy = { ...obj };
  for (const k of keys) delete copy[k];
  return copy;
}

export function Button(props: LinkProps | NativeProps) {
  const { variant = "primary", size = "md", className = "", children } = props;
  const classes = `${base} ${variants[variant]} ${sizes[size]} ${className}`;
  if (props.href !== undefined) {
    const rest = omit(props, ["href", "variant", "size", "className", "children"]);
    return (
      <Link href={props.href} className={classes} {...rest}>
        {children}
      </Link>
    );
  }
  const { type = "button" } = props;
  const rest = omit(props, ["href", "variant", "size", "className", "children", "type"]);
  return (
    <button type={type} className={classes} {...rest}>
      {children}
    </button>
  );
}
