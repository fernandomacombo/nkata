# NKATA UI Policy

Esta política define regras obrigatórias para a interface do NKATA.

## 1. Iconografia

- Toda iconografia funcional deve usar `lucide-react`.
- Não usar emojis em botões, navegação, reações, notificações, estados, badges, mensagens de sistema ou ações de perfil.
- O backend deve devolver códigos semânticos (`flower`, `heart`, `hand`, `sparkles`, etc.), nunca caracteres gráficos dependentes da fonte do sistema operativo.
- O React é responsável por mapear esses códigos para componentes Lucide.
- Os ícones devem manter `strokeWidth` consistente e não substituir texto necessário para acessibilidade.

## 2. Mobile é App Mode

Abaixo de `820px`, o NKATA não é tratado como website reduzido. É tratado como aplicação.

Regras mínimas:

- navegação inferior como navegação primária de membros autenticados;
- header compacto e orientado a ações;
- `100dvh` em experiências imersivas;
- respeito por `safe-area-inset-top` e `safe-area-inset-bottom`;
- targets de toque com pelo menos `44px`;
- inputs com pelo menos `16px` para evitar zoom automático no iOS;
- chat e visualizador de Momentos em ecrã inteiro;
- conteúdo protegido contra a barra inferior fixa;
- sem rodapé tradicional de website na área autenticada mobile;
- sem scroll horizontal acidental;
- feedback de toque apropriado para dispositivos sem hover;
- respeito por `prefers-reduced-motion`.

O modo é marcado globalmente no `body` com a classe `nk-app-mode` e no elemento `html` com `data-nkata-mode="app"`.

## 3. Desktop

Desktop mantém a identidade editorial premium do NKATA. As regras de App Mode não devem empobrecer a experiência desktop.

## 4. Verificação obrigatória

Antes de considerar uma alteração de interface pronta, executar no diretório `frontend`:

```bash
npm run check:ui
npm run build
```

`check:ui` deve falhar quando:

- existir emoji funcional no código verificado;
- `lucide-react` deixar de estar configurado;
- o contrato mobile não estiver carregado por último;
- elementos essenciais do App Mode desaparecerem.

Esta política deve ser preservada em novas telas e funcionalidades.
