# NKATA — validação do Centro de Ajuda (PR #15)

## Estado e limites

Este módulo está numa branch de desenvolvimento e não pode ser publicado sem validação na infraestrutura atual. A verificação do GitHub Actions confirma apenas os testes automáticos, não comprova o funcionamento real do servidor ou a entrega dos emails pelo Zoho.

## Preparação em staging

1. Confirmar que o código de staging tem as correções atuais do NKATA de pagamentos, planos, NKATA ID e branding; não fazer deploy da branch isolada se isso remover alterações posteriores.
2. Fazer snapshot/backup da base e confirmar que o rollback é possível.
3. Verificar a configuração de emails do ambiente (não imprimir segredos). Usar uma conta de teste e o destino de email controlado.
4. Instalar dependências do projeto e executar:
   - `python manage.py check`
   - `python manage.py makemigrations --check --dry-run`
   - `python manage.py migrate --plan`
   - `python manage.py test helpdesk`
   - `npm ci && npm run build` (dentro de `frontend/`)
5. Aplicar as migrações **apenas em staging** e verificar a página `/ajuda/` no desktop e em ecrãs pequenos.

## Teste funcional de ponta a ponta

- [ ] Visitante sem sessão acede a `/ajuda/`, pesquisa uma FAQ e envia um pedido de teste com email controlado.
- [ ] É criada a referência UUID do pedido, sem expor detalhes de outros pedidos.
- [ ] O superutilizador encontra o ticket em `/painel/` > Suporte.
- [ ] Um operador comum não consegue consultar a caixa de entrada do suporte nem no painel React nem em `/admin/`.
- [ ] Resposta enviada ao email de teste: verificar chegada na caixa de entrada, corpo da mensagem, branding NKATA e eventual classificação como spam.
- [ ] O ticket muda para o estado selecionado e a resposta fica no histórico.
- [ ] Utilizador autenticado cria ticket e consegue consultar apenas os seus pedidos e respostas.
- [ ] Utilizador autenticado não consegue manipular o email destinatário pelo formulário.
- [ ] Falha simulada do provedor de email: pedido preservado, erro mostrado e resposta não marcada como enviada.
- [ ] Verificar em dispositivo móvel se o menu Ajuda abre corretamente e se os inputs, botões e histórico são legíveis.
- [ ] Confirmar que contas suspensas conseguem abrir a página de ajuda.
- [ ] Confirmar que pagamentos, planos, verificação NKATA ID e recuperação de palavra-passe permanecem funcionais.

## Lacunas conhecidas (não confundir com implementado)

- Visitantes sem conta podem **abrir** pedidos, mas ainda não têm um portal de consulta autenticado por email. O ID não autoriza acesso por si só.
- O envio de email está integrado, mas a entrega efetiva via Zoho em staging/produção não foi ainda confirmada.
- O envio de respostas é síncrono; falta uma fila de entrega/idempotência robusta para falhas intermédias.
- Os pedidos de suporte não aceitam anexos nesta fase; nunca pedir imagens de BI ou dados completos de cartão.
- Falta configurar uma política de retenção/eliminação e um procedimento de triagem prioritária para denúncias graves.

## Critério de publicação

Não fazer merge/deploy enquanto:
1. O CI mais recente não estiver verde;
2. Os testes funcionais anteriores não forem concluídos em staging;
3. A branch de destino real da produção não for confirmada;
4. Não houver procedimento de rollback verificado.

**Não partilhar em chats logs com dados pessoais, tokens, chaves Zoho ou credenciais.**
