<!-- MODELO. Nada aqui vale como instrução enquanto não for preenchido e gravado no projeto. -->
# Mensagens ao dono

<!-- Oito textos para copiar para a conversa: não viram arquivo. Preencha as lacunas e apague os
     comentários e as linhas que ficarem vazias. Os rótulos em negrito são fixos, para o dono
     aprender onde olhar. Termo técnico vai entre parênteses, na primeira vez. -->

## 1. Entrega de uma mudança
<!-- Perfil dev: "Rodei e vi" vira os comandos com a saída; saem as explicações em parênteses. -->

{{O que mudou, em uma frase, pelo que você passa a ver ou a conseguir fazer.}}

- **Rodei e vi:** {{verificação, com o número copiado da saída}}. As verificações automáticas
  subiram até o degrau {{n}} ({{nome do degrau}}).
- **Inferi:** {{o que parece certo e não foi rodado, e por que não deu para rodar}}.
- **Não rodei:** {{verificação que ficou de fora, e onde está anotada}}.

- **Decidi sem perguntar:** {{decisão}}, porque {{motivo}}. Para desfazer: {{como}}.
- **Preciso de você:** {{decisão, passo ou autorização; "nada", se não houver}}.
- **Como conferir:** {{o roteiro do texto 2; ou um passo só, se a mudança é pequena}}.

## 2. Roteiro de validação
<!-- De três a sete passos, pelo menos um "não deve". A última linha é a lista que a palavra de
     liberação autoriza; se nada vai ao ambiente remoto, ela diz isso. Troque "validado" se a
     palavra combinada for outra. Perfil dev: os passos podem ser comandos, com a saída. -->

Para conferir: {{a mudança, em uma frase}}. Está rodando só na sua máquina, em {{endereço local}}.
Nada foi enviado: o que as pessoas usam não mudou.

1. Abra {{caminho}}. Deve aparecer {{o quê}}.
2. Clique em {{o quê}}. Deve {{acontecer o quê}}.
3. No celular, ou com a janela estreita, abra {{caminho}}. Deve {{o quê}}.
4. Sem entrar na conta, abra {{caminho}}. **Não** deve aparecer {{o quê}}.

Não está nesta entrega: {{o quê}}. Se algo estiver diferente, diga o número do passo e o que
apareceu.

Depois do seu "validado", nesta ordem: 1) {{banco}}; 2) {{dados}}; 3) {{código}}. Só isso.

## 3. Em que pé estamos
<!-- Leia o estado do disco antes. Contagem, não estimativa. Perfil dev: cole a linha `escada:`. -->

Em {{AAAA-MM-DD}}: {{onde o projeto está, em uma frase}}.

- **Fases:** {{x}} de {{y}} prontas. Em andamento: Fase {{n}} · {{nome}}, com {{a}} de {{b}} itens
  de "Pronto quando" marcados.
- **Falta nesta fase:** {{os itens abertos, pelo que você vai ver}}.
- **Rodei e vi:** {{a última rodada das verificações, com a data}}. **Não rodei:** {{o quê}}.
- **Fora da sua máquina:** {{o que as pessoas usam hoje; o que ainda não foi aplicado lá}}.
- **Com você:** decidir {{…}}; fazer {{…}}; autorizar {{…}}.
- **Ficou para depois:** {{item}}, para retomar em {{AAAA-MM-DD}}.

Não dou prazo: não tenho base para estimar. O que consigo contar são as fases e os itens.
Próximo passo: {{o quê}}. Estou esperando: {{a palavra ou a decisão que destrava; "nada"}}.

## 4. Fim de fase
<!-- Depois da escada inteira e da revisão. Perfil dev: a tabela de achados no lugar da frase. -->

A Fase {{n}} · {{nome}} terminou na sua máquina. {{O que você passa a conseguir fazer.}}

- **Pronto quando:** {{a}} de {{b}} itens marcados. {{O item que ficou aberto, e para onde foi.}}
- **Revisão:** {{n}} achados: {{n}} corrigidos, {{n}} recusados com motivo, {{n}} com você.
  {{Com um agente só: "Quem revisou foi quem escreveu: a independência é limitada."}}

{{Os seis rótulos do texto 1. Em "Rodei e vi", a escada inteira, com os números de cada degrau.}}

A próxima é a Fase {{n}} · {{nome}}. Começo depois de você conferir esta.

## 5. Ação barrada
<!-- Pare antes de escrever isto. Não tente outro caminho para o mesmo fim. Perfil dev: igual. -->

As permissões desta conversa barraram uma ação, e eu não tentei outro caminho.

- **O que eu ia fazer:** {{a ação exata}}.
- **Para quê:** {{o que ela resolve}}.
- **O que a recusa disse:** "{{motivo}}".
- **Como fica sem ela:** {{o efeito; o que se resolve sozinho, e em quanto tempo}}.
- **Se você quiser fazer:** {{o comando ou o clique}}. A decisão é sua.
- **Anotei em:** `docs/ESTADO.md`, com o que conferir antes de {{a próxima ação relacionada}}.

Sigo com {{o que não depende disso}}.

## 6. Segredo colado
<!-- Não repita o valor, nem em parte. Perfil dev: bastam a primeira frase e o item 1. -->

A {{chave ou senha, pelo nome do serviço}} que você colou ficou gravada nesta conversa: trate como
exposta. Eu não repeti o valor nem gravei em arquivo.

1. Troque no painel de {{o serviço}}. A antiga deixa de valer.
2. A nova não vem para a conversa. A de produção fica em {{o painel da hospedagem}}: {{o passo}}.
   A de teste, você cola em `{{arquivo de ambiente local}}`, que fica só na sua máquina.
3. Até lá, sigo com um valor de teste. {{O que não funciona sem a chave de verdade.}}

Anotei a troca em "Passos do dono".

## 7. Aviso de risco
<!-- Uma vez só, antes de cumprir. Perfil dev: uma linha para o risco, uma para a alternativa. -->

Faço como você pediu. Antes, um aviso, que não vou repetir:

- **O risco:** {{o que pode acontecer, para quem, em que situação}}.
- **A alternativa:** {{o que eu faria no lugar, e o que ela custa}}.
- **Se der errado depois:** {{o primeiro ajuste, e quanto trabalho é}}.

Se você mantiver o pedido, sigo e anoto no registro de decisões que a escolha foi sua.

## 8. A lista para o ambiente remoto
<!-- Quando o dono diz "pode subir" sem lista anterior, ou pede o que não estava nela. Um sim para
     a lista inteira, não um por passo. Perfil dev: os comandos no lugar das frases. -->

Antes de mexer no que as pessoas usam (produção), esta é a lista do que vou fazer, nesta ordem:

1. {{Banco: aplicar a mudança no banco (migração) tal.}}
2. {{Dados: carregar tal coisa. Antes, uma simulação: nela só pode sobrar tal mudança.}}
3. {{Código: enviar. É o que põe a versão nova no ar.}}
4. Conferir como visitante, em {{o endereço que você usa}}. {{Anotar o que foi feito: dizer se a
   anotação é enviada junto ou fica só na sua máquina.}}

- **Não tem volta:** {{o quê; "nada", se não houver}}. Não tenho um jeito pronto de voltar atrás
  nem cópia de segurança: {{o que existe hoje, se existe}}.
- **Sem verificação automática:** {{o degrau que ainda não existe; "nada", se não houver}}.
- **Fica com você:** {{o passo que só você faz, e quando}}.

Paro no primeiro resultado diferente do previsto e aviso. O que aparecer fora da lista, peço de
novo. Responda "sim" para a lista inteira.
