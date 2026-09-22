# Radar de Editais

Site gratuito e alertas pagos de **licitações públicas abertas**, gerados todo dia a partir dos
dados abertos do PNCP. Sem servidor, sem banco, sem custo fixo: GitHub Actions coleta e gera,
GitHub Pages hospeda, Telegram entrega, Kiwify cobra.

```
PNCP (API pública) ──► run.py collect ──► public/ (27 mil páginas SEO) ──► GitHub Pages
                                     │                                      │
                                     └► run.py notify ──► Telegram          ▼
                                            (canal grátis + canal Pro)   busca orgânica / IndexNow
                                                                            │
                          Kiwify (Pix/cartão, recorrente) ◄── /pro/ ◄───────┘
                                     │
                                     └► e-mail com o convite do canal Pro
```

| Documento | Conteúdo |
|---|---|
| [docs/pesquisa.md](docs/pesquisa.md) | 12 oportunidades avaliadas, top 3 e por que esta foi escolhida |
| [docs/operacao.md](docs/operacao.md) | Como roda, falhas tratadas, **passos que dependem de você**, checklist de manutenção |
| [docs/aquisicao.md](docs/aquisicao.md) | Canais orgânicos, materiais prontos, métricas e regras de decisão (matar/pivotar/dobrar) |
| [docs/kiwify.md](docs/kiwify.md) | Texto pronto para cadastrar o produto |

## Estrutura

```
run.py                 orquestrador: collect | notify | ping | health | all
config.json            marca, URL, preço, checkout (sobrescrito por variáveis do Actions)
radar/fetch.py         coleta paralela com limite de taxa, retry e recuperação pelo snapshot anterior
radar/segments.py      27 segmentos por palavra-chave (regex sobre texto sem acento)
radar/build.py         site estático: home, segmento, UF, segmento×UF, edital, /pro/, sitemap, RSS
radar/telegram.py      alertas (mensagens + planilha .csv) via Bot API
tests/test_radar.py    testes (stdlib unittest; sem dependências)
.github/workflows/     radar-diario (cron 06:15 BRT) e testes em cada push
```

Só biblioteca padrão do Python 3.12+. Nada para instalar.

```bash
python -m unittest discover -s tests -v
```

```bash
python run.py all --max-pages 10 --dry-run
```
