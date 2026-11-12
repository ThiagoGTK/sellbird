# Guia do Sellbird em português

Este guia cobre a versão traduzida e adaptada para o Brasil do
[Sellbird](https://github.com/ethanplusai/sellbird): instalação (Windows, macOS
e Linux), configuração, uso no dia a dia e os problemas mais comuns.

**Sumário**

1. [O que é e o que você precisa](#1-o-que-é-e-o-que-você-precisa)
2. [Instalação no Windows](#2-instalação-no-windows)
3. [Instalação no macOS e no Linux](#3-instalação-no-macos-e-no-linux)
4. [Jeito mais fácil: deixar o Claude configurar](#4-jeito-mais-fácil-deixar-o-claude-configurar)
5. [Configuração passo a passo](#5-configuração-passo-a-passo)
6. [Como o idioma de cada e-mail é escolhido](#6-como-o-idioma-de-cada-e-mail-é-escolhido)
7. [LGPD e boas práticas](#lgpd-e-boas-práticas)
8. [Uso no dia a dia](#8-uso-no-dia-a-dia)
9. [Atualizar com o projeto original](#9-atualizar-com-o-projeto-original)
10. [Problemas comuns](#10-problemas-comuns)
11. [O que foi alterado no código](#11-o-que-foi-alterado-no-código)

---

## 1. O que é e o que você precisa

O Sellbird é um robô de prospecção por e-mail frio que roda no seu computador.
Ele encontra empresas, lê o site delas, descobre quem decide, confere o e-mail,
escreve um e-mail personalizado para cada pessoa, envia e cuida das respostas.
Por padrão, **todo e-mail espera a sua aprovação** antes de sair.

| Item | Para quê | Custo |
|---|---|---|
| **Claude Pro ou Max** + Claude Code | É o "cérebro": escreve e-mails e respostas | A assinatura que você já tem |
| **Python 3.11 ou mais novo** | Roda o Sellbird | Grátis |
| **Git** | Baixar e atualizar o projeto | Grátis |
| **Uma caixa de e-mail para envio** | Gmail/Google Workspace, Microsoft 365 ou SMTP (Hostinger, Locaweb, Zoho...) | A partir de ~R$ 0 (se já tiver) |
| **Um verificador de e-mail** (Reoon) | Confirmar que o e-mail existe antes de enviar | Grátis até 600/mês |
| **Aquecimento da caixa** (TrulyInbox ou outro) | Não cair no spam | Pago (opcional, mas recomendado) |

> **Use um domínio secundário para enviar.** Se o seu site é `minhaempresa.com.br`,
> envie de algo como `minhaempresa-contato.com.br` ou `useminhaempresa.com.br`.
> Assim, se a reputação de envio cair, o e-mail do dia a dia da empresa não é afetado.
> Configure SPF, DKIM e DMARC nesse domínio e aqueça a caixa por 2 a 4 semanas.

---

## 2. Instalação no Windows

Tudo abaixo é no **PowerShell** (menu Iniciar → digite "PowerShell"). Não precisa
abrir como administrador.

### 2.1 Python, Git e Claude Code

```powershell
# Python 3.13 e Git pelo winget (já vem no Windows 10/11)
winget install Python.Python.3.13
winget install Git.Git

# Claude Code (instalador oficial)
irm https://claude.ai/install.ps1 | iex
```

Feche e abra o PowerShell de novo (para ele achar os programas novos) e entre no
Claude Code uma vez com a sua conta Pro/Max:

```powershell
claude
```

Ele abre o navegador para você entrar. Depois de logado, saia com `/exit`.
Instruções oficiais: https://code.claude.com/docs/en/setup

### 2.2 Baixar o Sellbird (esta versão em português)

```powershell
cd $HOME\Documents
git clone -b pt-br https://github.com/ThiagoGTK/sellbird.git   # -b pt-br = o ramo com a tradução
cd sellbird
```

### 2.3 Criar o ambiente virtual e instalar

```powershell
py -3.13 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

Se aparecer um erro dizendo que **a execução de scripts está desabilitada**,
rode uma vez e tente ativar de novo:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Teste:

```powershell
sellbird --help
```

> Toda vez que abrir um PowerShell novo, entre na pasta e ative o ambiente:
> `cd $HOME\Documents\sellbird` e `.venv\Scripts\Activate.ps1`.

Opcional, só se for usar a prospecção no LinkedIn:

```powershell
python -m playwright install chromium
```

> **Observação:** no Windows, o Sellbird funciona com o **Claude**. O Codex (plano
> do ChatGPT) só funciona no macOS e no Linux.

---

## 3. Instalação no macOS e no Linux

```bash
# macOS: o python3 do sistema é velho (3.9). Instale um mais novo:
brew install python@3.13

# Claude Code
curl -fsSL https://claude.ai/install.sh | bash
claude        # entre com a sua conta e saia com /exit

git clone -b pt-br https://github.com/ThiagoGTK/sellbird.git
cd sellbird
python3.13 -m venv .venv && source .venv/bin/activate && pip install -e .
sellbird --help
```

---

## 4. Jeito mais fácil: deixar o Claude configurar

Dentro da pasta do Sellbird (com o ambiente ativado), abra o Claude Code:

```bash
claude
```

E diga: **"configure o Sellbird para mim"**. O arquivo `CLAUDE.md` do projeto
transforma o Claude no guia de instalação: ele confere o que falta, instala,
pergunta uma coisa de cada vez e treina o Sellbird no seu produto, em português.

Se preferir fazer à mão, siga a próxima seção.

---

## 5. Configuração passo a passo

### 5.1 Chaves e senhas (`.env`)

```powershell
copy .env.example .env      # no macOS/Linux: cp .env.example .env
notepad .env                # ou o editor que preferir
```

Cada variável está explicada no próprio arquivo. O mínimo:

**Um provedor de e-mail** (escolha um e defina o mesmo em `channels.email.provider`):

- **Gmail / Google Workspace** (`provider: gmail`): crie um cliente OAuth do tipo
  "App para computador" no Google Cloud Console (Gmail API ativada), cole
  `GMAIL_CLIENT_ID` e `GMAIL_CLIENT_SECRET` e rode `sellbird gmail auth`.
- **SMTP** (`provider: smtp`), por exemplo e-mail da Hostinger:
  ```
  SMTP_HOST=smtp.hostinger.com
  SMTP_PORT=587
  SMTP_USERNAME=contato@seudominio-envio.com.br
  SMTP_PASSWORD=sua-senha
  IMAP_HOST=imap.hostinger.com
  IMAP_PORT=993
  ```
  (Locaweb, Zoho, KingHost etc. funcionam igual; confira os servidores no painel do seu provedor.)
- **Microsoft 365** (`provider: microsoft`): veja o passo a passo no `.env.example`.

**Um verificador de e-mail**: crie uma conta grátis no [Reoon](https://reoon.com/email-verifier)
e coloque a chave em `REOON_API_KEY`. Sem verificador, os e-mails encontrados
ficam como "palpite" e **nunca são enviados**.

### 5.2 Configuração (`sellbird.yaml`)

O `sellbird.yaml` já vem em português e com padrões brasileiros (idioma `pt-BR`,
fuso `America/Sao_Paulo`). Os pontos que você precisa olhar:

```yaml
channels:
  email:
    provider: "smtp"            # ou gmail / microsoft
    max_daily_sends: 50
    require_approval: true      # todo e-mail espera sua aprovação

language:
  default: "pt-BR"              # idioma quando não dá para saber o país
  by_country: true              # Brasil em português, exterior em inglês

compliance:
  postal_address: "Sua Empresa Ltda · Rua Exemplo, 100 · Curitiba/PR"
  opt_out_line_pt: "Não faz sentido pra você? É só me avisar que não envio mais e-mails."
```

> Quando você roda `sellbird train`, ele grava um `sellbird.local.yaml` com tudo
> que aprendeu. **Esse arquivo tem prioridade** sobre o `sellbird.yaml`: depois do
> treino, faça os ajustes nele.

### 5.3 Treinar com o seu site

```bash
sellbird train https://seusite.com.br
```

O Sellbird lê o site e escreve, em português: o que você vende, benefícios, preço,
cliente ideal (segmentos, cargos, porte), objeções e concorrentes. Revise o
`sellbird.local.yaml` e os arquivos `skills/product_knowledge.md` e
`skills/competitive_intel.md` gerados.

### 5.4 Definir a oferta

Todo primeiro e-mail termina oferecendo **uma coisa grátis e útil** ligada ao que
o Sellbird encontrou sobre a empresa (ex.: "um diagnóstico gratuito do funil de
vendas", "um protótipo da página inicial com agendamento online"). Ela decide mais
respostas do que qualquer outra linha.

Abra o painel (`sellbird dashboard`) → **Sua empresa → Sua oferta**. Use
**Sugerir ideias** e **Ver um e-mail de exemplo** até ficar bom, e salve.

### 5.5 Confirmar os sinais

Sinais são os fatos que o Sellbird coleta sobre cada empresa (sem agendamento
online, anuncia no Google, está contratando...). **Nada é coletado até você
confirmar.** Para ligar tudo que é grátis:

```bash
sellbird signals --confirm free
```

Ou revise um por um no painel, aba **Sinais**.

### 5.6 Encontrar empresas

A fonte padrão é o **OpenStreetMap**: grátis e sem conta.

```bash
sellbird discover --estimate                         # mostra o que vai buscar, sem gastar
sellbird discover --city "Curitiba, PR, Brasil"      # roda a busca
```

- Escreva as cidades com o estado e o país: `"Londrina, PR, Brasil"`,
  `"São Paulo, SP, Brasil"`. Para várias: `"Curitiba, PR, Brasil;Joinville, SC, Brasil"`.
  Você também pode colocar as cidades em `icp.geography` no YAML.
- Os segmentos (`icp.industries`) que a busca grátis entende em português incluem:
  clínica odontológica, odontologia, escritório de advocacia, contabilidade,
  imobiliária, academia, salão de beleza, barbearia, estética, restaurante,
  pizzaria, cafeteria, pet shop, veterinária, ótica, oficina mecânica, autopeças,
  autoescola, hotel, pousada, construtora, material de construção, fisioterapia,
  psicologia, padaria, mercado, farmácia, encanador/hidráulica, eletricista,
  ar-condicionado, paisagismo, telhados.
- A cobertura do OpenStreetMap no Brasil é parcial (muitas empresas não têm site
  cadastrado nele). Para listas maiores, existem fontes pagas (DataForSEO, Serper,
  Scavio): veja `sellbird discover --providers` ou a aba **Descobrir** do painel.

Depois, o Sellbird lê os sites encontrados (grátis) e procura os decisores nas
páginas "Quem somos", "Equipe", "Sobre", "Corpo clínico".

### 5.7 Abrir o painel e ligar

```bash
sellbird dashboard     # mostra um link privado; abra no navegador
sellbird run           # liga o ciclo (deixe esta janela aberta)
```

O ciclo acorda a cada 15 minutos, decide o que fazer (prospectar, escrever,
enviar, responder) e volta a dormir. Os e-mails escritos aparecem na **Caixa de
saída** do painel: leia, edite se quiser e aprove. Atalhos: `A` aprova, `E` edita,
`R` rejeita.

---

## 6. Como o idioma de cada e-mail é escolhido

O Sellbird decide por empresa, nesta ordem (para no primeiro que der resposta):

| Ordem | De onde vem | Exemplo |
|---|---|---|
| 1 | Localização da empresa | "Curitiba, PR", "Recife - Pernambuco", "Brasil" → português |
| 2 | Fuso horário já descoberto | `America/Sao_Paulo` → português |
| 3 | Final do domínio do e-mail ou do site | `.com.br` → português, `.pt` → português de Portugal |
| 4 | País das buscas configuradas | `icp.geography: ["Brasil"]` → português |
| 5 | Padrão (`language.default`) | `pt-BR` |

- Empresas fora do Brasil (EUA, Europa...) recebem e-mail em **inglês**.
- As **respostas** sempre seguem o idioma em que o prospect escreveu.
- Para escrever sempre no mesmo idioma, use `language.by_country: false` e defina
  `language.default`.
- Cada campanha tem um idioma só; as campanhas em português ganham o sufixo
  `-pt-BR` no nome.
- O rodapé de descadastro usa `compliance.opt_out_line_pt` nos e-mails em português
  e `compliance.opt_out_line` nos em inglês.

---

## LGPD e boas práticas

> Isto não é aconselhamento jurídico. Se a prospecção for importante para o seu
> negócio, vale conversar com um advogado especializado em proteção de dados.

O e-mail frio entre empresas (B2B) no Brasil costuma se apoiar na base legal do
**legítimo interesse** (art. 7º, IX, da LGPD, Lei 13.709/2018). Para essa base se
sustentar, as boas práticas são:

- **Relevância real:** só aborde quem tem relação com o que você vende, no papel
  profissional da pessoa. É para isso que servem o ICP e os sinais.
- **Dados profissionais e públicos:** e-mails corporativos encontrados no site da
  empresa ou no padrão do domínio. Nada de listas compradas.
- **Identificação clara:** nome real, empresa e endereço no rodapé
  (`compliance.postal_address`).
- **Saída fácil:** toda mensagem fria tem a linha de descadastro, e o Sellbird
  atende pedidos de saída **na hora e para sempre**, inclusive em português
  ("me descadastre", "não tenho interesse", "sair", "pare de me mandar e-mails").
- **Origem do dado:** se alguém perguntar como você conseguiu o e-mail, responda
  com a fonte. O Sellbird guarda de onde veio cada contato.
- **Volume baixo e aquecimento:** poucos e-mails por dia, de um domínio aquecido.
- Mensagens com ameaça jurídica, menção a Procon, ANPD, LGPD ou "isso é spam" são
  **passadas para você** e nunca respondidas automaticamente.
- Para destinatários nos EUA vale a **CAN-SPAM** (exige endereço postal e um jeito
  de sair); na Europa, a **GDPR**.

---

## 8. Uso no dia a dia

| Comando | O que faz |
|---|---|
| `sellbird dashboard` | Abre o painel (o link aparece no terminal) |
| `sellbird run` | Liga o ciclo |
| `sellbird status` | Resumo do funil no terminal |
| `sellbird outbox` | Lista o que espera aprovação (`--approve <id>`, `--approve-all`, `--reject <id>`) |
| `sellbird discover --city "..."` | Busca empresas |
| `sellbird profile` | Lê os sites das empresas encontradas (grátis) |
| `sellbird signals` | Mostra os sinais (`--confirm`, `--reject`) |
| `sellbird export` | CSV com os contatos válidos (para usar em outra ferramenta) |
| `sellbird sending pause` / `resume` | Botão de emergência: para/retoma todo envio |
| `sellbird warmup` | Confere se o domínio de envio está pronto (SPF, DKIM, DMARC...) |
| `sellbird train <url>` | Treina de novo com um site |
| `sellbird usage` | Uso do Claude/Codex pelo Sellbird |

Para mudar como o Sellbird escreve, edite os arquivos (em português) das pastas:

- `prompts/` — as instruções de cada agente (`writer.md` escreve os e-mails,
  `handler.md` responde).
- `skills/` — os playbooks de vendas (objeções, metodologia, oferta, sinais...).

---

## 9. Atualizar com o projeto original

O projeto original continua recebendo melhorias. Para trazer as novidades:

```bash
git remote add upstream https://github.com/ethanplusai/sellbird.git   # só na primeira vez
git fetch upstream
git merge upstream/main
```

Como esta versão traduziu muitos arquivos, é normal aparecerem **conflitos** nos
textos. O jeito mais fácil é abrir o Claude Code na pasta e pedir: *"resolva os
conflitos do merge mantendo a tradução em português e as novidades do original"*.
Depois rode os testes: `python -m pytest -q`.

---

## 10. Problemas comuns

**"sellbird" não é reconhecido como comando**
Ative o ambiente: `.venv\Scripts\Activate.ps1` (Windows) ou `source .venv/bin/activate`.

**"A execução de scripts foi desabilitada neste sistema" (Windows)**
Rode `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` e ative de novo.

**O Claude não responde / "headless mode" falha**
Rode `claude` uma vez e entre com a conta Pro/Max. Confira com `sellbird status --check`.

**Os e-mails encontrados ficam todos como "palpite" e nada é enviado**
Falta um verificador: coloque `REOON_API_KEY` (ou ZeroBounce/Hunter) no `.env`.

**A busca grátis encontrou poucas empresas**
O OpenStreetMap tem cobertura parcial no Brasil. Tente outros segmentos e cidades,
ou uma fonte paga (veja `sellbird discover --providers`).

**Um e-mail para uma empresa brasileira saiu em inglês**
A localização dela não indicou o Brasil e o domínio não é `.br`. Confira se
`language.default` está como `pt-BR` e escreva as cidades com estado e país
(`"Curitiba, PR, Brasil"`).

**Quero ver tudo o que aconteceu**
Aba **Atividade** do painel, ou o arquivo `data/sellbird.log`.

---

## 11. O que foi alterado no código

Para quem quer entender (ou manter) a tradução:

| Arquivo | Mudança |
|---|---|
| `sellbird/language.py` | **Novo.** Escolhe o idioma por país, detecta português num texto e tem as instruções de idioma para o modelo |
| `sellbird/config.py` | Seção `language`, linha `opt_out_line_pt`, validação da linha de descadastro em português, mensagens em português |
| `sellbird/agents/writer.py` | Uma campanha por idioma e instrução de idioma em cada e-mail |
| `sellbird/agents/handler.py` | Descadastro e escalada em português, resposta no idioma do prospect |
| `sellbird/email_style.py`, `sellbird/gate.py` | Clichês, saudações, despedidas, spam e pedidos de pagamento (Pix, boleto) em português; limites de palavras do português |
| `sellbird/agents/sender.py` | Rodapé em português para e-mails em português |
| `sellbird/collectors/*.py` | Páginas e cargos de sites brasileiros, segmentos em português no OpenStreetMap |
| `sellbird/send_window.py` | Estados brasileiros e seus fusos; "Curitiba, PR" é Paraná quando a operação é no Brasil |
| `sellbird/web/`, `sellbird/dashboard.py`, `sellbird/signals.py` | Painel em português |
| `sellbird/cli.py`, `setup.py`, `trainer.py`, `main.py` | Terminal em português; o treino grava em português |
| `prompts/`, `skills/` | Traduzidos e adaptados ao Brasil |
| `tests/test_portugues.py` | **Novo.** Testes de tudo acima |

Os testes rodam com `python -m pytest -q` (mais de 3.700 testes).
