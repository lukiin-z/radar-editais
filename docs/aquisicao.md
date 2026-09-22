# Aquisição orgânica (R$0)

Funil: **busca/Telegram → página de edital → CTA → /pro/ → Kiwify → canal privado**.

## 1. Automático (já construído, roda todo dia sem ninguém)

| Canal | Como funciona | Onde está |
|---|---|---|
| SEO programático | Uma página por edital aberto (~27 mil), mais páginas segmento × estado. Títulos no formato de busca real: "Pregão Eletrônico 90/2026 – aquisição de uniformes – Pinhais/PR". Listas com < 3 itens levam `noindex` para não virar página fina. | `radar/build.py` |
| Sitemap + robots | `sitemap.xml` (índice) + `sitemap-N.xml` (40 mil URLs cada), regenerados todo dia. | `build_meta_files` |
| IndexNow | Após cada deploy, avisa Bing/Yandex/Seznam das páginas novas. Sem conta. | `run.py ping` |
| RSS | `feed.xml` com as 100 mais recentes — agregadores e leitores de RSS. | `build_meta_files` |
| Canal gratuito no Telegram | 1 post/dia com as 8 de maior valor + link para o site e para o Pro. Canais públicos aparecem na busca do Telegram. | `radar/telegram.py` |
| CTA contextual | Toda página tem uma chamada específica ("Receba as novas licitações de limpeza em SP…"). | `Site.cta` |

## 2. Uma vez, na configuração [MINHA AÇÃO NECESSÁRIA — detalhado em operacao.md]

- Google Search Console: verificar o site e enviar `sitemap.xml` (Google não aceita IndexNow).
- Bing Webmaster Tools: importar do Search Console (1 clique).
- Canal público no Telegram com nome buscável: "Licitações Abertas Hoje — Radar de Editais".

## 3. Opcional, manual, só se você quiser acelerar (nada disso é necessário para o sistema rodar)

Regras: sem mensagem em massa, sem conta falsa, respeitar as regras de cada comunidade,
postar como você mesmo e só onde autopromoção é permitida.

**Post para LinkedIn (seu perfil):**

> Fiz um radar gratuito das licitações abertas no Brasil, organizado por segmento e estado.
> Hoje são mais de 27 mil com proposta aberta no PNCP — impossível acompanhar na mão.
> Separei em 27 segmentos (limpeza, TI, obras, alimentação, uniformes…) com prazo e valor estimado.
> Se você vende para governo ou conhece quem venda, pode ser útil: https://lukiin-z.github.io/radar-editais/

**Resposta útil para quem pergunta "onde acho licitação de X?" (fóruns/grupos):**

> O PNCP concentra tudo desde a Lei 14.133. Dá para filtrar lá direto, mas é lento; eu uso uma
> página que organiza por segmento e estado e atualiza todo dia: https://lukiin-z.github.io/radar-editais/segmento/<segmento>/

## 4. Métricas e regras de decisão (fase de iteração)

Fonte de cada número:
- visitas e cliques no CTA → GoatCounter (eventos `cta-inline`, `checkout-mensal`, `checkout-anual`, `canal-gratis`)
- impressões/cliques orgânicos → Search Console
- membros → estatísticas do canal no Telegram
- vendas, cancelamentos, receita → painel da Kiwify
- saúde da coleta → `status.json` e `data/history.csv` publicados no próprio site

| Quando | Sinal | Decisão |
|---|---|---|
| Dia 30 | < 100 impressões/dia no Search Console | Problema de indexação, não de oferta: checar cobertura no GSC, reduzir páginas de edital sem valor/descrição |
| Dia 45 | > 300 visitas/mês e 0 cliques em checkout | Oferta errada: testar preço R$ 9,90 ou trocar para planilha avulsa por segmento (pagamento único R$ 14,90) |
| Dia 45 | cliques em checkout > 20 e 0 vendas | Atrito no checkout/confiança: adicionar amostra grátis de 7 dias (Kiwify permite trial) |
| Dia 60 | 0 vendas e < 50 membros no canal gratuito | **Matar ou pivotar**: mesma infraestrutura serve para o radar de contratos vencendo (PNCP /contratos), com ticket maior |
| Qualquer momento | 1ª venda | Ver o segmento e a UF do comprador (e-mail de boas-vindas pergunta), criar página e post de canal específicos para esse nicho, subir o preço para novos assinantes |
| > 50 assinantes | churn manual vira trabalho | Construir o controle de acesso automático (webhook da Kiwify → Cloudflare Worker gratuito → bot remove quem cancelou) |
