import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowRight, Pause, Play, Plus, UserRound } from "lucide-react";
import "./suggestion-strip.css";

const reasons = {
  same_goal: ["Mesmo objetivo", "Same relationship goal"],
  preferred_city: ["Cidade preferida", "Preferred city"],
  preferred_age: ["Faixa etária preferida", "Preferred age range"],
};

export default function SuggestionStrip({ profiles, english, canPublish, composerOpen, onCreate, onOpenProfile, onExplore }) {
  const strip = useRef(null);
  const position = useRef(0);
  const [paused, setPaused] = useState(false);
  const [overflowing, setOverflowing] = useState(false);

  const advance = useCallback(() => {
    const items = strip.current.children;
    if (items.length < 2) return;
    position.current = (position.current + 1) % items.length;
    const target = items[position.current];
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    strip.current.scrollTo({
      left: target.offsetLeft,
      behavior: reducedMotion ? "auto" : "smooth",
    });
  }, []);

  useEffect(() => {
    position.current = 0;
    const track = strip.current;
    const measure = () => setOverflowing(track.scrollWidth > track.clientWidth + 1);
    const observer = new ResizeObserver(measure);
    observer.observe(track);
    measure();
    return () => observer.disconnect();
  }, [profiles?.length]);

  useEffect(() => {
    if (paused || composerOpen || !overflowing) return undefined;
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const timer = window.setInterval(() => {
      const track = strip.current;
      if (!motion.matches && !document.hidden && track.scrollWidth > track.clientWidth &&
          !track.closest(".nk-suggestion-strip").matches(":hover, :focus-within, :active")) {
        advance();
      }
    }, 4500);
    return () => window.clearInterval(timer);
  }, [advance, composerOpen, paused, overflowing]);

  return (
    <section className="nk-suggestion-strip" aria-label={english ? "Profile suggestions" : "Sugestões de perfis"}>
      <div className="nk-suggestion-strip__row">
        <button
          type="button"
          className="nk-suggestion-strip__create"
          disabled={!canPublish}
          aria-controls="nk-feed-composer"
          aria-expanded={composerOpen}
          onClick={onCreate}
        >
          <span className="nk-suggestion-strip__plus"><Plus size={20} strokeWidth={1.7} /></span>
          <span>{english ? "New post" : "Nova publicação"}</span>
        </button>
        <div className="nk-suggestion-strip__track" ref={strip}>
          {profiles?.map((profile) => (
            <button type="button" className="nk-suggestion-strip__profile" key={profile.id} onClick={() => onOpenProfile(profile)}>
              {profile.foto_url
                ? <img src={profile.foto_url} alt="" loading="lazy" decoding="async" />
                : <span className="nk-suggestion-strip__placeholder"><UserRound size={22} /></span>}
              <strong title={profile.nome_publico}><span>{profile.nome_publico}</span><small>{profile.idade}</small></strong>
              <span className="nk-suggestion-strip__reason">{reasons[profile.reasons?.[0]]?.[english ? 1 : 0]}</span>
            </button>
          ))}
          <button type="button" className="nk-suggestion-strip__profile nk-suggestion-strip__explore" onClick={onExplore}>
            <ArrowRight size={22} aria-hidden="true" />
            <span>{english ? "Explore more" : "Explorar mais"}</span>
          </button>
        </div>
      </div>
      {overflowing && (
        <div className="nk-suggestion-strip__controls">
          <button type="button" aria-label={paused ? (english ? "Resume carousel" : "Retomar carrossel") : (english ? "Pause carousel" : "Pausar carrossel")} onClick={() => setPaused((value) => !value)}>{paused ? <Play size={15} /> : <Pause size={15} />}</button>
        </div>
      )}
    </section>
  );
}
