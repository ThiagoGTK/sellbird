# Estratégia de oferta e mecânica de fechamento

## Regra principal: conquiste o direito de pedir

Nunca comece pela oferta. Nunca faça um discurso de venda num e-mail frio. A primeira abordagem existe para começar uma conversa, não para fechar um negócio.

As ofertas só aparecem depois que o prospect mostrou interesse de verdade:
- Respondeu de forma positiva
- Fez uma pergunta sobre o produto
- Contou uma dor que você resolve
- Perguntou sobre preço ou próximos passos

Se nada disso aconteceu, você ainda está na fase de "conquistar a atenção". Fique nela.

## A escada de ofertas

Nem todo prospect interessado recebe a mesma oferta. Ajuste a oferta ao nível de engajamento:

| Nível de engajamento | Sinal | Oferta |
|----------------------|-------|--------|
| **Curioso** | Fez uma pergunta, clicou num link | Responda a pergunta + pedido leve ("Se ajudar, te mostro como funciona") |
| **Interessado** | Contou uma dor, perguntou sobre recursos | Compartilhe um material ou caso relevante + sugira uma conversa rápida |
| **Pronto** | Perguntou preço, prazo ou próximos passos | Apresente a oferta específica com um próximo passo claro |
| **Urgente** | Tem prazo, perdeu o fornecedor atual, está contratando | Seja rápido: apresente a oferta na hora, deixando o prazo claro |

## Montando ofertas a partir do conhecimento do produto

Quando o Sellbird aprende sobre um produto (lendo o site ou por treinamento manual), ele deve identificar:

1. **Oferta principal**: o que estamos vendendo de fato? (assinatura de software, prestação de serviço, diagnóstico/auditoria)
2. **Ofertas de entrada**: jeitos de começar com menos compromisso (teste grátis, piloto, diagnóstico gratuito, sessão de estratégia)
3. **Ofertas de prova**: jeitos de mostrar valor antes de pedir dinheiro (relatório de exemplo, avaliação gratuita, calculadora de retorno)

### Como construir a oferta

Para cada produto, defina:
- **O que a pessoa recebe**: entrega ou acesso específico (não um "valor" vago)
- **Quanto custa**: preço, tempo dedicado ou "grátis"
- **Qual o risco**: nenhum (teste grátis), garantia de devolução ou mensal sem fidelidade
- **O que acontece depois**: a mecânica exata: clicar num link, responder com horários, preencher um formulário

### Exemplos de estrutura de oferta

**Software (SaaS):**
- Entrada: "Temos 14 dias de teste grátis, sem cartão. Quer que eu libere um para você?"
- Principal: "Os planos começam em R$ X/mês. Quer que eu te mostre qual faz sentido para a sua equipe?"

**Serviço/Agência:**
- Entrada: "Normalmente começamos com um diagnóstico gratuito de 30 minutos do que vocês usam hoje. Vale fazer?"
- Principal: "Nosso trabalho costuma começar em R$ X/mês. Monto um escopo sob medida se você me contar mais sobre o cenário."

**Consultoria:**
- Entrada: "Fiz uma análise rápida de [situação específica deles]. Quer que eu te mande?"
- Principal: "Fazemos isso como projeto [fechado/mensal]. Topa uma conversa de 20 minutos para ver se faz sentido?"

## Mecânica de fechamento: como marcar

O jeito de pedir o próximo passo importa. Sempre confirme com o usuário qual mecânica usar:

### Opção 1: link da agenda
Melhor quando: volume alto, sensação de autoatendimento, o usuário tem uma ferramenta de agendamento.
```
"Aqui está minha agenda, se quiser pegar 15 minutos: [LINK]"
```
- Use quando a configuração do produto tiver um `booking_url`
- Sempre diga o tempo ("15 minutos", "uma conversa rápida de 20 minutos")
- Nunca diga "agende uma demonstração"; diga "pegar um horário" ou "uma conversa rápida"

### Opção 2: sugerir horários específicos
Melhor quando: toque mais pessoal, venda mais consultiva, sem ferramenta de agenda.
```
"Fica bom quinta às 14h ou sexta de manhã para uma conversa rápida?"
```
- Ofereça exatamente 2 ou 3 opções
- Sempre dia + horário
- Janela curta (mesma semana)

### Opção 3: perguntar a preferência
Melhor quando: empresas grandes, respeito à agenda deles, quem decide é bem sênior.
```
"Como está sua agenda esta semana para uns 15 minutos?"
```
- Respeitoso, mas com tempo definido
- Bom para diretoria, quando você não quer parecer presunçoso

### Opção 4: próximo passo sem reunião
Melhor quando: o produto se vende sozinho, o prospect só precisa de acesso.
```
"Quer que eu crie uma conta de teste para você? Leva 2 minutos."
```
- Para produtos com teste grátis e autoatendimento
- Pule a reunião se o produto fala por si

## O que o Sellbird precisa confirmar com o usuário

Na configuração ou no treinamento, o Sellbird precisa saber:

1. **Qual é a oferta principal?** (assinatura, serviço, teste, diagnóstico etc.)
2. **Existe uma oferta de entrada?** (teste grátis, diagnóstico gratuito, amostra etc.)
3. **Qual é o objetivo da abordagem?** (marcar conversa, começar um teste, conseguir uma resposta etc.)
4. **Como as reuniões são marcadas?**
   - Link da agenda (informe a URL)
   - Sugerir horários
   - Perguntar a preferência
5. **Quem participa da reunião?** (o usuário, alguém do time de vendas, o Sellbird marca e outra pessoa atende)
6. **Alguma qualificação antes de marcar?** (porte, orçamento, necessidade específica)

Essas respostas vão para o `sellbird.yaml`, na configuração do produto, e orientam como o Sellbird escreve e-mails e responde.

## Quando a oferta aparece na sequência

### Sequência de e-mail frio (3 e-mails)
- **E-mail 1**: sem oferta de venda. Comece uma conversa. Faça uma pergunta. Traga uma observação útil.
- **E-mail 2**: menção leve, só se fizer sentido. "Ajudamos empresas como a sua a [fazer algo]. Vale conversar?"
- **E-mail 3**: e-mail de encerramento. Um pouco mais direto, mas ainda sem discurso de venda. "Se isso não for prioridade agora, tudo bem. Se [dor] aparecer, estou por aqui."

### Respostas (depois do interesse)
- **Primeira resposta interessada**: reconheça, responda a pergunta e apresente a oferta de entrada ou sugira uma conversa.
- **Follow-up depois do interesse**: se a pessoa sumiu depois de mostrar interesse, um lembrete gentil. Nunca mais de um.
- **Pronto para marcar**: apresente a mecânica de fechamento escolhida. Seja direto. "Vamos marcar."

## Regras de linguagem

**Diga:**
- "Vale uma conversa?"
- "Posso te mostrar como funciona"
- "Faz sentido pegarmos 15 minutos?"
- "Quer que eu te mande [coisa específica]?"

**Nunca diga:**
- "Agende uma demonstração" (soa como discurso de venda)
- "Marque uma reunião com nossa equipe" (impessoal)
- "Adoraria te mostrar" (foca em você, não nele)
- "Me avise se tiver interesse" (passivo, sem próximo passo claro)
- "Quando você está livre?" (aberto demais)

## Quando perguntam "quanto custa?"

Quando o prospect pergunta o preço antes de você qualificá-lo:

1. Dê uma resposta real; nunca fuja da pergunta
2. Dê contexto: "Os planos começam em R$ X/mês, dependendo de [variável]. A maioria das empresas do seu porte fica no plano [nome]."
3. Puxe para a qualificação: "Para te passar um valor exato, ajudaria saber [pergunta específica sobre a necessidade]."
4. Se existir uma oferta de entrada gratuita, comece por ela: "Tem um teste grátis para você ver se encaixa antes de assumir qualquer compromisso."
