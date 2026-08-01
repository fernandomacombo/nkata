# NKATA

NKATA é uma plataforma de relacionamento sério e comunidade privada para adultos.

## Estado atual

O projeto funciona atualmente com Django, templates HTML, CSS e JavaScript.

A estratégia escolhida é a **Opção A**:

1. manter o Django atual a funcionar;
2. organizar o backend;
3. criar uma API com Django REST Framework;
4. criar depois um frontend React + Tailwind;
5. migrar as telas aos poucos, sem quebrar o que já funciona.

## Stack planejada

- Backend: Django + Django REST Framework
- Frontend atual: Django Templates
- Frontend futuro: React + Tailwind
- Banco local: SQLite
- Banco futuro: PostgreSQL

## Como rodar localmente

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Variáveis de ambiente

Copie o ficheiro de exemplo:

```bash
copy .env.example .env
```

Depois ajuste os valores conforme o ambiente.

## Endpoints iniciais da API

```txt
GET /api/status/
GET /api/perfis/
GET /api/perfis/<id>/
GET /api/minha-conta/matches/
```

## Próximos passos

- criar frontend React + Tailwind em `frontend/`;
- melhorar autenticação para API;
- criar endpoints para ações de perfil;
- criar endpoints para chat/mensagens;
- preparar deploy do backend e frontend separadamente.
