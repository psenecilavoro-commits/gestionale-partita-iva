# Gestionale Partita IVA

Streamlit + Supabase con autenticazione individuale. Sette sezioni corrispondenti al foglio di riferimento, registrazioni separate dagli scenari fiscali. Leggere [stato](STATO_STRUTTURA.md) e [handover](HANDOVER_STRUTTURA.md) prima di usare i risultati.

## Avvio

Python 3.12 è l'ambiente locale verificato.

```sh
python -m venv .venv
# Windows: .venv/Scripts/python.exe; Linux: .venv/bin/python
python -m pip install -r requirements-lock.txt
python -m streamlit run app.py
```

Eseguire gli ultimi due comandi con il Python dell'ambiente virtuale (o attivarlo). `requirements.txt` fissa le dipendenze dirette; `requirements-lock.txt` registra anche le versioni transitive dell'ambiente verificato. Il workflow prova il lock anche su Linux.

Configurare `.streamlit/secrets.toml`, escluso da Git:

```toml
SUPABASE_URL = "https://REF_DEL_SOLO_PROGETTO_PARTITA_IVA.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "sb_publishable_..."
```

Mai usare service_role/secret. Il client autenticato è isolato per sessione, non condiviso in cache. L'utente deve esistere nel progetto Supabase corretto.

Per OCR servono Tesseract e le lingue previste in `packages.txt`; l'importazione assistita richiede sempre conferma degli importi. File caricati non conservati nel database.

## Test

```sh
python -m unittest discover -s tests -v
python -m compileall -q -x '\.venv' .
python -m pip check
```

Non richiedono credenziali. La CI esegue inoltre `tests/check_sql.py` contro un PostgreSQL temporaneo: **mai lanciarlo su un database reale**. Questa prova usa uno schema minimo e non certifica le policy del Supabase dell'utente.

## Database

Lo schema base esistente non è ricostruito da questo repository. Non applicare gli SQL ad altri progetti. I tre script aggiuntivi e i relativi prerequisiti sono descritti nello stato; nessuno viene eseguito automaticamente dall'app.

La fase grafica e la verifica fiscale/funzionale definitiva seguono separatamente questa consegna.
