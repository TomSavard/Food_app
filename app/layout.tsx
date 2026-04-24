import type { Metadata, Viewport } from "next";
import Link from "next/link";
import "./globals.css";
import { ChatPanel } from "@/components/chat-panel";
import { ServiceWorkerRegister } from "@/components/sw-register";

export const metadata: Metadata = {
  title: "Food App",
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
  themeColor: "#66BB6A",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className="dark">
      <body className="min-h-screen bg-background text-foreground antialiased">
        <header className="sticky top-0 z-40 border-b border-border/60 bg-background/80 backdrop-blur">
          <div className="container flex h-14 items-center justify-between">
            <Link href="/" className="flex items-center gap-2 font-semibold text-lg">
              <span className="text-primary">🍽️</span> Food App
            </Link>
            <nav className="flex items-center gap-2 text-sm">
              <Link className="px-3 py-1.5 rounded hover:bg-accent" href="/">
                📖 Recettes
              </Link>
              <Link className="px-3 py-1.5 rounded hover:bg-accent" href="/shopping">
                🛒 Liste
              </Link>
              <Link className="px-3 py-1.5 rounded hover:bg-accent" href="/ingredients">
                🧾 Ingrédients
              </Link>
            </nav>
          </div>
        </header>
        <main className="container py-6">{children}</main>
        <ChatPanel />
        <ServiceWorkerRegister />
      </body>
    </html>
  );
}
