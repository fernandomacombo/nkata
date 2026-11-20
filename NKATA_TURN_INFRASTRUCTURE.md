# NKATA — TURN e diagnóstico da infraestrutura

## O que foi verificado

- Railway: aplicação, Postgres e Redis presentes em **staging** e **production**.
- O campo `turn_configured` confirma apenas URLs e credenciais; não valida a conectividade.
- O painel passou a usar estados **configurado (não testado)** para integrações externas e **revisão humana** como modo de moderação, não falha.
- Este trabalho não lê nem divulga segredos e não ativa meios de pagamento.

## TURN para chamadas móveis

TURN exige um servidor acessível aos clientes e portas de retransmissão de média. A Railway publica HTTP/HTTPS e TCP Proxy, mas não publica UDP de entrada para serviços de Internet; portanto, **não alojar coturn de media UDP diretamente no serviço web da Railway**. Usar provedor TURN gerido ou um VPS externo dedicado, com UDP público e firewall apropriada.

Configurar no Railway os nomes de variáveis seguintes **apenas depois de verificar o fornecedor**:

- `NKATA_WEBRTC_TURN_URLS`: URLs fornecidas pelo serviço, por exemplo `turn:turn.example.org:3478?transport=udp,turn:turn.example.org:3478?transport=tcp` (exemplo fictício).
- Para autenticação dinâmica: `NKATA_WEBRTC_TURN_SHARED_SECRET`, com o segredo do provedor, compatível com REST API de coturn.
- Em alternativa, para contas estáticas (menos recomendado): `NKATA_WEBRTC_TURN_USERNAME` e `NKATA_WEBRTC_TURN_CREDENTIAL`.
- `NKATA_WEBRTC_TURN_CREDENTIAL_TTL`: tempo de validade das credenciais efémeras, por padrão 3600 segundos.

A configuração da Railway não é teste de conectividade. Validar com **dois dispositivos em redes diferentes** (Wi-Fi e dados móveis), com teste ICE que force `iceTransportPolicy: "relay"`. Verificar que existe candidato `relay` e que áudio/vídeo realmente trafegam. Não guardar URLs assinadas, credenciais nem dados de chamadas em logs de acesso.

## Antes de qualquer alteração em produção

1. Selecionar fornecedor TURN/VPS com UDP e TCP/TLS, certificado válido e limites de utilização.
2. Testar primeiro com credenciais e ambiente de staging.
3. Confirmar negociação de ICE, áudio e vídeo em Wi-Fi↔dados móveis e dados móveis↔dados móveis.
4. Confirmar custo, métricas e limites para não criar relay aberto abusivo.
5. Preparar rollback das variáveis e validar o estado do serviço NKATA.
6. Só então replicar as variáveis em produção, sem alterar o código de pagamentos, contas ou identidade.

**O painel não faz sondagens remotas automáticas**: cada selo indica configuração (ou a ligação Django ao banco). Um verdadeiro indicador de saúde TURN requer teste externo isolado, com credenciais efémeras, métricas do provedor e limite de frequência.
