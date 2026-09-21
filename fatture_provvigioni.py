"""Importazione assistita delle fatture: proposta di netto, mai salvataggio automatico.

Il totale verificato SOSTITUISCE (non incrementa) le provvigioni nette del
mese. I file e il testo estratto non sono salvati nel database. Le impronte
servono solo a riconoscere file identici nel lotto/sessione corrente.
"""
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import BytesIO
import re

import streamlit as st
from supabase import Client

from accantonamenti_completi import leggi_provvigioni_nette, salva_provvigione_netta
from fatturato import MESI, euro, importo_valido

MAX_FILES = 10
MAX_BYTES = 8 * 1024 * 1024
MAX_TOTAL = 40 * 1024 * 1024
MAX_PAGES = 4
CENT = Decimal("0.01")
# Non interpretare numeri di fattura, imponibili o IVA come importo netto.
SOMME = re.compile(
    r"(?<![\d.,])(?:\d{1,3}(?:[. ]\d{3})+|\d+),\d{2}(?!\d)"
    r"|(?<![\d.,])(?:\d{1,3}(?:,\d{3})+|\d+)\.\d{2}(?!\d)"
)
ETICHETTE = (
    (100, re.compile(r"\b(?:NETTO\s+(?:A|DA)\s+(?:PAGARE|RICEVERE|CORRISPONDERE|LIQUIDARE)|NETTO\s+LIQUIDATO|NETTO\s+PROVVIGIONI)\b", re.I)),
    (80, re.compile(r"\b(?:TOTALE\s+NETTO|IMPORTO\s+NETTO)\b", re.I)),
    (60, re.compile(r"\b(?:TOTALE|IMPORTO)\s+(?:DA\s+PAGARE|DA\s+CORRISPONDERE)\b", re.I)),
)
ESCLUDI = re.compile(r"\b(?:IMPONIBILE|TOTALE\s+IVA|IVA\s+ESCLUSA|ALIQUOTA|BASE\s+IMPONIBILE|NETTO\s+IVA)\b", re.I)


def _numero(testo: str) -> Decimal:
    s = testo.replace("€", "").replace(" ", "").strip()
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        risultato = Decimal(s)
    except InvalidOperation as exc:
        raise ValueError("Importo non leggibile") from exc
    if (not risultato.is_finite() or risultato <= 0
            or risultato > Decimal("9999999.99") or risultato != risultato.quantize(CENT)):
        raise ValueError("Importo non valido")
    return risultato


def suggerisci_netto(testo: str) -> tuple[Decimal | None, str]:
    """Propone solo una cifra univoca associata a una etichetta esplicita."""
    candidati: dict[int, set[Decimal]] = {}
    for linea in testo.splitlines():
        riga = " ".join(linea.split())
        if not riga or ESCLUDI.search(riga):
            continue
        trovato = next(((p, rx.search(riga)) for p, rx in ETICHETTE if rx.search(riga)), None)
        if trovato is None:
            continue
        priorita, match = trovato
        valori = set()
        for occorrenza in SOMME.finditer(riga[match.end():]):
            try:
                valori.add(_numero(occorrenza.group()))
            except ValueError:
                pass
        if valori:
            candidati.setdefault(priorita, set()).update(valori)
    if not candidati:
        return None, "Nessun netto chiaramente identificato: compila manualmente dopo aver letto la fattura."
    valori = candidati[max(candidati)]
    if len(valori) != 1:
        return None, "Importi netti discordanti o ambigui: scegli l'importo corretto dalla fattura."
    return next(iter(valori)), "Valore proposto da una dicitura della fattura: controlla IVA e trattenute."


def _nome_xml(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _leggi_xml(dati: bytes) -> tuple[Decimal | None, str, str]:
    from defusedxml import ElementTree as ET
    try:
        root = ET.fromstring(dati)
    except Exception as exc:
        raise ValueError("XML non leggibile o non sicuro.") from exc
    riferimenti = []
    importi = []
    for elemento in root.iter():
        nome = _nome_xml(elemento.tag)
        if nome == "DatiGeneraliDocumento":
            numero = next((x.text for x in elemento if _nome_xml(x.tag) == "Numero" and x.text), None)
            data = next((x.text for x in elemento if _nome_xml(x.tag) == "Data" and x.text), None)
            if numero:
                riferimenti.append("N. " + numero[:45])
            if data:
                riferimenti.append("Data " + data[:15])
        if nome == "DettaglioPagamento":
            for figlio in elemento:
                if _nome_xml(figlio.tag) == "ImportoPagamento" and figlio.text:
                    try:
                        importi.append(_numero(figlio.text))
                    except ValueError:
                        pass
    riferimento = " · ".join(riferimenti[:2])
    if len(importi) == 1:
        return importi[0], ("ImportoPagamento XML: potrebbe comprendere IVA e non coincidere con "
                            "le provvigioni nette; verifica sulla fattura."), riferimento
    if len(importi) > 1:
        return None, "L'XML contiene più pagamenti: non vengono sommati automaticamente.", riferimento
    return None, "L'XML non contiene un importo di pagamento univoco: inserisci il netto verificato.", riferimento


def _leggi_pdf(dati: bytes) -> str:
    from pypdf import PdfReader
    try:
        lettore = PdfReader(BytesIO(dati), strict=False)
        if lettore.is_encrypted or not 1 <= len(lettore.pages) <= MAX_PAGES:
            raise ValueError("PDF protetto o con più di quattro pagine.")
        testo = "\n".join(p.extract_text() or "" for p in lettore.pages)
        if testo.strip():
            return testo
        # OCR esclusivamente se il PDF non dispone di testo, senza renderlo persistente.
        import pypdfium2 as pdfium
        from sanitarie_documenti import _ocr
        pdf = pdfium.PdfDocument(dati)
        try:
            righe = []
            for i in range(len(pdf)):
                pagina = pdf[i]
                try:
                    bitmap = pagina.render(scale=2)
                    try:
                        immagine = bitmap.to_pil()
                        try:
                            righe.append(_ocr(immagine))
                        finally:
                            immagine.close()
                    finally:
                        bitmap.close()
                finally:
                    pagina.close()
            return "\n".join(righe)
        finally:
            pdf.close()
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("PDF non leggibile: prova con un altro PDF o una foto nitida.") from exc


def analizza_fattura(nome: str, dati: bytes) -> tuple[Decimal | None, str, str]:
    if not dati or len(dati) > MAX_BYTES:
        raise ValueError("File vuoto o superiore a 8 MB.")
    estensione = nome.lower().rsplit(".", 1)[-1]
    if estensione == "xml":
        return _leggi_xml(dati)
    if estensione == "pdf":
        return (*suggerisci_netto(_leggi_pdf(dati)), "")
    if estensione in ("png", "jpg", "jpeg"):
        from PIL import Image, UnidentifiedImageError
        from sanitarie_documenti import _ocr
        try:
            with Image.open(BytesIO(dati)) as immagine:
                return (*suggerisci_netto(_ocr(immagine)), "")
        except (Image.DecompressionBombError, Image.DecompressionBombWarning, UnidentifiedImageError) as exc:
            raise ValueError("Immagine non valida o troppo grande.") from exc
    raise ValueError("Formato non supportato: PDF, XML, JPG o PNG.")


def mostra_carica_fatture(client: Client, anno: dict) -> None:
    st.divider()
    st.markdown("#### Carica fatture → provvigioni nette")
    st.caption("Carica le fatture di UN mese alla volta (PDF, XML, JPG o PNG). "
               "L'importo proposto va controllato: il totale pagato di una fattura può comprendere "
               "IVA o trattenute e NON coincide necessariamente con la provvigione netta desiderata. "
               "I documenti e il testo estratto non vengono salvati nel database.")
    if anno["status"] != "open":
        st.info("Anno chiuso: caricamento disattivato.")
        return
    try:
        nette = leggi_provvigioni_nette(client, anno["id"])
    except Exception:
        st.info("Caricamento disattivato: verifica la tabella delle provvigioni nette e i permessi Supabase.")
        return
    nome_mese = st.selectbox("Mese a cui attribuire queste fatture", MESI,
                             key=f"fatture_mese_{anno['id']}")
    mese = MESI.index(nome_mese) + 1
    presente = next((r for r in nette if int(r["month"]) == mese), None)
    if presente:
        st.warning(f"Per {nome_mese} sono già registrati {euro(Decimal(str(presente['amount'])))}: "
                   "confermando le fatture SOSTITUIRAI quel totale, non gli sommerai gli importi. "
                   "Carica tutte le fatture del mese o completa manualmente il totale.")
    files = st.file_uploader("Seleziona le fatture da analizzare", type=["pdf", "xml", "jpg", "jpeg", "png"],
                             accept_multiple_files=True, key=f"fatture_upload_{anno['id']}")
    if not files:
        return
    if len(files) > MAX_FILES or sum(len(f.getvalue()) for f in files) > MAX_TOTAL:
        st.warning("Massimo 10 fatture, 8 MB ciascuna e 40 MB complessivi.")
        return
    cache = st.session_state.setdefault(f"fatture_cache_{anno['id']}", {})
    if len(cache) > 30:
        cache.clear()
    visti = set()
    disponibili = []
    ripetuti = 0
    for file in files:
        dati = file.getvalue()
        if not dati or len(dati) > MAX_BYTES:
            st.warning(f"{file.name}: file vuoto o superiore a 8 MB; lotto non elaborato.")
            return
        impronta = sha256(dati).hexdigest()
        if impronta in visti:
            ripetuti += 1
            continue
        visti.add(impronta)
        if impronta not in cache:
            try:
                importo, nota, riferimento = analizza_fattura(file.name, dati)
                cache[impronta] = (str(importo) if importo is not None else "", nota, riferimento)
            except Exception:
                cache[impronta] = ("", "Lettura non riuscita: controlla il file e inserisci l'importo manualmente.", "")
        disponibili.append((impronta, file.name, cache[impronta]))
    if ripetuti:
        st.info(f"{ripetuti} file identici ripetuti nello stesso caricamento: conteggiati una sola volta.")
    if not disponibili:
        return
    st.info("I duplicati fra sessioni diverse non sono verificabili automaticamente: "
            "confronta le fatture con il mese già registrato. Questo modulo SOSTITUISCE il totale, non lo incrementa.")
    with st.form(f"fatture_conferma_{anno['id']}_{mese}"):
        valori = []
        for impronta, nome, (suggerito, nota, riferimento) in disponibili:
            st.caption(f"{nome[:100]}" + (f" · {riferimento}" if riferimento else ""))
            st.caption(nota)
            valore = st.text_input("Provvigione netta verificata (€)",
                                   value=suggerito.replace(".", ","),
                                   key=f"fatture_importo_{anno['id']}_{mese}_{impronta}",
                                   help="Non usare automaticamente imponibile, IVA o importo totale: verifica il netto da registrare.")
            valori.append(valore)
        confermo = st.checkbox(
            f"Ho verificato le fatture, gli importi, il mese {nome_mese} {anno['fiscal_year']} "
            "e che il totale deve SOSTITUIRE quello già registrato (se presente)."
        )
        salva = st.form_submit_button("Registra il totale verificato del mese", type="primary")
    if not salva:
        return
    if not confermo:
        st.warning("Conferma mese, fatture, importi e sostituzione del totale.")
        return
    try:
        importi = [importo_valido(v) for v in valori]
        if any(v <= 0 for v in importi):
            raise ValueError("Ogni fattura deve avere un importo positivo.")
        totale = sum(importi, Decimal("0"))
        if totale > Decimal("9999999.99"):
            raise ValueError("Totale oltre il limite del campo: verifica gli importi.")
        aggiornate = leggi_provvigioni_nette(client, anno["id"])
        corrente = next((r for r in aggiornate if int(r["month"]) == mese), None)
        # Blocca la conferma se qualcun altro ha cambiato il mese dopo la lettura.
        if (presente is None) != (corrente is None) or (
            presente is not None and corrente is not None and
            (str(presente["id"]) != str(corrente["id"]) or
             Decimal(str(presente["amount"])) != Decimal(str(corrente["amount"])))
        ):
            st.warning("Il valore del mese è cambiato: aggiorna la pagina e verifica prima di salvare.")
            return
        if corrente is not None and Decimal(str(corrente["amount"])) == totale:
            st.info("Il mese contiene già lo stesso totale: non è stato aggiunto nulla.")
            return
        salva_provvigione_netta(client, anno["id"], mese, totale, corrente)
    except ValueError as exc:
        st.warning(str(exc))
    except Exception:
        st.error("Salvataggio non confermato: controlla il valore del mese prima di riprovare.")
    else:
        st.success(f"Totale verificato di {nome_mese}: {euro(totale)} registrato in sostituzione del valore precedente.")
        st.rerun()
