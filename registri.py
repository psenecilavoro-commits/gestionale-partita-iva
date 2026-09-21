"""Accesso ai registri: paginazione, anno aperto e aggiornamenti concorrenti."""
from decimal import Decimal


def leggi_tutti(client, tabella, campi="*", **filtri):
    righe, offset, ids = [], 0, set()
    while True:
        query = client.table(tabella).select(campi).order("id")
        for campo, valore in filtri.items():
            query = query.eq(campo, valore)
        pagina = query.range(offset, offset + 499).execute().data
        if pagina is None:
            raise RuntimeError("Lettura non confermata")
        if not pagina:
            return righe
        for r in pagina:
            if "id" in r:
                if r["id"] in ids:
                    raise ValueError("Lettura cambiata durante la paginazione: riprovare.")
                ids.add(r["id"])
        righe.extend(pagina)
        offset += len(pagina)  # supporta anche limiti server inferiori a 500


def anno_aperto(client, anno):
    righe = (client.table("fiscal_years").select("id,fiscal_year,status")
             .eq("id", anno["id"]).execute()).data or []
    if len(righe) != 1 or righe[0]["status"] != "open":
        raise ValueError("Anno chiuso o non accessibile: aggiorna la pagina.")
    if int(righe[0]["fiscal_year"]) != int(anno["fiscal_year"]):
        raise ValueError("Anno non coerente.")


def salva(client, tabella, anno, dati, precedente=None, elimina=False):
    """Le nuove tabelle hanno version incrementata dal trigger, anche via API."""
    anno_aperto(client, anno)
    if precedente:
        query = client.table(tabella)
        query = query.delete() if elimina else query.update(dati)
        risposta = (query.eq("id", precedente["id"])
                    .eq("fiscal_year_id", anno["id"])
                    .eq("version", precedente["version"]).execute())
    elif elimina:
        raise ValueError("Seleziona prima una registrazione.")
    else:
        risposta = client.table(tabella).insert({**dati, "fiscal_year_id": anno["id"]}).execute()
    if len(risposta.data or []) != 1:
        raise ValueError("Operazione non confermata o record modificato altrove: ricarica prima di riprovare.")


def denaro(valore, negativo=False):
    try:
        n = Decimal(str(valore))
        if (not n.is_finite() or abs(n) > Decimal("999999999999.99")
                or (not negativo and n < 0) or n != n.quantize(Decimal(".01"))):
            raise ValueError
        return n
    except (ValueError, ArithmeticError) as exc:
        raise ValueError("Importo non valido: usare al massimo due decimali.") from exc
