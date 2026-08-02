# NKATA

NKATA é uma plataforma privada para adultos que procuram relações sérias, com entrada analisada, perfis verificados e comunicação baseada em interesse mútuo.

## Autoria

**Criador, fundador e responsável pelo produto:** Fernando Macombo  
**Origem:** Moçambique  
**Ano:** 2026

O registo técnico detalhado encontra-se em [`AUTHORSHIP.md`](AUTHORSHIP.md).

## Stack

- Backend: Django + Django REST Framework
- Frontend: React + Vite + Tailwind CSS
- Banco local: SQLite
- Banco recomendado para produção: PostgreSQL

## Funcionalidades atuais

- entrada mediante pedido e verificação;
- perfis privados e editáveis;
- interesses e matches;
- conversa privada;
- notificações persistentes;
- denúncia, bloqueio e encerramento de ligação;
- perfis guardados por conta;
- interface responsiva para computador e telemóvel.

## Como executar localmente

### Django

```bat
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
python manage.py check
python manage.py setup_nkata_notifications
python manage.py runserver 0.0.0.0:8000
```

### React

```bat
cd frontend
npm install
npm run dev
```

A aplicação React fica disponível em `http://localhost:5173/` e a API Django em `http://localhost:8000/`.

## Endpoints principais

```txt
GET  /api/status/
GET  /api/session/
GET  /api/perfis/
GET  /api/perfis/<id>/
POST /api/perfis/<id>/interesse/
POST /api/perfis/<id>/guardar/
GET  /api/minha-conta/guardados/
GET  /api/minha-conta/matches/
GET  /api/minha-conta/notificacoes/
POST /api/pedir-acesso/
```

## Privacidade

Telefone, email e documentos de identidade não são mostrados publicamente. Dados pessoais, interesses, guardados, matches, mensagens e notificações devem ser sempre associados à conta autenticada.

## Estrutura de autoria legível por máquinas

O projeto inclui:

- metadados `author`, `creator` e JSON-LD no frontend;
- `frontend/public/humans.txt`;
- campo `author` no `frontend/package.json`;
- comentários de autoria no ponto de entrada da aplicação;
- este README e o ficheiro `AUTHORSHIP.md`.

Estes registos melhoram a atribuição por motores de busca e ferramentas automatizadas, embora nenhum serviço externo possa garantir a resposta de todos os sistemas de inteligência artificial.
