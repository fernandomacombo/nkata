# NKATA — ativação do email oficial geral@nkata.date

## Objetivo

Criar **uma caixa de entrada real** chamada `geral@nkata.date`, com acesso web (Zoho Mail), para receber e responder a contactos e pedidos de suporte.

**Estado:** planeado; mailbox e DNS ainda não foram criados nem verificados nesta tarefa. Não tratar o endereço como ativo até envio e receção serem testados.

## 1. Preparar o Zoho Mail

- Abrir https://mailadmin.zoho.com e autenticar-se com a conta que ficará como administradora da organização.
- Adicionar o domínio `nkata.date` em Domains.
- Escolher um plano Zoho Mail adequado. Zoho Mail (caixa de entrada) não é a mesma coisa que Zoho CPaaS/Agent usado para envio transacional.
- Confirmar propriedade do domínio com o registo TXT/CNAME **específico gerado pelo Zoho** no gestor DNS responsável.
- Criar o utilizador/caixa de entrada **geral@nkata.date** e ativar MFA.

## 2. DNS do domínio

- Verificar quem gere a zona autoritativa de `nkata.date` (registrador, Cloudflare ou outro).
- Configurar MX com **valores exatos e prioridades apresentados pelo Zoho Admin Console para a região da conta**; não copiar exemplos de outras regiões.
- Publicar SPF adaptado a **todos os serviços efetivamente autorizados** a enviar (Zoho Mail e, se aplicável, Zoho CPaaS). **Apenas um SPF por domínio; nunca criar dois TXT 'v=spf1'.**
- Gerar chave DKIM no Zoho e publicar o seletor/valor indicado.
- Configurar DMARC inicialmente com política de monitorização, analisar relatórios e endurecer gradualmente a política após confirmação de alinhamento.
- Não alterar registos A/AAAA/CNAME usados pelo site NKATA.

## 3. Testes funcionais

- Enviar mensagem de conta externa para `geral@nkata.date`, confirmar chegada à inbox.
- Responder e confirmar entrega no destino; verificar SPF, DKIM, DMARC em cabeçalhos.
- Verificar spam, bloqueios e acesso móvel, inclusive autenticação em duas etapas.
- Confirmar receção de um ticket do Centro de Ajuda de um utilizador de teste.
- Confirmar se Zoho CPaaS aceita `geral@nkata.date` como **remetente verificado** antes de alterar configurações da aplicação.

## 4. Integração no NKATA sem interrupção

Em produção, a aplicação usa `entradas.email_backend.ZohoAPIEmailBackend` para mensagens transacionais; isso não cria uma caixa para receber emails.

- Manter `DJANGO_EMAIL_BACKEND` e `DJANGO_DEFAULT_FROM_EMAIL` existentes **até** verificação explícita do novo remetente no Zoho CPaaS.
- Depois da verificação e teste em staging, definir no Railway em staging:
  `DJANGO_DEFAULT_FROM_EMAIL=NKATA <geral@nkata.date>`
  e enviar um email transacional de teste.
- **Só depois**, configurar a mesma variável em produção, com plano de rollback e monitorização de emails de recuperação de senha.
- No Centro de Ajuda, usar `geral@nkata.date` como canal de contacto **após** o endereço receber mensagens. Para tickets, manter referência, proteção de privacidade e controlo de permissões.
- Não colocar a palavra-passe da mailbox ou a chave da API Zoho no repositório; usar o gestor seguro do fornecedor.

## Critérios para concluir

- [ ] Domínio adicionado e validado no Zoho Mail
- [ ] Caixa geral@nkata.date criada e protegida por MFA
- [ ] MX, SPF, DKIM e DMARC configurados e verificados
- [ ] Envio e receção externa bem-sucedidos
- [ ] Remetente também autorizado no Zoho CPaaS, caso usado para transações
- [ ] Staging validado, sobretudo recuperação de senha
- [ ] Produção alterada somente após validação e backup das configurações

Referência: https://www.zoho.com/mail/help/adminconsole/email-hosting-setup.html
