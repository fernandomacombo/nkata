# NKATA — revisão técnica e comercial, 9 de novembro de 2026

## Veredicto

Não pronto para cobrar ou declarar lançamento validado. A base funcional tem testes aprovados, mas não existe integração de pagamentos, subscrição com validade ou confirmação financeira. Esta revisão foi feita em código e ambiente de testes local, sem acesso à configuração de produção, contas financeiras ou aparelhos físicos. Não é um teste de intrusão completo.

Base: `fix/pr-replacement-readiness`, commit `ccf2f3f7d92b0ad018fbcd7e7ef243c3b82eebbf`. A branch `main` contém uma versão antiga e não deve ser tomada como versão completa. O CI da base passou em 16/09/2026: https://github.com/fernandomacombo/nkata/actions/runs/35057576489 . A falha de agosto não representa o último estado.

## Oferta proposta: quatro opções, incluindo Free

| Opção | Preço proposto | Benefícios existentes |
|---|---:|---|
| NKATA Livre / Free | 0 MT | 3 sinais/dia, conversa por texto, consulta do feed e Momentos com frases predefinidas |
| NKATA Essencial | 250 MT | 15 sinais/dia, envio de voz, chamadas áudio/vídeo, publicação de media sujeita a moderação |
| NKATA Premium | 500 MT | 40 sinais/dia e funcionalidades do Essencial |
| Recarga NKATA +10 sinais | 50 MT | 10 sinais adicionais, consumidos depois da franquia diária; não desbloqueia recursos de planos pagos |

Estes valores são uma proposta de melhoria do modelo existente, não preços já aprovados ou cobrados. A duração dos planos continua por definir. A API e interface mantêm compras desativadas. Recargas antigas de 30/80 deixam de ser anunciadas, mas continuam reconhecidas no saldo histórico. O comando administrativo antigo continua disponível para testes/migração, sem constituir comprovativo de pagamento.

Filtros avançados e prioridade na descoberta apareciam como benefícios, mas a pesquisa no código só encontrou as flags e os rótulos, sem implementação. Foram desativados na oferta para não prometer recursos inexistentes. Premium distingue-se hoje sobretudo pela franquia de sinais; validar se essa diferença justifica 500 MT antes do lançamento.

Não é possível afirmar rentabilidade sem custos reais de alojamento, armazenamento, tráfego TURN, moderação, verificação de identidade, suporte e taxas do prestador. Calcular margem por pacote como receita líquida menos custos variáveis; depois dividir custos fixos pela margem média para estimar clientes necessários. Não assumir chamadas ilimitadas rentáveis sem medir consumo.

## Cobranças e marca

Não foi encontrada integração de gateway, webhook ou ocorrência de Ruzisan no código analisado. `plan_views.py` declara `payments_enabled=False`. `assign_plan` utiliza grupos Django; não consulta pagamentos nem datas de expiração. Os bloqueios atuais provam posse de um grupo, não pagamento.

É possível apresentar NKATA na interface e, numa futura integração PaySuite, nas referências e descrições. A documentação permite `reference` e `description`; não documenta nesses campos uma substituição do nome do comerciante. Não prometer que descrições mudam o nome mostrado pelo M-Pesa, e-Mola ou banco. Confirmar no cadastro/suporte do prestador a utilização de NKATA como nome comercial e testar a confirmação, checkout, recibo e extrato. A identificação da entidade contratante/emissora deve ser tratada separadamente, sem simplesmente substituir dados oficiais da Ruzisan por texto de marca.

Documentação consultada: https://paysuite.tech/docs/ . Não foram alteradas contas financeiras nem enviados pedidos ao prestador.

Antes de ativar compras:

1. Definir duração de Essencial/Premium, renovação manual/automática, cancelamento e efeitos de reembolso.
2. Criar pedidos com preço calculado no servidor, moeda MZN e referência NKATA única.
3. Confirmar pagamento pelo servidor com o prestador; nunca pelo regresso do navegador ou por um valor enviado pelo cliente.
4. Validar autenticidade de callbacks, referência, moeda e montante. Aplicar processamento idempotente e transações para impedir ativações/recargas duplicadas.
5. Registar subscrição, início/fim, pagamento que a originou e histórico administrativo. Uma conta Free não pode atribuir a si própria grupos pagos.
6. Aplicar expiração, falhas, reembolsos e reconciliação; separar concessões administrativas de pagamentos reais.
7. Testar pagamento aprovado, pendente, recusado, timeout e callback duplicado/forjado no ambiente de testes do prestador.

## Segurança e acesso pago

Há controlos de sessão, CSRF, propriedade de media, bloqueios/denúncias, moderação, limites de pedidos e requisitos de PostgreSQL/Redis/armazenamento privado em produção. Os testes automatizados dão evidência parcial; não comprovam a configuração real do servidor.

A API bloqueia envio de notas de voz, início de chamadas e publicação de media para Free. Foram acrescentados testes de chamadas diretas à API, tentativa de indicar PREMIUM no pedido e revogação ao regressar a Livre. Receber/consultar conteúdo já partilhado tem regras distintas do envio; não foi convertido indiscriminadamente em funcionalidade paga. A implementação de chamadas atualmente exige plano pago para ambos os participantes.

Ponto de atenção alto no NKATA ID: a variável `vivacidade_confirmada` é inferida de duas imagens diferentes com um rosto em cada imagem. Isto não demonstra por si só presença real ou resistência a apresentação de fotografias/vídeo. A aprovação automática pode ocorrer quando essa heurística é combinada com semelhança facial AWS. Antes de habilitar aprovação automática em produção, substituir por verificação de vivacidade apropriada e testar ataques de apresentação; manter revisão humana enquanto isso não for validado. Ver `identity_verification_service.py:finalize_identity_analysis`.

Também falta validar operacionalmente retenção/eliminação de documentos e selfies, acesso dos moderadores, recuperação de backups e alertas. Não marcar segurança como concluída apenas porque a suíte passa.

## Alterações desta revisão

- Catálogo público limitado a quatro opções, preços propostos entre Free e 500 MT, preservando créditos antigos.
- Compras continuam desativadas e a duração ainda por confirmar é comunicada.
- Removidas promessas de filtros avançados/prioridade não implementados.
- Vite atualizado para 8.3.7 e dependências transitivas corrigidas: auditoria npm passou de 3 alertas (2 altos/1 moderado) a zero.
- Pillow atualizado de 12.3 para 13.0 após alertas da auditoria de dependências.
- Testes adicionais para limites do catálogo e bloqueios de recursos pagos.

## Validação

Resultados finais registados abaixo após a execução. Chamadas em redes móveis, emails reais, pagamentos, interface em aparelhos físicos e produção não foram validados nesta revisão. Compilação frontend tem aviso de bundle acima de 500 kB, que é uma questão de desempenho a acompanhar.

- Backend: 218 testes aprovados, incluindo os novos testes de acesso pago.
- Frontend: 11 testes aprovados; política de UI e build de produção aprovados.
- `makemigrations --check --dry-run`: sem alterações pendentes.
- `pip check`: sem dependências incompatíveis.
- `npm audit`: zero alertas depois das atualizações.
- Auditoria Python após Pillow 13: sem alertas nas dependências da aplicação; o ambiente de teste também sinalizou o próprio pip 25.0.1, cuja atualização foi executada separadamente.

## Prioridades para concluir

1. Integração de pagamentos e subscrições com validade, sem ativação baseada no navegador.
2. Nome comercial NKATA confirmado pelo prestador em todos os canais relevantes.
3. Rever vivacidade/identidade e operação de moderação/retenção.
4. Validar produção, dispositivos, pagamentos de teste e recuperação de backups.
5. Validar custos e duração dos planos, sem prometer benefícios não implementados.

## Atualização: validade de 30 dias aprovada

O utilizador confirmou 30 dias para Essencial/Premium. A implementação posterior acrescenta `AcessoPlanoNKATA` com início/fim e valida a expiração em cada consulta de permissões, sem depender de tarefa agendada. O catálogo informa 30 dias e a conta apresenta a data/hora de fim. Esta secção substitui as referências anteriores a duração por definir e controlo apenas por grupos.

A concessão administrativa passa a durar 30 dias; renovar o mesmo plano antes do fim preserva os dias restantes. Depois da expiração, uma nova concessão começa na data atual. Uma troca administrativa de plano começa novo período de 30 dias; política comercial de upgrades continua pendente e não existe checkout habilitado. Voltar a Livre revoga a concessão. Não há débitos nem renovação financeira automática.

Grupos antigos sem registo de validade deixam de conceder acesso pago. Antes de aplicar a migração a dados reais, rever essas contas e atribuir conscientemente concessões administrativas quando justificadas; não tratar pertença a grupo como prova de pagamento. A migração não inventa pagamentos ou prazos retroativos.

A origem destes registos é ADMINISTRATIVA. A integração futura deve criar um fluxo separado, com registo financeiro, idempotência e confirmação do prestador antes de conceder acesso. O modelo novo não constitui comprovativo de cobrança e não resolve esse bloqueador.

## Atualização: pedidos e confirmação PaySuite

Foi acrescentado um fluxo de checkout, histórico, webhook assinado e consulta autenticada ao prestador com aplicação idempotente de planos/recargas. Ver `PAGAMENTOS_NKATA.md`. Esta secção substitui a afirmação histórica de ausência de integração no código. A integração mantém-se desativada por padrão e não foi homologada na conta real. Marca no prestador, reembolsos, operação de casos incertos, produção e vivacidade continuam pendentes.
