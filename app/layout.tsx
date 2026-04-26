import type { Metadata, Viewport } from "next";
import Link from "next/link";
import { GeistSans } from "geist/font/sans";
import "./globals.css";
import { ChatPanel } from "@/components/chat-panel";
import { Logo } from "@/components/logo";
import { MobileBottomNav } from "@/components/mobile-bottom-nav";
import {
  IconIngredients,
  IconListe,
  IconRecettes,
  IconReferences,
  IconSemaine,
} from "@/components/nav-icons";
import { ServiceWorkerRegister } from "@/components/sw-register";
import { ThemeScript } from "@/components/theme-script";
import { ThemeToggle } from "@/components/theme-toggle";

export const metadata: Metadata = {
  title: "MyFood",
  description: "Recipes, weekly meal planning, and shopping list.",
  manifest: "/manifest.json",
  icons: {
    icon: [
      { url: "/images/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/images/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: "/images/icon-192.png",
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#F8F4ED" },
    { media: "(prefers-color-scheme: dark)", color: "#161413" },
  ],
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" suppressHydrationWarning className={GeistSans.variable}>
      <head>
        <ThemeScript />
      </head>
      <body className="min-h-screen bg-background text-foreground antialiased font-sans">
        <header className="sticky top-0 z-40 glass-thin">
          <div className="container flex h-14 items-center justify-between">
            <Link href="/" className="flex items-center gap-2 font-semibold text-lg tracking-tight">
              <Logo size={28} className="text-primary" />
              <span>MyFood</span>
            </Link>
            <nav className="flex items-center gap-1 text-sm">
              <Link className="hidden md:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full hover:bg-accent/60 transition" href="/">
                <IconRecettes size={18} /> Recettes
              </Link>
              <Link className="hidden md:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full hover:bg-accent/60 transition" href="/meal-plan">
                <IconSemaine size={18} /> Semaine
              </Link>
              <Link className="hidden md:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full hover:bg-accent/60 transition" href="/shopping">
                <IconListe size={18} /> Liste
              </Link>
              <Link className="hidden md:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full hover:bg-accent/60 transition" href="/ingredients">
                <IconIngredients size={18} /> Ingrédients
              </Link>
              <Link className="hidden md:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full hover:bg-accent/60 transition" href="/reference">
                <IconReferences size={18} /> Références
              </Link>
              <ThemeToggle />
            </nav>
          </div>
        </header>
        <main className="container py-6 pb-24 md:pb-6">{children}</main>
        <MobileBottomNav />
        <ChatPanel />
        <ServiceWorkerRegister />
      </body>
    </html>
  );
}
