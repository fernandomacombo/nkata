# Pagamentos NKATA — integração PaySuite

Estado: código preparado e coberto por testes simulados; desativado por padrão. Nenhuma cobrança real foi feita nesta implementação. Testes na conta empresarial e homologação operacional continuam obrigatórios antes de habilitar compras.

## Oferta

- Livre: grátis.
- Essencial: 250 MT, 30 dias por confirmação.
- Premium: 500 MT, 30 dias por confirmação.
- Recarga +10 sinais: 50 MT, sem desbloquear recursos de planos pagos.

Preço, moeda MZN, duração e créditos são determinados no servidor e guardados no pedido. O navegador só envia `product` e `key` (UUID). Referências começam por NKATA e usam apenas letras/números. A descrição identifica NKATA. Isto não altera o nome legal do comerciante, o nome na confirmação M-Pesa/e-Mola ou no extrato; confirmar a apresentação comercial com PaySuite antes de lançar.

## Fluxo implementado

1. Conta autenticada com perfil ativo escolhe um produto. O backend cria um pedido e chama a API PaySuite.
2. Uma chave repetida devolve o mesmo pedido. Um pedido aberto impede nova cobrança na mesma conta até resolução. O envio de valores/estados pelo cliente é rejeitado.
3. Apenas checkout HTTPS num host explicitamente permitido é devolvido. As credenciais nunca são enviadas ao frontend.
4. O webhook valida `X-Signature` como HMAC-SHA256 do corpo original. Depois consulta o pedido diretamente na API autenticada do prestador; não confia no evento isoladamente.
5. Valida ID, referência, valor, moeda quando presente, estado do pedido e da transação. A API documenta valores em MZN e não inclui sempre um campo currency; ausência desse campo significa MZN pelo contrato do endpoint, não conversão de moeda.
6. Uma transação local bloqueia utilizador e pedido e aplica benefícios uma única vez. Pedidos de plano registam a validade concedida; recargas são creditadas uma única vez.
7. O cliente consulta o histórico e pode pedir verificação. O regresso do checkout, incluindo qualquer parâmetro `status`, nunca ativa direitos.

A validade começa na aplicação da confirmação ao NKATA. Renovar o mesmo plano soma 30 dias ao fim atual. Para evitar perda de dias ou uma política de pró-rata não acordada, compras de plano diferente são recusadas enquanto houver plano ativo. Trocas administrativas durante um pagamento ou conta bloqueada/pausada colocam pagamentos confirmados em REVISAO, sem atribuição silenciosa.

## Configuração (no servidor, fora do Git)

```dotenv
NKATA_PAYMENTS_ENABLED=False
NKATA_PAYSUITE_TOKEN=<token da conta empresarial>
NKATA_PAYSUITE_WEBHOOK_SECRET=<segredo do webhook>
NKATA_PAYMENT_ORIGIN=https://endereco-real-do-nkata
NKATA_CHECKOUT_HOSTS=paysuite.tech
```

O endereço público deve servir frontend e API na mesma origem HTTPS. `NKATA_PAYMENT_ORIGIN` define retorno e webhook por pedido; não altera a configuração global de outros produtos da mesma conta. Confirmar o host real retornado pelo ambiente PaySuite: o exemplo da documentação usa um domínio fictício, que não é autorizado automaticamente. A API de integração está fixada em `https://paysuite.tech/api/v1/payments`; não apontar para outro ambiente sem verificar o contrato oficial e adaptar/testar explicitamente.

Aplicar as migrações versionadas antes do arranque, incluindo 0023 e 0024. Só mudar ENABLED para True num ambiente controlado após configurar a conta, host e segredo. A aplicação recusa ativação sem credenciais/origem HTTPS. A flag desliga novas compras, mas a reconciliação de pedidos anteriores continua disponível enquanto as credenciais existirem.

## Rotas

- GET/POST `/api/minha-conta/pagamentos/`: histórico próprio / criar checkout.
- POST `/api/minha-conta/pagamentos/<uuid>/verificar/`: consulta autenticada ao prestador para pedido próprio.
- POST `/api/pagamentos/paysuite/webhook/`: callback autenticado por assinatura, sem sessão do navegador.

As operações de conta mantêm autenticação de sessão, CSRF e limites por utilizador. O histórico administrativo é de consulta, sem botão para marcar manualmente como pago. Os dados financeiros protegem a referência ao utilizador contra eliminação física acidental; definir processo de retenção/anonimização antes de implementar eliminação definitiva de contas.

## Reconciliação e casos incertos

```sh
python manage.py reconcile_nkata_payments --limit 20
```

O comando consulta pedidos não aplicados com ID do prestador, incluindo falhas para capturar confirmações tardias. Pode ser executado periodicamente pelo operador. Não foi criado um agendamento nem alterado um servidor nesta implementação.

Após timeout de criação, o pedido fica INCERTO e o POST ao prestador não é repetido automaticamente. Se não há ID guardado, um operador precisa localizar a referência NKATA no prestador, verificar o vínculo e resolver o pedido; não criar outra cobrança às cegas. A interface apresenta o histórico, mas não existe botão que apague ou force pagamentos. Pedidos sem resolução continuam a impedir novas compras nessa conta.

Notificação que chega antes de o ID ser guardado recebe 503 para repetição. Falha antiga não desfaz um benefício já aplicado. Falha transitória de confirmação pode ser novamente consultada pelo cliente/comando. Nunca guardar segredos ou corpos completos do prestador nos logs.

## Validação e limites

Testes usam respostas simuladas: montante adulterado, referência/ID/moeda errados, notificações forjadas, confirmação incompleta, repetição, falha, timeout, propriedade de conta, CSRF, recarga única, renovação e rollback. Ainda é necessário validar sandbox/prestador, duas transações concorrentes em PostgreSQL, diferentes redes/dispositivos, confirmação SMS/extrato, retorno real e tempos/repetições do webhook.

Reembolsos e chargebacks não são automatizados nesta etapa. Não processar devoluções sem revisão operacional dos direitos concedidos; implementar o ciclo de estorno e reconciliação antes de disponibilizar reembolsos ao utilizador. Não há faturação fiscal ou emissão de recibo fiscal nesta entrega; o histórico de pagamento não é uma fatura.

A integração não resolve o bloqueador de vivacidade do NKATA ID, custos de operação, moderação e validação da infraestrutura descritos na auditoria.

Documentação consultada em 9/11/2026: https://paysuite.tech/docs/ (versão indicada: 1/11/2026).

Resultado local desta etapa: 253 testes Django (29 de pagamentos), 11 testes frontend, compilação, verificação de configuração e compatibilidade de dependências aprovados; nenhuma migração adicional em falta. O build conserva o aviso de bundle acima de 500 kB.
