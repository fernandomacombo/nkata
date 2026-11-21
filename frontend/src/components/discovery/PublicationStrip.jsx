import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, Pause, Play, Plus } from "lucide-react";
import "./publication-strip.css";

export default function PublicationStrip({ publications, english, canPublish, composerOpen, onCreate }) {
  const strip = useRef(null);
  const position = useRef(0);
  const [paused, setPaused] = useState(false);

  const move = useCallback((direction) => {
    const items = strip.current.children;
    if (items.length < 2) return;
    position.current = (position.current + direction + items.length) % items.length;
    const target = items[position.current];
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    strip.current.scrollTo({
      left: target.offsetLeft,
      behavior: reducedMotion ? "auto" : "smooth",
    });
  }, []);

  useEffect(() => {
    position.current = 0;
  }, [publications.length]);

  useEffect(() => {
    if (paused || composerOpen || publications.length < 2) return undefined;
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const timer = window.setInterval(() => {
      const track = strip.current;
      if (!motion.matches && !document.hidden && track.scrollWidth > track.clientWidth &&
          !track.closest(".nk-publication-strip").matches(":hover, :focus-within, :active")) {
        move(1);
      }
    }, 4500);
    return () => window.clearInterval(timer);
  }, [composerOpen, move, paused, publications.length]);

  return (
    <section className="nk-publication-strip" aria-label={english ? "Recent posts" : "Publicações recentes"}>
      <div className="nk-publication-strip__row">
        <button
          type="button"
          className="nk-publication-strip__create"
          disabled={!canPublish}
          aria-controls="nk-feed-composer"
          aria-expanded={composerOpen}
          onClick={onCreate}
        >
          <Plus size={25} strokeWidth={1.6} />
          <span>{english ? "New post" : "Nova publicação"}</span>
        </button>
        <div className="nk-publication-strip__track" ref={strip}>
          {publications.map((post) => {
            const name = post.mine ? (english ? "Your post" : "A sua publicação") : post.profile.nome_publico;
            return (
              <button type="button" className="nk-publication-strip__post" key={post.id} onClick={() => document.getElementById(`nk-publication-${post.id}`)?.scrollIntoView({ block: "start" })}>
                {post.media_type === "VIDEO" ? (
                  <span className="nk-publication-strip__video" aria-hidden="true"><Play size={22} /></span>
                ) : <img src={post.media_url} alt="" loading="lazy" decoding="async" />}
                <strong title={name}>{name}</strong>
              </button>
            );
          })}
        </div>
      </div>
      {publications.length > 1 && (
        <div className="nk-publication-strip__controls">
          <button type="button" aria-label={english ? "Previous post" : "Publicação anterior"} onClick={() => move(-1)}><ChevronLeft size={17} /></button>
          <button type="button" aria-label={paused ? (english ? "Resume carousel" : "Retomar carrossel") : (english ? "Pause carousel" : "Pausar carrossel")} onClick={() => setPaused((value) => !value)}>{paused ? <Play size={15} /> : <Pause size={15} />}</button>
          <button type="button" aria-label={english ? "Next post" : "Publicação seguinte"} onClick={() => move(1)}><ChevronRight size={17} /></button>
        </div>
      )}
    </section>
  );
}
