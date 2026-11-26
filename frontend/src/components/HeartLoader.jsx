import useInterfaceLanguage from "../hooks/useInterfaceLanguage.js";

const copy = {
  profile: ["A preparar este perfil para si", "As boas conexões começam aqui.", "Preparing this profile for you", "Good connections start here."],
  home: ["A preparar o seu espaço", "Há sempre algo novo para descobrir.", "Preparing your space", "There is always something new to discover."],
  discover: ["A descobrir novas pessoas", "Uma nova ligação pode começar hoje.", "Discovering new people", "A new connection could start today."],
  matches: ["A reunir as suas afinidades", "Descubra quem partilha os seus interesses.", "Gathering your matches", "Discover who shares your interests."],
  chats: ["A preparar as suas conversas", "As melhores ligações começam com um olá.", "Preparing your chats", "The best connections start with hello."],
  conversation: ["A abrir a sua conversa", "Cada mensagem aproxima duas pessoas.", "Opening your conversation", "Every message brings people closer."],
  moments: ["A descobrir novos momentos", "Pequenos instantes, grandes histórias.", "Discovering new moments", "Small moments, great stories."],
  notifications: ["A reunir as suas novidades", "Fique a par do que acontece no NKATA.", "Gathering your updates", "Stay up to date with NKATA."],
  account: ["A preparar a sua conta", "O seu espaço, as suas escolhas.", "Preparing your account", "Your space, your choices."],
  saved: ["A reunir os seus perfis guardados", "Reencontre quem despertou o seu interesse.", "Gathering your saved profiles", "Rediscover those who caught your interest."],
  identity: ["A preparar a sua verificação", "A sua segurança é importante para nós.", "Preparing your verification", "Your safety matters to us."],
  admin: ["A actualizar o painel", "A reunir informação da comunidade.", "Updating the dashboard", "Gathering community information."],
};

export default function HeartLoader({ page = "home", compact = false }) {
  const english = useInterfaceLanguage() === "EN";
  const labels = copy[page] || copy.home;
  const [heading, subtitle] = english ? labels.slice(2) : labels;
  return (
          <div className={compact ? "nk-heart-loader nk-heart-loader--compact" : "nk-heart-loader"} role="status" aria-live="polite">
            <div className="nk-heart-loader__brand" aria-hidden="true">NKATA</div>
            <div className="nk-heart-loader__animation" aria-hidden="true">
              <div className="nk-heart-loader__halo"/>
              <div className="nk-heart-loader__ring"/>
              <svg className="nk-heart-loader__heart" viewBox="0 0 48 48"><path d="M24 41C20 37 5 27 5 16C5 5 18 2 24 12C30 2 43 5 43 16C43 27 28 37 24 41Z" fill="#842442"/></svg>
              <div className="nk-heart-loader__particles">
                {[
                  [-72,-65,-24,0],[4,-96,10,.08],[76,-53,20,.12],[93,15,30,.05],
                  [52,71,15,.18],[-56,70,-15,.1],[-92,5,-30,.15],
                ].map(([x,y,rotation,delay],index) => (
                  <svg key={index} viewBox="0 0 48 48" style={{"--x":x+"px","--y":y+"px","--r":rotation+"deg","--d":delay+"s"}}>
                    <path d="M24 41C20 37 5 27 5 16C5 5 18 2 24 12C30 2 43 5 43 16C43 27 28 37 24 41Z" fill="currentColor"/>
                  </svg>
                ))}
              </div>
            </div>
            <div className="nk-heart-loader__heading">{heading}</div>
            <div className="nk-heart-loader__sub">{subtitle}</div>
            <div className="nk-heart-loader__progress" aria-hidden="true"><i/></div>
          </div>
  );
}
