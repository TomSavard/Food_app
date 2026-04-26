"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  IconIngredients,
  IconListe,
  IconRecettes,
  IconReferences,
  IconSemaine,
} from "@/components/nav-icons";

type Item = {
  href: string;
  label: string;
  Icon: (p: { size?: number; className?: string }) => React.ReactElement;
  match: (p: string) => boolean;
};

const ITEMS: Item[] = [
  { href: "/", label: "Recettes", Icon: IconRecettes, match: (p) => p === "/" },
  { href: "/meal-plan", label: "Semaine", Icon: IconSemaine, match: (p) => p.startsWith("/meal-plan") },
  { href: "/shopping", label: "Liste", Icon: IconListe, match: (p) => p.startsWith("/shopping") },
  { href: "/ingredients", label: "Ingrédients", Icon: IconIngredients, match: (p) => p.startsWith("/ingredients") },
  { href: "/reference", label: "Références", Icon: IconReferences, match: (p) => p.startsWith("/reference") },
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
        {ITEMS.map(({ href, label, Icon, match }) => {
          const active = match(pathname);
          return (
            <li key={href} className="flex-1">
              <Link
                href={href}
                className={
                  "flex h-full flex-col items-center justify-center gap-1 text-[11px] transition " +
                  (active ? "text-primary font-medium" : "text-muted-foreground hover:text-foreground")
                }
              >
                <Icon size={22} />
                <span>{label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
