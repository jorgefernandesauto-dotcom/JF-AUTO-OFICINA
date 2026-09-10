# JF Auto Mecânica — versão profissional

Inclui:
- Login com utilizador e palavra-passe.
- Utilizador inicial: `admin`
- Palavra-passe inicial: `JFauto123!` (alterar em Definições > Segurança após entrar).
- Orçamentos editáveis antes de serem convertidos.
- Stock editável.
- Ordens de reparação editáveis e itens editáveis.
- Ao marcar um orçamento como **Convertido**, o stock das peças é descontado uma única vez, desde que a referência/descrição exista no stock e haja quantidade suficiente.
- Ao marcar uma ordem como **Entregue**, o stock das peças é descontado uma única vez.
- Calendário com hora de início e hora de fim.
- Faturas simples criadas diretamente, sem passar por ordem de reparação.
- Impressão de faturas simples com o logo JF Auto Mecânica.
- Ligação PostgreSQL através de `DATABASE_URL` para Render/Supabase.

## Nota importante
A opção **Fatura simples** é um documento de gestão/impressão. Não significa que o sistema seja, por si só, um software de faturação certificado pela Autoridade Tributária.

## Render
O serviço continua a usar Docker. A variável `DATABASE_URL` deve continuar configurada com a ligação PostgreSQL (por exemplo, o Session Pooler do Supabase).


## V7 corrigida
- Apagar ordens de reparação funciona e repõe no stock as peças já descontadas.
- Criar fatura diretamente da ordem de reparação.
- A fatura usa o logo JF Auto já existente em `static/img/jf-auto-logo.png`.
- Migração automática cria a coluna de ligação da ordem à fatura em instalações existentes.


## V7 corrigida + quilometragem
As faturas passaram a ter campo de quilómetros. O valor é guardado na fatura, aparece nos detalhes e é impresso no documento. Ao criar uma fatura diretamente de uma ordem de reparação, os km da ordem (ou da viatura) são copiados automaticamente.
