# Skills (playbooks de vendas)

Skills são arquivos Markdown editáveis que dão ao Sellbird o conhecimento de vendas básico. Cada agente carrega as skills de que precisa antes de tomar decisões.

> Versão em português (Sellbird PT-BR): os playbooks foram traduzidos e adaptados para o mercado brasileiro. O Sellbird escreve em português para empresas do Brasil e em inglês para empresas de fora; estas instruções valem para os dois idiomas.

## Como as skills funcionam

Quando um agente roda, ele chama `brain.load_skills_for_agent("nome_do_agente")`, que junta os arquivos de skill relevantes e coloca no prompt. Ou seja: você muda o comportamento do Sellbird editando estes arquivos, sem mexer em código.

## Qual skill vai para qual agente

| Skill | Scout | Writer | Handler | Sender | LinkedIn |
|-------|-------|--------|---------|--------|----------|
| `prospecting_tactics.md` | x | | | | x |
| `lead_qualification.md` | x | | | | |
| `account_navigation.md` | x | | | | |
| `signal_playbook.md` | x | x | | | |
| `email_frameworks.md` | | x | | x | |
| `sales_methodology.md` | | x | x | | |
| `offer_strategy.md` | | x | x | | |
| `objection_handling.md` | | | x | | |
| `linkedin_outreach.md` | | | | | x |
| `product_knowledge.md` | x | x | x | x | x |
| `competitive_intel.md` | | x | x | | |
| `selling_to_startups.md` | | x* | x* | | |

\* Só para prospects cuja empresa é uma startup segundo o próprio site (sinal `YC_BACKED` ou `ACCELERATOR`, ou um `FUNDING_ROUND` dos últimos 18 meses); não é carregada para todo mundo.

## Skills que já vêm prontas

- **`prospecting_tactics.md`**: buscas avançadas no Google, leitura do site da empresa, eventos-gatilho, indicações
- **`lead_qualification.md`**: triagem BANT, pontuação de ICP, MEDDIC, critérios de desqualificação
- **`account_navigation.md`**: várias pessoas na mesma empresa, por onde entrar, multithreading
- **`selling_to_startups.md`**: como escrever para fundadores de startups: quem lê, timing de aceleradoras e Demo Day, empresas que acabaram de captar (e quando a captação é velha demais para citar), o que não fazer, como lidar com as respostas. Usada automaticamente para prospects com aceleradora ou captação recente.
- **`signal_playbook.md`**: transformar sinais de compra (contratação, ferramentas, investimento) na primeira linha do e-mail; qual sinal vence quando há vários; usar uma vaga como gancho sem chutar nem insinuar informação de dentro
- **`email_frameworks.md`**: regras de texto para e-mail frio, padrões de IA proibidos, dados de taxa de resposta (tamanho, oferta como pedido, cadência, sem rastreamento), a sequência de 3 e-mails (Observação, Ângulo, Encerramento), assuntos, personalização
- **`sales_methodology.md`**: ciclo ABC, fluxo da conversa, ajuste de tom, ética
- **`offer_strategy.md`**: escada de ofertas por nível de engajamento, mecânica de fechamento, regras de timing
- **`objection_handling.md`**: método LAARC, 4 categorias de objeção com respostas
- **`linkedin_outreach.md`**: sequências de conexão, modelos de mensagem, limites de uso

## Skills geradas automaticamente

Criadas pelo `sellbird train <url>`, específicas do seu produto:

- **`product_knowledge.md`**: recursos, benefícios, preço, casos de uso, dores, gatilhos de compra
- **`competitive_intel.md`**: comparativos com cada concorrente, ângulos de diferenciação, caminhos de migração

## Adicionar ou editar skills

1. Edite qualquer arquivo `.md` desta pasta
2. As mudanças valem no próximo ciclo (não precisa reiniciar)
3. Para criar uma skill nova, crie o arquivo e adicione no `skill_map` em `sellbird/brain.py`
