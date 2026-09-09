# JF Auto Mecânica — versão corrigida

Esta versão corrige a página branca com:
- resposta de erro visível em vez de página vazia;
- rota `/health` para verificar servidor + base de dados;
- contexto global de templates protegido contra falhas da BD;
- Gunicorn com 1 worker para evitar corridas durante a criação/migração da BD;
- mantém login, ordens, orçamentos, stock, agenda e faturas simples.

## Render
Publicar os ficheiros deste ZIP no repositório `JF-AUTO-OFICINA`.
O Dockerfile usa automaticamente a porta `$PORT` do Render.
