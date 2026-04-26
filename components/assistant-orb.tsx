"use client";

/**
 * Animated assistant orb.
 *
 * Layered look:
 *  - outer halo: blurred radial glow, breathes slowly
 *  - rotating ring: conic gradient sliced by a transparent ring mask
 *  - inner core: small bright dot, gentle breathing
 *
 * Idle is subtle (long durations); hover ramps every layer up.
 * No deps — pure SVG + CSS keyframes scoped via the `assistant-orb` group class.
 */
export function AssistantOrb({ size = 28 }: { size?: number }) {
  return (
    <span
      aria-hidden
      className="assistant-orb relative inline-flex items-center justify-center"
      style={{ width: size, height: size }}
    >
      <span className="halo absolute inset-[-30%] rounded-full" />
      <span className="ring absolute inset-0 rounded-full" />
      <span className="core absolute rounded-full" />
      <style jsx>{`
        .assistant-orb .halo {
          background: radial-gradient(
            circle at 50% 50%,
            rgba(180, 230, 200, 0.55),
            rgba(180, 230, 200, 0) 65%
          );
          filter: blur(6px);
          opacity: 0.65;
          animation: orb-breathe 4.5s ease-in-out infinite;
        }
        .assistant-orb .ring {
          background: conic-gradient(
            from 0deg,
            #34d399,
            #22d3ee,
            #a3e635,
            #34d399
          );
          mask: radial-gradient(circle, transparent 38%, black 42%, black 95%, transparent 100%);
          -webkit-mask: radial-gradient(circle, transparent 38%, black 42%, black 95%, transparent 100%);
          animation: orb-spin 14s linear infinite;
          opacity: 0.9;
        }
        .assistant-orb .core {
          width: 38%;
          height: 38%;
          background: radial-gradient(
            circle at 35% 30%,
            #ffffff 0%,
            #d1fae5 40%,
            #34d399 75%,
            #047857 100%
          );
          box-shadow:
            0 0 6px rgba(52, 211, 153, 0.6),
            inset 0 0 4px rgba(255, 255, 255, 0.6);
          animation: orb-pulse 3.2s ease-in-out infinite;
        }

        :global(.assistant-orb-host:hover) .assistant-orb .ring {
          animation-duration: 4.5s;
          opacity: 1;
        }
        :global(.assistant-orb-host:hover) .assistant-orb .halo {
          opacity: 0.95;
          animation-duration: 1.8s;
        }
        :global(.assistant-orb-host:hover) .assistant-orb .core {
          animation-duration: 1.5s;
          box-shadow:
            0 0 10px rgba(52, 211, 153, 0.85),
            inset 0 0 4px rgba(255, 255, 255, 0.8);
        }

        @keyframes orb-spin {
          to { transform: rotate(360deg); }
        }
        @keyframes orb-breathe {
          0%, 100% { transform: scale(1); }
          50%      { transform: scale(1.08); }
        }
        @keyframes orb-pulse {
          0%, 100% { transform: scale(0.92); }
          50%      { transform: scale(1.08); }
        }

        @media (prefers-reduced-motion: reduce) {
          .assistant-orb .halo,
          .assistant-orb .ring,
          .assistant-orb .core {
            animation: none !important;
          }
        }
      `}</style>
    </span>
  );
}
