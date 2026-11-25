# Arquitectura proposta de media — estágio 67

## Inventário observado (25-11-2026)
Railway staging: nkata, Postgres e Redis, todos com último deploy SUCCESS,
região iad; domínio nkata-staging.up.railway.app, sem TCP proxy para nkata.
Não há serviço SFU/TURN neste ambiente. Não foram alterados serviços, DNS,
variáveis ou pagamentos. A branch de staging já acompanha fix/chats-proteger-historico;
commits podem desencadear o mecanismo existente de deploy automático.

## Decisão
Manter Django, PostgreSQL e Redis em Railway. O runtime actual exige IPv4
anunciado e porta UDP/TCP WebRTC. A documentação Railway descreve exposição
pública HTTP/HTTPS e TCP proxy, e UDP na rede privada. Não assumir UDP público.
Usar como referência um host Linux isolado para SFU e um relay TURN com IP
público e rede testada (podem ser co-localizados somente após teste de routing,
firewall e isolamento; não pressupor que funciona). Não reutilizar um host
de produção sem avaliação explícita. Nenhuma contratação nesta fase.

## Fluxos e portas
- Browser -> Railway staging HTTPS 443: sessão, tickets, créditos simulados.
- Browser -> SFU HTTPS/WSS 443: sinalização autenticada.
- Browser -> TURN 3478 UDP/TCP ou 5349 TLS/TCP: relay autenticado.
- TURN -> SFU 44444 UDP/TCP (somente transportes realmente suportados).
- SFU -> Railway staging HTTPS 443: admissão, leases e reconciliação HMAC.
- Porta 8085 do Node: somente loopback; não publicar.
- Relay: intervalo 49160–49200 UDP, restringir conforme configuração e
  resultado de testes. Bloquear destinos de relay que não sejam o SFU.
  Restringir acesso directo à porta SFU ao relay autorizado quando possível.
- Acesso administrativo somente por origem autorizada; firewall IPv4/IPv6
  e certificados válidos; não expor PostgreSQL nem Redis.

## Artefactos preparados
systemd.staging.service.example e nginx.staging.conf.example são modelos
para revisão; não executáveis sem configuração e não instalados.
coturn.staging.conf.example continua sujeito à verificação de routing e ACL.
Guardar segredos apenas em ficheiros de ambiente protegidos (0600) ou secret
manager. Nunca commitar valores. Não habilitar o serviço automaticamente.
O Nginx encaminha somente /signal; healthz fica local. A verificação de saúde
e as confirmações de staging ainda têm de ser executadas.

## Bloqueios
CI da etapa 66 ainda em fila na consulta; o artefacto de lockfiles ainda não
existe. Rever e versionar locks a partir do job aprovado; validar npm ci.
Não provisionar host, alterar Dockerfile ou ligar o frontend experimental
antes de CI aprovado, orçamento e host autorizados e ensaio de integração.
A autorização de instalação não equivale à autorização de produção.

Referências: https://docs.railway.com/networking/public-networking/specs-and-limits
https://docs.railway.com/networking/private-networking/how-it-works
https://docs.railway.com/networking/tcp-proxy
