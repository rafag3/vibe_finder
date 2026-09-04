export default function Header() {
  return (
    <header className="site-header">
      <a href="/" className="brand">
        <span className="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24"><path d="M12 3v10.55A4 4 0 1014 17V7h4V3h-6z" /></svg>
        </span>
        <span className="brand-word">vibe<span className="brand-word--accent">finder</span></span>
      </a>
    </header>
  );
}
