"""Caricamento documenti sanitari: OCR locale, conferma importi, totale annuo.

Non conservare file, immagini, testo OCR o dettagli clinici in Supabase.
Solo importo aggregato e impronte SHA-256 per prevenire doppi caricamenti.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import BytesIO
import json
import re

import streamlit as st
from supabase import Client

from fatturato import euro

D = Decimal
CENT = D("0.01")
MARCATORE = "TIPO_SANITARIE_FOGLIO; PARAMETRI FISCALI DA VERIFICARE"
DESCRIZIONE = "Spese sanitarie · documenti caricati"
PREFIX = MARCATORE + "\nSHA256_DOCUMENTI_V1:"
MAX_FILES = 10
MAX_BYTES = 8 * 1024 * 1024
MAX_PDF_PAGES = 3

# Importi monetari completi, mai quantita', date o codici senza decimali.
NUMERO = re.compile(r"(?<![\d.,])(?:\d{1,3}(?:[. ]\d{3})+|\d+),\d{2}(?!\d)|(?<![\d.,])\d+\.\d{2}(?!\d)")
RIGHE_IMPORTO = (
    (100, re.compile(r"\b(?:TOTALE\s+)?(?:IMPORTO\s+DETRAIBILE|SPES[AE]\s+SANITARI[AE]|SPESA\s+DETRAIBILE|TOTALE\s+SANITARI[OA])\b", re.I)),
    (70, re.compile(r"\b(?:TOTALE|TOT\.?|IMPORTO\s+PAGATO|TOTALE\s+DOCUMENTO|TOTALE\s+SCONTRINO|TOTALE\s+FATTURA)\b", re.I)),
    (40, re.compile(r"\b(?:DA\s+PAGARE|IMPORTO\s+FATTURA|CORRISPETTIVO\s+PAGATO)\b", re.I)),
)
ESCLUDI = re.compile(r"\b(?:RESTO|SUBTOTALE|TOTALE\s+IVA|IMPONIBILE\s+IVA|SCONTO|CONTANTI\s+RICEVUTI|BANCOMAT\s+RICEVUTO)\b", re.I)


def _valore(testo: str) -> D:
    s = str(testo).strip().replace("€", "").replace(" ", "")
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        v = D(s)
    except InvalidOperation as exc:
        raise ValueError("Importo non valido: usa ad esempio 12,50.") from exc
    if not v.is_finite() or v <= 0 or v > D("9999999.99") or v != v.quantize(CENT):
        raise ValueError("Serve un importo positivo, massimo due decimali.")
    return v


def suggerisci_importo(testo: str) -> D | None:
    """Accetta solo un unico importo a priorita' massima; altrimenti correzione manuale."""
    per_priorita: dict[int, set[D]] = {}
    for riga in testo.splitlines():
        normalizzata = " ".join(riga.upper().split())
        if not normalizzata or ESCLUDI.search(normalizzata):
            continue
        livello = next((score for score, regex in RIGHE_IMPORTO if regex.search(normalizzata)), None)
        if livello is None:
            continue
        importi = set()
        for match in NUMERO.finditer(normalizzata):
            try:
                importi.add(_valore(match.group()))
            except ValueError:
                pass
        if importi:
            per_priorita.setdefault(livello, set()).update(importi)
    if not per_priorita:
        return None
    candidati = per_priorita[max(per_priorita)]
    return next(iter(candidati)) if len(candidati) == 1 else None


def _ocr(immagine) -> str:
    import pytesseract
    from PIL import ImageOps

    immagine = ImageOps.exif_transpose(immagine)
    if immagine.width * immagine.height > 18_000_000:
        raise ValueError("Immagine troppo grande: riduci la risoluzione e riprova.")
    immagine.thumbnail((2400, 2400))
    immagine = ImageOps.autocontrast(immagine.convert("L"))
    return pytesseract.image_to_string(immagine, lang="ita+eng", config="--psm 6", timeout=15)


def _leggi_documento(nome: str, dati: bytes) -> str:
    if not dati or len(dati) > MAX_BYTES:
        raise ValueError("Documento vuoto o oltre 8 MB.")
    estensione = nome.lower().rsplit(".", 1)[-1]
    if estensione in ("jpg", "jpeg", "png"):
        from PIL import Image, UnidentifiedImageError
        try:
            with Image.open(BytesIO(dati)) as img:
                return _ocr(img)
        except (Image.DecompressionBombError, Image.DecompressionBombWarning, UnidentifiedImageError) as exc:
            raise ValueError("Immagine non leggibile o troppo grande.") from exc
    if estensione == "pdf":
        from pypdf import PdfReader
        try:
            lettore = PdfReader(BytesIO(dati), strict=False)
            if lettore.is_encrypted or not 1 <= len(lettore.pages) <= MAX_PDF_PAGES:
                raise ValueError("PDF protetto o con piu' di 3 pagine.")
            testo = "\n".join(p.extract_text() or "" for p in lettore.pages)
            if suggerisci_importo(testo) is not None:
                return testo
            # OCR solo per PDF scansionati o senza importo testuale riconoscibile.
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(dati)
            try:
                pagine = []
                for i in range(len(pdf)):
                    page = pdf[i]
                    try:
                        bitmap = page.render(scale=2)
                        try:
                            immagine = bitmap.to_pil()
                            try:
                                pagine.append(_ocr(immagine))
                            finally:
                                immagine.close()
                        finally:
                            bitmap.close()
                    finally:
                        page.close()
                return "\n".join(pagine) or testo
            finally:
                pdf.close()
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("PDF non leggibile: prova a caricare una foto nitida.") from exc
    raise ValueError("Formato non supportato: usa PDF, JPG o PNG.")


def _hash_presenti(note: str | None) -> set[str]:
    if not note or not note.startswith(PREFIX):
        return set()
    try:
        valori = json.loads(note[len(PREFIX):])
    except (ValueError, TypeError):
        raise ValueError("Registro duplicati non leggibile: nessuna modifica effettuata.")
    if not isinstance(valori, list) or any(not isinstance(v, str) or not re.fullmatch(r"[0-9a-f]{64}", v) for v in valori):
        raise ValueError("Registro duplicati non valido: nessuna modifica effettuata.")
    return set(valori)


def _registro(hashes: set[str]) -> str:
    return PREFIX + json.dumps(sorted(hashes), separators=(",", ":"))


def _trova_aggregato(crediti: list[dict], anno: int) -> dict | None:
    righe = [r for r in crediti if r["description"] == DESCRIZIONE and int(r["first_fiscal_year"]) == anno]
    if len(righe) > 1:
        raise ValueError("Ci sono piu' registri sanitari per l'anno: confrontiamoci prima di aggiungere importi.")
    if not righe:
        return None
    r = righe[0]
    if (D(str(r["credit_rate"])) != D("0.19") or int(r["installment_count"]) != 1
            or not str(r.get("notes") or "").startswith(PREFIX)):
        raise ValueError("La voce sanitaria importata e' stata modificata: occorre chiarire prima di sommare nuovi importi.")
    return r


def _salva(client: Client, anno: int, importi: dict[str, D]) -> tuple[int, D, D]:
    """Un record aggregato per anno; controllo doppi file tramite SHA-256."""
    if not importi:
        raise ValueError("Nessun documento nuovo da salvare.")
    if any(not re.fullmatch(r"[0-9a-f]{64}", h) or v <= 0 or v != v.quantize(CENT)
           for h, v in importi.items()):
        raise ValueError("Controllo importi non superato.")
    esistenti = (client.table("tax_credits")
                 .select("id,description,original_amount,credit_rate,installment_count,first_fiscal_year,notes")
                 .eq("first_fiscal_year", anno).eq("description", DESCRIZIONE).execute()).data or []
    riga = _trova_aggregato(esistenti, anno)
    gia = _hash_presenti(riga["notes"]) if riga else set()
    nuovi = {h: valore for h, valore in importi.items() if h not in gia}
    if not nuovi:
        return 0, D("0"), D(str(riga["original_amount"])) if riga else D("0")
    aggiunti = sum(nuovi.values(), D("0"))
    precedente = D(str(riga["original_amount"])) if riga else D("0")
    totale = precedente + aggiunti
    if totale > D("999999999999.99"):
        raise ValueError("Totale oltre il limite del database.")
    note = _registro(gia | set(nuovi))
    if riga:
        modifica = (client.table("tax_credits")
                    .update({"original_amount": str(totale), "notes": note})
                    .eq("id", riga["id"])
                    .eq("first_fiscal_year", anno)
                    .eq("original_amount", str(precedente))
                    .eq("notes", riga["notes"]).execute())
    else:
        modifica = client.table("tax_credits").insert({
            "description": DESCRIZIONE, "original_amount": str(totale),
            "credit_rate": "0.19", "installment_count": 1,
            "first_fiscal_year": anno, "notes": note,
        }).execute()
    if len(modifica.data or []) != 1:
        raise RuntimeError("Salvataggio non confermato: controlla il totale prima di riprovare.")
    return len(nuovi), aggiunti, totale


def mostra_caricamento(client: Client, anno: dict, crediti: list[dict] | None = None) -> None:
    anno_num = int(anno["fiscal_year"])
    st.markdown("### Carica scontrini farmacia e ricevute mediche")
    st.caption("Foto JPG/PNG o PDF, massimo 10 documenti per volta (8 MB ciascuno). "
               "Lettura sul server dell'app, senza servizi OCR esterni: "
               "non salvo immagini, testo o dettagli medici; solo totale annuo e impronte dei file identici.")
    if crediti is None:
        try:
            crediti = (client.table("tax_credits")
                       .select("id,description,original_amount,credit_rate,installment_count,first_fiscal_year,notes")
                       .eq("first_fiscal_year", anno_num).eq("description", DESCRIZIONE).execute()).data or []
        except Exception:
            st.error("Impossibile leggere il totale sanitario: nessuna modifica effettuata.")
            return
    try:
        riga = _trova_aggregato(crediti, anno_num)
        totale = D(str(riga["original_amount"])) if riga else D("0")
        precedenti = _hash_presenti(riga["notes"]) if riga else set()
    except ValueError as exc:
        st.error(str(exc))
        return
    st.metric(f"Spese sanitarie da documenti · {anno_num}", euro(totale))
    st.caption("Totale delle spese inserite da documenti, NON detrazione fiscale. La franchigia del foglio e' applicata una sola volta a questa voce. Se hai anche altre voci sanitarie manuali, va concordato il riepilogo prima dei calcoli fiscali.")
    notifica = st.session_state.pop(f"san_notifica_{anno_num}", None)
    if notifica:
        st.success(notifica)
    if anno["status"] != "open":
        st.info("Anno chiuso: nuovi documenti non inseribili.")
        return
    caricati = st.file_uploader("Carica uno o piu' documenti", type=["pdf", "jpg", "jpeg", "png"],
                               accept_multiple_files=True, key=f"san_documenti_{anno_num}")
    if not caricati:
        return
    if len(caricati) > MAX_FILES:
        st.warning(f"Seleziona al massimo {MAX_FILES} documenti alla volta.")
        return
    nuovi = {}
    cache = st.session_state.setdefault(f"san_cache_{anno_num}", {})
    ripetuti = 0
    errori = []
    for documento in caricati:
        dati = documento.getvalue()
        h = sha256(dati).hexdigest()
        if h in precedenti or h in nuovi:
            ripetuti += 1
            continue
        if h not in cache:
            try:
                testo = _leggi_documento(documento.name, dati)
                importo = suggerisci_importo(testo)
                cache[h] = str(importo) if importo is not None else ""
            except Exception:
                cache[h] = ""
                errori.append(documento.name)
        nuovi[h] = (documento.name, cache[h])
    if ripetuti:
        st.info(f"{ripetuti} file identici gia' acquisiti o ripetuti nella selezione: non saranno conteggiati di nuovo.")
    if not nuovi:
        return
    st.caption(f"{len(nuovi)} documenti nuovi da controllare. Nessun importo viene aggiunto prima della conferma.")
    if errori:
        st.warning("Documento non leggibile automaticamente: verifica l'importo nei campi qui sotto. "
                   "Non vengono conservate immagini o testi.")
    valori = {}
    with st.expander("Controlla o correggi gli importi proposti prima di confermare", expanded=bool(errori)):
        for h, (nome, proposto) in nuovi.items():
            valori[h] = st.text_input(
                f"{nome} · importo (€)",
                value=proposto.replace(".", ",") if proposto else "",
                key=f"san_importo_{anno_num}_{h}", placeholder="es. 12,50",
            )
    try:
        importi_validi = {h: _valore(valore) for h, valore in valori.items()}
    except ValueError:
        importi_validi = {}
    somma = sum(importi_validi.values(), D("0")) if len(importi_validi) == len(nuovi) else None
    st.metric("Totale nuovo da aggiungere", euro(somma) if somma is not None else "Da completare")
    selezione = sha256("".join(sorted(nuovi)).encode()).hexdigest()[:12]
    verifica = st.checkbox(f"Ho controllato gli importi e l'anno {anno_num} dei documenti; confermo la somma.",
                           key=f"san_verifica_{anno_num}_{selezione}")
    conferma = st.button("Conferma e aggiungi al totale sanitario", type="primary",
                         key=f"san_conferma_{anno_num}")
    if conferma:
        if not verifica:
            st.warning("Conferma prima che gli importi e l'anno siano corretti.")
            return
        try:
            importi = {h: _valore(valore) for h, valore in valori.items()}
            numero, aggiunta, complessivo = _salva(client, anno_num, importi)
        except ValueError as exc:
            st.warning(str(exc))
        except Exception:
            st.error("Salvataggio non confermato: aggiorna e controlla il totale prima di riprovare.")
        else:
            st.session_state[f"san_notifica_{anno_num}"] = (
                f"{numero} documenti acquisiti · aggiunti {euro(aggiunta)} · totale {euro(complessivo)}."
            )
            st.rerun()
