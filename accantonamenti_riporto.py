"""Snapshot degli avanzi alla chiusura; nessuna modifica alle formule fiscali."""
import json
import uuid
from decimal import Decimal as D, ROUND_HALF_UP
from registri import leggi_tutti
MARKER = "\n[PIVA_RESERVE_CLOSURE_V1]"
def snapshot(anno):
    notes = anno.get("notes") or ""
    if MARKER not in notes:
        return None
    try:
        return json.loads(notes.rsplit(MARKER, 1)[1])
    except (ValueError, TypeError):
        raise ValueError("Riepilogo di chiusura non valido: verifica l'anno fiscale.")
def nota_originale(anno):
    return (anno.get("notes") or "").rsplit(MARKER, 1)[0]
def riporto(client, anno):
    anni = leggi_tutti(client, "fiscal_years")
    per_anno = {int(a["fiscal_year"]): a for a in anni}
    def valido(a):
        s = snapshot(a)
        if a.get("status") != "closed" or not s:
            return False
        if s.get("source_token"):
            precedente = per_anno.get(int(a["fiscal_year"]) - 1)
            return bool(precedente and valido(precedente) and snapshot(precedente)["token"] == s["source_token"])
        return True
    precedente = per_anno.get(int(anno["fiscal_year"]) - 1)
    if not precedente or not valido(precedente):
        return D("0"), None
    s = snapshot(precedente)
    return D(s["carry_out"]), s["token"]
def prepara_chiusura(client, anno):
    from accantonamenti_confronto import _obiettivo_2026, _obiettivo_ordinario, _mesi_accantonati
    from accantonamenti import leggi_accantonamenti
    gross, _ = (_obiettivo_2026 if int(anno["fiscal_year"]) == 2026 else _obiettivo_ordinario)(client, anno)
    riserve = leggi_accantonamenti(client, anno["id"])
    _mesi_accantonati(riserve)
    reserved = sum((D(str(r["reserved_amount"])) for r in riserve), D("0"))
    incoming, source = riporto(client, anno)
    s = {"token": str(uuid.uuid4()), "source_token": source, "gross_need": str(gross), "reserved": str(reserved), "carry_in": str(incoming), "carry_out": str(max(incoming + reserved - gross, D("0")).quantize(D("0.01"), rounding=ROUND_HALF_UP))}
    return nota_originale(anno) + MARKER + json.dumps(s, separators=(",", ":"))

