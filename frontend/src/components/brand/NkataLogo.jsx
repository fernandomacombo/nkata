export default function NkataLogo({ className = "", title = "" }) {
  return (
    <span
      className={`nk-logo-asset ${className}`.trim()}
      role={title ? "img" : undefined}
      aria-label={title || undefined}
      aria-hidden={title ? undefined : "true"}
    >
      <img src="/images/nkata-logo-original.png" alt="" draggable="false" />
    </span>
  );
}
