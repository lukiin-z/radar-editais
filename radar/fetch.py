"""Coleta de contratações com proposta aberta na API pública de consulta do PNCP.

Endpoint: GET https://pncp.gov.br/api/consulta/v1/contratacoes/proposta
Sem autenticação. Máximo de 50 registros por página. A latência varia de 2 s a 25 s e o
serviço responde 429 acima de ~30 requisições/min: poucas threads e um espaçamento global.
"""
import json
import logging
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from .segments import classify

API = "https://pncp.gov.br/api/consulta/v1/contratacoes/proposta"
PAGE_SIZE = 50
USER_AGENT = "radar-editais/1.0 (+dados abertos PNCP; coleta 1x/dia)"
log = logging.getLogger("radar.fetch")


class Throttle:
    """Espaça o início das requisições entre todas as threads (a API responde 429 acima de ~30/min)."""

    def __init__(self, interval):
        self.interval = interval
        self.lock = threading.Lock()
        self.next_at = 0.0

    def wait(self):
        with self.lock:
            now = time.monotonic()
            start = max(now, self.next_at)
            self.next_at = start + self.interval
        time.sleep(max(0.0, start - now))

    def pause(self, seconds):
        """Após um 429, empurra todas as threads para depois da janela."""
        with self.lock:
            self.next_at = max(self.next_at, time.monotonic() + seconds)


THROTTLE = Throttle(2.0)


def _get_json(url, timeout=120, retries=4):
    last = None
    for attempt in range(retries):
        THROTTLE.wait()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 204:
                    return {"data": [], "totalPaginas": 0, "totalRegistros": 0}
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as e:
            last = e
            # 4xx de parâmetro não melhora com nova tentativa
            if isinstance(e, urllib.error.HTTPError) and 400 <= e.code < 500 and e.code != 429:
                break
            wait = 5 * (2 ** attempt)
            if isinstance(e, urllib.error.HTTPError) and e.code == 429:
                retry_after = e.headers.get("Retry-After", "")
                wait = int(retry_after) if retry_after.isdigit() else 30 * (attempt + 1)
                THROTTLE.pause(wait)
            log.warning("falha em %s (%s); nova tentativa em %ss", url, e, wait)
            time.sleep(wait)
    raise RuntimeError(f"falhou após {retries} tentativas: {url}: {last}")


def _page_url(data_final, page):
    return f"{API}?dataFinal={data_final}&pagina={page}&tamanhoPagina={PAGE_SIZE}"


def normalize_record(r):
    """Reduz o registro do PNCP aos campos usados pelo site e pelos alertas."""
    org = r.get("orgaoEntidade") or {}
    uni = r.get("unidadeOrgao") or {}
    cnpj, ano, seq = org.get("cnpj"), r.get("anoCompra"), r.get("sequencialCompra")
    objeto = (r.get("objetoCompra") or "").strip()
    return {
        "id": r.get("numeroControlePNCP"),
        "url": f"https://pncp.gov.br/app/editais/{cnpj}/{ano}/{seq}",
        "orgao": (org.get("razaoSocial") or "").strip(),
        "unidade": (uni.get("nomeUnidade") or "").strip(),
        "uf": (uni.get("ufSigla") or "").strip().upper(),
        "municipio": (uni.get("municipioNome") or "").strip(),
        "esfera": org.get("esferaId"),
        "objeto": objeto,
        "info": (r.get("informacaoComplementar") or "").strip()[:1500],
        "modalidade": r.get("modalidadeNome"),
        "modo_disputa": r.get("modoDisputaNome"),
        "numero": r.get("numeroCompra"),
        "processo": r.get("processo"),
        "srp": bool(r.get("srp")),
        "valor": r.get("valorTotalEstimado"),
        "abertura": r.get("dataAberturaProposta"),
        "encerramento": r.get("dataEncerramentoProposta"),
        "publicacao": r.get("dataPublicacaoPncp"),
        "link_origem": r.get("linkSistemaOrigem"),
        "segmentos": classify(objeto + " " + (r.get("informacaoComplementar") or "")),
    }


def fetch_open(horizon_days=90, workers=3, max_pages=None, now=None, interval=None, retry_pause=60):
    """Baixa todas as contratações com proposta aberta encerrando em até `horizon_days`.

    Retorna (registros, relatorio). Páginas que falham não abortam a coleta:
    ganham uma segunda passada no fim e, se ainda falharem, ficam em relatorio["failed_pages"]
    para o merge com o snapshot anterior.
    """
    now = now or datetime.now()
    data_final = (now + timedelta(days=horizon_days)).strftime("%Y%m%d")
    if interval is not None:
        THROTTLE.interval = interval
    t0 = time.time()
    first = _get_json(_page_url(data_final, 1), retries=6)  # sem a 1ª página não há como paginar
    total_pages = first.get("totalPaginas") or 0
    if max_pages:
        total_pages = min(total_pages, max_pages)
    log.info("PNCP: %s registros em %s páginas", first.get("totalRegistros"), total_pages)

    pages = {1: first.get("data") or []}
    failed = []

    def work(p):
        return p, _get_json(_page_url(data_final, p)).get("data") or []

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(work, p): p for p in range(2, total_pages + 1)}
        for f, p in futures.items():
            try:
                pages[p] = f.result()[1]
            except Exception as e:  # uma página ruim não derruba o dia
                log.error("%s", e)
                failed.append(p)

    # segunda passada: 502/504 do PNCP costumam ser momentâneos
    if failed:
        log.info("segunda passada em %s páginas após pausa", len(failed))
        time.sleep(retry_pause)
        still = []
        for p in failed:
            try:
                pages[p] = work(p)[1]
            except Exception as e:
                log.error("segunda passada: %s", e)
                still.append(p)
        failed = still

    records = {}
    for p in sorted(pages):
        for raw in pages[p]:
            rec = normalize_record(raw)
            if rec["id"]:
                records[rec["id"]] = rec
    report = {
        "api_total": first.get("totalRegistros"),
        "pages": total_pages,
        "failed_pages": failed,
        "fetched": len(records),
        "seconds": round(time.time() - t0, 1),
    }
    return list(records.values()), report


def still_open(rec, now):
    enc = rec.get("encerramento")
    if not enc:
        return False
    try:
        return datetime.fromisoformat(enc) >= now
    except ValueError:
        return False


def merge_with_previous(current, previous, report, now):
    """Se houve páginas com falha, recupera do snapshot anterior o que ainda está aberto."""
    if not report["failed_pages"] or not previous:
        report["recovered"] = 0
        return current
    ids = {r["id"] for r in current}
    recovered = [r for r in previous if r["id"] not in ids and still_open(r, now)]
    report["recovered"] = len(recovered)
    return current + recovered
