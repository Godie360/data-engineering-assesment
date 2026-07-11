interface SelcomLogoProps {
  className?: string;
  color?: string;
}

// SVG recreation of the Selcom speech-bubble wordmark.
// Shape: thick-stroked rounded-rectangle speech bubble (tail bottom-left),
// "selcom" bold text inside — all in brand red #E2001A by default.
export default function SelcomLogo({ className = "", color = "#E2001A" }: SelcomLogoProps) {
  return (
    <svg
      viewBox="0 0 240 168"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="Selcom"
    >
      {/* Speech bubble body */}
      <path
        d="
          M 22 8
          H 218
          Q 234 8 234 24
          V 110
          Q 234 126 218 126
          H 108
          L 90 154
          L 78 126
          H 22
          Q 6 126 6 110
          V 24
          Q 6 8 22 8
          Z
        "
        stroke={color}
        strokeWidth="9"
        strokeLinejoin="round"
        strokeLinecap="round"
        fill="none"
      />
      {/* selcom wordmark */}
      <text
        x="120"
        y="88"
        textAnchor="middle"
        dominantBaseline="middle"
        fontFamily="'Arial Rounded MT Bold', 'Arial Black', Arial, sans-serif"
        fontWeight="900"
        fontSize="52"
        letterSpacing="-1"
        fill={color}
      >
        selcom
      </text>
    </svg>
  );
}
