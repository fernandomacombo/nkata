# E-mail NKATA por Zoho CPaaS HTTPS

A API evita o bloqueio SMTP do Railway Trial/Hobby. Endpoint fixo:
https://cpaas.zoho.com/v1.1/email (conta Zoho do datacenter .com).

No Railway, após publicar este código, configure na mesma alteração:

```env
DJANGO_EMAIL_BACKEND=entradas.email_backend.ZohoAPIEmailBackend
DJANGO_DEFAULT_FROM_EMAIL=NKATA <notificacoes@nkata.date>
DJANGO_EMAIL_TIMEOUT=15
```

Adicione `NKATA_ZOHO_API_KEY` como segredo, copiando a chave API do Agent NKATA
em SMTP/API > API Setup (não a palavra-passe SMTP). Aceita token puro ou
prefixado com `Zoho-enczapikey `. Nunca guardar a chave em git ou screenshots.
As variáveis SMTP deixam de ser usadas por este backend.

Domínio verificado e remetente autorizado no Agent são necessários.
Após redeploy, executar no serviço:

```bash
python manage.py sendtestemail fmacombo@gmail.com
```

O retorno sem erro confirma aceitação pela API, não entrega. Verificar os logs
do Agent e a caixa de entrada/Spam. Não repetir automaticamente após timeout:
a API pode ter aceite o envio antes de a resposta se perder.

Suporta texto, HTML, CC/BCC e Reply-To. Anexos e cabeçalhos personalizados são
rejeitados explicitamente. Tracking de aberturas e cliques desactivado.
Nenhum envio real foi efectuado pelos testes unitários (HTTP simulado).
