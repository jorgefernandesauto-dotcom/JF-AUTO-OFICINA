PERSONALIZAÇÃO JF AUTO: Nome da oficina: JF Auto Mecânica. Logótipo incluído em static/img/jf-auto-logo.png.

# Oficina Manager — publicação online

Esta pasta está preparada para publicar o Oficina Manager como aplicação web Flask com PostgreSQL.

## Opção recomendada: Render

1. Criar uma conta no GitHub e um repositório público ou privado.
2. Enviar todos os ficheiros desta pasta para o repositório.
3. No Render, escolher **New > Blueprint** e ligar o repositório.
4. O ficheiro `render.yaml` cria automaticamente a aplicação e a base PostgreSQL.
5. Aguardar o deploy. O Render atribui um endereço `onrender.com`.

Não é necessário manter o computador ligado.

## Atenção
A aplicação ainda não tem sistema de login de utilizadores. Antes de uso comercial, deve ser adicionado autenticação e controlo de acesso.


## Melhorias desta versão
- Edição de orçamentos, ordens de reparação e peças/stock.
- Calendário com hora de início e fim.
- Faturas simples diretas, com peças/mão de obra e atualização de stock.
- Impressão com logótipo JF Auto Mecânica.

Nota: a função de fatura simples é um documento de faturação interno e não deve ser apresentada como software certificado pela AT sem a respetiva certificação/integração fiscal.
