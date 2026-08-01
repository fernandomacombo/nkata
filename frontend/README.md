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

Exemplo:

```text
http://192.168.0.100:5173
```

## API

O frontend utiliza por defeito o mesmo endereço do navegador, na porta `8000`.
Também pode ser configurado através de:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Páginas disponíveis

- Home premium;
- Descobrir perfis;
- detalhe do perfil;
- estados de carregamento, erro e ausência de resultados;
- áreas reservadas preparadas para autenticação, matches e mensagens.

## Verificação antes do commit

```bash
npm run build
```

Não enviar `node_modules/` para o GitHub.
