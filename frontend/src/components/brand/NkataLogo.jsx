export default function NkataLogo({ className = "", title = "" }) {
  const labelled = Boolean(title);
  return (
    <svg
      className={className}
      viewBox="0 0 512 360"
      role={labelled ? "img" : undefined}
      aria-label={labelled ? title : undefined}
      aria-hidden={labelled ? undefined : "true"}
      focusable="false"
    >
      <path fill="#8b1736" d="M43 315V154C43 87 91 42 157 42c67 0 108 46 108 112v57L407 42h76L265 315V154c0-43-27-71-68-71-42 0-70 28-70 71v161H43Z" />
      <path fill="#625953" d="m337 213 48-49 99 151h-62c-19 0-34-8-45-24l-40-78Z" />
    </svg>
  );
}
