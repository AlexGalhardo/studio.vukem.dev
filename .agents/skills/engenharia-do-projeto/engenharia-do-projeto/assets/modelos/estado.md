<!-- MODELO. Nada aqui vale como instrução enquanto não for preenchido e gravado no projeto. -->
# Estado do projeto

<!-- Como preencher. Este arquivo é a casa única do que muda, e quem o lê é o dono: escreva em
     linguagem comum, falando com ele. A cada atualização, substitua o bloco inteiro e troque a
     data do título: não empilhe parágrafos datados (o histórico mora no git e no registro de
     decisões). Não mude os títulos: o diagnóstico lê a data, e os outros documentos citam as
     listas pelo nome. Lista sem item leva "Nada.", para a sessão seguinte saber que foi olhada.
     Item que nasceu de uma decisão cita o número do registro. Identificador, endereço interno e
     dado pessoal se escrevem pelo papel; segredo não entra. Enquanto não houver ambiente remoto,
     a linha dele diz só "ainda não existe". Apague os comentários ao preencher. -->

## Estado em {{AAAA-MM-DD}}

{{Em uma frase: onde o projeto está e o que vem a seguir.}}

### Ambientes

- **Ambiente local:** {{o que está no ar e como você abre}}.
- **Ambiente remoto:** aplicado até {{a última mudança no banco que já está lá}}, em
  {{AAAA-MM-DD}}, {{a pedido de quem}}. **Ainda não aplicado:** {{o que só existe no ambiente
  local e o que depende disso para ir a produção; ou "nada"}}.

### Verificações automáticas: última rodada

<!-- Cole inteira a linha "escada:" que escada.py imprime e, abaixo, a contagem por degrau copiada
     da saída dos comandos: é por ela que a sessão seguinte percebe se o número caiu. -->

As verificações rodam em ordem, da mais barata à mais cara: é a escada, e cada uma é um degrau.

{{escada: a linha colada}}

- Degrau {{número}} ({{nome}}): {{quantos testes passaram, copiado da saída}}.

### Para decidir

- {{O problema, as opções, a que estou seguindo por padrão e o risco de deixar como está.}}

### Passos do dono

- {{O que só você consegue fazer, onde está o passo a passo e para quando precisa estar pronto.}}

### Autorizações não dadas

- {{A ação que sei fazer e não faço sem o seu sim, e o que fica parado enquanto isso.}}

### Ficou para depois

- {{O que foi adiado, pelo nome}}. Adiado em {{AAAA-MM-DD}}, por {{prazo ou orçamento}}. Retomar
  em {{AAAA-MM-DD ou gatilho}}. Até lá: {{o que fica sem cobertura}}.

### Pendência aceita

- {{O risco conhecido, o que ele expõe, o cuidado até lá e o que fecha.}}

### Como trabalhamos aqui

- **Perfil do dono:** {{nunca programou | dev}}.
- **Palavra de liberação:** "validado" (para a especificação, "aprovado").
- **Na sua máquina, não derrubo:** {{o que você deixa aberto, e a porta que os testes usam}}.
- **Banco do ambiente local:** {{recriar apaga o que você cadastrou: aviso antes | nada seu lá}}.
