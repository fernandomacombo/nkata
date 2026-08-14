export default function CompactPageHeader({ title, children }) {
  return (
    <section className="nk-page-header">
      <div className="nk-shell nk-page-header__inner">
        <h1>{title}</h1>
        {children && <div className="nk-page-header__actions">{children}</div>}
      </div>
    </section>
  );
}
