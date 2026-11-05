# Banco, código e armazenamento: o que segura quando a tela erra?

Leia quando: o teste de ponta a ponta já existe e faltam as outras três camadas (passo 6 do
fluxo), ou quando for desenhar onde o conteúdo pago mora.
Não é aqui: criar a matriz de permissões do banco do zero (skill irmã `app-com-supabase`).

## O mínimo

- O conteúdo pago mora separado do registro público, e uma função só o lê.
- Essa função decide o acesso antes de consultar, e o banco confere de novo na consulta.
- No banco, visitante, logado sem plano e ex-assinante leem zero linhas de conteúdo pago.
- Um teste lê o código-fonte e reprova quem lê o conteúdo pago por outro caminho.
- Arquivo pago fica em repositório privado e sai por link assinado de até 60 segundos.

Conteúdo: 1. Por que quatro camadas 2. Banco 3. Código 4. Armazenamento

## 1. Por que quatro camadas

| Camada | O que prova | O que não vê |
| --- | --- | --- |
| Resposta crua (ponta a ponta) | o que de fato sai, por persona e por rota | rota que ficou fora da lista; quem chama o banco direto |
| Banco, por persona | a regra como o banco a impõe, sem o aplicativo no meio | leitura feita com a chave de serviço, que ignora a regra |
| Código-fonte (fronteira) | que só existe um caminho de leitura, e que ele não passa por cache nem por navegador | o que o caminho permitido devolve |
| Armazenamento | que o arquivo não tem endereço público | o texto que está no banco |

A chave pública do banco vai dentro do JavaScript do site: qualquer pessoa pode chamar o banco
direto com ela. Por isso a tela certa não basta, e o teste de banco existe.

## 2. Banco

**Desenho.** O corpo fica em tabela própria, ligada ao item. A leitura pública seleciona da
tabela de itens e nunca traz o corpo, nem com "todas as colunas". A política de leitura da tabela
de conteúdo pergunta a uma função de acesso:

```sql
-- Lê o corpo quem pode ver o item e, se o item é pago, tem o plano. Admin lê tudo.
create policy conteudos_leitura on app_conteudos for select using (
  exists (select 1 from app_itens i where i.id = item_id and (
    (i.status = 'publicado' and (i.acesso = 'livre' or (select app_tem_plano())))
    or (select app_e_admin()))));
```

**Teste.** O molde é `assets/moldes/banco-por-persona.sql`, em Postgres puro. Ele:

1. cria os próprios dados, com marcadores, numa faixa de identificadores que não colide com a
   dos dados de exemplo, e desfaz tudo no fim;
2. vira cada persona pelo caminho que o produto usa e varre **toda** tabela e visão que ela
   consegue ler, procurando a classe proibida;
3. prova que a varredura enxerga: o visitante lê o conteúdo livre, a assinante lê o pago;
4. tenta a autopromoção (o logado insere a própria assinatura; o ex-assinante reativa a dele) e
   varre de novo;
5. confere, de volta ao dono, que nenhuma tentativa ficou gravada.

| Cuidado | Por quê |
| --- | --- |
| Afirme bloqueio só depois de trocar de papel | como dono do banco a política é ignorada e tudo passa |
| Ao trocar de persona, troque o papel e a identidade | a identidade da anterior continua valendo |
| Alterar barrado por política afeta zero linhas, sem erro | confira pelo efeito, na prova final, e não só pela exceção |
| Função exposta como chamada remota fica fora da varredura | teste cada uma pelo nome, por persona |

**Sem segurança por linha.** Se a permissão mora só no aplicativo, este teste não se aplica: o
banco entrega tudo a quem chega nele. A camada passa a ser o teste da função de leitura (§3) com
cada persona, e a regra "nenhum outro caminho" pesa o dobro. Para montar políticas, privilégios e
o teste de privilégios, use a skill irmã `app-com-supabase`.

## 3. Código

**A função única.** Um módulo só de servidor, com uma função que recebe o item e a pessoa:

```ts
export async function lerConteudoPago(item: ItemPublico, pessoa: Pessoa): Promise<Resultado> {
  if (!podeLer(item, pessoa)) return { estado: "bloqueado" }; // decide ANTES: nenhuma consulta
  const { data, error } = await bancoDaSessao().from("app_conteudos")
    .select("corpo").eq("item_id", item.id).maybeSingle();    // o banco confere de novo
  if (error) throw new Error("não consegui ler o conteúdo");  // erro lança: nunca libera
  return data ? { estado: "ok", corpo: data.corpo } : { estado: "indisponivel" };
}
```

- Três resultados, e não dois: "bloqueado" mostra a oferta, "indisponível" mostra um aviso.
  Misturar os dois faz a tela oferecer o plano a quem já paga.
- A consulta usa o cliente da sessão da pessoa, nunca o da chave de serviço: com a chave de
  serviço a segunda conferência some.
- Erro ao ler a assinatura conta como "sem plano". Erro nunca libera.
- Quem chama é um componente de servidor (ou uma rota), e a tela de bloqueio é outro arquivo, que
  não importa o leitor. O texto nunca é passado a um componente de navegador que decide mostrar.

**As cinco regras.** O molde é `assets/moldes/fronteira.test.ts`. Rodou em Vitest contra um
projeto de brinquedo: passou limpo e reprovou as cinco com dois arquivos violadores plantados.

| Regra | O que impede |
| --- | --- |
| 1. A tabela do conteúdo pago só é citada no leitor e na área de admin | a segunda leitura, escrita com pressa em outra tela |
| 2. A função de leitura só é importada por um arquivo | o texto entregue a um componente que não devia tê-lo |
| 3. Código em cache compartilhado não importa leitura por pessoa nem sessão | a resposta da assinante servida ao visitante |
| 4. Código de navegador não importa o leitor nem os clientes de servidor | o texto, ou a chave, dentro do pacote JavaScript |
| 5. O corpo é selecionado uma vez, no leitor | a listagem que passa a trazer o corpo junto |

O teste prova que enxerga antes de afirmar: leu pelo menos N arquivos, cada pasta contribuiu, e
cada regra acusa um violador plantado em memória e poupa um inocente parecido. Sem isso, uma
pasta renomeada deixa tudo verde. Baixar o mínimo de arquivos até passar não é conserto. Para as
regras de cache do framework (o que pode e o que não pode entrar em função com cache), a skill
irmã é `nextjs-boas-praticas`.

## 4. Armazenamento

| Regra | Por quê |
| --- | --- |
| Arquivo pago em repositório privado, separado do de imagens públicas | endereço público não pergunta quem está pedindo |
| Link assinado gerado no servidor, depois da função de acesso, a cada clique | link gerado ao montar a página vai para o HTML de todo mundo |
| Validade de até 60 segundos | o link é uma chave ao portador: quem o recebe baixa sem pagar |
| O caminho do arquivo não vai ao navegador | com o caminho e um link antigo se monta outro |
| Nome de arquivo sem o título do item, com uma parte sorteada | caminho previsível se adivinha |

Como testar, sem molde próprio (**adaptação**, exceto os dois primeiros itens):

- Na resposta crua, para todas as personas: o nome do repositório privado e o nome da coluna do
  caminho não aparecem (`NOMES_INTERNOS` no molde de vazamento).
- A ação que gera o link, chamada como logado sem plano, devolve erro e não assina nada.
- O endereço público do arquivo pago, pedido sem sessão, responde 4xx.
- Um link assinado, pedido 2 minutos depois, responde 4xx.

Vídeo por transmissão e arquivo servido por rede de distribuição têm regras próprias de
assinatura de endereço: ficam fora desta skill.

## O que evitar

- **Guardar o corpo na tabela do item "porque é mais simples".** Toda leitura pública passa a
  depender de alguém lembrar de tirar a coluna.
- **Ler com a chave de serviço "só para montar a página".** A página montada com tudo vai para o
  cache e para o HTML.
- **Decidir o acesso no navegador.** O navegador é de quem visita.
- **Link assinado de 1 dia "para não dar erro".** Ele circula em grupo de mensagem no mesmo dia.
