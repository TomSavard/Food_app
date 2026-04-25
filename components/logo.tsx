/**
 * App logo — two herb leaves rising from a bowl.
 *
 * Single-color (uses currentColor for stroke + fill-opacity for the bowl
 * tint), so it adapts to light/dark theme and accent color automatically.
 * Pure SVG: scales cleanly from 16px favicon to 512px PWA icon.
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
      {/* Left leaf — rises up-left from the bowl rim */}
      <path
        d="M12 10.5C9.2 9.7 7.6 7.7 8 4.8c2.3.4 3.8 2.1 4 5.7Z"
        fill="currentColor"
      />
      {/* Right leaf — rises up-right from the bowl rim */}
      <path
        d="M12 10.5C14.8 9.7 16.4 7.7 16 4.8c-2.3.4-3.8 2.1-4 5.7Z"
        fill="currentColor"
      />
      {/* Bowl rim */}
      <path
        d="M3 11h18"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      {/* Bowl body — outline */}
      <path
        d="M4 11.6c.5 4.6 3.7 7.4 8 7.4s7.5-2.8 8-7.4"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Bowl body — soft tint fill */}
      <path
        d="M4 11.6c.5 4.6 3.7 7.4 8 7.4s7.5-2.8 8-7.4Z"
        fill="currentColor"
        fillOpacity="0.14"
      />
    </svg>
  );
}
