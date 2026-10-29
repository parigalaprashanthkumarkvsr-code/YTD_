interface LogoProps {
  size?: number;
}

export function Logo({ size = 28 }: LogoProps) {
  return (
    <span
      role="img"
      aria-label="YTD"
      className="font-mono font-extrabold tracking-[-0.04em] select-none text-text"
      style={{ fontSize: size, lineHeight: 1 }}
    >
      YTD
      <span className="ytd-cursor text-accent" aria-hidden="true">
        _
      </span>
    </span>
  );
}
