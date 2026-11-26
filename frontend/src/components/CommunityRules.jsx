export const RULES_VERSION = "2026-11-26";

const rules = [
  ["Perfil", "Crie apenas uma conta, tenha pelo menos 18 anos e use a sua própria identidade. Indique a sua idade verdadeira e respeite a privacidade das pessoas que menciona.", "Profile", "You must be at least 18. Use one account, your own identity and your actual age. Respect the privacy of anyone you mention."],
  ["Fotografias", "Escolha fotografias suas. Na principal, mostre o rosto com clareza. Evite expor terceiros sem autorização. Não publique nudez, imagens íntimas, documentos, números de telefone, contactos de redes sociais ou códigos QR.", "Photos", "Use photos of yourself and show your face clearly in your main photo. Get permission from anyone else pictured. Keep nudity, intimate images, documents, phone numbers, social handles and QR codes out of your photos."],
  ["Conversas e chamadas", "Pergunte antes de ligar ou de enviar conteúdo pessoal. Respeite uma recusa, o silêncio e o bloqueio. Insultos, discriminação, ameaças e pressão para obter respostas, dinheiro ou intimidade violam estas regras.", "Chats and calls", "Ask before calling or sending personal content. Respect a refusal, silence or a block. Insults, discrimination, threats and pressure for replies, money or intimacy break these rules."],
  ["Publicações e segurança", "Estas regras também se aplicam a momentos, vídeos, áudios e comentários. Não divulgue conversas, imagens ou dados de outra pessoa sem autorização. São proibidos burlas, chantagem, spam e pedidos de códigos de acesso.", "Posts and safety", "These rules also cover moments, video, audio and comments. Get permission before sharing someone else’s messages, images or information. Scams, blackmail, spam and requests for access codes are prohibited."],
  ["Denúncias e moderação", "Se alguém o incomodar, pode bloquear ou denunciar o perfil. Indique o que aconteceu e evite divulgar dados sensíveis. A equipa pode retirar conteúdo ou restringir uma conta conforme a gravidade da situação. Se considerar que houve um engano, contacte o apoio.", "Reports and moderation", "You can block or report a profile. Describe what happened and avoid disclosing sensitive details. The team may remove content or restrict an account depending on the seriousness of the issue. Contact support if you think a decision was mistaken."],
];

export default function CommunityRules({ english = false }) {
  return (
    <details>
      <summary>{english ? "Read the NKATA community rules" : "Ler as regras da comunidade NKATA"}</summary>
      <small>{english ? "Version" : "Versão"} {RULES_VERSION}</small>
      {rules.map(([title, body, enTitle, enBody]) => (
        <p key={title}><strong>{english ? enTitle : title}</strong><br />{english ? enBody : body}</p>
      ))}
    </details>
  );
}
