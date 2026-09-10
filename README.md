# JF Auto Oficina V9

Versão V9 da gestão de oficina JF Auto, com organização inspirada no fluxo moderno de software de oficinas.

## Novidades V9
- Histórico completo por viatura.
- Fotografias/documentos de diagnóstico por ordem através de links.
- Rentabilidade estimada por ordem (venda, custo e margem).
- Gestão de encomendas a fornecedores.
- Receção de encomendas com atualização automática do stock.
- Estados de trabalho preparados para o quadro Kanban.
- Mantidas as funções da V8.1: receção, pesquisa global, aprovação de orçamentos, quadro de trabalho, faturas a partir da ordem, quilómetros, stock e eliminação de ordens com reposição de stock.

## Deploy
1. Substituir os ficheiros no GitHub `JF-AUTO-OFICINA`, branch `main`.
2. No Render, usar o Web Service `JF-AUTO` ligado ao GitHub e fazer Deploy latest commit.
3. Não apagar a base de dados.

## Nota sobre fotografias
Na V9 as fotografias/documentos são guardados como links. Assim não dependem do disco local do Render. Para upload de ficheiros diretamente na aplicação, recomenda-se ligar armazenamento persistente/object storage numa versão futura.
