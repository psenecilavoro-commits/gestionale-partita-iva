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
