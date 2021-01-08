"""ask for an input file and an output file and generates the TRAF2000 records from a .csv or .xml"""

import datetime
import csv
import tempfile
import xml.etree.ElementTree
import unidecode
import wx

def download_input_file(parent):
    """download input file"""
    start_date = parent.start_date_picker.GetValue().Format("%d/%m/%Y")
    end_date = parent.end_date_picker.GetValue().Format("%d/%m/%Y")
    input_file_url = 'https://report.casadicurasanrossore.it:8443/reportserver?/STAT_FATTURATO_CTERZI&dataI='+start_date+'&dataF='+end_date+'&rs:Format=XML'
    downloaded_input_file = parent.session.get(input_file_url)
    if downloaded_input_file.status_code != 200:
        parent.log_dialog.log_text.SetDefaultStyle(wx.TextAttr(wx.RED, font=wx.Font(wx.FontInfo(8).Bold())))
        parent.log_dialog.log_text.AppendText("ERRORE: impossibile scaricare il file di input.\nControllare la connessione ad internet e l'operatività del portale CCSR. Code %d\n" % downloaded_input_file.status_code)
        parent.log_dialog.log_text.SetDefaultStyle(wx.TextAttr())
        wx.Yield()
        return

    input_file_descriptor, parent.input_file_path = tempfile.mkstemp(suffix='.xml')
    parent.input_files.append(parent.input_file_path)
    with open(input_file_descriptor, 'wb') as input_file:
        input_file.write(downloaded_input_file.content)

def import_csv(parent) -> dict:
    """Return a dict containing the invoices info"""
    invoices = dict()
    with open(parent.input_file_path, newline="") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=",")

        for _ in range(4):
            next(csv_reader)

        for line in csv_reader:
            if len(line) == 0:
                break
            invoice_num = line[1]
            invoice_type = line[8]
            amount = line[15]
            sign = 1
            if invoice_type == "Nota di credito" and '(' not in amount:
                sign = -1
            amount = int(line[15].replace("€", "").replace(",", "").replace(".", "").replace("(", "").replace(")", "")) * sign
            if invoice_num not in invoices:
                invoice = {
                    "numFattura": invoice_num,
                    "tipoFattura": invoice_type,
                    "rifFattura": line[4],
                    "dataFattura": line[2].replace("/", ""),
                    "ragioneSociale": unidecode.unidecode(line[6] + " " + " ".join(line[5].split()[0:2])),
                    "posDivide": str(len(line[6]) + 1),
                    "cf": line[7],
                    "importoTotale": 0,
                    "ritenutaAcconto": 0,
                    "righe": dict()
                }
                invoices[invoice_num] = invoice

            if line[14] == "Ritenuta d'acconto":
                invoices[invoice_num]["ritenutaAcconto"] = amount

            else:
                invoices[invoice_num]["importoTotale"] += amount
                invoices[invoice_num]["righe"][line[14]] = amount
            parent.log_dialog.log_text.AppendText("Importata fattura n. %s\n" % invoice_num)
            wx.Yield()
    return invoices

def import_xml(parent) -> dict:
    """Return a dict containing the invoices info"""
    invoices = dict()

    tree = xml.etree.ElementTree.parse(parent.input_file_path)
    root = tree.getroot()

    for invoice in root.iter('{STAT_FATTURATO_CTERZI}Dettagli'):
        lines = dict()
        invoice_num = invoice.get('protocollo_fatturatestata')
        invoice_type = invoice.get('fat_ndc')
        total_amount = 0
        ritenuta_acconto = 0

        for line in invoice.iter('{STAT_FATTURATO_CTERZI}Dettagli2'):
            desc = line.get('descrizione_fatturariga1')
            sign = 1
            if invoice_type == 'Nota di credito' and '-' not in line.get('prezzounitario_fatturariga1'):
                sign = -1
            amount = int(format(round(float(line.get('prezzounitario_fatturariga1')), 2), '.2f').replace('.', '').replace('-', '')) * sign
            if desc == "Ritenuta d'acconto":
                ritenuta_acconto = amount
            else:
                lines[desc] = amount
                total_amount += amount

        invoice_elem = {
            "numFattura": invoice_num,
            "tipoFattura": invoice_type,
            "rifFattura": invoice.get('protocollo_fatturatestata1'),
            "dataFattura": datetime.datetime.fromisoformat(invoice.get('data_fatturatestata')).strftime("%d%m%Y"),
            "ragioneSociale": unidecode.unidecode(invoice.get('cognome_cliente') + ' ' + ' '.join(invoice.get('nome_cliente').split()[0:2])),
            "posDivide": str(len(invoice.get('cognome_cliente')) + 1),
            "cf": invoice.get('cf_piva_cliente'),
            "importoTotale": total_amount,
            "ritenutaAcconto": ritenuta_acconto,
            "righe": lines,
        }
        invoices[invoice_num] = invoice_elem
        parent.log_dialog.log_text.AppendText("Importata fattura n. %s\n" % invoice_num)
        wx.Yield()
    return invoices


def convert(parent):
    """Output to a file the TRAF2000 records"""
    output_file_path = None

    parent.log_dialog.log_text.AppendText("Download file input\n")
    wx.Yield()
    download_input_file(parent)

    invoices = import_xml(parent)

    if parent.output_traf2000_dialog.ShowModal() == wx.ID_OK:
        output_file_path = parent.output_traf2000_dialog.GetPath()
    else:
        parent.log_dialog.log_text.SetDefaultStyle(wx.TextAttr(wx.RED, font=wx.Font(wx.FontInfo(8).Bold())))
        parent.log_dialog.log_text.AppendText("ERRORE: non è stato selezionato il file di output del tracciato.\n")
        parent.log_dialog.log_text.SetDefaultStyle(wx.TextAttr())
        wx.Yield()
        return

    with open(output_file_path, "w") as traf2000_file:
        parent.log_dialog.nc_text.AppendText("Note di credito:\n")
        wx.Yield()

        for invoice in invoices.values():
            if invoice["tipoFattura"] != "Fattura" and invoice["tipoFattura"] != "Nota di credito":
                parent.log_dialog.log_text.SetDefaultStyle(wx.TextAttr(wx.RED, font=wx.Font(wx.FontInfo(8).Bold())))
                parent.log_dialog.log_text.AppendText("Errore: il documento %s può essere FATTURA o NOTA DI CREDITO\n" % invoice["numFattura"])
                parent.log_dialog.log_text.SetDefaultStyle(wx.TextAttr())
                wx.Yield()
                continue

            if len(invoice["cf"]) != 16 and len(invoice["cf"]) == 11:
                parent.log_dialog.log_text.SetDefaultStyle(wx.TextAttr(wx.RED, font=wx.Font(wx.FontInfo(8).Bold())))
                parent.log_dialog.log_text.AppendText("Errore: il documento %s non ha cf/piva\n" % invoice["numFattura"])
                parent.log_dialog.log_text.SetDefaultStyle(wx.TextAttr())
                wx.Yield()
                continue

            if invoice["tipoFattura"] == "Nota di credito":
                # As for now this script doesn't handle "Note di credito"
                parent.log_dialog.nc_text.AppendText(invoice["numFattura"]+"\n")
                wx.Yield()
                continue

            line = ["04103", "3", "0", "00000"]  # TRF-DITTA + TRF-VERSIONE + TRF-TARC + TRF-COD-CLIFOR
            line.append(invoice["ragioneSociale"][:32]+' '*(32-len(invoice["ragioneSociale"])))  # TRF-RASO
            line.append(' '*30)  # TRF-IND
            line.append('00000')  # TRF-CAP
            line.append(' '*27)  # TRF-CITTA + TRF-PROV

            if len(invoice["cf"]) == 16:  # se c.f. presente
                line.append(invoice["cf"])  # TRF-COFI
                line.append('0'*11)  # TRF-PIVA
                line.append('S')  # TRF-PF
            else:  # se piva presente
                line.append(' '*16)  # TRF-COFI
                line.append(invoice["cf"])  # TRF-PIVA
                line.append('N')  # TRF-PF

            line.append('0'*(2-len(invoice["posDivide"])) + invoice["posDivide"])  # TRF-DIVIDE
            line.append('0000')  # TRF-PAESE
            line.append(' '*33)  # TRF-PIVA-ESTERO + TRF-COFI-ESTERO + TRF-SESSO
            line.append('0'*8)  # TRF-DTNAS
            line.append(' '*64)  # TRF-COMNA + TRF-PRVNA + TRF-PREF + TRF-NTELE-NUM + TRF-FAX-PREF + TRF-FAX-NUM
            line.append('0'*22)  # TRF-CFCONTO + TRF-CFCODPAG + TRF-CFBANCA + TRF-CFAGENZIA + TRF-CFINTERM

            if invoice["tipoFattura"] == "Fattura":
                line.append('001')  # TRF-CAUSALE
                line.append("FATTURA VENDITA")  # TRF-CAU-DES
            else:
                line.append('002')  # TRF-CAUSALE
                line.append("N.C. A CLIENTE ")  # TRF-CAU-DES

            line.append(' '*86)  # TRF-CAU-AGG + TRF-CAU-AGG-1 + TRF-CAU-AGG-2
            line.append(invoice["dataFattura"]*2)  # TRF-DATA-REGISTRAZIONE + TRF-DATA-DOC
            line.append('00000000')  # TRF-NUM-DOC-FOR
            line.append(invoice["numFattura"][4:9])  # TRF-NDOC
            line.append('00')  # TRF-SERIE
            line.append('0'*72)  # TRF-EC-PARTITA + TRF-EC-PARTITA-ANNO + TRF-EC-COD-VAL + TRF-EC-CAMBIO + TRF-EC-DATA-CAMBIO + TRF-EC-TOT-DOC-VAL + TRF-EC-TOT-IVA-VAL + TRF-PLAFOND

            count = 0
            for desc, imponibile in invoice["righe"].items():
                count += 1
                imponibile = str(imponibile)
                if '-' in imponibile:
                    imponibile.replace('-', '')
                    imponibile = '0'*(11-len(imponibile)) + imponibile + "-"
                else:
                    imponibile = '0'*(11-len(imponibile)) + imponibile + "+"
                line.append(imponibile)  # TRF-IMPONIB
                if desc != "Bollo":
                    line.append('308')  # TRF-ALIQ
                else:
                    line.append('315')  # TRF-ALIQ
                line.append('0'*16)  # TRF-ALIQ-AGRICOLA + TRF-IVA11 + TRF-IMPOSTA

            for _ in range(8-count):
                line.append('0'*31)

            total = str(invoice["importoTotale"])
            if '-' in total:
                total.replace('-', '')
                total = '0'*(11-len(total)) + total + "-"
            else:
                total = '0'*(11-len(total)) + total + "+"
            line.append(total)  # TRF-TOT-FAT

            count = 0
            for desc, imponibile in invoice["righe"].items():
                count += 1
                imponibile = str(imponibile)
                if '-' in imponibile:
                    imponibile.replace('-', '')
                    imponibile = '0'*(11-len(imponibile)) + imponibile + "-"
                else:
                    imponibile = '0'*(11-len(imponibile)) + imponibile + "+"
                if desc != "Bollo":
                    line.append('4004300')  # TRF-CONTO-RIC
                else:
                    line.append('4004500')  # TRF-CONTO-RIC
                line.append(imponibile)  # TRF-IMP-RIC

            for _ in range(8-count):
                line.append('0'*19)

            line.append('000')  # TRF-CAU-PAG
            line.append(' '*83)  # TRF-CAU-DES-PAGAM + TRF-CAU-AGG-1-PAGAM + TRF-CAU-AGG-2-PAGAM
            line.append(('0000000' + ' ' + '0'*12 + ' '*18 + '0'*26)*80)  # TRF-CONTO + TRF-DA + TRF-IMPORTO + TRF-CAU-AGGIUNT + TRF-EC-PARTITA-PAG + TRF-EC-PARTITA-ANNO-PAG + TRF-EC-IMP-VAL
            line.append((' ' + '0'*18)*10)  # TRF-RIFER-TAB + TRF-IND-RIGA + TRF-DT-INI + TRF-DT-FIN
            line.append('000000')  # TRF-DOC6
            line.append('N' + '0')  # TRF-AN-OMONIMI + TRF-AN-TIPO-SOGG
            line.append('00'*80)  # TRF-EC-PARTITA-SEZ-PAG
            line.append('0'*15)  # TRF-NUM-DOC-PAG-PROF + TRF-DATA-DOC-PAG-PROF

            if invoice["ritenutaAcconto"] != 0:
                imponibile = str(invoice["ritenutaAcconto"])
                imponibile = '0'*(11-len(imponibile)) + imponibile + "+"
                line.append(imponibile)  # TRF-RIT-ACC
            else:
                line.append('0'*12)  # TRF-RIT-ACC

            line.append('0'*60)  # TRF-RIT-PREV + TRF-RIT-1 + TRF-RIT-2 + TRF-RIT-3 + TRF-RIT-4
            line.append('00'*8)  # TRF-UNITA-RICAVI
            line.append('00'*80)  # TRF-UNITA-PAGAM
            line.append(' '*24)  # TRF-FAX-PREF-1 + TRF-FAX-NUM-1
            line.append(' ' + ' ')  # TRF-SOLO-CLIFOR + TRF-80-SEGUENTE
            line.append('0000000')  # TRF-CONTO-RIT-ACC
            line.append('0'*35)   # TRF-CONTO-RIT-PREV + TRF-CONTO-RIT-1 + TRF-CONTO-RIT-2 + TRF-CONTO-RIT-3 + TRF-CONTO-RIT-4
            line.append('N' + 'N' + '00000000' + '000')  # TRF-DIFFERIMENTO-IVA + TRF-STORICO + TRF-STORICO-DATA + TRF-CAUS-ORI
            line.append(' ' + ' ' + '0'*16 + ' ')  # TRF-PREV-TIPOMOV + TRF-PREV-RATRIS + TRF-PREV-DTCOMP-INI + TRF-PREV-DTCOMP-FIN + TRF-PREV-FLAG-CONT
            line.append(' '*20 + '0'*21 + ' '*44 + '0'*8 + ' ' + '0'*6 + ' ' + '00' + ' ')  # TRF-RIFERIMENTO + TRF-CAUS-PREST-ANA + TRF-EC-TIPO-PAGA + TRF-CONTO-IVA-VEN-ACQ + TRF-PIVA-VECCHIA + TRF-PIVA-ESTERO-VECCHIA + # TRF-RISERVATO + TRF-DATA-IVA-AGVIAGGI + TRF-DATI-AGG-ANA-REC4 + TRF-RIF-IVA-NOTE-CRED + TRF-RIF-IVA-ANNO-PREC + TRF-NATURA-GIURIDICA + TRF-STAMPA-ELENCO
            line.append('000'*8 + ' '*20 + '0' + ' '*4 + '0'*6 + ' '*20 + 'S' + 'N')  # TRF-PERC-FORF + TRF-SOLO-MOV-IVA + TRF-COFI-VECCHIO + TRF-USA-PIVA-VECCHIA + TRF-USA-PIVA-EST-VECCHIA + TRF-USA-COFI-VECCHIO + TRF-ESIGIBILITA-IVA + TRF-TIPO-MOV-RISCONTI + TRF-AGGIORNA-EC + TRF-BLACKLIST-ANAG + TRF-BLACKLIST-IVA-ANNO + TRF-CONTEA-ESTERO + TRF-ART21-ANAG + TRF-ART21-IVA

            if invoice["tipoFattura"] == "Fattura":
                line.append('N')  # TRF-RIF-FATTURA
            else:
                line.append('S')  # TRF-RIF-FATTURA
            line.append('S' + ' '*2 + 'S' + ' '*2)  # TRF-RISERVATO-B + TRF-MASTRO-CF + TRF-MOV-PRIVATO + TRF-SPESE-MEDICHE + TRF-FILLER
            line.append('\n')
            parent.log_dialog.log_text.AppendText("Creato record #0 per fattura n. %s\n" % invoice["numFattura"])
            wx.Yield()

            #RECORD 5 per Tessera Sanitaria
            line.append('04103' + '3' + '5')  # TRF5-DITTA + TRF5-VERSIONE + TRF5-TARC
            line.append(' '*1200)  # TRF-ART21-CONTRATTO
            line.append('0'*6 + invoice["cf"])  # TRF-A21CO-ANAG + # TRF-A21CO-COFI
            total = str(invoice["importoTotale"])
            total = '0'*(13-len(total)) + total + "+"
            line.append(invoice["dataFattura"] + 'S' + '000' + total + '0'*14 + '0' + invoice["numFattura"][4:9] + '00' + ' '*40)  # TRF-A21CO-DATA + TRF-A21CO-FLAG + TRF-A21CO-ALQ + TRF-A21CO-IMPORTO + TRF-A21CO-IMPOSTA + TRF-A21CO-NDOC + TRF-A21CO-CONTRATTO
            line.append(('0'*6 + ' '*16 + '0'*8 + ' ' + '000' + '0'*14 + '0'*14 + '0'*8 + ' '*40)*49)  # TRF-A21CO-DATA + TRF-A21CO-FLAG + TRF-A21CO-ALQ + TRF-A21CO-IMPORTO + TRF-A21CO-IMPOSTA + TRF-A21CO-NDOC + TRF-A21CO-CONTRATTO

            if invoice["tipoFattura"] == "Nota di credito":
                line.append('000' + invoice["rifFattura"][4:9])  # TRF-RIF-FATT-NDOC
                line.append('0'*8)  # TRF-RIF-FATT-DDOC
            else:
                line.append('0'*16)  # TRF-RIF-FATT-NDOC + TRF-RIF-FATT-DDOC
            line.append('F' + 'SR' + '2')  # TRF-A21CO-TIPO + TRF-A21CO-TIPO-SPESA + TRF-A21CO-FLAG-SPESA
            line.append((' ' + '  ' + ' ')*49)  # TRF-A21CO-TIPO + TRF-A21CO-TIPO-SPESA + TRF-A21CO-FLAG-SPESA
            line.append(' ' + 'S' + ' '*76)  # TRF-SPESE-FUNEBRI + TRF-A21CO-PAGAM + FILLER + FILLER
            line.append('\n')
            parent.log_dialog.log_text.AppendText("Creato record #5 per fattura n. %s\n" % invoice["numFattura"])
            wx.Yield()

            #RECORD 1 per num. doc. originale
            line.append('04103' + '3' + '1')  # TRF1-DITTA + TRF1-VERSIONE + TRF1-TARC
            line.append('0'*7 + ' '*3 + '0'*14)  # TRF-NUM-AUTOFATT + TRF-SERIE-AUTOFATT + TRF-COD-VAL + TRF-TOTVAL
            line.append((' '*8 + '0'*24 + ' ' + '0'*36 + ' '*2 + '0'*9 + ' '*5)*20)  # TRF-NOMENCLATURA + TRF-IMP-LIRE + TRF-IMP-VAL + TRF-NATURA + TRF-MASSA + TRF-UN-SUPPL + TRF-VAL-STAT + TRF-REGIME + TRF-TRASPORTO + TRF-PAESE-PROV + TRF-PAESE-ORIG + TRF-PAESE-DEST + TRF-PROV-DEST + TRF-PROV-ORIG + TRF-SEGNO-RET
            line.append(' ' + '0'*6 + ' '*173)  # TRF-INTRA-TIPO + TRF-MESE-ANNO-RIF + SPAZIO
            line.append('0'*45 + ' '*4 + '0'*20 + ' '*28 + '0'*25)  # TRF-RITA-TIPO + TRF-RITA-IMPON + TRF-RITA-ALIQ + TRF-RITA-IMPRA + TRF-RITA-PRONS + TRF-RITA-MESE + TRF-RITA-CAUSA + TRF-RITA-TRIBU + TRF-RITA-DTVERS + TRF-RITA-IMPAG + TRF-RITA-TPAG + TRF-RITA-SERIE + TRF-RITA-QUIETANZA + TRF-RITA-NUM-BOLL + TRF-RITA-ABI + TRF-RITA-CAB + TRF-RITA-AACOMP + TRF-RITA-CRED
            line.append(' ' + '0'*44 + ' '*11 + '0'*64)  #TRF-RITA-SOGG + TRF-RITA-BASEIMP + TRF-RITA-FRANCHIGIA + TRF-RITA-CTO-PERC + TRF-RITA-CTO-DITT + FILLER + TRF-RITA-DATA + TRF-RITA-TOTDOC + TRF-RITA-IMPVERS + TRF-RITA-DATA-I + TRF-RITA-DATA-F + TRF-EMENS-ATT + TRF-EMENS-RAP + TRF-EMENS-ASS + TRF-RITA-TOTIVA
            line.append('0'*6 + ' '*178)  # TRF-CAUS-PREST-ANA-B + TRF-RITA-CAUSA-B + FILLER
            line.append('0'*13 + ' '*30 + '0'*14)  # TRF-POR-CODPAG + TRF-POR-BANCA + TRF-POR-AGENZIA + TRF-POR-DESAGENZIA + TRF-POR-TOT-RATE + TRF-POR-TOTDOC
            line.append(('0'*65 + ' '*2)*12)  # TRF-POR-NUM-RATA + TRF-POR-DATASCAD + TRF-POR-TIPOEFF + TRF-POR-IMPORTO-EFF + TRF-POR-IMPORTO-EFFVAL + TRF-POR-IMPORTO-BOLLI + TRF-POR-IMPORTO-BOLLIVAL + TRF-POR-FLAG + TRF-POR-TIPO-RD
            line.append('0'*4 + ' '*336)  # TRF-POR-CODAGE + TRF-POR-EFFETTO-SOSP + TRF-POR-CIG + TRF-POR-CUP + SPAZIO
            line.append((' '*3 + '0'*16)*20)  # TRF-COD-VAL-IV + TRF-IMP-VALUTA-IV
            line.append((' '*6 + '0'*35 + ' '*2 + '0'*20 + ' '*19 + '0'*16)*20)  # TRF-CODICE-SERVIZIO + TRF-STATO-PAGAMENTO + TRF-SERV-IMP-EURO + TRF-SERV-IMP-VAL + TRF-DATA-DOC-ORIG + TRF-MOD-EROGAZIONE + TRF-MOD-INCASSO + TRF-PROT-REG + TRF-PROG-REG + TRF-COD-SEZ-DOG-RET + TRF-ANNO-REG-RET + TRF-NUM-DOC-ORIG + TRF-SERV-SEGNO-RET + TRF-SERV-COD-VAL-IV + TRF-SERV-IMP-VALUTA-IV
            line.append(' '*1 + '0'*6)  # TRF-INTRA-TIPO-SERVIZIO + TRF-SERV-MESE-ANNO-RIF
            line.append(' '*8)  # TRF-CK-RCHARGE
            line.append('0'*(15-len(invoice["numFattura"])) + invoice["numFattura"])  # TRF-XNUM-DOC-ORI
            line.append(' ' + '00' + ' '*1090)  # TRF-MEM-ESIGIB-IVA + TRF-COD-IDENTIFICATIVO + TRF-ID-IMPORTAZIONE + TRF-XNUM-DOC-ORI-20 + SPAZIO + FILLER
            parent.log_dialog.log_text.AppendText("Creato record #1 per fattura n. %s\n" % invoice["numFattura"])
            wx.Yield()

            line = ''.join(line) + '\n'

            traf2000_file.write(line)
            parent.log_dialog.log_text.AppendText("Convertita fattura n. %s\n" % invoice["numFattura"])
            wx.Yield()

        parent.log_dialog.log_text.SetDefaultStyle(wx.TextAttr(wx.BLACK, font=wx.Font(wx.FontInfo(8).Bold())))
        parent.log_dialog.log_text.AppendText("Conversione terminata.\nTracciato TRAF2000 salvato in %s\n" % output_file_path)
        parent.log_dialog.log_text.SetDefaultStyle(wx.TextAttr())
        wx.Yield()
