"""Envio de alertas pelo Bot API do Telegram (gratuito, sem dependências).

Variáveis de ambiente (segredos no GitHub Actions, nunca no repositório):
  TELEGRAM_BOT_TOKEN       token do bot criado no @BotFather
  TELEGRAM_PUBLIC_CHAT     canal gratuito (ex.: @radareditais) — amostra diária
  TELEGRAM_PRO_CHAT        canal privado dos assinantes (id numérico, ex.: -100123...)
  TELEGRAM_ADMIN_CHAT      seu chat pessoal com o bot, para alertas de falha
"""
import csv
import html
import io
import json
import logging
import os
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime

from .build import brl, days_left, dt, id_slug, sentence_case, short
from .segments import SEGMENTS, SEGMENT_NAMES

log = logging.getLogger("radar.telegram")
MAX_MSG = 3900  # limite do Telegram é 4096 caracteres
HASHTAG = {slug: "#" + slug.replace("-", "_") for slug, *_ in SEGMENTS}


class Telegram:
    def __init__(self, token):
        self.base = f"https://api.telegram.org/bot{token}/"

    def _call(self, method, data=None, body=None, headers=None, retries=3):
        last = None
        for attempt in range(retries):
            try:
                if body is None:
                    body = json.dumps(data).encode()
                    headers = {"Content-Type": "application/json"}
                req = urllib.request.Request(self.base + method, data=body, headers=headers)
                with urllib.request.urlopen(req, timeout=60) as resp:
                    return json.loads(resp.read())
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")
                if e.code == 429:  # rate limit: respeita retry_after
                    wait = json.loads(detail).get("parameters", {}).get("retry_after", 30)
                    time.sleep(wait + 1)
                    continue
                # a URL contém o token: nunca registrá-la
                raise RuntimeError(f"Telegram {method} HTTP {e.code}: {detail[:300]}") from None
            except (urllib.error.URLError, TimeoutError) as e:
                time.sleep(5 * (attempt + 1))
                last = e
        raise RuntimeError(f"Telegram {method} falhou após {retries} tentativas: {type(last).__name__}")

    def send(self, chat, text):
        r = self._call("sendMessage", {"chat_id": chat, "text": text, "parse_mode": "HTML",
                                       "disable_web_page_preview": True})
        time.sleep(3.1)  # limite de ~20 mensagens/min em canal
        return r

    def send_file(self, chat, filename, content, caption=""):
        boundary = uuid.uuid4().hex
        parts = []
        for k, v in (("chat_id", str(chat)), ("caption", caption), ("parse_mode", "HTML")):
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="document"; filename="{filename}"\r\n'
                     f"Content-Type: text/csv\r\n\r\n".encode() + content + b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        r = self._call("sendDocument", body=b"".join(parts),
                       headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        time.sleep(3.1)
        return r


def _line(r, site_url):
    e = html.escape
    link = f"{site_url.rstrip('/')}/edital/{id_slug(r['id'])}/"
    return (f"• <a href=\"{e(link)}\">{e(short(sentence_case(r['objeto']), 110))}</a>\n"
            f"  {e(r['municipio'])}/{e(r['uf'])} · {e(brl(r['valor']))} · até {e(dt(r['encerramento'], False))}")


def chunk_messages(header, lines):
    """Quebra uma lista longa em mensagens abaixo do limite do Telegram."""
    msgs, cur = [], header
    for ln in lines:
        if len(cur) + len(ln) + 2 > MAX_MSG:
            msgs.append(cur)
            cur = header + " (cont.)"
        cur += "\n\n" + ln
    msgs.append(cur)
    return msgs


def to_csv(recs, site_url):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["encerramento", "uf", "municipio", "orgao", "modalidade", "numero", "objeto",
                "valor_estimado", "publicado", "link_pncp", "pagina_radar"])
    for r in recs:
        w.writerow([dt(r["encerramento"]), r["uf"], r["municipio"], r["orgao"], r["modalidade"], r["numero"],
                    r["objeto"], f"{r['valor']:.2f}".replace(".", ",") if r["valor"] else "", dt(r["publicacao"]),
                    r["url"], f"{site_url.rstrip('/')}/edital/{id_slug(r['id'])}/"])
    return ("﻿" + buf.getvalue()).encode("utf-8")  # BOM: acentos certos no Excel


def notify(records, cfg, now=None, dry_run=False):
    """Posta a amostra gratuita e o pacote Pro. Sem token configurado, só registra e sai."""
    now = now or datetime.now()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    public, pro = os.environ.get("TELEGRAM_PUBLIC_CHAT"), os.environ.get("TELEGRAM_PRO_CHAT")
    site_url = cfg["site_url"]
    novos = [r for r in records if r.get("novo")]
    by_seg = {s: [] for s, *_ in SEGMENTS}
    for r in sorted(novos, key=lambda r: -(r["valor"] or 0)):
        for s in r["segmentos"]:
            by_seg[s].append(r)
    outbox = []  # (chat, tipo, payload)

    if public:
        top = sorted(novos, key=lambda r: -(r["valor"] or 0))[:8]
        head = (f"📡 <b>{len(novos)} novas licitações hoje</b> ({now:%d/%m})\n"
                f"As 8 de maior valor estimado:")
        body = [_line(r, site_url) for r in top]
        tail = (f"\n\nTodas por segmento e estado: {site_url}\n"
                f"Alerta completo do seu segmento + planilha, todo dia: {site_url.rstrip('/')}/pro/")
        outbox.append((public, "msg", chunk_messages(head, body)[0] + tail))

    if pro:
        outbox.append((pro, "msg", f"☀️ <b>Radar de {now:%d/%m/%Y}</b>\n{len(novos)} licitações novas no PNCP. "
                                   f"Use a busca do canal com a hashtag do seu segmento."))
        for s, items in by_seg.items():
            if not items:
                continue
            head = f"{HASHTAG[s]} <b>{html.escape(SEGMENT_NAMES[s])}</b> — {len(items)} novas"
            for m in chunk_messages(head, [_line(r, site_url) for r in items[:60]]):
                outbox.append((pro, "msg", m))
            open_all = [r for r in records if s in r["segmentos"]]
            outbox.append((pro, "file", (f"{s}-{now:%Y%m%d}.csv", to_csv(open_all, site_url),
                                         f"{HASHTAG[s]} planilha com as {len(open_all)} abertas")))
        closing = [r for r in records if days_left(r["encerramento"], now)[1] == "hot"]
        if closing:
            closing.sort(key=lambda r: -(r["valor"] or 0))
            for m in chunk_messages(f"⏰ <b>Encerram hoje ou amanhã</b> — {len(closing)} (maiores valores)",
                                    [_line(r, site_url) for r in closing[:40]]):
                outbox.append((pro, "msg", m))

    if dry_run or not token:
        if not token:
            log.warning("TELEGRAM_BOT_TOKEN ausente: %s envios preparados e não enviados", len(outbox))
        return {"sent": 0, "prepared": len(outbox), "outbox": outbox}

    tg, sent, errors = Telegram(token), 0, []
    for chat, kind, payload in outbox:
        try:
            if kind == "msg":
                tg.send(chat, payload)
            else:
                tg.send_file(chat, *payload)
            sent += 1
        except RuntimeError as e:
            errors.append(str(e))
            log.error("%s", e)
    return {"sent": sent, "prepared": len(outbox), "errors": errors}


def alert_admin(text):
    token, admin = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_ADMIN_CHAT")
    if not (token and admin):
        return False
    try:
        Telegram(token).send(admin, text[:MAX_MSG])
        return True
    except RuntimeError as e:
        log.error("alerta admin falhou: %s", e)
        return False
