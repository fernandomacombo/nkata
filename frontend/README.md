# NKATA Frontend

Interface React + Tailwind do NKATA, desenvolvida de forma progressiva sobre o backend Django existente.

## Direção do produto

- experiência premium e discreta;
- prioridade para confiança, privacidade e organização;
- mobile-first sem comprometer o desktop;
- integração gradual com a API Django;
- linguagem madura e adequada a uma comunidade seletiva.

## Executar o backend

Na raiz do projeto:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

## Executar o frontend

```bash
cd frontend
npm install
npm run dev
```

Abrir no computador:

```text
http://localhost:5173
```

Abrir no telemóvel ligado à mesma rede:

```text
http://IP_DO_COMPUTADOR:5173
```

## Configuração

O frontend utiliza por defeito o mesmo endereço do navegador, na porta `8000`.
Também pode ser configurado através de:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

A fotografia de fundo da Home também pode ser substituída sem alterar o código:

```env
VITE_HERO_IMAGE_URL=https://exemplo.com/fotografia-horizontal.jpg
```

## Endereços da aplicação

```text
/                         Início
/perfis/                  Perfis
/perfis/<id>/             Detalhe de um perfil
/guardados/               Perfis guardados
/matches/                 Matches
/matches/<id>/conversa/   Conversa privada
/conta/                   Conta do membro
/entrar/                  Login React
```

Os formulários Django continuam no backend, incluindo:

```text
http://localhost:8000/solicitar-entrada/
http://localhost:8000/recuperar-senha/
```

## Funcionalidades atuais

- Home com hero de ecrã inteiro;
- descoberta e filtros de perfis;
- detalhe e partilha de perfil;
- perfis guardados e vistos recentemente;
- login por sessão Django;
- demonstração de interesse e criação de match;
- lista de matches e conversa privada;
- área da conta, edição e controlo de visibilidade;
- rotas sincronizadas com o histórico do navegador.

## Verificação antes do commit

```bash
npm run build
```

Não enviar `node_modules/` para o GitHub.
