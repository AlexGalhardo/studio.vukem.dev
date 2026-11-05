# O que testar: o que cada persona tem de provar?

Leia quando: for escrever os testes de um papel, a guarda do admin, o login pela tela, um
formulário obrigatório ou um rascunho (passos 4 e 5 do fluxo).
Não é aqui: gerar as sessões (`references/personas-e-sessoes.md`); provar que conteúdo pago não
sai do servidor (skill `vazamento-de-paywall`).

## O mínimo

- Para cada tela, escreva o que cada persona vê e o que ela não pode ver. O teste que falta quase
  sempre é o do "não".
- A guarda do admin se prova pela resposta crua, sem seguir o redirecionamento, com um controle
  positivo ao lado.
- O login pela tela tem um teste só, com conta nova e o código lido na caixa de e-mail local.
- Regra de fluxo se testa tentando furar: ir direto à etapa seguinte, avançar sem responder.
- "Não aparece" só vale depois de provar que a página terminou de carregar.

Conteúdo: 1. A matriz 2. Guarda do admin 3. O que cada papel vê 4. Login de verdade 5. Formulário
obrigatório 6. Rascunho que sobrevive 7. Localizadores

## 1. A matriz

Monte esta tabela com o dono antes de escrever. Cada célula vira um teste, e a mesma bateria roda
em laço sobre as personas que dividem a resposta.

| Tela | Visitante | Logado | Assinante | Admin |
| --- | --- | --- | --- | --- |
| Página pública | vê, com o convite para assinar | vê | vê, com o selo do plano | vê |
| Conta | vai ao login, com o caminho de volta | vê os dados dele, sem plano | vê o plano ativo e o botão de gerenciar | vê |
| Conteúdo pago | vê a prévia e o convite | vê a prévia e o convite | vê o conteúdo | vê |
| Área de admin | vai ao login | "não encontrado" | "não encontrado" | entra |

```ts
for (const { persona, estado } of SEM_ACESSO) {
  test.describe(`conteúdo pago para ${persona}`, () => {
    test.use({ storageState: estado });
    // a mesma bateria, com o nome da persona no título
  });
}
```

## 2. Guarda do admin

Molde: `assets/moldes/guarda-admin.spec.ts`. Ele tem cinco peças, e nenhuma é dispensável:

| Peça | O que prova | Sem ela |
| --- | --- | --- |
| Lista conferida | o número de arquivos de página restrita é igual ao tamanho da lista de rotas | página nova nasce sem teste, e ninguém percebe |
| Controle positivo | como admin, todo marcador aparece em alguma resposta | marcador que mudou de nome faz o resto passar à toa |
| Resposta crua | para visitante, logado e assinante, nenhuma rota traz marcador, sem seguir o redirecionamento | a guarda pode ser só visual |
| Visitante | vai ao login com o caminho de volta da página pedida, não um fixo | depois do login a pessoa cai no lugar errado |
| Logado sem papel | vê o mesmo "não encontrado" de uma rota que não existe | a resposta confirma que a área existe |

Por que a resposta crua: no sistema de origem a guarda estava só na casca da área de admin, e o
framework renderizava a página mesmo assim. Visitante e logado recebiam as telas no corpo da
resposta, limitadas só pela permissão do banco. O teste de tela ("fui redirecionado") passava.

- Use `request.get(rota, { maxRedirects: 0 })`. Seguir o redirecionamento examina a página de
  login, que não tem marcador nenhum.
- Marcador é um texto que só a tela restrita tem: identificador de teste, rótulo de botão, nome de
  campo interno, o título de um rascunho dos dados de exemplo.
- Confira o corpo e a tela, não o código de status: em framework que envia a página em pedaços o
  status pode ser 200 com a guarda funcionando.
- A guarda de verdade mora em cada página e em cada leitura do servidor. Onde colocá-la: skills
  `app-com-supabase` e `nextjs-boas-praticas`.

## 3. O que cada papel vê e não vê

- **Prove a carga antes do "não".** `toHaveCount(0)` passa numa página que ainda não carregou.
  Primeiro espere algo que só existe com a tela pronta (o título, o convite do visitante), depois
  afirme a ausência.
- **Só os dados da própria pessoa.** O assinante vê os itens salvos dele: confira a contagem exata
  dos dados de exemplo, não "pelo menos um".
- **Duas telas válidas.** Sem as chaves do serviço externo (o CI roda assim), a oferta dá lugar a
  um aviso. Afirme `oferta.or(aviso)` visível e o esqueleto de carregamento ausente.
- **Não afirme o que depende do dia.** Selo de "novo", ordem por uso, "vigente desde ontem": deixe
  fora, e escreva no cabeçalho do arquivo por quê.
- **Mensagem de erro vem da fonte única do aplicativo.** O teste importa a constante em vez de
  repetir o texto.

## 4. Login de verdade

Molde: `assets/moldes/login.spec.ts`. Um arquivo, porque é o único que depende do envio de e-mail.

1. Conta nova por teste: `emailDeTeste(...)`, com o projeto e o processo no rótulo.
2. Peça o código pela tela e leia o e-mail na caixa de captura local, pela API dela, com
   `expect.poll` e limite de 30 s. A mensagem de falha diz para quem o e-mail não chegou.
3. Tire o código do corpo sem as tags: uma cor em hexadecimal no HTML pode parecer um código.
4. Afirme: o destino depois do login; o cookie de sessão com a duração que o produto promete; o
   caminho de volta externo ignorado (`https://…` e `//…`); a saída, que devolve a rota protegida
   ao login.
5. O `afterAll` apaga as contas que o processo criou e as sobras antigas.

Os testes do arquivo rodam em fila (`test.describe.configure({ mode: "default" })`): o serviço de
login limita pedidos por origem, e vários códigos ao mesmo tempo estouram o limite. Desktop e
celular continuam em paralelo entre si.

Conta nova cai nos passos obrigatórios do primeiro acesso. É a deixa para o item 5.

## 5. Formulário obrigatório que não pode ser pulado

A obrigatoriedade mora no servidor. O teste a prova tentando furar, com uma conta própria (ela
grava a resposta):

| Tentativa | O que afirmar |
| --- | --- |
| Abrir outra rota do aplicativo antes de responder | volta ao formulário |
| Ir direto ao endereço da etapa seguinte | volta à etapa pendente |
| Avançar sem responder tudo | fica na etapa, com o erro em cada pergunta que faltou |
| Procurar um botão de pular ou a ação final antes da hora | `toHaveCount(0)`, depois de provar a carga |
| Persona que já respondeu | não vê o formulário |
| Responder tudo | grava uma vez (confira a linha no banco) e só então libera o resto |

As tentativas 1, 3, 4 e 6 saíram de testes em uso; a 2 e a 5 são propostas, ainda não rodadas.

## 6. Rascunho que sobrevive a recarregar

1. Responda metade, avance uma etapa e chame `page.reload()`.
2. Afirme os valores nos campos e a etapa em que a pessoa estava.
3. Afirme que o rascunho é da pessoa: outra persona, no mesmo navegador, começa do zero.
4. Envie e reabra: o rascunho foi limpo, e o envio não se repete.

Os passos 1 e 2 saíram de um teste em uso; o 3 e o 4 são propostas, ainda não rodadas.

Marque uma opção como a pessoa faz, clicando no rótulo, e confira o estado no campo de verdade. O
campo pode estar escondido só para os olhos.

## 7. Localizadores

- Por papel acessível e nome (`getByRole`), ou por rótulo (`getByLabel`). Texto solto acha dois
  elementos quando a tela anterior continua escondida no documento.
- Identificador de teste para contêiner sem papel (uma grade, um painel), com `:visible` quando há
  cópia escondida.
- Alvo de toque: meça a caixa do elemento (`boundingBox`) e afirme 44 px ou mais, no celular.

## Pronto quando

- Cada célula da matriz tem um teste, e o título do teste traz a persona.
- Tirar a guarda de uma página de propósito deixa vermelha a resposta crua, e criar uma página
  restrita sem pôr a rota na lista deixa vermelha a lista conferida.
- O teste de login passa três vezes seguidas, sem repetição automática.
