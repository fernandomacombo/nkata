import { useEffect, useState } from "react";
import { ArrowRight, UserRound } from "lucide-react";
import { normalizeProfile, request } from "../../services/api.js";
import "./discovery-panel.css";

const SUGGESTIONS_URL = "/api/descoberta/sugestoes/";
const QUESTION_URL = "/api/descoberta/pergunta/";

const reasonLabels = {
  same_goal: ["Procuram o mesmo tipo de relação", "You share a relationship goal"],
  preferred_city: ["Na cidade que prefere", "In your preferred city"],
  preferred_age: ["Na faixa etária que prefere", "In your preferred age range"],
};

export default function DiscoveryPanel({ english, onOpenProfile, onExplore }) {
  const [profiles, setProfiles] = useState(null);
  const [poll, setPoll] = useState(null);
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
      setPoll(await request(QUESTION_URL, { method: "POST", body: { date: poll.date, option } }));
    } catch {
      setVoteError(english ? "Could not vote. Refresh the page and try again." : "Não foi possível votar. Atualize a página e tente novamente.");
    } finally {
      setVoting(false);
    }
  }

  const totalVotes = poll?.counts?.reduce((total, count) => total + count, 0);
  return (
    <>
      {profiles && (
        <section className="nk-discovery-panel" aria-labelledby="nk-suggestions-title">
          <header>
            <h2 id="nk-suggestions-title">{english ? "Profiles for you" : "Perfis para si"}</h2>
            <button type="button" className="nk-discovery-link" onClick={onExplore}>
              {english ? "Explore all profiles" : "Explorar todos os perfis"} <ArrowRight size={16} />
            </button>
          </header>
          {profiles.length ? (
            <ul className="nk-discovery-profiles">
              {profiles.map((profile) => (
                <li key={profile.id}>
                  <button type="button" onClick={() => onOpenProfile(profile)}>
                    <span className="nk-discovery-portrait">
                      {profile.foto_url
                        ? <img src={profile.foto_url} loading="lazy" alt="" />
                        : <UserRound size={22} />}
                    </span>
                    <span>
                      <strong>{profile.nome_publico}, {profile.idade}</strong>
                      <small>{reasonLabels[profile.reasons[0]]?.[english ? 1 : 0]}</small>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p>{english ? "There are no suggestions based on your preferences yet." : "Ainda não há sugestões com base nas suas preferências."}</p>
          )}
        </section>
      )}

      {poll && (
        <section className="nk-discovery-panel" aria-labelledby="nk-poll-title">
          <h2 id="nk-poll-title">{english ? "Question of the day" : "Pergunta do dia"}</h2>
          <p>{poll.question[language]}</p>
          <div className="nk-discovery-votes" aria-live="polite">
            {poll.options.map((option, index) => {
              if (poll.choice === null) {
                return <button type="button" key={index} disabled={voting} onClick={() => vote(index)}>{option[language]}</button>;
              }
              const percentage = totalVotes ? Math.round(100 * poll.counts[index] / totalVotes) : 0;
              return (
                <div className={poll.choice === index ? "is-selected" : undefined} key={index}>
                  <span>{option[language]}{poll.choice === index && <small> · {english ? "Your vote" : "O seu voto"}</small>}</span>
                  <strong>{percentage}%</strong>
                </div>
              );
            })}
          </div>
          {poll.counts && <small>{totalVotes} {english ? (totalVotes === 1 ? "vote" : "votes") : (totalVotes === 1 ? "voto" : "votos")}</small>}
          {voteError && <p role="alert">{voteError}</p>}
        </section>
      )}
    </>
  );
}
