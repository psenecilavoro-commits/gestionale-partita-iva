# Inserimenti tutti gli anni — checkpoint

Branch feature/inserimenti-tutti-anni, base 5fd91d34417d9f9c8e8cc85a7705efcc2e29e77b.
Costi ordinario: clic sulle stime annuali, compresi i mancanti, tramite gli stessi moduli e validatori Python esistenti. IVA, deducibilità, penale km, Auto e totali non editabili. Moduli completi spese documentate, detrazioni e ammortamenti mantenuti per richiesta esplicita. Fatturato, Accantonamenti e Auto già comuni a tutti gli anni; protezione chiusi invariata. Nessuna formula o schema/RLS modificato.
Corretto mapping insert senza result_ids per celle dirette; mapping categorie temporanee del motore mantenuto.
13 test JS/Pyodide e build passati. Prossimo passo: collaudo browser branch separata con dati sintetici, poi CI e pubblicazione. Non toccare dati reali per collaudare.