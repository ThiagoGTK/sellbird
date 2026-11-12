# Navegação de contas: várias pessoas na mesma empresa

## Empresas x contatos

Uma empresa é uma conta. Um contato é uma pessoa nessa empresa. Uma empresa pode ter vários contatos. O Sellbird sempre cria o perfil da empresa primeiro e depois liga os contatos a ela.

## Perfil da empresa

Toda empresa que o Sellbird pesquisa precisa ter:
- **Nome**: o nome real da empresa
- **Domínio**: o domínio do site (ex.: exemplo.com.br)
- **Site**: a URL completa
- **Descrição**: o que a empresa faz (1 ou 2 frases)
- **Segmento**: o segmento principal
- **Porte**: faixa de funcionários
- **Localização**: cidade/estado da sede
- **Origem**: como o Sellbird encontrou (google, linkedin, leitura do site)
- **URL de origem**: a URL exata onde o Sellbird achou a informação

O Sellbird deve tirar isso do site da empresa, da página da empresa no LinkedIn ou dos resultados do Google. Não chute. Se não der para confirmar um campo, deixe em branco.

## Perfil do contato

Todo contato precisa ter no mínimo:
- **Nome**: obrigatório. Real e confirmado.
- **Sobrenome**: obrigatório. Real e confirmado.
- **Cargo**: obrigatório. O cargo atual de verdade.
- **Empresa**: ligada ao perfil da empresa.

Campos opcionais (só preencha se der para confirmar):
- **E-mail**: só inclua se foi verificado por checagem MX/SMTP ou se está no site da empresa. Marque email_verified = true só se confirmado.
- **Telefone**: muito difícil de achar. Só inclua se estiver público (site da empresa, perfil do LinkedIn). Marque phone_verified = true só se confirmado. NÃO chute telefones.
- **URL do LinkedIn**: inclua se encontrar.
- **Senioridade**: c_suite, vp, director, manager, individual. Deduza pelo cargo.
- **Departamento**: vendas, marketing, engenharia, operações etc. Deduza pelo cargo.

### Regras de qualidade de dados
1. Nunca invente informação de contato. Se não der para confirmar, não inclua.
2. Padrões de e-mail (nome.sobrenome@dominio.com.br) só valem depois da verificação SMTP.
3. Um contato sem e-mail verificado ainda pode valer para abordagem no LinkedIn.
4. Sempre registre onde achou cada informação (origem + URL de origem).

## Com quem falar na empresa

### Matriz de porta de entrada

Nem todo contato é igual. Com quem você fala primeiro depende do tipo de negócio:

| Tipo de negócio | Primeiro contato | Segundo contato | Evite primeiro |
|-----------------|------------------|-----------------|----------------|
| **Compra pequena** (até ~R$ 2.500/mês) | Usuário final / gerente | O chefe dele | Diretoria (sênior demais) |
| **Médio porte** (R$ 2.500 a 25 mil/mês) | Diretor / head | Gerente que usaria | Analistas |
| **Grande empresa** (acima de R$ 25 mil/mês) | Head / diretoria | Defensor (gerente que vai apoiar) | Equipe júnior |

### Multithreading: várias pessoas na mesma empresa

Quando o Sellbird encontra vários contatos numa empresa:

1. **Comece por um.** Nunca escreva para várias pessoas da mesma empresa ao mesmo tempo. Parece spam e elas vão comparar.

2. **Comece no nível certo.** Escolha quem tem mais chance de:
   - Sentir a dor que seu produto resolve
   - Ter autoridade para avaliar soluções
   - Realmente ler e responder e-mail

3. **Suba ou desça conforme a resposta:**
   - O gerente não respondeu? Tente o diretor.
   - O diretor disse "fala com a minha equipe"? Escreva para o gerente citando o diretor.
   - O gerente se interessou? Pergunte se ele quer incluir o chefe.

4. **Espere entre contatos.** Se você escreveu para a Pessoa A na Acme, espere pelo menos 5 dias úteis antes de escrever para a Pessoa B. Trate a empresa como uma conta, não como contatos soltos.

5. **Compartilhe o contexto.** Se a Pessoa A respondeu, o Sellbird precisa saber disso ao escrever para a Pessoa B. "Sua colega Sara comentou que vocês estão avaliando opções" é poderoso.

### Identificando a senioridade

Deduza a senioridade pelo cargo:

- **Diretoria executiva (C-Suite)**: CEO, CTO, CFO, CMO, COO, dono, sócio, fundador, "Diretor-presidente", "Chief __"
- **VP / Head**: vice-presidente, VP, "Head de __", diretor executivo
- **Diretor**: diretor, diretor sênior, "Diretor de __"
- **Gerente**: gerente, gerente sênior, coordenador, líder de equipe
- **Individual**: analista, especialista, assistente, assistente técnico, engenheiro

### Quando parar

Pare de contatar uma empresa se:
- 3 contatos diferentes receberam e-mail sem nenhuma resposta
- Qualquer contato disse claramente "sem interesse" ou "pare de mandar e-mails"
- A empresa não encaixa no ICP depois de pesquisar mais

## Verificação por amostra

Antes de colocar prospects no funil de verdade, o Sellbird deve montar uma amostra de 5 a 10 empresas + contatos e mostrar ao usuário para revisão. Isso garante que:

1. O ICP está certo (segmentos e portes certos)
2. Os cargos dos contatos são os que o usuário quer
3. A qualidade dos dados atende às expectativas
4. As fontes da pesquisa são legítimas

### Fluxo da amostra
1. O Sellbird pesquisa 5 a 10 empresas e seus contatos
2. Mostra como amostra: "Encontrei estas 8 empresas. Cada uma tem 1 ou 2 contatos. Dá uma olhada e me diz se é esse o tipo de alvo."
3. O usuário revisa e comenta ("pequena demais", "segmento errado", "perfeito", "já trabalhamos com eles")
4. O Sellbird ajusta a busca conforme o retorno
5. Depois da aprovação, o Sellbird segue com a prospecção completa

Essa etapa de amostra só acontece uma vez no começo (ou quando o ICP muda). Depois que o usuário aprova, o Sellbird prospecta sozinho.
