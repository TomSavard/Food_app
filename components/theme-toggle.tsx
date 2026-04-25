"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";

type Mode = "light" | "dark" | "system";

function currentDark(): boolean {
  return document.documentElement.classList.contains("dark");
}

function applyMode(mode: Mode) {
  const sys = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const dark = mode === "system" ? sys : mode === "dark";
  document.documentElement.classList.toggle("dark", dark);
  if (mode === "system") localStorage.removeItem("theme");
  else localStorage.setItem("theme", mode);
}

export function ThemeToggle() {
  const [mounted, setMounted] = useState(false);
  const [dark, setDark] = useState(false);

  useEffect(() => {
    setMounted(true);
    setDark(currentDark());

    // If user is on "system" (no explicit choice), follow live changes.
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      if (!localStorage.getItem("theme")) {
        document.documentElement.classList.toggle("dark", mq.matches);
        setDark(mq.matches);
      }
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  if (!mounted) {
    // Render a stable placeholder to keep header layout steady before hydration.
    return <Button size="icon" variant="ghost" className="h-9 w-9" aria-hidden />;
  }

  return (
    <Button
      size="icon"
      variant="ghost"
      className="h-9 w-9"
      aria-label={dark ? "Passer en mode clair" : "Passer en mode sombre"}
      onClick={() => {
        const next: Mode = dark ? "light" : "dark";
        applyMode(next);
        setDark(next === "dark");
      }}
    >
      {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </Button>
  );
}
