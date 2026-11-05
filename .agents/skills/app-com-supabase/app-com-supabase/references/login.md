# Login por código no e-mail: como a pessoa entra e continua dentro?

Leia quando: for montar ou consertar o login, a sessão, o e-mail do código ou o formulário
obrigatório depois do primeiro acesso (passo 5 do fluxo).
Não é aqui: os clientes e o proxy em detalhe (`references/clientes-e-chaves.md`); login por
senha, login social e link mágico, que esta skill não cobre.

## O mínimo

- O login roda em ação de servidor. O navegador não fala com o Auth, e quem grava o cookie da
  sessão é o servidor.
- O tamanho do código é configuração do painel: o validador aceita a faixa, não um número fixo.
- A sessão dura enquanto o cookie durar e o proxy renovar. Limite de sessão ligado no painel
  derruba o login antes.
- E-mail de verdade pede SMTP próprio, e os dois modelos de e-mail mostram o código.
- Painel é do dono: SMTP, modelos, tamanho do código, limites e endereço do site.

Conteúdo: 1. O desenho 2. Enviar 3. Conferir 4. Tamanho do código 5. Sessão longa 6. E-mail
7. Formulário obrigatório 8. Para onde voltar 9. No banco local 10. Passos do dono

## 1. O desenho

| Passo | Quem | O que faz |
| --- | --- | --- |
| 1 | tela | pede o e-mail e chama a ação de enviar |
| 2 | ação `sendLoginCode` | valida o e-mail e chama `signInWithOtp` com o cliente de servidor |
| 3 | Supabase Auth | manda o e-mail com o código |
| 4 | ação `verifyLoginCode` | valida, chama `verifyOtp` com `type: "email"`, e o cliente de servidor grava os cookies |
| 5 | a mesma ação | confere o formulário obrigatório e redireciona |

Molde: `assets/moldes/login-por-codigo.ts`. As três ações (enviar, conferir, sair) são a exceção
à regra da guarda: criam e encerram a sessão. Nada nelas lê ou grava dado do produto.

## 2. Enviar o código

- `signInWithOtp({ email, options: { shouldCreateUser: true } })` cria a conta no primeiro login.
  A resposta da ação é a mesma para conta nova e antiga: se mudar, a tela revela quem tem conta.
- Normalize o e-mail (sem espaços, minúsculas) e limite a 254 caracteres antes de chamar.
- No registro de erro vão o status e o código do erro, sem o e-mail.
- Mensagem ao usuário por tipo de erro (limite de envio, e-mail recusado): os códigos de erro do
  Auth são a conferir na documentação do Supabase. Sem isso, uma frase única serve.

## 3. Conferir o código

- `verifyOtp({ email, token, type: "email" })`, no cliente de servidor: é ele que grava os
  cookies da sessão na resposta da ação, e o redirecionamento seguinte já chega logado.
- Aceite o código colado com espaço ou hífen ("123 456"): tire os dois antes de validar.
- Dando certo, a ação redireciona e não devolve valor. O `redirect` funciona lançando: fica fora
  de `try/catch`.
- A leitura seguinte usa o mesmo cliente: só ele conhece a sessão nova. Os cookies da requisição
  ainda são os de visitante.

## 4. O tamanho do código vem do painel

No banco local o tamanho está em `supabase/config.toml` (`otp_length`, em `[auth.email]`); no
projeto remoto, no painel, e pode ser outro. No projeto de origem a tela aceitava de 6 a 10
dígitos. A faixa exata que o painel permite é a conferir na documentação do Supabase.

- Validador: `^\d{6,10}$`, depois de tirar espaço e hífen.
- Campo da tela: `inputmode="numeric"`, `autocomplete="one-time-code"`, sem `maxlength` de 6.
- Texto da tela: "o código que chegou no seu e-mail", sem dizer quantos dígitos.

Sintoma do erro: o login funciona no banco local e, em produção, "código inválido" sempre.

## 5. Sessão longa

| Peça | Fato | Onde foi visto |
| --- | --- | --- |
| Cookie | o pacote `@supabase/ssr` grava com validade de 400 dias, `path=/`, `sameSite=lax` e sem `httpOnly`: script da página alcança, então XSS é roubo de sessão | na versão 0.12 do pacote |
| Token de acesso | curto (`jwt_expiry`, 3600 s no banco local) e trocado pelo token de renovação | `config.toml` |
| Renovação | o proxy chama `getClaims()` a cada requisição e grava os cookies novos | `assets/moldes/clientes.ts` |
| Limites do painel | "tempo máximo de sessão" e "tempo de inatividade" (`timebox` e `inactivity_timeout` em `[auth.sessions]`) derrubam a sessão antes do cookie | deixe desligados |

- Componente de servidor não grava cookie. Sem o proxy, a pessoa cai quando o token de acesso
  vence, em cerca de 1 hora.
- O proxy só renova. Proteção de rota fica na página e na ação: um padrão de rotas errado no
  proxy vira sessão que vence cedo, e não falha de segurança.
- `getClaims()` confere o token; o usuário lido direto do cookie por `getSession()` não é
  confiável no servidor (aviso do próprio pacote).
- Sair: `signOut({ scope: "local" })` encerra só este aparelho. O padrão do pacote e o efeito de
  cada escopo são a conferir na documentação.

## 6. E-mail: SMTP próprio e modelos

- **O e-mail embutido do Supabase não serve para produção.** No projeto de origem só entregava à
  equipe do projeto e com limite baixo por hora; os números atuais são a conferir na documentação.
  O dono liga um SMTP próprio no painel, com um domínio verificado no provedor de e-mail.
- **O limite de e-mails por hora** só ficou editável depois do SMTP próprio. Cada login gasta um
  e-mail: o dono sobe o limite para o pico esperado.
- **Dois modelos mostram o código.** Quem já tem conta recebe o modelo "magic link"; quem é novo
  recebe o de "confirmação de cadastro" quando a confirmação de e-mail está ligada. Os dois
  levam `{{ .Token }}` e nenhum link. Com um só trocado, metade das pessoas recebe um link.
- **No banco local** os modelos são arquivos em `supabase/templates/`, apontados em
  `config.toml` (`[auth.email.template.magic_link]` e `[auth.email.template.confirmation]`). O
  projeto remoto não lê esse arquivo: o dono cola o mesmo HTML no painel.

## 7. Formulário obrigatório depois do primeiro login

1. Uma tabela `profiles`, com `user_id` como chave e as respostas. "Já respondeu" é ter a linha.
2. Depois do `verifyOtp`, a ação lê a linha com o mesmo cliente. Sem linha, redireciona para o
   formulário e leva o `next` junto.
3. Um portão na casca do aplicativo cobre quem entra por outra porta (sessão antiga, link direto).
4. A ação que grava valida o conteúdo de novo no servidor: quem pode gravar a própria linha pode
   gravá-la direto pela API, sem a tela.
5. Leitura que falha libera. Banco fora do ar não pode prender ninguém no formulário.

O formulário é passo de experiência, não permissão: nenhuma policy depende dele.

## 8. Para onde voltar

O `next` que vem da URL só vale se for caminho interno: começa com uma barra, o segundo
caractere não é barra, sem barra invertida nem caractere de controle, até 512 caracteres. Uma
função só (`safeNextPath`) decide, usada ao montar o endereço de login e ao redirecionar. Sem
isso, um link de login leva a pessoa para outro site depois de entrar.

## 9. No banco local

- O Supabase local sobe uma caixa de e-mail de teste: todo código cai nela, e o endereço aparece
  na saída de `supabase start`. Nenhum e-mail sai para fora.
- Teste de ponta a ponta do login lê o código nessa caixa. Para ele não travar, suba os limites
  de `[auth.rate_limit]` em `config.toml`, com um comentário dizendo que é só local.
- `site_url`, em `[auth]`, é o endereço local. No remoto o endereço do site é do painel.

## 10. Passos do dono, no painel do projeto remoto

Os nomes dos menus mudam: confira na documentação do Supabase. Entregue esta lista ao dono.

- [ ] Ligar o SMTP próprio, com remetente de um domínio verificado.
- [ ] Colar os dois modelos de e-mail, com o código e sem link.
- [ ] Escolher o tamanho e a validade do código.
- [ ] Subir o limite de e-mails por hora.
- [ ] Deixar o cadastro por e-mail ligado, se a conta nasce no primeiro login.
- [ ] Deixar desligados os dois limites de sessão.
- [ ] Conferir o endereço do site e os endereços de retorno permitidos.

## O que evitar

- **Guardar "logado" em estado do navegador.** A verdade é o cookie conferido no servidor.
- **Dizer "e-mail não cadastrado".** Revela quem tem conta.
- **Pedir a senha do SMTP na conversa.** O dono cola no painel.

## Pronto quando

- [ ] No banco local: pedir o código, ler na caixa de teste, entrar, recarregar e continuar dentro.
- [ ] Código errado e código vencido dão mensagem, sem sessão.
- [ ] Primeiro login cai no formulário; o segundo, não.
- [ ] O dono recebeu a lista da §10.
