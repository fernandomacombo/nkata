# NKATA — controlo de media (fase experimental)

O Django é a autoridade financeira. O gateway SFU deverá controlar os transportes WebRTC (mediasoup é a opção seleccionada para avaliação). Este directório contém um runtime experimental com mediasoup e WebSocket. **Não está pronto para publicar**, nem foi validado numa rede real.

- Endpoint exclusivamente de staging, desactivado por omissão; flag NKATA_MEDIA_GATEWAY_TEST_ENABLED e segredo separado NKATA_MEDIA_GATEWAY_SECRET (mínimo 32 caracteres; nunca VITE_).
- Configurar Redis partilhado entre workers, HTTPS, relógios sincronizados e ambiente de pagamentos simulados.
- Nunca criar consumidores activos antes da autorização. Autenticar cada participante e confirmar no SFU os dois transportes conectados. Não confiar em IDs, SDP, presença ou heartbeats reportados pelo browser.
- No final do minuto pausar a transmissão antes de solicitar novo débito. Desligar transportes se a autorização falhar. O relógio e a autorização têm de ser impostos no processo de media, não no cliente.
- Antes de disponibilizar chamadas: integrar sinalização autenticada, controlo de produtores/consumidores no SFU, watchdog independente para crash ou bloqueio do processo, revogação por bloqueio/desconexão, testes de rede e de interrupção real de RTP. A perda de resposta depois do débito precisa de reconciliação.
- Railway continua a alojar o backend; a infra de media necessita de rede UDP adequada, TLS e TURN. Não criar serviços pagos nem activar produção sem aprovação.

Documentação: https://mediasoup.org/documentation/v3/communication-between-client-and-server/

## Arranque experimental (host isolado)
- Node.js 22+, instalar dependências em media-gateway com npm install; gerar e rever package-lock.json, executar npm audit e testar o worker nativo antes de qualquer deploy.
- Definir NKATA_MEDIA_RUNTIME=isolated-staging, NKATA_STAGING_WEB_ORIGIN, NKATA_STAGING_API_ORIGIN, NKATA_MEDIA_GATEWAY_SECRET (igual ao backend de testes) e NKATA_MEDIA_ANNOUNCED_IP (IPv4 alcançável pelos clientes).
- O processo HTTP escuta apenas em 127.0.0.1:8085 (NKATA_SIGNAL_PORT); o proxy TLS deve encaminhar /signal (WSS) e, se necessário, /healthz. Nunca encaminhar HTTP sem TLS aos browsers.
- O servidor WebRTC escuta UDP e TCP na porta 44444 (NKATA_MEDIA_PORT); abrir exclusivamente as portas necessárias no host de testes. TURN com credenciais temporárias e cliente de media ainda pendentes.
- npm test; npm start. O teste unitário não substitui um ensaio de transmissão RTP real com dois dispositivos.
- Apenas créditos simulados. O runtime exige RTP de cada produtor antes da primeira autorização, mas isso não comprova que o destinatário ouviu ou viu a chamada. Ainda falta watchdog fora do processo Node, revogação e reconciliação financeira em falhas.


## Relay STUN/TURN experimental
- Endpoint autenticado POST /api/chats/chamadas/<uuid>/ice/ (apenas chamada ACEITE, participantes autorizados, HTTPS, staging isolado). Devolve ice_servers e expires_at; não consome créditos.
- Configurar NKATA_WEBRTC_TURN_SHARED_SECRET com segredo aleatório independente (mínimo 32 caracteres), igual ao static-auth-secret do coturn. Nunca partilhar com o gateway HMAC.
- NKATA_WEBRTC_TURN_URLS deve incluir turns: com TLS, mais turn: UDP/TCP conforme a rede. O novo endpoint não aceita credenciais estáticas nem funciona sem TURN configurado.
- O username inclui expiração, sessão e utilizador; a validade cobre o limite máximo acordado mais cinco minutos. TURN não interpreta a sessão NKATA nem revoga automaticamente alocações activas quando a chamada termina. O SFU deve fechar o transporte; o relay deve restringir destinos, quotas e tráfego.
- O ficheiro coturn.staging.conf.example é um modelo não executável até substituir os marcadores e validar a versão instalada. Restringir egress exclusivamente ao IP/porta do SFU de staging, incluindo IPv6; não expor redes internas. TLS válido e sincronização NTP obrigatórios.
- Testar UDP e TURN/TLS TCP, incluindo iceTransportPolicy=relay no cliente de testes. Verificar os pares ICE seleccionados, áudio/vídeo, desconexão e fim de saldo. Nenhum servidor TURN foi instalado nesta etapa.


## Validação nativa automatizada
O job media-native instala mediasoup, ws e mediasoup-client num runner isolado,
audita dependências e testa pacotes RTP sintéticos no worker C++.
O teste exige recepção em ambos os sentidos somente após autorização e fecho
dos consumidores quando a renovação é negada. Não usa contas nem dinheiro reais.
Ainda é necessário gerar/rever e versionar o lockfile, testar browsers com ICE/DTLS/TURN
reais e confirmar o watchdog independente; a passagem deste teste não autoriza deploy.


## Ensaio entre navegadores
O job media-native inclui um ensaio Chromium com dois contextos independentes,
microfone e câmara sintéticos, WSS com certificado efémero e coturn ligado
exclusivamente ao loopback do runner. Testa AUDIO e VIDEO, RTP nos consumidores,
frames de vídeo e encerramento após renovação negada com créditos simulados.
A permissão coturn de loopback é exclusiva do laboratório e não deve ser usada
em staging público ou produção. Este ensaio não cobre Django real, dispositivos
físicos, redes móveis, TURN/TLS público ou watchdog independente.


## Supervisor independente (Linux)
npm start executa supervisor.mjs, não server.mjs directamente. O supervisor
inicia o Node e o worker nativo num grupo de processos, exige uma resposta
de worker.dump a cada 250 ms e, após o arranque, termina o grupo com SIGKILL
se ficar mais de 1,25 s sem heartbeat (mais a latência do agendamento do SO).
O encerramento de todo o gateway é deliberado: afecta todas as chamadas
activas desse processo, em vez de deixar media a circular sem controlo.
Usar uma unidade systemd dedicada com KillMode=control-group, sem reinício
automático até reconciliar sessões e débitos, para limpar também os filhos
se o próprio supervisor falhar. O heartbeat não constitui uma garantia de
corte exacto no prazo financeiro: a aplicação ainda precisa de um watchdog
de leases individuais com prazo absoluto. Não publicar antes disso.

## Prazo financeiro independente
Cada autorização é registada por IPC no supervisor antes de retomar RTP. O
supervisor mede o prazo restante num relógio monotónico independente e mata
o grupo inteiro se um lease continuar registado no prazo. O controlador
antecipa a pausa em 750 ms; só limpa o registo após a confirmação de pausa
pelo SFU ou confirmação de remoção do router pelo worker. A renovação continua
a ser pedida no prazo anterior, não antecipadamente. A margem pode causar
uma breve pausa audível por minuto; é uma opção conservadora experimental.
O agendamento Linux não oferece garantias de tempo real; medir a latência
real de corte e testar falhas de IPC antes de publicar. Uma falha numa sala
pode interromper todas as chamadas do grupo; ainda não existe isolamento
por processo por chamada.


## Reconciliação financeira experimental
O gateway informa o Django, por pedido HMAC, somente se a tentativa de autorização
terminou sem invocar resume nesse minuto. A sessão é encerrada sob o mesmo bloqueio
transaccional da cobrança. Se houve débito, cria-se um movimento ESTORNO separado,
com chave idempotente; se o pedido de débito ainda não chegou, o encerramento impede
a cobrança tardia. O índice do minuto e o débito original não são modificados.
Falhas durante/após resume, perda integral do processo e ausência de confirmação
de entrega são casos ambíguos, não elegíveis para estorno automático por este fluxo.
As três tentativas de envio não substituem uma fila persistente. Falhas de envio
geram media_reconciliation_required; antes de produção é necessário registo
durável de activação e fila de revisão financeira. Não foram usados créditos reais.


## Evidência persistente por minuto
A migration 0057 cria um registo por minuto debitado, dentro da mesma transacção.
O gateway regista intenção de retoma antes de chamar resume e confirmação após
resposta do SFU. Após o prazo, autorizações ou intenções sem confirmação aparecem
no filtro Requer revisão da área Chamadas. O registo sobrevive à perda do processo.
Uma intenção incerta bloqueia estorno automático; a confirmação de resume não
prova recepção efectiva por uma pessoa. A fila é de consulta, sem ajuste manual,
sem gravação de chamadas e sem reprocessamento automático de casos ambíguos.
