"""Accesso ai registri: paginazione, anno aperto, cache per rerun e aggiornamenti concorrenti."""
from decimal import Decimal

import streamlit as st

_CACHE_KEY = "_piva_run_read_cache"


def avvia_cache_letture() -> None:
    """Azzera la cache di lettura all'inizio di ogni rerun Streamlit.

    La cache vive soltanto nella sessione corrente e soltanto per un singolo
    rerun: serve a evitare query duplicate nello stesso caricamento senza
    rischiare di mostrare dati vecchi dopo un salvataggio.
    """
    st.session_state[_CACHE_KEY] = {}


def _cache_corrente():
    cache = st.session_state.get(_CACHE_KEY)
    return cache if isinstance(cache, dict) else None


def _chiave_cache(tabella, campi, filtri):
    return (
        tabella,
        campi,
        tuple(sorted((str(k), repr(v)) for k, v in filtri.items())),
    )


def _copia_righe(righe):
    return [dict(r) for r in righe]


def leggi_tutti(client, tabella, campi="*", **filtri):
    """Legge tutte le righe con paginazione e deduplica le letture nel rerun."""
    cache = _cache_corrente()
    chiave = _chiave_cache(tabella, campi, filtri)
    if cache is not None and chiave in cache:
        return _copia_righe(cache[chiave])

    righe, offset, ids = [], 0, set()
    totale_atteso = None
    while True:
        base = client.table(tabella)
        if offset == 0:
            try:
                query = base.select(campi, count="exact")
            except TypeError:
                # Compatibilità con client/mock che non accettano il parametro count.
                query = base.select(campi)
        else:
            query = base.select(campi)
        query = query.order("id")
        for campo, valore in filtri.items():
            query = query.eq(campo, valore)
        risposta = query.range(offset, offset + 499).execute()
        pagina = risposta.data
        if pagina is None:
            raise RuntimeError("Lettura non confermata")
        if totale_atteso is None:
            totale_atteso = getattr(risposta, "count", None)
        if not pagina:
            break
        for r in pagina:
            if "id" in r:
                if r["id"] in ids:
                    raise ValueError("Lettura cambiata durante la paginazione: riprovare.")
                ids.add(r["id"])
        righe.extend(pagina)
        if totale_atteso is not None and len(righe) >= int(totale_atteso):
            break
        offset += len(pagina)  # supporta anche limiti server inferiori a 500

    if cache is not None:
        cache[chiave] = _copia_righe(righe)
    return _copia_righe(righe)


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
