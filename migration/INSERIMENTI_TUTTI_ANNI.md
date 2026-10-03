# Inserimenti tutti gli anni — checkpoint 2026-10-03

Completato tramite PR #21. Branch feature/inserimenti-tutti-anni; commit funzionale b05190d46e99305f3450e529271b174749a7dd7c, merge main c674eed9c36f5927b43fe832b369278e0e70c94d.

Costi ordinario: clic sulle stime annuali, compresi i mancanti, tramite gli stessi moduli e validatori Python esistenti. IVA, deducibilità, penale km, Auto e totali non editabili. Moduli completi spese documentate, detrazioni e ammortamenti mantenuti per richiesta esplicita. Fatturato, Accantonamenti e Auto già comuni a tutti gli anni; protezione chiusi invariata. Nessuna formula o schema/RLS modificato.

Corretto mapping insert senza result_ids per celle dirette; mapping categorie temporanee del motore mantenuto.

13 test JS/Pyodide, build e entrambe CI passati. Collaudo Cloudflare separato demo deploy 06d909cb-9bbd-4db9-8138-bb1e51cb3c32: assicurazione 2027 sostituita e sidebar aggiornata; PC vuoto salvato zero; nuovo 2028 creato, Commercialista inserito e riaperto; 2027 chiuso con celle disabilitate. Soltanto dati sintetici modificati. Nessuna modifica dati reali.

Prossimo passo esatto: verificare deploy main Cloudflare, poi nessun lavoro restante. Non ripetere migrazione o collaudo su database reale.
