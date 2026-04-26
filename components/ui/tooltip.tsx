"use client";

import { ReactNode, useEffect, useRef, useState } from "react";

/**
 * Minimal tooltip — appears after a hover delay (default 1s), no cursor
 * change, no underline. Wraps any inline trigger.
 *
 * <Tooltip content="explanation">{trigger}</Tooltip>
 */
export function Tooltip({
  content,
  children,
  delay = 1000,
  side = "top",
}: {
  content: ReactNode;
  children: ReactNode;
  delay?: number;
  side?: "top" | "bottom";
}) {
  const [open, setOpen] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);

  function show() {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => setOpen(true), delay);
  }
  function hide() {
    if (timer.current) {
      clearTimeout(timer.current);
      timer.current = null;
    }
    setOpen(false);
  }

  return (
    <span
      className="relative inline-flex"
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      {children}
      <span
        role="tooltip"
        className={
          "pointer-events-none absolute left-1/2 z-50 -translate-x-1/2 whitespace-normal " +
          "rounded-md border bg-popover px-2.5 py-1.5 text-xs text-popover-foreground shadow-md " +
          "transition-opacity duration-150 " +
          (open ? "opacity-100" : "opacity-0") + " " +
          (side === "top" ? "bottom-full mb-2" : "top-full mt-2")
        }
        style={{ minWidth: 200, maxWidth: 320 }}
      >
        {content}
      </span>
    </span>
  );
}
