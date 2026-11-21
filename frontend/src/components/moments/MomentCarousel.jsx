import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, Pause, Play, Plus, UserRound } from "lucide-react";
import "./moment-carousel.css";

export default function MomentCarousel({ groups, loading, english, composerOpen, onCreate, onOpen }) {
  const viewport = useRef(null);
  const settleTimer = useRef(null);
  const cycle = useRef(0);
  const [looping, setLooping] = useState(false);
  const [paused, setPaused] = useState(false);
  const ids = groups.map((group) => group.profile.id).join(",");

  useLayoutEffect(() => {
    const element = viewport.current;
    const firstCard = element.firstElementChild;
    if (!firstCard) {
      setLooping(false);
      return undefined;
    }

    const measure = () => {
      const cardWidth = firstCard.getBoundingClientRect().width;
      const gap = parseFloat(getComputedStyle(element).columnGap);
      cycle.current = (cardWidth + gap) * groups.length;
      setLooping(cycle.current - gap > element.clientWidth + 1);
    };

    const observer = new ResizeObserver(measure);
    observer.observe(element);
    observer.observe(firstCard);
    measure();
    return () => observer.disconnect();
  }, [ids, looping, groups.length]);

  useLayoutEffect(() => {
    viewport.current.scrollLeft = looping ? cycle.current : 0;
    return () => window.clearTimeout(settleTimer.current);
  }, [ids, looping]);

  const advance = (direction) => {
    const element = viewport.current;
    if (looping && groups.length) {
      const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      element.scrollBy({ left: direction * cycle.current / groups.length, behavior: reducedMotion ? "auto" : "smooth" });
    }
  };

  useEffect(() => {
    if (!looping || paused || composerOpen) return undefined;
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const timer = window.setInterval(() => {
      const element = viewport.current;
      const carousel = element.closest(".nk-moment-carousel");
      if (!reducedMotion.matches && !document.hidden && !carousel.matches(":hover, :focus-within, :active")) {
        element.scrollBy({ left: cycle.current / groups.length, behavior: "smooth" });
      }
    }, 4200);
    return () => window.clearInterval(timer);
  }, [looping, paused, composerOpen, groups.length]);

  function settle() {
    if (!looping) return;
    window.clearTimeout(settleTimer.current);
    settleTimer.current = window.setTimeout(() => {
      const element = viewport.current;
      const distance = cycle.current;
      if (element.scrollLeft < distance - 1 || element.scrollLeft >= 2 * distance - 1) {
        element.scrollLeft = distance + ((element.scrollLeft % distance) + distance) % distance;
      }
    }, 140);
  }

  const previous = english ? "Previous profile" : "Perfil anterior";
  const next = english ? "Next profile" : "Perfil seguinte";
  const pause = paused ? (english ? "Play carousel" : "Retomar carrossel") : (english ? "Pause carousel" : "Pausar carrossel");
  const newMoment = english ? "New Moment" : "Novo Momento";

  return (
    <section className="nk-moment-carousel" aria-label={english ? "Recent Moments" : "Momentos recentes"}>
      <div className="nk-moment-carousel__row">
        <button type="button" className="nk-moment-carousel__create" onClick={onCreate} aria-expanded={composerOpen} aria-controls="nk-moment-composer">
          <span><Plus size={24} strokeWidth={1.7} /></span>
          <strong>{newMoment}</strong>
        </button>
        <div className="nk-moment-carousel__viewport" ref={viewport} onScroll={settle}>
          {(looping ? [0, 1, 2] : [1]).flatMap((copy) => groups.map((group) => (
            <button
              type="button"
              className="nk-moment-carousel__profile"
              key={`${copy}-${group.profile.id}`}
              tabIndex={copy === 1 ? undefined : -1}
              aria-hidden={copy === 1 ? undefined : true}
              onClick={() => onOpen(group)}
            >
              <span className="nk-moment-rail__ring">
                <span>
                  {group.profile.foto_url
                    ? <img src={group.profile.foto_url} alt="" loading="lazy" decoding="async" />
                    : <UserRound size={24} />}
                  {group.moments.some((item) => item.media_type === "VIDEO") && <em><Play size={10} fill="currentColor" /></em>}
                </span>
              </span>
              <strong>{group.mine ? (english ? "Yours" : "O seu") : group.profile.nome_publico}</strong>
              <small>{group.moments.length} {english ? (group.moments.length === 1 ? "Moment" : "Moments") : (group.moments.length === 1 ? "Momento" : "Momentos")}</small>
            </button>
          )))}
        </div>
        {!groups.length && <p className="nk-moment-carousel__empty">{loading
          ? (english ? "Loading Moments…" : "A carregar Momentos…")
          : (english ? "No active Moments" : "Nenhum Momento ativo")}</p>}
      </div>
      {looping && (
        <div className="nk-moment-carousel__controls">
          <button type="button" aria-label={previous} title={previous} onClick={() => advance(-1)}><ChevronLeft size={17} /></button>
          <button type="button" aria-label={pause} title={pause} onClick={() => setPaused((value) => !value)}>{paused ? <Play size={15} /> : <Pause size={15} />}</button>
          <button type="button" aria-label={next} title={next} onClick={() => advance(1)}><ChevronRight size={17} /></button>
        </div>
      )}
    </section>
  );
}
