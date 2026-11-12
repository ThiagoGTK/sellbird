<p align="center">
  <a href="https://sellbird.ai">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/brand/sellbird-wordmark-white.svg">
      <img src="docs/brand/sellbird-wordmark.svg" alt="Sellbird" width="300">
    </picture>
  </a>
</p>

<p align="center"><strong>Sellbird em português (PT-BR): a plataforma de prospecção de código aberto que roda no seu plano do Claude ou do ChatGPT.</strong></p>

<p align="center">
O Sellbird encontra empresas que precisam do que você vende, descobre quem decide, confere o e-mail, escreve um e-mail frio personalizado para cada pessoa, envia e cuida das respostas.
Ele roda no seu computador e, por padrão, nada sai sem a sua aprovação.
</p>

> **Esta é uma versão traduzida e adaptada para o Brasil** do projeto original
> [ethanplusai/sellbird](https://github.com/ethanplusai/sellbird) (licença AGPL-3.0).
> O README original, em inglês, está em [README.en.md](README.en.md).
> **Guia completo de instalação e uso em português: [docs/pt-BR/GUIA.md](docs/pt-BR/GUIA.md).**

## O que muda nesta versão

| | Original | Esta versão (PT-BR) |
|---|---|---|
| **Idioma dos e-mails** | Inglês | **Português do Brasil para empresas no Brasil**, inglês para empresas de fora (detectado pela localização, fuso, domínio `.br` etc.) |
| **Respostas** | Inglês | No mesmo idioma em que o prospect escreveu |
| **Pedido de descadastro** | Inglês, espanhol, francês, hebraico | + **português** ("me descadastre", "não tenho interesse", "sair", "pare de me mandar e-mails"...) |
| **Ameaça jurídica → humano** | Inglês, hebraico | + **português** (advogado, Procon, LGPD, "isso é spam"...) |
| **Rodapé** | Linha de descadastro em inglês | Linha em português para e-mails em português (`compliance.opt_out_line_pt`) |
| **Regras de estilo** | Clichês de IA em inglês | + clichês em português ("espero que esteja bem", "venho por meio deste", "solução inovadora"...) |
| **Sites brasileiros** | Páginas "team/about" | + "quem somos", "equipe", "corpo clínico", cargos como sócio-fundador, proprietário, Dra. |
| **Busca grátis (OpenStreetMap)** | Segmentos em inglês | + segmentos em português ("clínica odontológica", "contabilidade", "imobiliária", "academia"...) |
| **Painel, terminal, prompts e playbooks** | Inglês | **Português** |

## O que ele faz

O Sellbird é um funil que você roda do começo ao fim, ou para em qualquer etapa.

| | O que acontece |
|---|---|
| **Encontrar empresas** | Procura negócios que encaixam no seu cliente ideal: grátis no OpenStreetMap, ou numa fonte paga que você escolher. Toda busca paga mostra o custo antes de rodar. |
| **Entender por que comprariam** | Lê o site de cada empresa procurando os sinais de compra que você confirmou (sem agendamento online, anunciando no Google, contratando). Sem chamar o modelo, sem custo. |
| **Descobrir quem decide** | Encontra o dono ou gestor citado nas páginas da própria empresa, no máximo duas pessoas por empresa. |
| **Conferir o e-mail** | Descobre o padrão de e-mail da empresa e verifica um endereço. Cada e-mail fica marcado como verificado, arriscado, palpite ou inválido, e só os que entregam recebem envio. |
| **Escrever e enviar** | Escreve uma sequência curta para cada pessoa a partir do que encontrou e envia do seu Gmail, Microsoft 365 ou SMTP (Hostinger, Locaweb...), dentro do limite diário e do horário comercial dela. |
| **Cuidar das respostas** | Lê cada resposta, escreve uma resposta, separa respostas automáticas, atende pedidos de saída na hora e passa para você o que não deve responder sozinho. |

Só quer a lista? Pare depois da verificação e rode `sellbird export` para ter um CSV de tudo que ele encontrou.

## Sem conta de API de modelo

O Sellbird pensa pelo Claude Code no seu plano Claude Pro ou Max, ou pelo Codex num plano do ChatGPT (Codex só no macOS/Linux). Não há chave de API nem cobrança por token, e ele se limita para deixar espaço para o seu próprio uso.

| | |
|---|---|
| Claude Pro ou Max, ou plano do ChatGPT com Codex | a assinatura que você já tem |
| Encontrar empresas | **US$ 0** na fonte padrão (OpenStreetMap) |
| Ler os sites | **US$ 0**: três requisições HTTP por empresa, sem modelo |
| Escrever e enviar | sua assinatura e uma caixa de e-mail |
| Ferramentas de prospecção | **Nenhuma.** Sem Apollo, ZoomInfo, Clearbit ou Clay. |

## Começo rápido

Você precisa de:

- **Python 3.11 ou mais novo.**
- **Claude Pro ou Max** com o Claude Code instalado e logado (`claude`), ou um **plano do ChatGPT com o Codex CLI** (macOS/Linux).
- **Uma caixa de e-mail para enviar**, de preferência num domínio secundário só para envio.
- **Aquecimento nessa caixa.** Recomendamos o [TrulyInbox](https://trulyinbox.com/?via=sellbird) (link de afiliado do projeto original): ele aquece uma caixa nova antes do e-mail frio e mantém ela fora do spam depois.

### Deixe o Claude configurar

```bash
git clone -b pt-br https://github.com/ThiagoGTK/sellbird.git
cd sellbird
claude
```

Depois diga **"configure o Sellbird para mim"**. O `CLAUDE.md` do repositório transforma o Claude Code no guia de instalação, em português.

### Ou faça você mesmo

Passo a passo completo (Windows, macOS e Linux) em **[docs/pt-BR/GUIA.md](docs/pt-BR/GUIA.md)**. Resumo:

```bash
# 1. Instalar (no Windows: py -3.13 -m venv .venv  e  .venv\Scripts\activate)
python3 -m venv .venv && source .venv/bin/activate && pip install -e .

# 2. Chaves e senhas (cada variável está explicada no arquivo)
cp .env.example .env

# 3. Aprender com o seu site (grava sellbird.local.yaml)
sellbird train https://seusite.com.br

# 4. Confirmar o que faz um bom prospect
sellbird signals --confirm free

# 5. Encontrar empresas (grátis, sem conta)
sellbird discover --city "Curitiba, PR"

# 6. Abrir o painel e ligar o ciclo
sellbird dashboard          # mostra um link privado para http://127.0.0.1:5555
sellbird run
```

## Nada sai sem você

Todo e-mail espera na **Caixa de saída** até você aprovar, a não ser que você ligue o piloto automático. Antes de qualquer envio, uma checagem sem modelo barra variáveis não preenchidas, frases proibidas, e-mails longos demais, links demais e endereços que não entregam. `sellbird sending pause` para tudo na hora.

> **LGPD e e-mail frio:** este projeto não é aconselhamento jurídico. Veja as boas práticas na seção
> "LGPD e boas práticas" do [guia](docs/pt-BR/GUIA.md#lgpd-e-boas-práticas).

## Documentação

- **[Guia em português](docs/pt-BR/GUIA.md)**: instalação, configuração, uso diário e problemas comuns.
- Documentação técnica original (inglês): [docs/](docs/), começando por [How Sellbird works](docs/how-it-works.md).

## Licença

O Sellbird é licenciado sob a [GNU Affero General Public License v3.0](LICENSE). Esta tradução segue a mesma licença: você pode usar e modificar à vontade; se oferecer o Sellbird modificado como serviço para outras pessoas pela rede, precisa disponibilizar o código modificado. Versões do Harvey até 0.3.x foram lançadas sob MIT; veja [NOTICE](NOTICE).

Os links do TrulyInbox neste projeto são links de afiliado do mantenedor original: ele pode ganhar uma comissão, sem custo extra para você.
