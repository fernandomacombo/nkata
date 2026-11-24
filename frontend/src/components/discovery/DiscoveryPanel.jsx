import { useEffect, useState } from "react";
import { Check, ChevronRight, MessageCircle, Share2 } from "lucide-react";
import { normalizeProfile, request } from "../../services/api.js";
import "./discovery-panel.css";
import SuggestionStrip from "./SuggestionStrip.jsx";

const SUGGESTIONS_URL = "/api/descoberta/sugestoes/";
const QUESTION_URL = "/api/descoberta/pergunta/";

export default function DiscoveryPanel({ english, onOpenProfile, onExplore, canPublish, composerOpen, onCreate }) {
  const [profiles, setProfiles] = useState(null);
  const [poll, setPoll] = useState(null);
  const [showParticipation, setShowParticipation] = useState(false);
  const [showCounts, setShowCounts] = useState(false);
  const [voting, setVoting] = useState(false);
  const [voteError, setVoteError] = useState("");
  const language = english ? "en" : "pt";

  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;
    request(SUGGESTIONS_URL, { signal })
      .then((data) => setProfiles(data.results.map((profile) => ({ ...normalizeProfile(profile), reasons: profile.reasons }))))
      .catch(() => {});
    request(QUESTION_URL, { signal })
      .then(setPoll)
      .catch(() => {});
    return () => controller.abort();
  }, []);

  async function vote(option) {
    setVoting(true);
    setVoteError("");
    try {
      setPoll(await request(QUESTION_URL, { method: "POST", body: { date: poll.date, option, show_participation: showParticipation } }));
    } catch {
      setVoteError(english ? "Could not vote. Refresh the page and try again." : "Não foi possível votar. Atualize a página e tente novamente.");
    } finally {
      setVoting(false);
    }
  }

  const totalVotes = poll?.counts?.reduce((total, count) => total + count, 0);
  const participants = poll?.participants || [];
  const shareUrl = poll && new URL(`/pergunta-do-dia/${poll.date}/`, window.location.origin);
  if (shareUrl && english) shareUrl.searchParams.set("lang", "en");
  function avatar(person) {
    return person.photo
      ? <img src={person.photo} alt="" loading="lazy" />
      : <span aria-hidden="true">{person.name?.trim().charAt(0) || "·"}</span>;
  }
  return (
    <>
      <section className="nk-discovery-panel nk-discovery-panel--profiles" aria-labelledby="nk-suggestions-title">
          <header>
            <h2 id="nk-suggestions-title">{english ? "Profiles for you" : "Perfis para si"}</h2>
          </header>
          <SuggestionStrip
            profiles={profiles}
            english={english}
            canPublish={canPublish}
            composerOpen={composerOpen}
            onCreate={onCreate}
            onOpenProfile={onOpenProfile}
            onExplore={onExplore}
          />
        </section>

      {poll && (
        <section className="nk-discovery-panel nk-discovery-panel--poll" aria-labelledby="nk-poll-title">
          <header className="nk-discovery-poll-heading">
            <span aria-hidden="true"><MessageCircle size={17} /></span>
            <span className="nk-poll-label">{english ? "Question of the day" : "Pergunta do dia"}</span>
          </header>
          <h2 id="nk-poll-title">{poll.question[language]}</h2>
          {poll.choice === null && <label className="nk-poll-opt">
            <input type="checkbox" checked={showParticipation} disabled={voting}
              onChange={event => setShowParticipation(event.target.checked)} />
            {english ? "Show my profile in the voters list" : "Mostrar o meu perfil na lista de votantes"}
          </label>}
          <div className="nk-discovery-votes" aria-live="polite">
            {poll.options.map((option, index) => {
              if (poll.choice === null) {
                return <button type="button" key={index} disabled={voting} onClick={() => vote(index)}><span>{option[language]}</span><ChevronRight size={16} aria-hidden="true" /></button>;
              }
              const percentage = totalVotes ? Math.round(100 * poll.counts[index] / totalVotes) : 0;
              return (
                <div className={poll.choice === index ? "is-selected" : undefined} key={index} style={{ "--nk-vote-share": `${percentage}%` }}>
                  <span>{option[language]}{poll.choice === index && <small className="nk-poll-choice"><Check size={13} aria-hidden="true" />{english ? "Your vote" : "O seu voto"}</small>}</span>
                  <strong>{showCounts ? poll.counts[index] : percentage}{showCounts ? "" : "%"}</strong>
                </div>
              );
            })}
          </div>
          {poll.counts && <footer className="nk-poll-footer"><small>{totalVotes} {english ? (totalVotes === 1 ? "vote" : "votes") : (totalVotes === 1 ? "voto" : "votos")}</small><button type="button" onClick={() => setShowCounts(!showCounts)}>{showCounts ? (english ? "See percentages" : "Ver percentagens") : (english ? "See vote counts" : "Ver número de votos")}</button></footer>}
          <details className="nk-poll-people">
            <summary>
              <span className="nk-poll-faces" aria-hidden="true">{participants.slice(0, 3).map(person =>
                <span className="nk-poll-face" key={person.id}>{avatar(person)}</span>)}</span>
              {english ? "Visible voter profiles" : "Perfis de votantes visíveis"} ({participants.length})
            </summary>
            <p>{english
              ? "Every vote counts. Here you can see other members who chose to appear and whose profiles you can view."
              : "Todos os votos contam. Aqui aparecem os outros membros que escolheram mostrar a sua participação e cujo perfil pode visitar."}</p>
            {participants.length > 0 && <ul>{participants.map(person =>
              <li key={person.id}><a href={`/perfis/${person.id}/`}>
                <span className="nk-poll-face">{avatar(person)}</span>
                {person.name}<ChevronRight size={16} aria-hidden="true" />
              </a></li>)}</ul>}
          </details>
          <a className="nk-poll-share" href={`https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(shareUrl.href)}`}
            target="_blank" rel="noopener noreferrer"><Share2 size={16} aria-hidden="true" />
            {english ? "Share on Facebook" : "Partilhar no Facebook"}</a>
          {voteError && <p role="alert">{voteError}</p>}
        </section>
      )}
    </>
  );
}
