# Correções da auditoria funcional — 14/11/2026

Base: `audit/nkata-payments-20261109`, commit `37bbe28`. As alterações foram preparadas numa branch separada. Nenhum servidor, conta ou pagamento real foi alterado durante o desenvolvimento.

## Comportamento corrigido

- Chamadas a conectar expiram após 60 segundos. Chamadas ativas dependem da presença dos dois participantes; 90 segundos sem presença permitem recuperar uma chamada abandonada. Redis é o armazenamento partilhado em produção.
- O servidor recusa ativar uma chamada ainda não atendida. Bloqueios dos dois utilizadores impedem iniciar chamadas simultâneas para matches diferentes.
- O componente fecha a chamada em erros e desmontagem, cancela capturas que terminem depois de sair e oferece ativação manual do som quando o navegador recusa autoplay. Já existiam encerramentos best-effort no bridge de navegação e em pagehide; a recuperação do servidor cobre falhas desses pedidos.
- Notas de voz são descodificadas com FFmpeg, verificadas pela duração real e convertidas para WAV mono. WebM/Opus, MP4/AAC e OGG foram exercitados. Conteúdo falso e valores de duração não finitos são recusados. A ausência do descodificador falha de forma explícita, sem aceitar uploads não verificados.
- O email permanece único para autenticação. Cada telefone normalizado e BI só pode estar associado a um pedido/conta. Pedidos pendentes, recusados e bloqueados também impedem reutilização. Para corrigir ou recuperar acesso, deve ser tratado o pedido existente. A equipa lê o número no BI antes de aprovar; uma declaração falsa não contorna a verificação. Aprovação em lote e criação direta no Django Admin foram desativadas; a aprovação individual é feita no painel NKATA.
- O número do BI é guardado como HMAC, sem persistir o número em claro. `NKATA_IDENTITY_HASH_KEY`, quando definido, deve permanecer estável. Na ausência dessa variável usa-se `DJANGO_SECRET_KEY`; nesse caso não rodar esse segredo sem planear a migração dos identificadores. As imagens privadas existentes continuam sujeitas à política de retenção da plataforma.
- Duas fotografias diferentes e semelhança facial deixam de ser tratadas como prova de vivacidade. Novas análises ficam para revisão humana até existir um mecanismo adequado de vivacidade. Decisões antigas não foram reclassificadas.
- O catálogo explica que ambos precisam de plano pago para chamar, a renovação é manual e a mudança de plano depende da expiração do atual.

## Migração e compatibilidade

Aplicar `0025_account_identity_limits`. Ela acrescenta os campos e a tabela de coordenação e preenche os telefones normalizados; não desativa contas antigas nem altera registos financeiros. Os BIs de contas antigas não podem ser deduzidos de um hash de imagem: precisam de conferência pela equipa para ficarem associados ao novo controlo. Até essa revisão, não afirmar que todo o histórico já foi deduplicado por titular.

A migração `0014_prepare_feature_tables` **já criava as tabelas opcionais**. A primeira versão da auditoria classificou incorretamente isto como ausência de preparação automática. Foi corrigido no relatório. O novo comando `check_nkata_runtime` apenas verifica o esquema e o descodificador; as migrações continuam a ser a fonte de verdade.

O arranque executa a verificação após `migrate`. A imagem Docker instala FFmpeg. Em instalações fora de Docker é necessário instalar o pacote FFmpeg do sistema antes de usar esta versão. Web e worker devem executar a mesma revisão.

## Configuração operacional

```sh
python manage.py migrate --noinput
python manage.py check_nkata_runtime
python manage.py check_nkata_runtime --require-turn --require-payments
```

O último comando é um controlo de configuração, não um teste de conectividade TURN nem uma homologação do prestador.

O processo `NKATA_PROCESS_TYPE=payments` executa `reconcile_nkata_payments --watch --interval 60`; deve ser criado e supervisionado no ambiente de implantação. Só consulta pedidos existentes, sem criar cobranças. Nenhum processo foi criado no servidor nesta entrega. Pedidos INCERTO sem ID do prestador continuam a exigir resolução operacional; não repetir cobranças às cegas.

## Validação

Os testes de regressão cobrem perda de presença, timeout de negociação, ativação fora de ordem, ficheiros falsos, formatos reais de navegador, duração real, limite por telefone/BI e conferência administrativa. A suíte específica de PostgreSQL cobre ainda criação concorrente de contas, chamadas concorrentes e aplicação única de uma confirmação de pagamento.

Resultados locais: 288 testes na suíte geral (285 aprovados e 3 reservados para PostgreSQL); 44 testes específicos em PostgreSQL aprovados, incluindo esses 3; 13 testes frontend aprovados; build, Django check, verificação de migrações e instalação numa base vazia aprovados. Permanece o aviso de bundle acima de 500 kB.

O CI passa a correr em pushes de `fix/**` e `audit/**`, valida uma instalação nova e executa os testes de concorrência num serviço PostgreSQL.

## Antes de publicar

1. Rever o PR e validar a implantação num ambiente de teste com PostgreSQL e Redis, usando dados fictícios.
2. Confirmar o commit atualmente publicado e a branch de implantação; `main` ainda é antiga.
3. Validar Android e iPhone com duas contas de teste de pessoas diferentes, Wi-Fi e dados móveis: atender, recusar, silenciar, desligar câmara, sair, perder rede, retomar e iniciar outra chamada.
4. Testar o relay TURN real e as permissões de câmara/microfone nos aparelhos.
5. Homologar checkout, callbacks e apresentação NKATA no prestador; confirmar o acompanhamento do processo de reconciliação.
6. Conferir os BIs das contas históricas antes de declarar o limite integralmente aplicado ao histórico.

Não foram implementados estornos automáticos, faturação fiscal, nova infraestrutura de vivacidade ou novos benefícios Premium. O funcionamento completo em produção depende das validações e configurações acima.

## Regra corrigida pelo titular

Uma pessoa só pode ter uma conta: email, telefone e BI não podem ser reutilizados em contas diferentes. A referência anterior a duas contas foi uma interpretação incorreta, corrigida antes da publicação.
