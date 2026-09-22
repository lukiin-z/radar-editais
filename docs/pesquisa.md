# Fase 1 — Pesquisa de oportunidades (22/09/2026)

Critérios obrigatórios: R$0 inicial, aquisição orgânica, digital, entrega automática,
margem alta, primeira venda rápida, escala, pouco atendimento, ferramentas gratuitas,
sem produção manual diária de conteúdo.

Notas de 1 (ruim) a 5 (ótimo). "Dificuldade" e "Risco": 5 = baixo/fácil.

| # | Oportunidade | Dific. impl. | Tempo MVP | 1ª venda | Ticket | Margem | Automação | Aquisição | Risco | Dep. plataforma | Escala | **Total** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **Radar de licitações nichado** (dados abertos PNCP → site SEO programático + alertas pagos no Telegram) | 4 | 1 dia | 3 | R$20–50/mês | ~78% | 5 | 4 | 4 | 3 | 5 | **40** |
| 2 | Radar de contratos públicos vencendo (PNCP /contratos → quem fornece hoje e quando vence) | 3 | 2 dias | 3 | R$50–150/mês | ~85% | 5 | 3 | 4 | 3 | 4 | **37** |
| 3 | Radar de imóveis Caixa com desconto (CSV diário por UF) | 3 | 2 dias | 3 | R$20–40/mês | ~80% | 4 | 3 | 2 | 2 | 4 | **33** |
| 4 | Planilhas hiper-específicas (precificação confeitaria, controle MEI) na Kiwify/Hotmart | 4 | 1 dia | 2 | R$19–47 | ~85% | 5 | 2 | 4 | 2 | 3 | **33** |
| 5 | Gerador de documentos (recibo, contrato de aluguel) client-side + templates premium | 4 | 1 dia | 2 | R$9–19 | ~85% | 5 | 2 | 4 | 4 | 3 | **32** |
| 6 | Templates Notion/Sheets no Gumroad Discover (mercado global, USD) | 4 | 1 dia | 2 | US$9–29 | ~88% | 5 | 2 | 4 | 2 | 3 | **32** |
| 7 | Calculadoras trabalhistas (rescisão, férias, CLT×PJ) | 5 | 1 dia | 1 | anúncio | alta | 5 | 1 | 5 | 3 | 3 | **30** |
| 8 | Currículo ATS gerador + modelos pagos | 4 | 1 dia | 2 | R$9–19 | ~85% | 5 | 1 | 4 | 3 | 3 | **30** |
| 9 | Pacotes de prompts / GPTs nichados | 5 | horas | 1 | R$9–29 | ~90% | 5 | 1 | 3 | 2 | 2 | **28** |
| 10 | Listas de leads de CNPJs recém-abertos (dados da Receita) | 3 | 2 dias | 4 | R$50–200 | ~90% | 5 | 3 | **1** | 3 | 4 | descartada (LGPD: MEI = pessoa física) |
| 11 | Extensão Chrome utilitária | 3 | 2 dias | 2 | freemium | alta | 5 | 3 | 4 | 2 | 4 | descartada (cadastro na Chrome Web Store custa US$5) |
| 12 | Imagens/figurinhas personalizadas com IA | 3 | 1 dia | 3 | R$5–15 | baixa | 4 | 3 | 3 | 2 | 3 | descartada (geração de imagem custa por unidade) |

## Evidências coletadas

- **API do PNCP é pública, sem cadastro** e testada daqui: `GET /api/consulta/v1/contratacoes/proposta`
  devolveu **26.236 contratações com proposta aberta** (17.208 só em pregão eletrônico
  encerrando nos próximos 30 dias). Limite: 50 registros/página, ~25 s por requisição.
- **Demanda paga comprovada**: LicitaFree cobra R$49,90/mês por alerta; RadarLicita,
  Monitor de Licitações, Alerta Licitação, LicitaCerta vendem alertas por e-mail/Telegram/WhatsApp.
  Há mercado pagando — a questão é aquisição, não demanda.
- **Kiwify**: sem mensalidade, 8,99% + R$2,49 por venda, suporta **assinatura recorrente**
  com Pix/cartão/boleto e entrega automática de conteúdo. Hotmart: 9,9% + R$1,00.
- **Gumroad** paga brasileiros via PayPal (mín. US$10, conversão 3–4%) — pior que Kiwify para público BR.
- Caixa publica `Lista_imoveis_<UF>.csv` diariamente, mas o site tem proteção anti-bot —
  risco técnico/termos maior.
- SEO programático funciona em 2026 **só com páginas de conteúdo único e útil**; páginas
  finas e quase idênticas são penalizadas. Dados de licitação são únicos por natureza
  (cada edital é diferente) e mudam todo dia.

## Top 3 (critério: soma das notas, desempate por risco e tempo até MVP)

1. **Radar de licitações nichado** — 40
2. **Radar de contratos vencendo** — 37 (mesma fonte de dados; vira upsell do #1)
3. **Radar de imóveis Caixa** — 33 (risco técnico maior)

## Fase 2 — Escolha: Radar de licitações nichado

Por quê:
- **Assimetria de dados**: o governo publica tudo de graça, mas espalhado e difícil de filtrar.
  Organizar por *segmento × estado* e empurrar para o celular é o valor.
- **Custo marginal zero**: o mesmo job diário atende 1 ou 10.000 assinantes.
- **Aquisição orgânica embutida**: cada edital aberto vira uma página indexável com conteúdo
  único ("pregão eletrônico de uniformes em Pinhais-PR"), atualizado todo dia sem eu escrever nada.
- **Cliente com motivo claro para pagar**: uma única licitação ganha paga anos de assinatura.
- **Hospedagem, agendamento e dados grátis**: GitHub Pages + GitHub Actions + PNCP.
- **Pagamento e entrega sem conversa**: Kiwify cobra e entrega o link do canal privado.
- O #2 (contratos vencendo) usa a mesma infraestrutura e fica como próximo passo se houver sinal.

Posicionamento contra concorrentes (que já usam IA): **preço baixo + nicho + zero cadastro para
ver**. O site é aberto e gratuito; paga-se pela conveniência (alerta diário filtrado no Telegram
+ planilha pronta + aviso de prazo encerrando).

## Fontes

- [Swagger da API de consulta do PNCP](https://pncp.gov.br/api/consulta/swagger-ui/index.html)
- [Manual das APIs de consulta do PNCP](https://www.gov.br/pncp/pt-br/pncp/manuais/versoes-anteriores/ManualPNCPAPIConsultasVerso1.0.pdf)
- [PNCP em dados abertos](https://www.gov.br/pncp/pt-br/acesso-a-informacao/dados-abertos)
- [LicitaFree — alerta de licitação](https://www.licitafree.com.br/alerta-licitacao)
- [RadarLicita](https://radarlicita.app/) · [Monitor de Licitações](https://monitordelicitacoes.com.br/) · [Alerta Licitação](https://alertalicitacao.com.br/) · [LicitaCerta](https://licitacerta.com.br/)
- [Taxas da Kiwify 2026](https://www.cakto.com.br/blog/taxas-kiwify) · [Kiwify — assinaturas](https://investfinance.com.br/taxas-kiwify-para-2026-para-produtor-ou-afiliado/)
- [Gumroad — pagamentos para fora dos EUA](https://insightraider.com/en/answers/when-does-gumroad-pay-out)
- [Caixa — download da lista de imóveis](https://venda-imoveis.caixa.gov.br/sistema/download-lista.asp)
- [SEO programático em 2026](https://www.indiehackers.com/post/best-pseo-tools-2026-programmatic-seo-software-compared-aUKfjmVmEXaJiblpo1X6)
