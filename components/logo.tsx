/**
 * App logo — sage sprig in a bowl.
 *
 * Single-color (uses currentColor for stroke + fill-opacity for the bowl
 * tint), so it adapts to light/dark theme and accent color automatically.
 * Scales cleanly from favicon (16px) to PWA install icon (512px).
 */
export function Logo({
  size = 24,
  className,
}: {
  size?: number;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden
    >
      {/* Sprig stem */}
      <path
        d="M12 3.5v6"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      {/* Left leaf */}
      <path
        d="M12 6c-2.2 0-3.6 1.1-3.6 3.1 1.7 0 3.2-1 3.6-3.1Z"
        fill="currentColor"
      />
      {/* Right leaf */}
      <path
        d="M12 7.6c2.2 0 3.6 1 3.6 2.8-1.7 0-3.2-.9-3.6-2.8Z"
        fill="currentColor"
      />
      {/* Bowl rim */}
      <path
        d="M3 11h18"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      {/* Bowl body */}
      <path
        d="M4 11.6c.5 4.6 3.7 7.4 8 7.4s7.5-2.8 8-7.4"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M4 11.6c.5 4.6 3.7 7.4 8 7.4s7.5-2.8 8-7.4Z"
        fill="currentColor"
        fillOpacity="0.14"
      />
    </svg>
  );
}
