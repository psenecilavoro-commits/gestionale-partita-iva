# Correzione accesso — 21 settembre 2026

Il controllo iniziale chiamava get_user senza sessione Supabase e cancellava
l'intero session_state in caso di errore. Sul submit questo eliminava anche
lo stato del pulsante Accedi: sign_in_with_password non veniva chiamato.

Ora l'assenza di sessione lascia elaborare il modulo. L'utente con sessione
continua a essere verificato con get_user. La perdita di una sessione
precedentemente autenticata e il logout eliminano i dati privati locali.

Regressione riprodotta con AppTest prima della correzione (zero chiamate al
login). Dopo la correzione: 31 test unittest/AppTest superati, inclusi errore
credenziali, nuovo tentativo riuscito, logout e perdita della sessione.
Trasporto Supabase simulato: nessuna password reale o scrittura sul database.
Nessuna migrazione necessaria. Il login reale va verificato dopo il deploy
Streamlit della versione corretta, usando il proprio account.
