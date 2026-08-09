# Publicação do NKATA

Este projeto está preparado para executar o frontend React e a API Django no
mesmo domínio. A publicação real ainda depende de serviços externos: domínio,
PostgreSQL, armazenamento privado, email e TURN.

## 1. Domínio

`nkata.online` é curto e adequado ao produto. Antes de comprar, confirme a
disponibilidade e conflitos de marca. Uma estrutura simples é:

- aplicação: `https://nkata.online`;
- administração: `https://nkata.online/admin/`;
- TURN próprio, se usado: `turn.nkata.online`.

Não publique documentos, relatórios internos ou painéis de BI em rotas públicas.

## 2. Infraestrutura mínima

- um serviço web que execute o `Dockerfile`;
- PostgreSQL gerido com cópias de segurança e TLS;
- Redis gerido para limites de requisições compartilhados entre processos;
- bucket S3 compatível, privado, para fotografias, documentos, publicações,
  momentos e áudio;
- SMTP transacional;
- servidor/fornecedor TURN com UDP e TCP/TLS;
- um segundo processo com `NKATA_PROCESS_TYPE=worker` se a moderação automática
  de media estiver ativa.

O SQLite e o disco efémero não são adequados para produção.

## 3. Variáveis obrigatórias

Copie `.env.example` para o painel seguro do provedor e não envie o ficheiro
`.env` ao GitHub. Para produção, configure pelo menos:

```dotenv
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<chave longa e aleatória>
DJANGO_ALLOWED_HOSTS=nkata.online,www.nkata.online
NKATA_FRONTEND_URL=https://nkata.online
DATABASE_URL=postgresql://...
REDIS_URL=rediss://...
CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=https://nkata.online
CSRF_TRUSTED_ORIGINS=https://nkata.online
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
NKATA_TRUST_PROXY_HEADERS=True
```

`NKATA_TRUST_PROXY_HEADERS=True` só deve ser usado quando o proxy do provedor
substitui e controla `X-Forwarded-Proto`.

Configure também as variáveis `NKATA_STORAGE_*` e `DJANGO_EMAIL_*` descritas em
`.env.example`. O bucket deve permanecer privado; a aplicação entrega os
ficheiros somente depois de verificar sessão, perfil, match ou permissão de
administrador.

## 4. TURN/WebRTC

STUN sozinho não garante chamadas em redes móveis, CGNAT ou firewalls. Configure
`NKATA_WEBRTC_TURN_URLS` e uma destas formas de autenticação:

1. recomendada para coturn: `NKATA_WEBRTC_TURN_SHARED_SECRET`; o backend gera
   credenciais HMAC temporárias para cada membro;
2. compatibilidade: `NKATA_WEBRTC_TURN_USERNAME` e
   `NKATA_WEBRTC_TURN_CREDENTIAL` estáticos.

Exemplo de URLs:

```dotenv
NKATA_WEBRTC_TURN_URLS=turn:turn.nkata.online:3478?transport=udp,turn:turn.nkata.online:3478?transport=tcp,turns:turn.nkata.online:5349?transport=tcp
NKATA_WEBRTC_TURN_SHARED_SECRET=<mesmo segredo configurado no coturn>
NKATA_WEBRTC_TURN_CREDENTIAL_TTL=3600
```

Abra no firewall 3478 TCP/UDP, 5349 TCP e a faixa UDP de relay definida no
servidor TURN. Teste entre duas redes diferentes, por exemplo Wi‑Fi e dados
móveis; testar dois separadores no mesmo computador não comprova o relay.

## 5. Implantação

O container executa automaticamente:

```sh
python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn config.wsgi:application
```

Não execute `makemigrations` no servidor. As migrações versionadas no repositório
são a fonte de verdade.

Antes de direcionar o domínio, valide numa implantação de teste:

```sh
python manage.py check --deploy
python manage.py test
cd frontend && npm ci && npm run build && npm audit --audit-level=high
```

## 6. Verificação após publicar

- `GET /api/status/` responde `status: online` e confirma acesso ao banco;
- criar pedido, preencher questionário, aprovar e entrar;
- fotografias aparecem no computador e no telemóvel, sem URL `/media/` pública;
- uma conta não consegue abrir documentos de identidade;
- interesse mútuo cria match e a conversa envia/recebe mensagens;
- chamada recusada, perdida e concluída aparece no histórico, com duração;
- áudio e vídeo funcionam entre redes distintas e o painel técnico confirma TURN;
- recuperação de senha chega por email;
- reiniciar web/worker não elimina media nem dados;
- logs não contêm senhas, tokens, documentos ou credenciais TURN.

Mantenha backup diário do banco e política de retenção do bucket. Teste a
restauração antes do lançamento público.
