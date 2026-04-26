/**
 * Bottom-nav icons — drawn in the same visual language as <Logo/>:
 * 24×24 viewBox, currentColor, 1.6 stroke, round caps/joins, 0.14
 * fill-opacity tint for bodies. One pure-SVG component per route.
 */

type IconProps = { size?: number; className?: string };

const STROKE = "1.6";

function Frame({ size = 24, className, children }: IconProps & { children: React.ReactNode }) {
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
      {children}
    </svg>
  );
}

/** Recettes — recipe card with a sprout in the corner. */
export function IconRecettes(props: IconProps) {
  return (
    <Frame {...props}>
      {/* card body tint */}
      <path
        d="M6 4h9l3 3v13H6z"
        fill="currentColor"
        fillOpacity="0.14"
      />
      {/* card outline + folded corner */}
      <path
        d="M6 4h9l3 3v13H6z M15 4v3h3"
        stroke="currentColor"
        strokeWidth={STROKE}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* recipe lines */}
      <path
        d="M9 12h6 M9 15h4"
        stroke="currentColor"
        strokeWidth={STROKE}
        strokeLinecap="round"
      />
      {/* small leaf accent */}
      <path
        d="M9 8.5c-.2-1.4.5-2.3 1.7-2.5.2 1.4-.5 2.3-1.7 2.5Z"
        fill="currentColor"
      />
    </Frame>
  );
}

/** Semaine — calendar with two binder tabs. */
export function IconSemaine(props: IconProps) {
  return (
    <Frame {...props}>
      {/* body tint */}
      <path
        d="M4 8h16v11H4z"
        fill="currentColor"
        fillOpacity="0.14"
      />
      {/* outline */}
      <path
        d="M4 8h16v11H4z M4 11h16"
        stroke="currentColor"
        strokeWidth={STROKE}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* binder tabs */}
      <path
        d="M8 5v4 M16 5v4"
        stroke="currentColor"
        strokeWidth={STROKE}
        strokeLinecap="round"
      />
      {/* highlighted day */}
      <circle cx="12" cy="15" r="1.4" fill="currentColor" />
    </Frame>
  );
}

/** Liste — shopping basket with handle. */
export function IconListe(props: IconProps) {
  return (
    <Frame {...props}>
      {/* basket body tint */}
      <path
        d="M4.5 10h15l-1.4 8.2a1.5 1.5 0 0 1-1.5 1.3H7.4a1.5 1.5 0 0 1-1.5-1.3z"
        fill="currentColor"
        fillOpacity="0.14"
      />
      {/* handle */}
      <path
        d="M8 10V8a4 4 0 0 1 8 0v2"
        stroke="currentColor"
        strokeWidth={STROKE}
        strokeLinecap="round"
      />
      {/* basket outline */}
      <path
        d="M4 10h16l-1.5 8.5a1.5 1.5 0 0 1-1.5 1.3H7a1.5 1.5 0 0 1-1.5-1.3z"
        stroke="currentColor"
        strokeWidth={STROKE}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* vertical weave */}
      <path
        d="M9 13v4 M12 13v4 M15 13v4"
        stroke="currentColor"
        strokeWidth={STROKE}
        strokeLinecap="round"
      />
    </Frame>
  );
}

/** Ingrédients — symmetric apple with a clearly visible leaf. */
export function IconIngredients(props: IconProps) {
  // Body path: symmetric around x=12. Fills the frame (y 6.5 → 20)
  // so the apple visually weighs the same as the other icons.
  const body =
    "M12 6.8 C13.9 5.2 17.6 5.6 18.9 8.6 C19.9 11.6 19.2 16.6 16 19.4 " +
    "C14.5 20.2 13 19.7 12 19.7 C11 19.7 9.5 20.2 8 19.4 " +
    "C4.8 16.6 4.1 11.6 5.1 8.6 C6.4 5.6 10.1 5.2 12 6.8 Z";
  return (
    <Frame {...props}>
      {/* apple body tint */}
      <path d={body} fill="currentColor" fillOpacity="0.14" />
      {/* apple outline */}
      <path
        d={body}
        stroke="currentColor"
        strokeWidth={STROKE}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* short stem */}
      <path
        d="M12 6.8 L12 4.4"
        stroke="currentColor"
        strokeWidth={STROKE}
        strokeLinecap="round"
      />
      {/* leaf — large teardrop tucked next to the stem */}
      <path
        d="M12 5.2 C13.6 2.9 17.0 2.6 18.4 3.7 C18.0 5.9 15.3 7.2 12 5.2 Z"
        fill="currentColor"
      />
    </Frame>
  );
}

/** Références — open book. */
export function IconReferences(props: IconProps) {
  return (
    <Frame {...props}>
      {/* page tint */}
      <path
        d="M3 6c2.5-1 6-1 9 .5 3-1.5 6.5-1.5 9-.5v12c-2.5-1-6-1-9 .5-3-1.5-6.5-1.5-9-.5z"
        fill="currentColor"
        fillOpacity="0.14"
      />
      {/* spine + page outlines */}
      <path
        d="M3 6c2.5-1 6-1 9 .5 3-1.5 6.5-1.5 9-.5v12c-2.5-1-6-1-9 .5-3-1.5-6.5-1.5-9-.5z M12 6.5v13"
        stroke="currentColor"
        strokeWidth={STROKE}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* text rules */}
      <path
        d="M5.5 10h4 M5.5 13h4 M14.5 10h4 M14.5 13h4"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
      />
    </Frame>
  );
}
