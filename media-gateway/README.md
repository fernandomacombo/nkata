# NKATA — controlo de media (fase experimental)

O Django é a autoridade financeira. O gateway SFU deverá controlar os transportes WebRTC (mediasoup é a opção seleccionada para avaliação). Este directório contém o cliente HMAC e a lógica de autorização/fecho, **não** um SFU completo, nem um serviço pronto para publicar.

- Endpoint exclusivamente de staging, desactivado por omissão; flag NKATA_MEDIA_GATEWAY_TEST_ENABLED e segredo separado NKATA_MEDIA_GATEWAY_SECRET (mínimo 32 caracteres; nunca VITE_).
- Configurar Redis partilhado entre workers, HTTPS, relógios sincronizados e ambiente de pagamentos simulados.
- Nunca criar consumidores activos antes da autorização. Autenticar cada participante e confirmar no SFU os dois transportes conectados. Não confiar em IDs, SDP, presença ou heartbeats reportados pelo browser.
- No final do minuto pausar a transmissão antes de solicitar novo débito. Desligar transportes se a autorização falhar. O relógio e a autorização têm de ser impostos no processo de media, não no cliente.
- Antes de disponibilizar chamadas: integrar sinalização autenticada, controlo de produtores/consumidores no SFU, watchdog independente para crash ou bloqueio do processo, revogação por bloqueio/desconexão, testes de rede e de interrupção real de RTP. A perda de resposta depois do débito precisa de reconciliação.
- Railway continua a alojar o backend; a infra de media necessita de rede UDP adequada, TLS e TURN. Não criar serviços pagos nem activar produção sem aprovação.

Documentação: https://mediasoup.org/documentation/v3/communication-between-client-and-server/
