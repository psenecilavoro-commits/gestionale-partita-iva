"""Anagrafica mandanti: solo dati dell'utente autenticato via RLS Supabase."""

from supabase import Client

_RAPPORTI = frozenset({"plurimandatario", "monomandatario"})


def elenco_mandanti(client: Client) -> list[dict]:
    from registri import leggi_tutti
    return sorted(leggi_tutti(client, "principals"), key=lambda r: r["name"])


def aggiungi_mandante(client: Client, nome: str, rapporto: str) -> dict:
    """Inserisce una mandante dopo il controllo dei duplicati per utente."""
    nome = " ".join(nome.split())
    if not nome or len(nome) > 120:
        raise ValueError("Il nome deve contenere da 1 a 120 caratteri.")
    if rapporto not in _RAPPORTI:
        raise ValueError("Seleziona un tipo di rapporto Enasarco valido.")

    # Controllo preventivo nell'app; non sostituisce un vincolo UNIQUE nel DB.
    chiave = nome.casefold()
    if any(" ".join(item["name"].split()).casefold() == chiave for item in elenco_mandanti(client)):
        raise ValueError("Questa mandante è già presente nel tuo elenco.")

    result = (
        client.table("principals")
        .insert({"name": nome, "enasarco_relationship": rapporto})
        .execute()
    )
    if not result.data:
        raise RuntimeError("Il database non ha confermato la creazione della mandante.")
    return result.data[0]
