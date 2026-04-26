"use client";

/**
 * Animated assistant orb — translucent, glassy, accent-tinted.
 *
 * Inspired by the Siri-style orb. Pure SVG + CSS. No background fill —
 * the orb is see-through, only the colored blobs + highlights + halo
 * make it visible. Uses the app's --primary HSL token so it picks up
 * the warm-sage accent in light theme and a brighter sage in dark.
 *
 * Layers (all inside one SVG so they compose with the goo filter):
 *  - 3 swirling blobs (radial gradients, accent color, ~50% alpha) drifting
 *    on different orbits with different durations.
 *  - Goo filter: blur + threshold so blobs merge and ripple at the edge,
 *    giving the fluid "metaball" look.
 *  - A subtle specular highlight (small white ellipse) for the glassy
 *    sphere illusion.
 *  - A separate CSS halo behind the SVG breathes slowly.
 *
 * Hover (`:hover` on `.assistant-orb-host` ancestor) ramps every layer.
 * `prefers-reduced-motion` freezes everything.
 */
export function AssistantOrb({ size = 56 }: { size?: number }) {
  return (
    <span
      aria-hidden
      className="assistant-orb relative inline-flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      <span className="halo absolute inset-[-25%] rounded-full" />
      <svg
        viewBox="0 0 100 100"
        className="orb-svg relative h-full w-full overflow-visible"
      >
        <defs>
          {/* Metaball goo: blur then steepen alpha to recover crisp blob edges. */}
          <filter id="orb-goo">
            <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="b" />
            <feColorMatrix
              in="b"
              mode="matrix"
              values="
                1 0 0 0 0
                0 1 0 0 0
                0 0 1 0 0
                0 0 0 18 -7"
            />
          </filter>
          <radialGradient id="orb-blob-a" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.85" />
            <stop offset="60%" stopColor="hsl(var(--primary))" stopOpacity="0.45" />
            <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="orb-blob-b" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity="0.7" />
            <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity="0" />
          </radialGradient>
          <radialGradient id="orb-spec" cx="35%" cy="30%" r="40%">
            <stop offset="0%" stopColor="white" stopOpacity="0.85" />
            <stop offset="60%" stopColor="white" stopOpacity="0.15" />
            <stop offset="100%" stopColor="white" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* Goo group — three blobs that drift independently. */}
        <g filter="url(#orb-goo)">
          <circle className="blob blob-1" cx="50" cy="50" r="22" fill="url(#orb-blob-a)" />
          <circle className="blob blob-2" cx="50" cy="50" r="18" fill="url(#orb-blob-b)" />
          <circle className="blob blob-3" cx="50" cy="50" r="14" fill="url(#orb-blob-a)" />
        </g>

        {/* Glassy specular highlight — outside the goo so it stays crisp. */}
        <ellipse className="spec" cx="38" cy="32" rx="14" ry="8" fill="url(#orb-spec)" />
      </svg>

      <style jsx>{`
        .halo {
          background: radial-gradient(
            circle,
            hsl(var(--primary) / 0.55),
            hsl(var(--primary) / 0) 65%
          );
          filter: blur(8px);
          opacity: 0.6;
          animation: orb-breathe 5s ease-in-out infinite;
        }

        .blob {
          transform-origin: 50px 50px;
          animation: var(--anim) ease-in-out infinite;
          mix-blend-mode: screen;
        }
        .blob-1 { --anim: orb-orbit-1 8s; }
        .blob-2 { --anim: orb-orbit-2 11s; animation-direction: reverse; }
        .blob-3 { --anim: orb-orbit-3 6s; }

        .spec {
          animation: orb-spec-shift 7s ease-in-out infinite;
          opacity: 0.9;
        }

        :global(.assistant-orb-host:hover) .halo {
          opacity: 0.95;
          animation-duration: 2s;
        }
        :global(.assistant-orb-host:hover) .blob-1 { animation-duration: 3s; }
        :global(.assistant-orb-host:hover) .blob-2 { animation-duration: 4s; }
        :global(.assistant-orb-host:hover) .blob-3 { animation-duration: 2.4s; }
        :global(.assistant-orb-host:hover) .spec  { animation-duration: 2.5s; }

        @keyframes orb-breathe {
          0%, 100% { transform: scale(1); }
          50%      { transform: scale(1.12); }
        }
        @keyframes orb-orbit-1 {
          0%   { transform: translate(-6px, -4px) scale(1.0); }
          25%  { transform: translate( 5px, -7px) scale(1.15); }
          50%  { transform: translate( 7px,  5px) scale(0.95); }
          75%  { transform: translate(-4px,  6px) scale(1.1); }
          100% { transform: translate(-6px, -4px) scale(1.0); }
        }
        @keyframes orb-orbit-2 {
          0%   { transform: translate( 4px,  5px) scale(1.05); }
          33%  { transform: translate(-6px,  3px) scale(0.9); }
          66%  { transform: translate(-3px, -6px) scale(1.15); }
          100% { transform: translate( 4px,  5px) scale(1.05); }
        }
        @keyframes orb-orbit-3 {
          0%   { transform: translate( 0,    0)  scale(1.0); }
          50%  { transform: translate( 3px, -3px) scale(1.2); }
          100% { transform: translate( 0,    0)  scale(1.0); }
        }
        @keyframes orb-spec-shift {
          0%, 100% { transform: translate(0, 0)         scale(1); opacity: 0.85; }
          50%      { transform: translate(4px, 2px)     scale(1.1); opacity: 1; }
        }

        @media (prefers-reduced-motion: reduce) {
          .halo, .blob, .spec { animation: none !important; }
        }
      `}</style>
    </span>
  );
}
