# Ambientes: como arrumar ambientes e segredos para o descuido cair no lugar seguro?

Leia quando: fase de base (§1); o dono colou uma chave (§2); antes de rodar comando que lê arquivo
de ambiente (§1); antes de rodar algo pesado, ou que recria o banco, na máquina do dono (§4).
Não é aqui: a ordem de ida a produção (`references/producao.md`).

## O mínimo

- Mantenha um arquivo de ambiente por alvo, e só o exemplo no git.
- O arquivo que as ferramentas carregam sozinhas aponta para o ambiente local: o descuido cai ali.
- Segredo colado na conversa não se repete, nem em parte, e se troca.
- Dados de exemplo (seed) e contas de teste não vão ao ambiente remoto.
- Rode um processo pesado por vez na máquina do dono, e não derrube o que ele deixa aberto.
- O banco local também tem dono: avise antes de recriar.

Conteúdo: 1. Um arquivo por alvo 2. Segredo colado na conversa 3. O que não vai ao remoto nem ao
git 4. A máquina do dono também é ambiente 5. O que a credencial alcança

## 1. Um arquivo por alvo

| Arquivo | Aponta para | Quem carrega | No git |
| --- | --- | --- | --- |
| Local, o padrão das ferramentas | o ambiente local, com chaves de teste | as ferramentas, sozinhas | não |
| Remoto | o ambiente remoto | só o comando que o cita pelo nome | não |
| Exemplo | nada: traz só os nomes das variáveis | ninguém | sim |

1. Ignore no git todos os arquivos de ambiente e reinclua só o exemplo.
2. Dê ao arquivo remoto um nome que nenhuma ferramenta carrega sozinha: ele só entra por opção
   explícita do comando. O segredo de produção não fica em arquivo: mora no painel da hospedagem.
3. No código, leia o segredo em um módulo só de servidor, separado do módulo de variáveis
   públicas. É esse módulo que vai em `segredos.caminhos`, em `[zonas]`.

- **Antes de rodar comando que lê arquivo de ambiente,** confira o destino pela linha `ambiente:`
  do diagnóstico, que mostra só nomes de chave. Abrir o arquivo para olhar põe o valor na conversa.
- **Um comando rodou contra o ambiente remoto por engano:** pare, diga ao dono qual foi e o que
  ele pode ter escrito, confira o efeito só com leitura e corrija a arrumação antes de seguir.

## 2. Segredo colado na conversa

O valor já está no histórico. O texto ao dono é o de `assets/modelos/mensagens-ao-dono.md` §6.

1. Não repita o valor, nem em parte: em resposta, comando, arquivo, commit, nota ou estado.
2. Diga que ficou exposto e precisa ser trocado. Trocar é passo do dono, no painel do serviço.
3. Diga onde a chave nova mora: a de produção, no painel da hospedagem; a de teste, no arquivo de
   ambiente local, que o dono preenche. Nenhuma das duas vem para a conversa.
4. Siga com valor de teste, diga o que não funciona sem a chave de verdade e anote a troca em
   "Passos do dono", sem o valor.

- **"Coloca lá para mim":** pôr a chave na hospedagem não entra na lista do agente. É passo do dono.
- **O valor já foi repetido ou gravado:** diga ao dono onde. Fora do git, apague. Dentro do git, o
  histórico guarda, e o que resolve é trocar a chave: reescrever o histórico é ação sem volta.

## 3. O que não vai ao remoto nem ao git

| O quê | Onde fica | Por quê |
| --- | --- | --- |
| Dados de exemplo e contas de teste | Só no ambiente local: o arquivo deles não roda no ambiente remoto | Criariam em produção contas de senha conhecida e dados falsos |
| Material restrito que é o próprio produto, e arquivos pesados | Fora do git: a pasta inteira ignorada, menos o leia-me dela | É o que se vende, e o repositório pode ser copiado |
| Arquivos de ambiente, chaves e certificados | Fora do git | Vazam pelo histórico, que não se apaga |

Preencha `[envio]`, em `metodo.ini`: é dali que `scripts/envio.py` lê o que não pode sair.

```ini
[envio]
; as outras chaves de [envio] ficam como estão. "!" reinclui, e só vale em nunca_enviar
nunca_enviar = .env, .env.*, !.env.example, *.pem, *.key, <pasta do material restrito>/**
; chave de mentira, usada só pelos testes: sem a exceção, envio.py acusa o arquivo a cada envio
excecoes_de_segredo = <pasta dos dados de teste>/**
```

Exceção só para valor de mentira, com o motivo no comentário: ela desliga a conferência no caminho.

- **Foi ao git o que não devia:** diga ao dono, tire do rastreio num commit próprio e acrescente o
  caminho a `nunca_enviar`. Se era segredo, vale a §2.
- **Dados de exemplo foram ao ambiente remoto:** liste o que foi criado e pergunte antes de apagar.

## 4. A máquina do dono também é ambiente

- **Um processo pesado por vez.** Build, ponta a ponta e duas subidas da escada ao mesmo tempo
  travam máquina de pouca memória. `scripts/escada.py` recusa a segunda subida.
- **Servidor de desenvolvimento com horas de uso degrada** e faz teste falhar ao acaso. Reinicie o
  que o agente abriu; o resultado que vale é contra o build de produção.
- **O que o dono deixa aberto não se derruba.** Teste contra o build roda em outra porta. Anote o
  que é dele em "Como trabalhamos aqui", no estado.
- **O banco local tem dono.** É a casa deste fato. O degrau do banco recria um banco de teste com
  nome próprio, e não o de desenvolvimento, onde o dono cadastrou coisas à mão. Se a stack não
  separa os dois, avise antes de cada subida que recria, e anote isso em "Como trabalhamos aqui".
  Recriado sem aviso: diga o que se perdeu. O que o dono cadastrou não volta com o comando.

## 5. O que a credencial alcança

A listagem da ferramenta não é o limite da credencial: a mesma conta pode alcançar um ambiente
antigo, com gente de verdade, que a ferramenta nem mostra.

- Antes da primeira escrita fora do ambiente local, pergunte ao dono que ambientes e projetos a
  conta alcança, inclusive os antigos.
- Anote no estado, pelo papel, o ambiente que não se toca ("o ambiente remoto antigo") e o
  endereço de nome parecido que não é do projeto.
- Em todo comando contra o ambiente remoto, diga o alvo pelo nome, e não "o padrão da ferramenta".

## O que evitar

- **O atalho de comando do projeto escolhe o ambiente por conta própria.** Quem roda não vê para
  onde foi. O atalho não escolhe: o leia-me mostra a linha do ambiente local e a de produção.
- **Um serviço do ambiente local que o projeto não usa falha ao subir e trava o resto.** Desligue-o
  na configuração, com o motivo escrito no próprio arquivo.
- **O comando funciona num terminal e falha no da máquina do dono.** Sintaxe de um shell usada em
  outro, ou ferramenta fora do caminho de busca. Guarde numa nota de memória a forma que funcionou.

## Pronto quando

- [ ] O arquivo carregado por padrão aponta para o ambiente local, e só o exemplo está no git.
- [ ] O segredo é lido em um módulo só, e esse módulo está em `segredos.caminhos`.
- [ ] `[envio]` lista o que não pode sair, e cada exceção de segredo tem o motivo no comentário.
- [ ] Nenhum valor colado foi repetido nem gravado, e a troca está em "Passos do dono".
- [ ] O degrau 3 recria um banco de teste com nome próprio, ou o aviso está no estado.
- [ ] O estado diz o que não derrubar na máquina e que ambiente a credencial alcança e não se toca.

Volte ao `SKILL.md`, §7.
