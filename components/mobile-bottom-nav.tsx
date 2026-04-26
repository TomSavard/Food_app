"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const ITEMS: { href: string; label: string; icon: string; match: (p: string) => boolean }[] = [
  { href: "/", label: "Recettes", icon: "📖", match: (p) => p === "/" },
  { href: "/meal-plan", label: "Semaine", icon: "📅", match: (p) => p.startsWith("/meal-plan") },
  { href: "/shopping", label: "Liste", icon: "🛒", match: (p) => p.startsWith("/shopping") },
  { href: "/ingredients", label: "Ingrédients", icon: "🧾", match: (p) => p.startsWith("/ingredients") },
  { href: "/reference", label: "Références", icon: "📚", match: (p) => p.startsWith("/reference") },
];

export function MobileBottomNav() {
  const pathname = usePathname() || "/";
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-40 glass-thin border-t md:hidden"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
      aria-label="Navigation principale"
    >
      <ul className="flex h-16 items-stretch justify-around">
        {ITEMS.map((it) => {
          const active = it.match(pathname);
          return (
            <li key={it.href} className="flex-1">
              <Link
                href={it.href}
                className={
                  "flex h-full flex-col items-center justify-center gap-0.5 text-[11px] transition " +
                  (active ? "text-primary font-medium" : "text-muted-foreground hover:text-foreground")
                }
              >
                <span aria-hidden className="text-lg leading-none">{it.icon}</span>
                <span>{it.label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
