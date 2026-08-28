# Publicação segura do NKATA

O NKATA está preparado para servir React e Django no mesmo endereço HTTPS.
Enquanto o domínio ainda não foi comprado, a primeira publicação deve usar o
subdomínio HTTPS atribuído pela hospedagem, por exemplo
`https://nome-do-projecto.provedor.app`.

## Domínio futuro

`www.nkata.co.mz` fica reservado como endereço futuro. Escrever esse nome no
código não regista o domínio nem cria DNS ou certificado. Só depois da compra e
da confirmação de controlo do DNS devem ser acrescentados:

- `www.nkata.co.mz` em `DJANGO_ALLOWED_HOSTS`;
- `https://www.nkata.co.mz` nas URLs públicas e origens confiáveis;
- os registos DNS indicados pela hospedagem;
- o certificado HTTPS emitido para esse domínio.

Até esse momento, não use `www.nkata.co.mz` em links enviados aos utilizadores.

## Infraestrutura mínima

- serviço web que construa o `Dockerfile` e ofereça HTTPS;
- PostgreSQL gerido, com TLS e cópias de segurança;
- Redis privado para rate limiting partilhado entre processos;
- bucket S3 compatível e privado para fotografias e documentos de identidade;
- SMTP transacional para entrada e recuperação de palavra-passe;
- TURN para chamadas entre redes móveis/NATs restritivos;
- segundo processo com `NKATA_PROCESS_TYPE=worker` quando a moderação automática
  de media estiver ativa.

SQLite, cache local e disco efémero não são aceites pela configuração de
produção. Num servidor próprio, o armazenamento local só pode ser assumido com
`NKATA_ALLOW_LOCAL_MEDIA_IN_PRODUCTION=True` e volumes persistentes, cifrados e
incluídos nos backups.

## Variáveis da primeira publicação

Substitua `nome-do-projecto.provedor.app` pelo endereço realmente entregue pela
hospedagem. Guarde os segredos apenas no painel seguro do provedor.

```dotenv
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<chave longa, aleatória e exclusiva>
DJANGO_ALLOWED_HOSTS=nome-do-projecto.provedor.app
NKATA_FRONTEND_URL=https://nome-do-projecto.provedor.app
NKATA_PUBLIC_APP_URL=https://nome-do-projecto.provedor.app

DATABASE_URL=postgresql://...
DJANGO_DB_SSL_REQUIRED=True
REDIS_URL=rediss://...

CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=https://nome-do-projecto.provedor.app
CSRF_TRUSTED_ORIGINS=https://nome-do-projecto.provedor.app

SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_SSL_REDIRECT=True
DJANGO_SECURE_HSTS_SECONDS=3600
DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS=False
DJANGO_SECURE_HSTS_PRELOAD=False
NKATA_TRUST_PROXY_HEADERS=True
```

Use `NKATA_TRUST_PROXY_HEADERS=True` somente se o proxy da hospedagem substituir
e controlar `X-Forwarded-Proto`. Depois de confirmar HTTPS estável, aumente HSTS
gradualmente. Não ative `includeSubDomains` ou preload num domínio que não
controla.

Configure também:

- `NKATA_STORAGE_*` para bucket privado;
- `DJANGO_EMAIL_*` para SMTP real;
- `NKATA_WEBRTC_TURN_*` para TURN;
- `NKATA_WEBPUSH_*` para Push, quando necessário.

O frontend não precisa de `VITE_API_BASE_URL` em produção: `/api` usa a mesma
origem HTTPS da aplicação, mantendo cookies de sessão e CSRF no mesmo domínio.

## Arranque

O container executa automaticamente:

```sh
python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn config.wsgi:application
```

Não use `python manage.py runserver` em produção e não execute `makemigrations`
no servidor. As migrações versionadas são a fonte de verdade.

## Validação antes de publicar

Execute com as variáveis reais de produção carregadas:

```sh
python manage.py check --deploy
python manage.py test
python -m pip check
cd frontend
npm ci
npm run test:api-runtime
npm run test:nkata-id
npm run build
npm audit --audit-level=high
```

Não publique se algum comando falhar. Uma auditoria sem falhas reduz riscos,
mas não garante segurança absoluta; o ambiente publicado também precisa ser
testado.

## Verificação após a implantação de teste

- `GET /api/status/` responde `status: online`;
- o login cria sessão sem CORS, CSRF ou `Failed to fetch`;
- host desconhecido é recusado;
- HTTP redireciona para HTTPS e cookies têm `Secure`, `HttpOnly` e `SameSite`;
- respostas incluem CSP, `X-Content-Type-Options`, política de referência e
  proteção contra frames;
- uma conta não abre BI, selfie ou media privada de outra conta;
- rate limiting continua igual com mais de um processo web;
- recuperação de palavra-passe chega por SMTP sem revelar se o email existe;
- reiniciar web/worker não elimina dados nem media;
- logs não contêm palavras-passe, tokens, BI, selfies ou credenciais TURN;
- restauração de backup do PostgreSQL e do bucket é testada.

## Mudança futura para `www.nkata.co.mz`

Depois da compra e do DNS ativo, altere apenas as variáveis de origem/host para
o domínio real, mantenha o endereço temporário durante a transição e execute
novamente todos os testes. O código da aplicação não precisa ser reescrito.
