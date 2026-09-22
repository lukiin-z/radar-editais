"""Geração do site estático (páginas SEO, oferta, sitemap, RSS, dados)."""
import gzip
import html
import json
import os
import re
import shutil
from collections import defaultdict
from datetime import datetime
from urllib.parse import urlparse

from .segments import SEGMENTS, SEGMENT_NAMES

UF_NAMES = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia", "CE": "Ceará",
    "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão", "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul", "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
    "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
    "SE": "Sergipe", "TO": "Tocantins",
}
MIN_INDEXABLE = 3  # listas com menos itens que isso recebem noindex (evita página fina)

esc = html.escape


# ---------------------------------------------------------------- formatação

def brl(v):
    if not v:
        return "valor não informado"
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def num(n):
    return f"{n:,}".replace(",", ".")


def dt(iso, with_time=True):
    if not iso:
        return "—"
    try:
        d = datetime.fromisoformat(iso)
    except ValueError:
        return iso
    return d.strftime("%d/%m/%Y %H:%M" if with_time else "%d/%m/%Y")


def days_left(iso, now):
    try:
        d = datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return "", ""
    delta = (d.date() - now.date()).days
    if delta <= 0:
        return "encerra hoje", "hot"
    if delta == 1:
        return "encerra amanhã", "hot"
    if delta <= 7:
        return f"encerra em {delta} dias", "warm"
    return f"encerra em {delta} dias", ""


def short(text, n=110):
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(" ", 1)[0]
    return cut.rstrip(",.;:-") + "…"


def id_slug(rec_id):
    return re.sub(r"[^0-9A-Za-z-]+", "-", rec_id).strip("-")


def sentence_case(text):
    """Objetos costumam vir em CAIXA ALTA; deixa legível sem perder siglas curtas."""
    if text and sum(c.isupper() for c in text) > 0.6 * sum(c.isalpha() for c in text):
        return text[:1].upper() + text[1:].lower()
    return text


# ---------------------------------------------------------------- site

class Site:
    def __init__(self, cfg, out_dir, now):
        self.cfg = cfg
        self.out = out_dir
        self.now = now
        self.base = urlparse(cfg["site_url"]).path.rstrip("/")
        self.sitemap = []

    def u(self, path):
        return f"{self.base}{path}"

    def abs(self, path):
        return self.cfg["site_url"].rstrip("/") + path

    def write(self, path, content, index=True):
        full = os.path.join(self.out, path.lstrip("/"))
        if full.endswith("/") or full.endswith(os.sep):
            full = os.path.join(full, "index.html")
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        if index and path.endswith("/"):
            self.sitemap.append(path)

    # -- layout

    def page(self, path, title, desc, body, noindex=False, jsonld=None):
        cfg = self.cfg
        brand = esc(cfg["brand"])
        full_title = f"{title} | {cfg['brand']}" if title != cfg["brand"] else title
        meta_robots = '<meta name="robots" content="noindex,follow">' if noindex else ""
        verify = (f'<meta name="google-site-verification" content="{esc(cfg["google_site_verification"])}">'
                  if cfg.get("google_site_verification") else "")
        analytics = (f'<script data-goatcounter="https://{esc(cfg["goatcounter"])}.goatcounter.com/count" '
                     'async src="//gc.zgo.at/count.js"></script>' if cfg.get("goatcounter") else "")
        ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>' if jsonld else ""
        return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(self.abs(path))}">
{meta_robots}{verify}
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(full_title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(self.abs(path))}">
<meta property="og:locale" content="pt_BR">
<link rel="alternate" type="application/rss+xml" title="{brand}" href="{self.u('/feed.xml')}">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Ccircle cx='16' cy='16' r='14' fill='%230f766e'/%3E%3Ccircle cx='16' cy='16' r='8' fill='none' stroke='white' stroke-width='2.5'/%3E%3Ccircle cx='16' cy='16' r='2.5' fill='white'/%3E%3C/svg%3E">
<link rel="stylesheet" href="{self.u('/assets/style.css')}">
{ld}{analytics}
</head>
<body>
<header class="top"><div class="wrap">
<a class="logo" href="{self.u('/')}"><span class="dot"></span>{brand}</a>
<nav><a href="{self.u('/segmentos/')}">Segmentos</a><a href="{self.u('/estados/')}">Estados</a><a class="nav-pro" href="{self.u('/pro/')}">Alertas Pro</a></nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer class="foot"><div class="wrap">
<p><strong>{brand}</strong> organiza, todos os dias, as licitações com proposta aberta publicadas no
<a href="https://pncp.gov.br" rel="noopener">Portal Nacional de Contratações Públicas (PNCP)</a>.
Site independente, sem vínculo com o governo. Confira sempre o edital oficial antes de participar.</p>
<p>Atualizado em {self.now.strftime('%d/%m/%Y às %H:%M')} · <a href="{self.u('/sobre/')}">Sobre e fonte dos dados</a> · <a href="{self.u('/feed.xml')}">RSS</a></p>
</div></footer>
</body>
</html>
"""

    def crumbs(self, items):
        """items: [(nome, path|None)]; devolve (html, jsonld)."""
        parts, ld = [], []
        for i, (name, path) in enumerate(items, 1):
            parts.append(f'<a href="{self.u(path)}">{esc(name)}</a>' if path else f"<span>{esc(name)}</span>")
            entry = {"@type": "ListItem", "position": i, "name": name}
            if path:
                entry["item"] = self.abs(path)
            ld.append(entry)
        return (f'<nav class="crumbs">{" › ".join(parts)}</nav>',
                {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": ld})

    # -- componentes

    def item(self, r):
        label, cls = days_left(r["encerramento"], self.now)
        novo = '<span class="tag new">novo</span>' if r.get("novo") else ""
        where = f"{r['municipio']}/{r['uf']}" if r["municipio"] else r["uf"]
        return f"""<li class="item">
<a class="item-t" href="{self.u('/edital/' + id_slug(r['id']) + '/')}">{esc(short(sentence_case(r['objeto'])))}</a>
<div class="item-m">{novo}<span class="tag {cls}">{esc(label)}</span><span>{esc(where)}</span><span>{esc(r['modalidade'] or '')}</span><span class="val">{esc(brl(r['valor']))}</span></div>
</li>"""

    def listing(self, recs, limit):
        shown = recs[:limit]
        more = ""
        if len(recs) > limit:
            more = f'<p class="muted">Mostrando {limit} de {len(recs)} licitações, ordenadas pelo prazo mais próximo.</p>'
        if not shown:
            return '<p class="muted">Nenhuma licitação aberta neste recorte hoje.</p>'
        return f'<ul class="list">{"".join(self.item(r) for r in shown)}</ul>{more}'

    def cta(self, segment_name=None, uf=None):
        alvo = " de " + segment_name if segment_name else ""
        if uf:
            alvo += f" em {UF_NAMES.get(uf, uf)}"
        return f"""<aside class="cta">
<div><strong>Receba as novas licitações{esc(alvo)} no Telegram, todo dia às 7h.</strong>
<p>Alerta filtrado por segmento, planilha pronta para Excel e aviso de prazo encerrando. Por {esc(self.cfg['price_month'])}/mês.</p></div>
<a class="btn" href="{self.u('/pro/')}" data-goatcounter-click="cta-inline">Quero os alertas</a>
</aside>"""

    def chips(self, pairs):
        return '<div class="chips">' + "".join(
            f'<a class="chip" href="{self.u(p)}">{esc(n)} <b>{c}</b></a>' for n, p, c in pairs) + "</div>"


def checkout_block(site):
    cfg = site.cfg
    if cfg.get("checkout_url"):
        mensal = (f'<a class="btn big" href="{esc(cfg["checkout_url"])}" '
                  'data-goatcounter-click="checkout-mensal" rel="noopener">Assinar por '
                  f'{esc(cfg["price_month"])}/mês</a>')
        anual = ""
        if cfg.get("checkout_url_anual"):
            anual = (f'<a class="btn big ghost" href="{esc(cfg["checkout_url_anual"])}" '
                     'data-goatcounter-click="checkout-anual" rel="noopener">Plano anual: '
                     f'{esc(cfg["price_year"])} (2 meses grátis)</a>')
        return f'<div class="buy">{mensal}{anual}</div><p class="muted small">Pagamento por Pix, cartão ou boleto. Garantia de 7 dias: não gostou, pede reembolso direto na plataforma.</p>'
    if cfg.get("public_telegram_url"):
        return (f'<div class="buy"><a class="btn big" href="{esc(cfg["public_telegram_url"])}" rel="noopener" '
                'data-goatcounter-click="canal-gratis">Entrar no canal gratuito</a></div>'
                '<p class="muted small">Assinaturas Pro abrem em breve. Quem estiver no canal gratuito recebe o aviso primeiro.</p>')
    return '<div class="buy"><span class="btn big disabled">Assinaturas abrem em breve</span></div>'


# ---------------------------------------------------------------- build

def build_site(records, cfg, out_dir, now, status, history_csv=""):
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)
    site = Site(cfg, out_dir, now)
    recs = sorted(records, key=lambda r: (r["encerramento"] or "9999", r["id"]))

    by_seg = defaultdict(list)
    by_uf = defaultdict(list)
    by_seg_uf = defaultdict(list)
    for r in recs:
        by_uf[r["uf"]].append(r)
        for s in r["segmentos"]:
            by_seg[s].append(r)
            by_seg_uf[(s, r["uf"])].append(r)

    seg_order = [s for s, *_ in SEGMENTS]
    total = len(recs)
    novos = [r for r in recs if r.get("novo")]
    valor_total = sum(r["valor"] or 0 for r in recs)

    # assets
    os.makedirs(os.path.join(out_dir, "assets"))
    with open(os.path.join(out_dir, "assets", "style.css"), "w", encoding="utf-8") as f:
        f.write(CSS)

    # home
    soon = [r for r in recs if days_left(r["encerramento"], now)[1] == "hot"]
    newest = sorted(novos, key=lambda r: r["publicacao"] or "", reverse=True)
    seg_chips = site.chips([(SEGMENT_NAMES[s], f"/segmento/{s}/", len(by_seg[s])) for s in seg_order if by_seg[s]])
    uf_chips = site.chips([(uf, f"/uf/{uf.lower()}/", len(by_uf[uf])) for uf in sorted(by_uf) if uf in UF_NAMES])
    body = f"""<section class="hero">
<h1>Licitações abertas hoje, organizadas por segmento e estado</h1>
<p class="lead"><b>{num(total)}</b> licitações com proposta aberta agora, somando <b>{esc(brl(valor_total))}</b> em valor estimado.
<b>{num(len(novos))}</b> publicadas desde a última atualização. Dados oficiais do PNCP, atualizados todo dia.</p>
</section>
{site.cta()}
<h2>Por segmento</h2>{seg_chips}
<h2>Por estado</h2>{uf_chips}
<h2>Encerram hoje ou amanhã</h2>{site.listing(soon, 30)}
<h2>Publicadas recentemente</h2>{site.listing(newest, 30)}
"""
    site.write("/", site.page("/", "Licitações abertas hoje por segmento e estado",
                              f"{total} licitações com proposta aberta hoje no Brasil, organizadas por segmento e estado. "
                              "Dados do PNCP atualizados diariamente.", body,
                              jsonld={"@context": "https://schema.org", "@type": "WebSite", "name": cfg["brand"],
                                      "url": site.abs("/")}))

    # índices
    body = "<h1>Licitações abertas por segmento</h1>" + site.chips(
        [(SEGMENT_NAMES[s], f"/segmento/{s}/", len(by_seg[s])) for s in seg_order])
    site.write("/segmentos/", site.page("/segmentos/", "Licitações abertas por segmento",
                                         "Escolha o segmento e veja todas as licitações com proposta aberta hoje.", body))
    body = "<h1>Licitações abertas por estado</h1>" + site.chips(
        [(f"{UF_NAMES[uf]}", f"/uf/{uf.lower()}/", len(by_uf[uf])) for uf in sorted(UF_NAMES)])
    site.write("/estados/", site.page("/estados/", "Licitações abertas por estado",
                                       "Licitações com proposta aberta hoje em cada estado do Brasil.", body))

    # segmento e segmento × UF
    for s in seg_order:
        name = SEGMENT_NAMES[s]
        items = by_seg[s]
        crumbs, ld = site.crumbs([("Início", "/"), ("Segmentos", "/segmentos/"), (name, None)])
        ufs = site.chips([(uf, f"/segmento/{s}/{uf.lower()}/", len(by_seg_uf[(s, uf)]))
                          for uf in sorted(UF_NAMES) if by_seg_uf[(s, uf)]])
        body = f"""{crumbs}<h1>Licitações de {esc(name)} abertas hoje</h1>
<p class="lead">{len(items)} licitações de {esc(name.lower())} com proposta aberta no Brasil, somando {esc(brl(sum(r['valor'] or 0 for r in items)))}.</p>
<h2>Filtrar por estado</h2>{ufs}
{site.cta(name)}
<h2>Por prazo de encerramento</h2>{site.listing(items, 200)}"""
        site.write(f"/segmento/{s}/", site.page(
            f"/segmento/{s}/", f"Licitações de {name} abertas hoje",
            f"{len(items)} licitações de {name.lower()} com proposta aberta hoje. Veja órgão, valor estimado e prazo. Atualizado diariamente.",
            body, noindex=len(items) < MIN_INDEXABLE, jsonld=ld), index=len(items) >= MIN_INDEXABLE)
        for uf in sorted(UF_NAMES):
            items_uf = by_seg_uf[(s, uf)]
            if not items_uf:
                continue
            path = f"/segmento/{s}/{uf.lower()}/"
            crumbs, ld = site.crumbs([("Início", "/"), (name, f"/segmento/{s}/"), (UF_NAMES[uf], None)])
            cidades = defaultdict(int)
            for r in items_uf:
                cidades[r["municipio"]] += 1
            top = ", ".join(f"{c} ({n})" for c, n in sorted(cidades.items(), key=lambda x: -x[1])[:6] if c)
            body = f"""{crumbs}<h1>Licitações de {esc(name)} em {esc(UF_NAMES[uf])}</h1>
<p class="lead">{len(items_uf)} licitações abertas hoje em {esc(UF_NAMES[uf])}{(' — mais frequentes em ' + esc(top)) if top else ''}.</p>
{site.cta(name, uf)}
{site.listing(items_uf, 300)}
<p><a href="{site.u(f'/segmento/{s}/')}">Ver {esc(name)} em todo o Brasil</a> · <a href="{site.u(f'/uf/{uf.lower()}/')}">Todas as licitações em {esc(UF_NAMES[uf])}</a></p>"""
            site.write(path, site.page(
                path, f"Licitações de {name} em {UF_NAMES[uf]} ({uf})",
                f"{len(items_uf)} licitações de {name.lower()} abertas hoje em {UF_NAMES[uf]}. Prazos, valores e link para o edital oficial.",
                body, noindex=len(items_uf) < MIN_INDEXABLE, jsonld=ld), index=len(items_uf) >= MIN_INDEXABLE)

    # UF
    for uf in sorted(UF_NAMES):
        items = by_uf[uf]
        path = f"/uf/{uf.lower()}/"
        crumbs, ld = site.crumbs([("Início", "/"), ("Estados", "/estados/"), (UF_NAMES[uf], None)])
        segs = defaultdict(int)
        for r in items:
            for s in r["segmentos"]:
                segs[s] += 1
        chips = site.chips([(SEGMENT_NAMES[s], f"/segmento/{s}/{uf.lower()}/", segs[s]) for s in seg_order if segs[s]])
        body = f"""{crumbs}<h1>Licitações abertas em {esc(UF_NAMES[uf])}</h1>
<p class="lead">{len(items)} licitações com proposta aberta hoje em {esc(UF_NAMES[uf])}.</p>
<h2>Por segmento</h2>{chips}
{site.cta(uf=uf)}
<h2>Por prazo de encerramento</h2>{site.listing(items, 200)}"""
        site.write(path, site.page(path, f"Licitações abertas em {UF_NAMES[uf]} ({uf})",
                                   f"{len(items)} licitações com proposta aberta hoje em {UF_NAMES[uf]}, por segmento e prazo.",
                                   body, noindex=len(items) < MIN_INDEXABLE, jsonld=ld),
                   index=len(items) >= MIN_INDEXABLE)

    # edital
    for r in recs:
        path = f"/edital/{id_slug(r['id'])}/"
        seg = r["segmentos"][0] if r["segmentos"] else None
        where = f"{r['municipio']}/{r['uf']}" if r["municipio"] else r["uf"]
        trail: list = [("Início", "/")]
        if seg:
            trail += [(SEGMENT_NAMES[seg], f"/segmento/{seg}/"), (r["uf"], f"/segmento/{seg}/{r['uf'].lower()}/")]
        else:
            trail += [(UF_NAMES.get(r["uf"], r["uf"]), f"/uf/{r['uf'].lower()}/")]
        trail.append((f"{r['modalidade']} {r['numero'] or ''}".strip(), None))
        crumbs, ld = site.crumbs(trail)
        pool = by_seg_uf[(seg, r["uf"])] if seg else by_uf[r["uf"]]
        related = [x for x in pool if x["id"] != r["id"]][:8]
        label, cls = days_left(r["encerramento"], now)
        segs_html = " ".join(f'<a class="chip" href="{site.u(f"/segmento/{s}/")}">{esc(SEGMENT_NAMES[s])}</a>'
                             for s in r["segmentos"])
        info = f"<h2>Informação complementar</h2><p>{esc(r['info'])}</p>" if r.get("info") else ""
        origem = (f' · <a href="{esc(r["link_origem"])}" rel="noopener nofollow">sistema de origem</a>'
                  if r.get("link_origem") else "")
        title = f"{r['modalidade']} {r['numero'] or ''} – {short(sentence_case(r['objeto']), 60)} – {where}"
        body = f"""{crumbs}
<article class="edital">
<h1>{esc(sentence_case(r['objeto']) or 'Licitação sem descrição')}</h1>
<p><span class="tag {cls}">{esc(label)}</span> {'<span class="tag">registro de preços</span>' if r['srp'] else ''}</p>
<dl class="facts">
<dt>Órgão</dt><dd>{esc(r['orgao'])}{(' — ' + esc(r['unidade'])) if r['unidade'] else ''}</dd>
<dt>Local</dt><dd>{esc(where)}</dd>
<dt>Modalidade</dt><dd>{esc(r['modalidade'] or '—')}{(' · disputa ' + esc(r['modo_disputa'].lower())) if r.get('modo_disputa') else ''}</dd>
<dt>Número</dt><dd>{esc(r['numero'] or '—')} · processo {esc(r['processo'] or '—')}</dd>
<dt>Valor estimado</dt><dd>{esc(brl(r['valor']))}</dd>
<dt>Propostas</dt><dd>de {esc(dt(r['abertura']))} até <b>{esc(dt(r['encerramento']))}</b></dd>
<dt>Publicado no PNCP</dt><dd>{esc(dt(r['publicacao']))}</dd>
<dt>Controle PNCP</dt><dd>{esc(r['id'])}</dd>
</dl>
<p><a class="btn" href="{esc(r['url'])}" rel="noopener nofollow">Abrir edital oficial no PNCP</a>{origem}</p>
{('<p>' + segs_html + '</p>') if segs_html else ''}
{info}
</article>
{site.cta(SEGMENT_NAMES[seg] if seg else None, r['uf'])}
<h2>Outras licitações abertas {('de ' + esc(SEGMENT_NAMES[seg].lower()) + ' ') if seg else ''}em {esc(UF_NAMES.get(r['uf'], r['uf']))}</h2>
{site.listing(related, 8)}"""
        site.write(path, site.page(path, title,
                                   f"{r['modalidade']} de {r['orgao']} ({where}): {short(r['objeto'], 120)} Propostas até {dt(r['encerramento'], False)}. Valor estimado: {brl(r['valor'])}.",
                                   body, jsonld=ld))

    build_offer_pages(site, recs, by_seg, novos)
    build_meta_files(site, recs, status, history_csv)
    return site


def build_offer_pages(site, recs, by_seg, novos):
    cfg = site.cfg
    # exemplo real de alerta, montado com os dados do dia
    sample_seg = max(by_seg, key=lambda s: len([r for r in by_seg[s] if r.get("novo")]), default=None)
    sample = [r for r in by_seg.get(sample_seg, []) if r.get("novo")][:4] or by_seg.get(sample_seg, [])[:4]
    lines = "".join(
        f"<li><b>{esc(short(sentence_case(r['objeto']), 80))}</b><br>{esc(r['municipio'])}/{esc(r['uf'])} · "
        f"{esc(brl(r['valor']))} · até {esc(dt(r['encerramento'], False))}</li>" for r in sample)
    exemplo = (f'<div class="phone"><div class="msg"><p>📡 <b>{esc(SEGMENT_NAMES.get(sample_seg, ""))}</b> — '
               f'{len([r for r in by_seg.get(sample_seg, []) if r.get("novo")])} novas hoje</p><ul>{lines}</ul>'
               f'<p class="muted small">+ planilha .csv com todas as abertas</p></div></div>') if sample_seg else ""
    body = f"""<section class="hero">
<h1>Pare de caçar edital. Receba as licitações do seu segmento no celular, todo dia.</h1>
<p class="lead">Hoje há <b>{len(recs)}</b> licitações abertas e <b>{len(novos)}</b> novas desde ontem. Ninguém tem tempo de olhar tudo isso —
o Radar olha por você e manda só o que é do seu ramo.</p>
</section>
<div class="two">
<div>
<h2>O que você recebe</h2>
<ul class="checks">
<li><b>Alerta diário às 7h no Telegram</b> com as licitações publicadas nas últimas 24h, separadas por segmento com hashtag (#limpeza_conservacao, #obras_engenharia…) — silencie o que não interessa.</li>
<li><b>Planilha pronta</b> (.csv que abre no Excel) com todas as licitações abertas de cada segmento: órgão, cidade, valor, prazo e link do edital.</li>
<li><b>Aviso de prazo</b>: lista das que encerram em 48h, para você não perder a data.</li>
<li><b>{len(SEGMENTS)} segmentos</b> e os 27 estados, direto da fonte oficial (PNCP), sem cadastro de CNPJ nem configuração.</li>
</ul>
<h2>Como funciona</h2>
<ol class="steps"><li>Você assina pela plataforma de pagamento (Pix, cartão ou boleto).</li>
<li>Na mesma hora recebe por e-mail o link de entrada no canal privado do Telegram.</li>
<li>No dia seguinte, às 7h, chega o primeiro alerta. Pronto.</li></ol>
</div>
<div>{exemplo}</div>
</div>
<section class="price">
<h2>Preço</h2>
<p class="big-price">{esc(cfg['price_month'])}<small>/mês</small></p>
<p>Menos que um almoço. Uma única licitação ganha paga anos de assinatura.</p>
{checkout_block(site)}
</section>
<h2>Perguntas frequentes</h2>
<details><summary>De onde vêm os dados?</summary><p>Do Portal Nacional de Contratações Públicas (PNCP), onde União, estados e municípios são obrigados a publicar suas contratações pela Lei 14.133/2021. Coletamos a API pública uma vez por dia.</p></details>
<details><summary>Qual a diferença para o site gratuito?</summary><p>O site mostra tudo, mas você precisa lembrar de entrar e procurar. O Pro chega sozinho, só com o que é novo, filtrado por segmento, com planilha e aviso de prazo.</p></details>
<details><summary>Cobre todas as licitações do Brasil?</summary><p>Cobre tudo o que é publicado no PNCP com prazo de proposta aberto. Alguns órgãos ainda publicam só em portais próprios; esses não aparecem.</p></details>
<details><summary>Posso cancelar?</summary><p>Sim, a qualquer momento, na própria plataforma de pagamento. Sem fidelidade. Nos primeiros 7 dias o reembolso é integral.</p></details>
<details><summary>Vocês participam da licitação por mim?</summary><p>Não. O Radar encontra as oportunidades; a proposta e a habilitação são com você.</p></details>
"""
    site.write("/pro/", site.page("/pro/", "Alertas diários de licitação no Telegram",
                                  f"Receba todo dia as novas licitações do seu segmento no Telegram, com planilha e aviso de prazo. {cfg['price_month']}/mês.",
                                  body))
    body = f"""<section class="hero"><h1>Assinatura confirmada. Obrigado!</h1>
<p class="lead">O link de entrada no canal privado do Telegram foi enviado para o seu e-mail pela plataforma de pagamento
(confira também a caixa de spam e a área de membros da compra).</p></section>
<ol class="steps"><li>Instale o Telegram, se ainda não tiver.</li><li>Abra o link recebido e toque em <b>Entrar</b>.</li>
<li>Use a busca do canal com a hashtag do seu segmento (ex.: <code>#limpeza_conservacao</code>) ou silencie as demais.</li></ol>
<p>O primeiro alerta chega às 7h do próximo dia. Enquanto isso, veja as <a href="{site.u('/segmentos/')}">licitações abertas por segmento</a>.</p>"""
    site.write("/obrigado/", site.page("/obrigado/", "Assinatura confirmada", "Próximos passos da assinatura.", body, noindex=True),
               index=False)
    body = f"""<h1>Sobre o {esc(cfg['brand'])}</h1>
<p>O {esc(cfg['brand'])} é um site independente que organiza as licitações públicas com proposta aberta, publicadas no
<a href="https://pncp.gov.br" rel="noopener">PNCP</a>. Os dados são públicos (Lei 14.133/2021 e Lei de Acesso à Informação)
e são coletados uma vez por dia pela API oficial de consulta.</p>
<p>A classificação por segmento é automática, feita por palavras-chave no objeto da contratação; uma licitação pode aparecer
em mais de um segmento ou em nenhum. Sempre confira o edital oficial antes de tomar qualquer decisão.</p>
<p>Não temos vínculo com nenhum órgão público. Não coletamos dados pessoais de visitantes; a medição de audiência, quando ativa,
é agregada e sem cookies.</p>"""
    site.write("/sobre/", site.page("/sobre/", "Sobre e fonte dos dados", "Como o site coleta e organiza as licitações do PNCP.", body))
    site.write("/404.html", site.page("/404.html", "Página não encontrada",
                                      "Esta licitação pode ter encerrado.",
                                      f"<h1>Página não encontrada</h1><p>Esta licitação provavelmente já encerrou o prazo de propostas e saiu do radar.</p>"
                                      f"<p><a class='btn' href='{site.u('/segmentos/')}'>Ver licitações abertas</a></p>", noindex=True),
               index=False)


def build_meta_files(site, recs, status, history_csv):
    out = site.out
    urls = sorted(set(site.sitemap))
    chunks = [urls[i:i + 40000] for i in range(0, len(urls), 40000)] or [[]]
    today = site.now.strftime("%Y-%m-%d")
    for n, chunk in enumerate(chunks, 1):
        with open(os.path.join(out, f"sitemap-{n}.xml"), "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
            for p in chunk:
                f.write(f"<url><loc>{esc(site.abs(p))}</loc><lastmod>{today}</lastmod></url>\n")
            f.write("</urlset>\n")
    with open(os.path.join(out, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for n in range(1, len(chunks) + 1):
            f.write(f"<sitemap><loc>{esc(site.abs(f'/sitemap-{n}.xml'))}</loc><lastmod>{today}</lastmod></sitemap>\n")
        f.write("</sitemapindex>\n")
    with open(os.path.join(out, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nDisallow: /obrigado/\nSitemap: {site.abs('/sitemap.xml')}\n")

    newest = sorted(recs, key=lambda r: r["publicacao"] or "", reverse=True)[:100]
    items = "".join(
        f"<item><title>{esc(short(sentence_case(r['objeto']), 120))} ({esc(r['municipio'])}/{esc(r['uf'])})</title>"
        f"<link>{esc(site.abs('/edital/' + id_slug(r['id']) + '/'))}</link>"
        f"<guid isPermaLink=\"false\">{esc(r['id'])}</guid>"
        f"<description>{esc(r['orgao'])} · {esc(brl(r['valor']))} · propostas até {esc(dt(r['encerramento']))}</description></item>"
        for r in newest)
    with open(os.path.join(out, "feed.xml"), "w", encoding="utf-8") as f:
        f.write(f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{esc(site.cfg["brand"])}</title>'
                f'<link>{esc(site.abs("/"))}</link><description>Licitações abertas publicadas no PNCP</description>'
                f'<language>pt-br</language>{items}</channel></rss>')

    data_dir = os.path.join(out, "data")
    os.makedirs(data_dir, exist_ok=True)
    with gzip.open(os.path.join(data_dir, "snapshot.json.gz"), "wt", encoding="utf-8") as f:
        json.dump(recs, f, ensure_ascii=False)
    with open(os.path.join(out, "status.json"), "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=1)
    header = "data,total,novos,paginas_falhas,recuperados,segundos\n"
    line = (f"{site.now.strftime('%Y-%m-%d %H:%M')},{status['total']},{status['novos']},"
            f"{len(status['failed_pages'])},{status.get('recovered', 0)},{status['seconds']}\n")
    history = history_csv if history_csv.startswith("data,") else header
    with open(os.path.join(data_dir, "history.csv"), "w", encoding="utf-8") as f:
        f.write(history.rstrip("\n") + "\n" + line)
    if site.cfg.get("indexnow_key"):  # prova de posse para o IndexNow (Bing, Yandex, Seznam...)
        with open(os.path.join(out, f"{site.cfg['indexnow_key']}.txt"), "w", encoding="utf-8") as f:
            f.write(site.cfg["indexnow_key"])
    # .nojekyll: GitHub Pages serve os arquivos como estão
    open(os.path.join(out, ".nojekyll"), "w").close()


CSS = """:root{--bg:#fbfaf7;--fg:#1c1f23;--muted:#5d6670;--line:#e4e1da;--card:#fff;--accent:#0f766e;--accent-2:#115e59;--hot:#b42318;--hot-bg:#fdecea;--warm:#9a6700;--warm-bg:#fff4d6;--new:#1d4ed8;--new-bg:#e6edff}
@media (prefers-color-scheme:dark){:root{--bg:#121416;--fg:#e8e6e1;--muted:#9aa3ad;--line:#2a2e33;--card:#1a1d20;--accent:#2dd4bf;--accent-2:#5eead4;--hot:#ff8a80;--hot-bg:#3a1d1b;--warm:#f5c451;--warm-bg:#352b12;--new:#9db4ff;--new-bg:#1c2542}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--accent)}a:hover{color:var(--accent-2)}
.wrap{max-width:1040px;margin:0 auto;padding:0 16px}
.top{border-bottom:1px solid var(--line);background:var(--card)}.top .wrap{display:flex;align-items:center;justify-content:space-between;gap:12px;min-height:58px;flex-wrap:wrap}
.logo{font-weight:700;text-decoration:none;color:var(--fg);display:flex;align-items:center;gap:8px}.dot{width:14px;height:14px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 4px color-mix(in srgb,var(--accent) 25%,transparent)}
nav a{margin-left:16px;text-decoration:none;color:var(--muted);font-size:15px}nav a:first-child{margin-left:0}.nav-pro{color:var(--accent)!important;font-weight:600}
main{padding:24px 16px 48px}h1{font-size:clamp(1.5rem,3.2vw,2.2rem);line-height:1.2;margin:.4em 0}h2{font-size:1.2rem;margin:1.8em 0 .6em}
.lead{font-size:1.08rem;color:var(--muted);max-width:760px}.muted{color:var(--muted)}.small{font-size:.88rem}
.hero{padding:12px 0 4px}
.chips{display:flex;flex-wrap:wrap;gap:8px}.chip{display:inline-flex;gap:6px;align-items:center;padding:6px 12px;border:1px solid var(--line);border-radius:999px;background:var(--card);text-decoration:none;color:var(--fg);font-size:.92rem}.chip b{color:var(--accent);font-weight:600}.chip:hover{border-color:var(--accent)}
.list{list-style:none;padding:0;margin:0;border:1px solid var(--line);border-radius:12px;background:var(--card);overflow:hidden}
.item{padding:12px 16px;border-top:1px solid var(--line)}.item:first-child{border-top:0}
.item-t{font-weight:600;text-decoration:none;color:var(--fg);display:block}.item-t:hover{color:var(--accent)}
.item-m{display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:4px;font-size:.88rem;color:var(--muted)}.val{font-variant-numeric:tabular-nums}
.tag{display:inline-block;padding:1px 8px;border-radius:6px;font-size:.8rem;background:var(--line);color:var(--fg)}.tag.hot{background:var(--hot-bg);color:var(--hot)}.tag.warm{background:var(--warm-bg);color:var(--warm)}.tag.new{background:var(--new-bg);color:var(--new)}
.cta{display:flex;gap:16px;align-items:center;justify-content:space-between;flex-wrap:wrap;margin:24px 0;padding:16px 20px;border-radius:12px;border:1px solid color-mix(in srgb,var(--accent) 40%,var(--line));background:color-mix(in srgb,var(--accent) 7%,var(--card))}.cta p{margin:.2em 0 0;color:var(--muted);font-size:.95rem}
.btn{display:inline-block;padding:10px 18px;border-radius:10px;background:var(--accent);color:#fff!important;text-decoration:none;font-weight:600;border:0}.btn:hover{background:var(--accent-2)}
@media (prefers-color-scheme:dark){.btn{color:#062b27!important}}
.btn.big{padding:14px 24px;font-size:1.05rem}.btn.ghost{background:transparent;color:var(--accent)!important;border:1.5px solid var(--accent)}.btn.disabled{background:var(--line);color:var(--muted)!important;cursor:default}
.buy{display:flex;gap:12px;flex-wrap:wrap;margin:16px 0 8px}
.crumbs{font-size:.88rem;color:var(--muted);margin-bottom:4px}.crumbs a{color:var(--muted)}
.edital{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:8px 20px 16px}
.facts{display:grid;grid-template-columns:170px 1fr;gap:6px 16px;margin:16px 0}.facts dt{color:var(--muted)}.facts dd{margin:0}
@media (max-width:600px){.facts{grid-template-columns:1fr}.facts dt{margin-top:6px}}
.two{display:grid;grid-template-columns:1.3fr 1fr;gap:32px;align-items:start}@media (max-width:800px){.two{grid-template-columns:1fr}}
.checks{padding-left:1.2em}.checks li{margin:.5em 0}.steps li{margin:.4em 0}
.phone{border:1px solid var(--line);border-radius:24px;padding:18px;background:var(--card);max-width:380px;margin-top:24px}.msg{background:color-mix(in srgb,var(--accent) 9%,var(--card));border-radius:14px;padding:12px 14px;font-size:.92rem}.msg ul{padding-left:1.1em;margin:.4em 0}.msg li{margin:.5em 0}
.price{margin:32px 0;padding:20px 24px;border:1px solid var(--line);border-radius:14px;background:var(--card)}.big-price{font-size:2.4rem;font-weight:700;margin:.1em 0}.big-price small{font-size:1rem;color:var(--muted);font-weight:400}
details{border-top:1px solid var(--line);padding:10px 0}summary{cursor:pointer;font-weight:600}
.foot{border-top:1px solid var(--line);color:var(--muted);font-size:.88rem;padding:8px 0 24px}
code{background:var(--line);padding:1px 6px;border-radius:4px}
"""
