import gzip
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from radar.build import brl, build_site, days_left, id_slug  # noqa: E402
from radar.fetch import merge_with_previous, normalize_record, still_open  # noqa: E402
from radar.segments import classify  # noqa: E402
from radar.telegram import MAX_MSG, chunk_messages, notify, to_csv  # noqa: E402

NOW = datetime(2026, 9, 22, 12, 0)
CFG = {"brand": "Radar de Editais", "site_url": "https://exemplo.github.io/radar-editais",
       "checkout_url": "", "checkout_url_anual": "", "public_telegram_url": "", "price_month": "R$ 19,90",
       "price_year": "R$ 199", "goatcounter": "", "google_site_verification": ""}


def fixture():
    with open(os.path.join(ROOT, "tests", "fixtures", "pncp_page.json"), encoding="utf-8") as f:
        return [normalize_record(r) for r in json.load(f)["data"]]


def rec(i, objeto, uf="SP", enc="2026-09-30T10:00:00", valor=1000.0, novo=False):
    return {"id": f"123-1-{i:06d}/2026", "url": "https://pncp.gov.br/app/editais/123/2026/1", "orgao": "PREFEITURA X",
            "unidade": "", "uf": uf, "municipio": "Cidade", "esfera": "M", "objeto": objeto, "info": "",
            "modalidade": "Pregão - Eletrônico", "modo_disputa": "Aberto", "numero": f"{i}/2026", "processo": "1",
            "srp": False, "valor": valor, "abertura": "2026-09-20T08:00:00", "encerramento": enc,
            "publicacao": "2026-09-22T08:00:00", "link_origem": None, "segmentos": classify(objeto), "novo": novo}


class TestSegments(unittest.TestCase):
    def test_classifica_por_palavra_chave_sem_acento(self):
        self.assertIn("limpeza-conservacao", classify("AQUISIÇÃO DE MATERIAL DE LIMPEZA E HIGIENE"))
        self.assertIn("medicamentos", classify("Registro de preços para aquisição de medicamentos"))
        self.assertIn("uniformes-textil", classify("Confecção de uniformes escolares"))

    def test_exclusao_evita_falso_positivo(self):
        self.assertNotIn("limpeza-conservacao", classify("Serviços de limpeza urbana e varrição"))
        self.assertIn("residuos-ambiental", classify("Serviços de limpeza urbana e varrição"))
        self.assertNotIn("seguranca-vigilancia", classify("Ações de vigilância sanitária"))

    def test_texto_vazio(self):
        self.assertEqual(classify(""), [])
        self.assertEqual(classify(None), [])


class TestFetch(unittest.TestCase):
    def test_normaliza_registro_real(self):
        recs = fixture()
        self.assertEqual(len(recs), 10)
        r = recs[0]
        self.assertEqual(r["uf"], "PR")
        self.assertTrue(r["url"].startswith("https://pncp.gov.br/app/editais/95423000000100/2023/"))
        self.assertIn("funera", r["objeto"].lower())

    def test_still_open(self):
        self.assertTrue(still_open({"encerramento": "2026-09-22T13:00:00"}, NOW))
        self.assertFalse(still_open({"encerramento": "2026-09-22T11:00:00"}, NOW))
        self.assertFalse(still_open({"encerramento": None}, NOW))

    def test_segunda_passada_recupera_pagina_instavel(self):
        from radar import fetch
        raw = json.load(open(os.path.join(ROOT, "tests", "fixtures", "pncp_page.json"), encoding="utf-8"))["data"]
        calls = {}

        def fake(url, retries=4):
            page = int(url.split("pagina=")[1].split("&")[0])
            calls[page] = calls.get(page, 0) + 1
            if page == 3 and calls[page] == 1:
                raise RuntimeError("504")
            return {"totalPaginas": 3, "totalRegistros": 3, "data": [raw[page]]}

        orig, fetch._get_json = fetch._get_json, fake
        try:
            recs, rep = fetch.fetch_open(interval=0, retry_pause=0, now=NOW)
        finally:
            fetch._get_json = orig
        self.assertEqual(len(recs), 3)
        self.assertEqual(rep["failed_pages"], [])

    def test_merge_recupera_so_quando_houve_falha(self):
        cur, prev = [rec(1, "a")], [rec(1, "a"), rec(2, "b"), rec(3, "c", enc="2026-09-01T00:00:00")]
        rep = {"failed_pages": []}
        self.assertEqual(len(merge_with_previous(cur, prev, rep, NOW)), 1)
        rep = {"failed_pages": ["7"]}
        out = merge_with_previous(cur, prev, rep, NOW)
        self.assertEqual(sorted(r["id"] for r in out), [rec(1, "")["id"], rec(2, "")["id"]])
        self.assertEqual(rep["recovered"], 1)


class TestBuild(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.recs = fixture() + [rec(i, "Aquisição de material de limpeza", uf="SP", novo=True) for i in range(5)] + \
            [rec(99, "Aquisição de material de limpeza", uf="AC")]
        status = {"total": len(self.recs), "novos": 5, "failed_pages": [], "seconds": 1, "recovered": 0}
        self.site = build_site(self.recs, CFG, self.tmp, NOW, status, "")

    def read(self, path):
        with open(os.path.join(self.tmp, path), encoding="utf-8") as f:
            return f.read()

    def test_paginas_principais_existem(self):
        for p in ["index.html", "pro/index.html", "obrigado/index.html", "sobre/index.html", "404.html",
                  "segmentos/index.html", "estados/index.html", "uf/sp/index.html",
                  "segmento/limpeza-conservacao/index.html", "segmento/limpeza-conservacao/sp/index.html",
                  "robots.txt", "sitemap.xml", "sitemap-1.xml", "feed.xml", "status.json",
                  "data/snapshot.json.gz", "data/history.csv", "assets/style.css", ".nojekyll"]:
            self.assertTrue(os.path.exists(os.path.join(self.tmp, p)), p)

    def test_uma_pagina_por_edital(self):
        for r in self.recs:
            self.assertTrue(os.path.exists(os.path.join(self.tmp, "edital", id_slug(r["id"]), "index.html")))

    def test_links_respeitam_base_path_do_github_pages(self):
        html = self.read("index.html")
        self.assertIn('href="/radar-editais/assets/style.css"', html)
        self.assertIn('<link rel="canonical" href="https://exemplo.github.io/radar-editais/">', html)

    def test_lista_fina_recebe_noindex_e_fica_fora_do_sitemap(self):
        self.assertIn("noindex", self.read("segmento/limpeza-conservacao/ac/index.html"))
        self.assertNotIn("noindex", self.read("segmento/limpeza-conservacao/sp/index.html"))
        sm = self.read("sitemap-1.xml")
        self.assertIn("/segmento/limpeza-conservacao/sp/", sm)
        self.assertNotIn("/segmento/limpeza-conservacao/ac/", sm)
        self.assertNotIn("/obrigado/", sm)

    def test_sem_checkout_configurado_nao_mostra_link_quebrado(self):
        self.assertIn("Assinaturas abrem em breve", self.read("pro/index.html"))

    def test_com_checkout_mostra_botao(self):
        cfg = dict(CFG, checkout_url="https://pay.kiwify.com.br/abc")
        build_site(self.recs, cfg, self.tmp, NOW, {"total": 1, "novos": 0, "failed_pages": [], "seconds": 1}, "")
        self.assertIn('href="https://pay.kiwify.com.br/abc"', self.read("pro/index.html"))

    def test_historico_acumula(self):
        hist = self.read("data/history.csv")
        build_site(self.recs, CFG, self.tmp, NOW, {"total": 2, "novos": 0, "failed_pages": [], "seconds": 1}, hist)
        self.assertEqual(len(self.read("data/history.csv").strip().splitlines()), 3)

    def test_snapshot_legivel(self):
        with gzip.open(os.path.join(self.tmp, "data", "snapshot.json.gz"), "rt", encoding="utf-8") as f:
            self.assertEqual(len(json.load(f)), len(self.recs))

    def test_html_escapa_conteudo_do_pncp(self):
        evil = rec(500, '<script>alert(1)</script> limpeza')
        build_site([evil], CFG, self.tmp, NOW, {"total": 1, "novos": 0, "failed_pages": [], "seconds": 1}, "")
        page = self.read(os.path.join("edital", id_slug(evil["id"]), "index.html"))
        self.assertNotIn("<script>alert(1)", page)


class TestFormat(unittest.TestCase):
    def test_brl(self):
        self.assertEqual(brl(1234567.891), "R$ 1.234.567,89")
        self.assertEqual(brl(None), "valor não informado")

    def test_days_left(self):
        self.assertEqual(days_left("2026-09-22T18:00:00", NOW)[1], "hot")
        self.assertEqual(days_left("2026-09-26T18:00:00", NOW), ("encerra em 4 dias", "warm"))


class TestTelegram(unittest.TestCase):
    def test_chunk_respeita_limite(self):
        msgs = chunk_messages("cabeçalho", ["x" * 500] * 30)
        self.assertGreater(len(msgs), 1)
        self.assertTrue(all(len(m) <= MAX_MSG for m in msgs))

    def test_csv_com_bom_e_ponto_e_virgula(self):
        data = to_csv([rec(1, "limpeza; e higiene")], CFG["site_url"])
        self.assertTrue(data.startswith("﻿".encode("utf-8")))
        self.assertIn(b'"limpeza; e higiene"', data)

    def test_sem_token_nao_envia(self):
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        os.environ["TELEGRAM_PRO_CHAT"] = "-100"
        try:
            out = notify([rec(1, "material de limpeza", novo=True)], CFG, NOW)
        finally:
            os.environ.pop("TELEGRAM_PRO_CHAT")
        self.assertEqual(out["sent"], 0)
        kinds = [k for _, k, _ in out["outbox"]]
        self.assertIn("file", kinds)
        self.assertIn("#limpeza_conservacao", out["outbox"][1][2])


if __name__ == "__main__":
    unittest.main()
