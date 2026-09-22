# Operação do Radar de Editais

## Como roda sozinho

Todo dia às 06:15 (Brasília) o GitHub Actions (`.github/workflows/daily.yml`, grátis em repositório público):

1. roda os testes;
2. `python run.py collect` — baixa ~27 mil licitações abertas do PNCP (3 conexões, 1 requisição a cada 2 s, ~20–45 min),
   classifica por segmento, marca as novas (comparando com o snapshot publicado ontem) e gera `public/`;
3. publica `public/` no GitHub Pages;
4. `python run.py notify` — posta no canal gratuito e no canal Pro do Telegram;
5. `python run.py ping` — avisa os buscadores (IndexNow);
6. `python run.py health` — confere as regras de saúde; se alguma falha, manda alerta no seu Telegram
   e o job fica vermelho (o GitHub te manda e-mail);
7. guarda `status.json`/`notify.json` como artefato por 30 dias e reativa o próprio agendamento (keepalive).

Não existe servidor, banco nem estado no repositório: o estado de ontem é o próprio site publicado
(`/data/snapshot.json.gz` e `/data/history.csv`).

## Tratamento de falhas (já automático)

| Falha | O que o sistema faz |
|---|---|
| Página do PNCP dá timeout/5xx | 4 tentativas com espera exponencial; se continuar falhando, segue sem ela e recupera do snapshot anterior as licitações que ainda estão abertas |
| 1ª página do PNCP falha (API fora do ar) | 6 tentativas; se continuar, **modo degradado**: republica o snapshot de ontem (só o que ainda está aberto), não posta "novas", e o health acusa |
| > 20% das páginas falharam | health acusa |
| < 5.000 licitações abertas | health acusa (sinal de mudança na API) |
| < 40% classificadas em algum segmento | health acusa (sinal de mudança no texto do objeto) |
| Telegram 429 (rate limit) | espera o `retry_after` e tenta de novo |
| Telegram recusou envio | registra em `notify.json`; health acusa |
| Sem token do Telegram | coleta e site continuam; alertas simplesmente não saem |

Segredos nunca aparecem em log: o token do Telegram fica na URL da API e as mensagens de erro
não incluem a URL.

---

## Configuração inicial — [MINHA AÇÃO NECESSÁRIA]

Tudo abaixo exige login em conta sua ou aceite de termos, que eu não posso fazer por você.
Ordem pensada para o sistema já funcionar a partir do passo 1; os demais só ligam mais peças.

### 1. Publicar o site (≈2 min) — se eu ainda não tiver publicado

```bash
gh repo create radar-editais --public --source . --push
```

Depois: GitHub → repositório → **Settings → Pages → Source: GitHub Actions**.
Em seguida **Actions → radar-diario → Run workflow** para a primeira execução.

### 2. Telegram (≈5 min)

1. No Telegram, fale com **@BotFather** → `/newbot` → guarde o token.
2. Crie o canal **público** (ex.: `@licitacoesabertashoje`) e o canal **privado** "Radar de Editais Pro".
   Adicione o bot como **administrador** dos dois (permissão de postar).
3. Mande qualquer mensagem para o seu bot; abra `https://api.telegram.org/bot<TOKEN>/getUpdates`
   e copie o `chat.id` — é o seu chat de admin. Para o id do canal privado, poste algo nele e repita
   (começa com `-100`).
4. No canal privado: **Gerenciar canal → Links de convite → criar link** — é o link que a Kiwify vai entregar.
5. GitHub → **Settings → Secrets and variables → Actions → Secrets**:
   `TELEGRAM_BOT_TOKEN`, `TELEGRAM_PUBLIC_CHAT` (ex.: `@licitacoesabertashoje`),
   `TELEGRAM_PRO_CHAT` (ex.: `-100…`), `TELEGRAM_ADMIN_CHAT`.
6. **Variables**: `PUBLIC_TELEGRAM_URL` = `https://t.me/licitacoesabertashoje`.

### 3. Kiwify — recebimento (≈10 min)

Criar conta em kiwify.com.br, cadastrar o produto com o texto de [kiwify.md](kiwify.md), e colar os
links de checkout em **Variables**: `CHECKOUT_URL` e `CHECKOUT_URL_ANUAL`. O botão "em breve" vira
botão de compra na próxima execução (ou rode o workflow manualmente).

### 4. Medição (≈5 min, opcional mas recomendado)

- **GoatCounter** (gratuito, sem cookies): criar conta com o código `radareditais` → Variable `GOATCOUNTER=radareditais`.
- **Google Search Console**: adicionar a propriedade `https://lukiin-z.github.io/radar-editais/`,
  método "tag HTML", colar só o `content` em Variable `GOOGLE_SITE_VERIFICATION`, rodar o workflow,
  clicar em verificar e enviar `sitemap.xml`.
- **Bing Webmaster Tools**: "importar do Google Search Console".

---

## Checklist de manutenção

**Semanal (2 min)** — só se não chegou alerta no Telegram:
- [ ] Último run do `radar-diario` está verde?
- [ ] `https://lukiin-z.github.io/radar-editais/status.json` com data de hoje?

**Mensal (10 min):**
- [ ] Kiwify → assinaturas canceladas: remover essas pessoas do canal privado
      (Telegram → canal → Inscritos). Limitação conhecida até ~50 assinantes; ver regra em [aquisicao.md](aquisicao.md).
- [ ] Revogar e recriar o link de convite do canal privado se houver sinal de compartilhamento;
      atualizar o conteúdo do produto na Kiwify.
- [ ] Search Console → Páginas: erros de cobertura?
- [ ] `data/history.csv`: total de abertas estável? Queda brusca = mudança na API.
- [ ] Aplicar a tabela de decisão de [aquisicao.md](aquisicao.md).

**Quando o health acusar "classificadas < 40%":** abrir `data/snapshot.json.gz`, olhar objetos sem
segmento e acrescentar palavras-chave em `radar/segments.py` (tem teste em `tests/test_radar.py`).

## Comandos locais

```bash
python -m unittest discover -s tests -v
```

```bash
python run.py all --max-pages 10 --dry-run
```

```bash
python -m http.server 8000 --directory public
```

O `--dry-run` grava as mensagens que seriam enviadas em `work/outbox-preview.txt`.
Para servir localmente sob o mesmo caminho do GitHub Pages, gere com `SITE_URL=http://localhost:8000`.

## Plano B se o GitHub Actions não alcançar o PNCP

Hipótese não verificada: alguns sites gov.br bloqueiam IPs de fora do Brasil. Se o log do Actions
mostrar timeouts em todas as páginas, rode a coleta nesta máquina pelo Agendador de Tarefas do Windows
(`python run.py collect && python run.py notify`) e publique `public/` num branch `gh-pages`.
