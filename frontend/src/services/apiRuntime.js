export function resolveApiBaseUrl(configuredBaseUrl, location) {
  const protocol = String(location?.protocol || "");
  const origin = String(location?.origin || "").replace(/\/$/, "");

  // Em HTTPS, a aplicação e a API partilham sempre a mesma origem. Além de
  // simplificar a produção, isto mantém sessão e CSRF no mesmo domínio e evita
  // que localhost e o IP da rede criem pedidos cross-origin acidentalmente.
  if (protocol === "https:") return origin;

  const configured = String(configuredBaseUrl || "").trim().replace(/\/$/, "");
  if (configured) return configured;

  const hostname = String(location?.hostname || "localhost");
  return `${protocol || "http:"}//${hostname}:8000`;
}
