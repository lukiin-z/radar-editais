"""Orquestrador do Radar de Editais.

  python run.py collect [--max-pages N]   coleta PNCP + gera site em public/
  python run.py notify [--dry-run]        envia alertas do Telegram (após o deploy)
  python run.py ping                      avisa buscadores (IndexNow) das páginas novas
  python run.py health                    valida a execução; sai com erro se algo está ruim
  python run.py all [--max-pages N]       collect + notify + health (uso local)

Configuração: config.json, sobrescrita por variáveis de ambiente de mesmo nome em
maiúsculas (SITE_URL, CHECKOUT_URL, ...), que é como o GitHub Actions injeta valores.
"""
import argparse
import gzip
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from radar.build import build_site
from radar.fetch import fetch_open, merge_with_previous, still_open
from radar.telegram import alert_admin, notify

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "public")
WORK = os.path.join(ROOT, "work")
TZ = timezone(timedelta(hours=-3))  # Brasília; sem horário de verão desde 2019
log = logging.getLogger("radar")


def load_config():
    with open(os.path.join(ROOT, "config.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    for key in list(cfg):
        val = os.environ.get(key.upper())
        if val:
            cfg[key] = type(cfg[key])(val) if isinstance(cfg[key], (int, float)) else val
    return cfg


def now_brt():
    # dados do PNCP vêm em horário de Brasília, sem fuso
    return datetime.now(TZ).replace(tzinfo=None, microsecond=0)


def _download(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": "radar-editais/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def load_previous(cfg):
    """Snapshot e histórico da última execução: primeiro local, senão do site publicado."""
    snap, hist = None, ""
    local = os.path.join(WORK, "previous.json.gz")
    try:
        if os.path.exists(local):
            with gzip.open(local, "rt", encoding="utf-8") as f:
                snap = json.load(f)
        else:
            snap = json.loads(gzip.decompress(_download(cfg["site_url"].rstrip("/") + "/data/snapshot.json.gz")))
    except Exception as e:
        log.warning("sem snapshot anterior (%s); todos os publicados nas últimas 24h contam como novos", e)
    try:
        hist = _download(cfg["site_url"].rstrip("/") + "/data/history.csv").decode("utf-8")
    except Exception as e:
        log.warning("sem histórico anterior (%s)", e)
    return snap, hist


def mark_new(records, previous, now):
    if previous:
        old = {r["id"] for r in previous}
        for r in records:
            r["novo"] = r["id"] not in old
    else:
        cutoff = (now - timedelta(hours=24)).isoformat()
        for r in records:
            r["novo"] = (r.get("publicacao") or "") >= cutoff


def cmd_collect(cfg, max_pages=None):
    now = now_brt()
    previous, history = load_previous(cfg)
    try:
        records, report = fetch_open(cfg["horizon_days"], cfg["workers"], max_pages, now, cfg["request_interval"])
    except RuntimeError as e:
        # PNCP fora do ar: publica o snapshot anterior (o que ainda está aberto) e deixa o health acusar
        if not previous:
            raise
        log.error("PNCP indisponível (%s); modo degradado com o snapshot anterior", e)
        records, report = [], {"api_total": None, "pages": 1, "failed_pages": ["todas"], "fetched": 0,
                               "seconds": 0, "degraded": True}
    records = merge_with_previous(records, previous, report, now)
    records = [r for r in records if still_open(r, now)]
    mark_new(records, previous, now)
    status = {
        "generated_at": now.isoformat(),
        "total": len(records),
        "novos": sum(1 for r in records if r["novo"]),
        "classificados": sum(1 for r in records if r["segmentos"]),
        **report,
    }
    build_site(records, cfg, OUT, now, status, history)
    os.makedirs(WORK, exist_ok=True)
    with gzip.open(os.path.join(WORK, "run.json.gz"), "wt", encoding="utf-8") as f:
        json.dump({"status": status, "records": records}, f, ensure_ascii=False)
    with open(os.path.join(WORK, "status.json"), "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=1)
    log.info("site gerado: %s abertas, %s novas, %s páginas com falha, %ss",
             status["total"], status["novos"], len(status["failed_pages"]), status["seconds"])
    return status


def _load_run():
    with gzip.open(os.path.join(WORK, "run.json.gz"), "rt", encoding="utf-8") as f:
        return json.load(f)


def cmd_notify(cfg, dry_run=False):
    run = _load_run()
    result = notify(run["records"], cfg, now_brt(), dry_run=dry_run)
    if dry_run:
        os.makedirs(WORK, exist_ok=True)
        with open(os.path.join(WORK, "outbox-preview.txt"), "w", encoding="utf-8") as f:
            for chat, kind, payload in result["outbox"]:
                f.write(f"=== {chat} [{kind}] ===\n")
                f.write((payload if kind == "msg" else f"{payload[0]} ({len(payload[1])} bytes) {payload[2]}") + "\n\n")
    result.pop("outbox", None)
    with open(os.path.join(WORK, "notify.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)
    log.info("telegram: %s", result)
    return result


def cmd_ping(cfg):
    """Avisa buscadores compatíveis com IndexNow sobre páginas novas (gratuito, sem conta)."""
    if not cfg.get("indexnow_key"):
        return {"skipped": "sem indexnow_key"}
    from radar.build import id_slug
    from radar.segments import SEGMENTS
    base = cfg["site_url"].rstrip("/")
    records = _load_run()["records"]
    urls = [base + "/", base + "/pro/"] + [f"{base}/segmento/{s}/" for s, *_ in SEGMENTS]
    urls += [f"{base}/edital/{id_slug(r['id'])}/" for r in records if r.get("novo")]
    urls = urls[:10000]
    host = urllib.parse.urlparse(base).netloc
    body = json.dumps({"host": host, "key": cfg["indexnow_key"], "urlList": urls,
                       "keyLocation": f"{base}/{cfg['indexnow_key']}.txt"}).encode()
    req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body,
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = {"status": resp.status, "urls": len(urls)}
    except urllib.error.HTTPError as e:
        result = {"status": e.code, "urls": len(urls), "erro": e.read().decode(errors="replace")[:200]}
    log.info("indexnow: %s", result)
    with open(os.path.join(WORK, "ping.json"), "w", encoding="utf-8") as f:
        json.dump(result, f)
    return result


def cmd_health(cfg):
    """Regras de saúde. Qualquer violação: alerta no Telegram do admin e exit 1 (GitHub manda e-mail)."""
    problems = []
    try:
        status = json.load(open(os.path.join(WORK, "status.json"), encoding="utf-8"))
    except FileNotFoundError:
        status = None
        problems.append("status.json não existe: a coleta nem terminou")
    if status:
        if status.get("degraded"):
            problems.append("PNCP indisponível: site publicado com o snapshot do dia anterior")
        if status["total"] < cfg["min_total_ok"]:
            problems.append(f"só {status['total']} licitações abertas (mínimo esperado {cfg['min_total_ok']})")
        if status["pages"] and len(status["failed_pages"]) / status["pages"] > 0.2:
            problems.append(f"{len(status['failed_pages'])} de {status['pages']} páginas do PNCP falharam")
        if status["total"] and status["classificados"] / status["total"] < 0.4:
            problems.append(f"só {status['classificados']} de {status['total']} classificadas em segmento")
    notify_file = os.path.join(WORK, "notify.json")
    if os.path.exists(notify_file):
        n = json.load(open(notify_file, encoding="utf-8"))
        if n.get("errors"):
            problems.append(f"{len(n['errors'])} envios ao Telegram falharam: {n['errors'][0][:200]}")
    if problems:
        msg = "🚨 Radar de Editais — execução com problema:\n- " + "\n- ".join(problems)
        log.error(msg)
        alert_admin(msg)
        return 1
    log.info("saúde OK: %s", status)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["collect", "notify", "ping", "health", "all"])
    ap.add_argument("--max-pages", type=int, default=None, help="limita páginas do PNCP (teste local)")
    ap.add_argument("--dry-run", action="store_true", help="prepara as mensagens sem enviar")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = load_config()
    t0 = time.time()
    try:
        if args.cmd in ("collect", "all"):
            cmd_collect(cfg, args.max_pages)
        if args.cmd in ("notify", "all"):
            cmd_notify(cfg, args.dry_run)
        if args.cmd == "ping":
            cmd_ping(cfg)
        if args.cmd in ("health", "all"):
            return cmd_health(cfg)
    except Exception as e:
        log.exception("falha em %s", args.cmd)
        alert_admin(f"🚨 Radar de Editais — '{args.cmd}' quebrou: {type(e).__name__}: {e}"[:500])
        return 1
    finally:
        log.info("%s em %.0fs", args.cmd, time.time() - t0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
