import { Mail } from "lucide-react";

export default function SocialLinks() {
  return (
    <nav className="nk-social-links" aria-label="Redes sociais e email do NKATA">
      <a href="https://www.facebook.com/profile.php?id=61593396540834" target="_blank" rel="noopener noreferrer">
        <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
          <circle cx="12" cy="12" r="12" fill="#0866ff" />
          <path fill="#fff" d="M13.6 24v-9h3l.5-3.5h-3.5V9.2c0-1 .3-1.7 1.8-1.7h1.9V4.4c-.3-.1-1.4-.2-2.7-.2-2.7 0-4.6 1.6-4.6 4.7v2.6H7V15h3v8.8c.7.1 1.3.2 2 .2z" />
        </svg>
        Facebook
      </a>
      <a href="https://www.instagram.com/nkata.date/" target="_blank" rel="noopener noreferrer">
        <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
          <rect width="24" height="24" rx="7" fill="#bc286c" />
          <g fill="none" stroke="#fff" strokeWidth="1.6">
            <rect x="5.2" y="5.2" width="13.6" height="13.6" rx="4" />
            <circle cx="12" cy="12" r="3.2" />
          </g>
          <circle cx="16.2" cy="7.8" r="1" fill="#fff" />
        </svg>
        Instagram
      </a>
      <a href="mailto:social@nkata.date">
        <Mail size={20} aria-hidden="true" />
        social@nkata.date
      </a>
    </nav>
  );
}
