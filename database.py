"""Accesso ai dati tramite il client Supabase autenticato del visitatore.

Mai usare una chiave service_role e mai condividere un client autenticato
fra sessioni Streamlit diverse.
"""

from supabase import Client


def get_fiscal_year(client: Client, year: int = 2027) -> dict | None:
    """Legge l'anno visibile all'utente corrente (filtrato anche dalla RLS)."""
    result = (
        client.table("fiscal_years")
        .select("id,fiscal_year,status")
        .eq("fiscal_year", year)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def create_fiscal_year(client: Client, year: int = 2027) -> dict:
    """Crea un anno per l'utente autenticato, senza inserire user_id dal client.

    Il database assegna user_id tramite DEFAULT auth.uid() e la policy RLS
    verifica che coincida con l'identità della richiesta.
    """
    result = (
        client.table("fiscal_years")
        .insert({"fiscal_year": year, "status": "open"})
        .execute()
    )
    if not result.data:
        raise RuntimeError("Creazione dell'anno non confermata dal database")
    return result.data[0]


def set_fiscal_year_status(client: Client, anno: dict, nuovo_stato: str) -> dict:
    """Chiude o riapre un anno fiscale con controllo dello stato precedente.

    Sono ammessi soltanto i passaggi open -> closed e closed -> open.
    L'update usa anche lo stato corrente come guardia contro modifiche concorrenti.
    """
    stato_corrente = str(anno.get("status") or "")
    transizioni = {("open", "closed"), ("closed", "open")}
    if (stato_corrente, nuovo_stato) not in transizioni:
        raise ValueError("Transizione dello stato fiscale non consentita.")

    risposta = (
        client.table("fiscal_years")
        .update({"status": nuovo_stato})
        .eq("id", anno["id"])
        .eq("fiscal_year", int(anno["fiscal_year"]))
        .eq("status", stato_corrente)
        .execute()
    )
    if len(risposta.data or []) == 1:
        return risposta.data[0]

    # Alcune configurazioni PostgREST possono non restituire la riga aggiornata.
    # Verifica esplicita prima di considerare l'operazione fallita.
    aggiornato = get_fiscal_year(client, int(anno["fiscal_year"]))
    if aggiornato is not None and aggiornato.get("id") == anno["id"] and aggiornato.get("status") == nuovo_stato:
        return aggiornato
    raise RuntimeError("Cambio di stato non confermato dal database.")
