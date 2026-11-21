import { useEffect, useState } from "react";
import { MessageCircle } from "lucide-react";
import { normalizeProfile, request } from "../../services/api.js";
import "./discovery-panel.css";
import SuggestionStrip from "./SuggestionStrip.jsx";

const SUGGESTIONS_URL = "/api/descoberta/sugestoes/";
const QUESTION_URL = "/api/descoberta/pergunta/";

export default function DiscoveryPanel({ english, onOpenProfile, onExplore, canPublish, composerOpen, onCreate }) {
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
            <h2 id="nk-poll-title">{english ? "Question of the day" : "Pergunta do dia"}</h2>
          </header>
          <p>{poll.question[language]}</p>
          <div className="nk-discovery-votes" aria-live="polite">
            {poll.options.map((option, index) => {
              if (poll.choice === null) {
                return <button type="button" key={index} disabled={voting} onClick={() => vote(index)}>{option[language]}</button>;
              }
              const percentage = totalVotes ? Math.round(100 * poll.counts[index] / totalVotes) : 0;
              return (
                <div className={poll.choice === index ? "is-selected" : undefined} key={index} style={{ "--nk-vote-share": `${percentage}%` }}>
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
