# Checklist de instalação experimental — NKATA Media

**Estado: BLOQUEADO para produção.** Este documento não instala nem activa
serviços. Todos os passos de infraestrutura requerem aprovação separada.

## 1. Antes de instalar
- CI verde para o commit exacto: backend, PostgreSQL, frontend, media-native
  (RTP, Chromium AUDIO e VIDEO, coturn), watchdog e migration 0057.
- Gerar e rever lockfile do media-gateway; npm ci e auditoria das dependências.
- Confirmar host Linux separado, capacidade de UDP/TCP, IP público IPv4
  e DNS/TLS próprios de staging. Não presumir que Railway expõe UDP.
- Fixar configuração de staging; nunca utilizar o domínio, carteira,
  credenciais, armazenamento ou dados pessoais de produção.
- Backend Railway de staging: Redis, HTTPS, pagamento simulado,
  e-mail dummy, crédito simulado. Segredos HMAC e TURN independentes.
- Plano de rollback: desligar a feature, fechar gateway e relay,
  verificar sessões expiradas e ocorrências financeiras; preservar ledger.

## 2. Instalação (somente após autorização)
- Aplicar migrations em staging e validar instalação nova / upgrade.
- Configurar coturn restrito ao SFU, firewall também IPv6, quotas e TLS.
- Executar supervisor em unidade systemd dedicada com KillMode=control-group,
  sem reinício automático; proxy WSS e limites de recursos.
- Validar health, IP/portas, DNS e certificados. Não expor segredos em logs.
- Bootstrap do frontend experimental continua pendente: integrar
  mediasoup-client com lockfile e habilitação explicitamente limitada
  a staging. Não usar chamadas legadas como fallback.

## 3. Validação de aceitação
- Dois utilizadores de teste verificados, conversa aceite, consentimento
  explícito, permissão de microfone/câmara, recusa sem débito.
- Testes em dois dispositivos físicos: Wi-Fi, rede móvel, TURN UDP e TLS,
  verificar candidato relay e transmissão efectiva nos dois sentidos.
- Testar interrupção, perda de rede, bloqueio, revogação, saldo zero,
  limite de minutos, falha de Django/Redis, watchdog e encerramento.
- Confirmar saldo e movimentos idempotentes, estorno quando comprovado,
  casos incertos na fila de revisão, sem alteração directa de saldo.
- Medir atraso de corte no fim da autorização, pausa por minuto e consumo
  de recursos. Não confundir confirmação de resume com recepção humana.
- Validar privacidade: não armazenar media, não expor tickets nem segredos.

## 4. Critério de bloqueio
Qualquer falha de CI, configuração, transmissão, isolamento, auditoria,
ou resultado financeiro não explicado bloqueia a activação.
Mesmo com o CI verde, não publicar sem aprovação explícita e ensaio
integrado do runtime real com Django e os dispositivos de teste.
