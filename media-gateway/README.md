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
