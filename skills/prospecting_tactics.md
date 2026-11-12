# Táticas de prospecção faça você mesmo

O playbook do Sellbird para encontrar leads sem ferramentas caras como Apollo, ZoomInfo ou Clearbit.

---

## Estratégia 1: buscas avançadas no Google (Google dorking)

### Encontrar perfis no LinkedIn
```
site:linkedin.com/in "Gerente de Marketing" "SaaS" "São Paulo"
site:linkedin.com/in "Sócio" "clínica odontológica" "Curitiba"
site:linkedin.com/in "{{title}}" "{{industry}}" "{{location}}"
```

### Encontrar páginas de equipe
```
site:{{domain}} "equipe" OR "quem somos" OR "sobre" OR "diretoria"
"{{company name}}" "equipe" "{{title}}"
```

### Encontrar empresas de um segmento
```
"{{industry}}" "{{location}}" "funcionários" site:linkedin.com/company
"{{industry}}" "rodada" OR "investimento" site:startupi.com.br
"{{industry}}" "Series A" OR "Series B" site:crunchbase.com
```

### Encontrar padrões de e-mail
```
"@{{domain}}" e-mail
site:{{domain}} "contato" OR "e-mail" OR "@"
"{{first_name}} {{last_name}}" "{{company}}" e-mail
```

---

## Estratégia 2: busca no LinkedIn

### Filtros de busca de pessoas
- **Cargo**: busque "Gerente de Marketing" para achar o cargo exato
- **Empresa**: filtre pela empresa atual
- **Localização**: filtre pela região
- **Setor**: filtre pelas categorias de setor do LinkedIn
- **Conexões**: conexões de 2º grau aceitam mais

### Sales Navigator (se tiver)
- Busca booleana: "Gerente de Marketing" AND "SaaS" NOT "consultor"
- Buscas salvas com alerta de novos resultados
- Listas de leads para organizar a abordagem

### Sem o Sales Navigator
- Use a busca básica com combinações de palavras
- Veja "Pessoas também viram" em perfis relevantes
- Abra a página da empresa → aba "Pessoas"
- Busque dentro de grupos relevantes

---

## Estratégia 3: leitura do site da empresa

### Páginas de equipe/sobre
A maioria das empresas lista a liderança em /equipe, /nossa-equipe, /quem-somos, /sobre, /sobre-nos, /corpo-clinico (ou /team, /about nos sites em inglês).

**Extraia:**
- Nome + cargo dos cards da equipe
- Às vezes e-mail ou link do LinkedIn direto
- Indício de porte pela quantidade de pessoas na equipe

### Vagas
- Empresas contratando para funções que seu produto apoia = prospects com intenção alta
- Veja as páginas /trabalhe-conosco, /vagas, /carreiras
- Veja também sites de vagas: LinkedIn Vagas, Indeed, Gupy, Catho, Vagas.com

### Descobrindo as ferramentas que usam
- **BuiltWith/Wappalyzer**: identificam as ferramentas atuais
- Útil para: "Vi que vocês usam o {{concorrente}}, veja como a gente se compara"
- Existem extensões gratuitas para o navegador

---

## Estratégia 4: descobrindo o padrão de e-mail

### Formatos de e-mail mais comuns (do mais para o menos comum)
1. `nome.sobrenome@dominio.com.br` (o mais comum)
2. `nome@dominio.com.br`
3. `nomesobrenome@dominio.com.br`
4. `nsobrenome@dominio.com.br` (inicial do nome + sobrenome)
5. `nomes@dominio.com.br`
6. `n.sobrenome@dominio.com.br`
7. `sobrenome.nome@dominio.com.br`
8. `nome_sobrenome@dominio.com.br`
9. `nome-sobrenome@dominio.com.br`

### Métodos de verificação (grátis)
1. **Registro MX**: confirme que o domínio recebe e-mail (consulta DNS)
2. **SMTP RCPT TO**: pergunte ao servidor de e-mail se o endereço existe
3. **Plano grátis do Hunter.io**: 25 buscas/mês + 50 verificações/mês
4. **Formato a partir de endereços conhecidos**: se você sabe o e-mail de uma pessoa da empresa, o padrão vale para todos

### Domínios "aceita tudo" (catch-all)
Alguns domínios aceitam qualquer endereço. A verificação SMTP não funciona neles. Confie no padrão + verificação do domínio.

---

## Estratégia 5: eventos-gatilho

Sinais de timing que indicam que o prospect pode estar pronto para comprar:

1. **Contratação nova num cargo relevante**: estão montando a área que você atende
2. **Investimento recente**: têm verba para gastar
3. **Lançamento de produto**: precisam de marketing/crescimento
4. **Vaga na área do seu produto**: estão investindo nisso
5. **Concorrente usando seu produto**: ângulo de prova social
6. **Expansão (nova unidade, filial)**: equipes crescendo precisam de ferramentas novas
7. **Troca de liderança**: líderes novos trazem ferramentas novas
8. **Troca de ferramentas**: estão avaliando alternativas

### Onde achar eventos-gatilho (grátis)
- Alertas do Google Notícias para as empresas-alvo
- LinkedIn: siga as empresas-alvo
- Crunchbase (plano grátis) e portais como Startupi: anúncios de investimento
- Blogs e salas de imprensa das empresas
- Sites de vagas: vagas novas nos departamentos relevantes

---

## Estratégia 6: indicações

Quando o prospect diz "não sou eu quem cuida disso":
1. Pergunte quem É a pessoa certa (nome + cargo)
2. Pergunte se ela toparia fazer uma apresentação
3. Sem apresentação, use o nome dela como referência: "{{name}}, da sua equipe, sugeriu que eu falasse com você..."

Quando um negócio fecha:
1. Peça indicações de empresas parecidas
2. Pergunte se a pessoa conhece colegas em outras empresas com desafios parecidos
3. LinkedIn: veja as conexões dela que encaixam no ICP

---

## Metas diárias de prospecção

Para construir um funil sustentável:
- **Pesquisa**: 20 a 30 empresas por dia
- **Prospects novos identificados**: 10 a 15 por dia
- **E-mails verificados**: 10 a 15 por dia
- **Total de prospects adicionados ao banco**: 10 a 15 por dia
- **Controle de qualidade**: pontue todo prospect antes de entrar na abordagem
