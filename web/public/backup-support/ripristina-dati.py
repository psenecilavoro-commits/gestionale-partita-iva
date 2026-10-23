"""Genera SQL per un NUOVO database; non si collega a nessun servizio."""
import json,uuid
from pathlib import Path
root=Path(__file__).resolve().parent
data=json.loads((root/'ripristino/dati-tutti-gli-anni.json').read_text(encoding='utf-8'))
owner=str(uuid.UUID(input('UUID del tuo nuovo utente Supabase (crealo prima nel nuovo progetto): ').strip()))
quote=lambda value: "'"+value.replace("'","''")+"'"
ident=lambda value:'"'+value.replace('"','""')+'"'
tables=data['tables']
sql=['-- SOLO database di ripristino NUOVO. Eseguire prima recovery-schema.sql.', 'BEGIN;', 'SET LOCAL session_replication_role = replica;']
for name,rows in tables.items():
    sql.append('DO $$ BEGIN IF EXISTS (SELECT 1 FROM public.'+ident(name)+') THEN RAISE EXCEPTION \'Database non vuoto: ripristino interrotto\'; END IF; END $$;')
for name,rows in tables.items():
    if not rows:continue
    converted=[{k:(owner if k=='user_id' else v) for k,v in row.items()} for row in rows]
    sql.append('INSERT INTO public.'+ident(name)+' SELECT * FROM jsonb_populate_recordset(NULL::public.'+ident(name)+','+quote(json.dumps(converted,ensure_ascii=False))+"::jsonb);")
sql+=['SET LOCAL session_replication_role = origin;','COMMIT;']
(root/'ripristino/ripristina-dati.sql').write_text('\n'.join(sql),encoding='utf-8')
print('Creato ripristino/ripristina-dati.sql. Nessun dato inviato online.')
