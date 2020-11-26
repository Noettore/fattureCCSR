"""ask for an input file and an output file and generates the TRAF2000 records from a .csv or .xml"""

import os
import datetime
import csv
import xml.etree.ElementTree
import unidecode

import exc

def import_csv(csv_file_path):
    """Return a dict containing the invoices info"""
    fatture = dict()
    with open(csv_file_path, newline="") as csv_file:
        lettore = csv.reader(csv_file, delimiter=",")

        for _ in range(4):
            next(lettore)

        for linea in lettore:
            if len(linea) == 0:
                break
            num_fattura = linea[1]
            tipo_fattura = linea[8]
            importo = linea[15]
            segno = 1
            if tipo_fattura == "Nota di credito" and '(' not in importo:
                segno = -1
            importo = int(linea[15].replace("€", "").replace(",", "").replace(".", "").replace("(", "").replace(")", "")) * segno
            if num_fattura not in fatture:
                fattura = {
                    "numFattura": num_fattura,
                    "tipoFattura": tipo_fattura,
                    "rifFattura": linea[4],
                    "dataFattura": linea[2].replace("/", ""),
                    "ragioneSociale": unidecode.unidecode(linea[6] + " " + " ".join(linea[5].split(" ")[0:2])),
                    "posDivide": str(len(linea[6]) + 1),
                    "cf": linea[7],
                    "importoTotale": 0,
                    "ritenutaAcconto": 0,
                    "righe": dict()
                }
                fatture[num_fattura] = fattura

            if linea[14] == "Ritenuta d'acconto":
                fatture[num_fattura]["ritenutaAcconto"] = importo

            else:
                fatture[num_fattura]["importoTotale"] += importo
                fatture[num_fattura]["righe"][linea[14]] = importo
    return fatture

def import_xml(xml_file_path):
    """Return a dict containing the invoices info"""
    fatture = dict()

    tree = xml.etree.ElementTree.parse(xml_file_path)
    root = tree.getroot()

    for fattura in root.iter('{STAT_FATTURATO_CTERZI}Dettagli'):
        righe = dict()
        num_fattura = fattura.get('protocollo_fatturatestata')
        tipo_fattura = fattura.get('fat_ndc')
        importo_totale = 0
        ritenuta_acconto = 0

        for riga in fattura.iter('{STAT_FATTURATO_CTERZI}Dettagli2'):
            desc = riga.get('descrizione_fatturariga1')
            segno = 1
            if tipo_fattura == 'Nota di credito' and '-' not in riga.get('prezzounitario_fatturariga1'):
                segno = -1
            importo = int(format(round(float(riga.get('prezzounitario_fatturariga1')), 2), '.2f').replace('.', '').replace('-', '')) * segno
            if desc == "Ritenuta d'acconto":
                ritenuta_acconto = importo
            else:
                righe[desc] = importo
                importo_totale += importo

        fattura_elem = {
            "numFattura": num_fattura,
            "tipoFattura": tipo_fattura,
            "rifFattura": fattura.get('protocollo_fatturatestata1'),
            "dataFattura": datetime.datetime.fromisoformat(fattura.get('data_fatturatestata')).strftime("%d%m%Y"),
            "ragioneSociale": unidecode.unidecode(fattura.get('cognome_cliente') + ' ' + ' '.join(fattura.get('nome_cliente').split(' ')[0:2])),
            "posDivide": str(len(fattura.get('cognome_cliente')) + 1),
            "cf": fattura.get('cf_piva_cliente'),
            "importoTotale": importo_totale,
            "ritenutaAcconto": ritenuta_acconto,
            "righe": righe,
        }
        fatture[num_fattura] = fattura_elem
    return fatture


def convert(input_file_path, out_file_path):
    """Output to a file the TRAF2000 records"""
    input_file_ext = os.path.splitext(input_file_path)[1]
    if input_file_ext == ".csv":
        fatture = import_csv(input_file_path)

    elif input_file_ext == ".xml":
        fatture = import_xml(input_file_path)

    else:
        raise exc.WrongFileExtension("Expected .csv or .xml but received " + input_file_ext)

    with open(out_file_path, "w") as traf2000_file:
        print("Note di credito:\n")

        for fattura in fatture.values():
            if fattura["tipoFattura"] != "Fattura" and fattura["tipoFattura"] != "Nota di credito":
                print("Errore: il documento " + fattura["numFattura"] + " può essere FATTURA o NOTA DI CREDITO")
                continue

            if len(fattura["cf"]) != 16 and len(fattura["cf"]) == 11:
                print("Errore: il documento " + fattura["numFattura"] + " non ha cf/piva")
                continue

            if fattura["tipoFattura"] == "Nota di credito":
                # As for now this script doesn't handle "Note di credito"
                print(fattura["numFattura"])
                continue

            linea = ["04103", "3", "0", "00000"]  # TRF-DITTA + TRF-VERSIONE + TRF-TARC + TRF-COD-CLIFOR
            linea.append(fattura["ragioneSociale"][:32]+' '*(32-len(fattura["ragioneSociale"])))  # TRF-RASO
            linea.append(' '*30)  # TRF-IND
            linea.append('00000')  # TRF-CAP
            linea.append(' '*27)  # TRF-CITTA + TRF-PROV

            if len(fattura["cf"]) == 16:  # se c.f. presente
                linea.append(fattura["cf"])  # TRF-COFI
                linea.append('0'*11)  # TRF-PIVA
                linea.append('S')  # TRF-PF
            else:  # se piva presente
                linea.append(' '*16)  # TRF-COFI
                linea.append(fattura["cf"])  # TRF-PIVA
                linea.append('N')  # TRF-PF

            linea.append('0'*(2-len(fattura["posDivide"])) + fattura["posDivide"])  # TRF-DIVIDE
            linea.append('0000')  # TRF-PAESE
            linea.append(' '*33)  # TRF-PIVA-ESTERO + TRF-COFI-ESTERO + TRF-SESSO
            linea.append('0'*8)  # TRF-DTNAS
            linea.append(' '*64)  # TRF-COMNA + TRF-PRVNA + TRF-PREF + TRF-NTELE-NUM + TRF-FAX-PREF + TRF-FAX-NUM
            linea.append('0'*22)  # TRF-CFCONTO + TRF-CFCODPAG + TRF-CFBANCA + TRF-CFAGENZIA + TRF-CFINTERM

            if fattura["tipoFattura"] == "Fattura":
                linea.append('001')  # TRF-CAUSALE
                linea.append("FATTURA VENDITA")  # TRF-CAU-DES
            else:
                linea.append('002')  # TRF-CAUSALE
                linea.append("N.C. A CLIENTE ")  # TRF-CAU-DES

            linea.append(' '*86)  # TRF-CAU-AGG + TRF-CAU-AGG-1 + TRF-CAU-AGG-2
            linea.append(fattura["dataFattura"]*2)  # TRF-DATA-REGISTRAZIONE + TRF-DATA-DOC
            linea.append('00000000')  # TRF-NUM-DOC-FOR
            linea.append(fattura["numFattura"][4:9])  # TRF-NDOC
            linea.append('00')  # TRF-SERIE
            linea.append('0'*72)  # TRF-EC-PARTITA + TRF-EC-PARTITA-ANNO + TRF-EC-COD-VAL + TRF-EC-CAMBIO + TRF-EC-DATA-CAMBIO + TRF-EC-TOT-DOC-VAL + TRF-EC-TOT-IVA-VAL + TRF-PLAFOND

            conta = 0
            for desc, imponibile in fattura["righe"].items():
                conta += 1
                imponibile = str(imponibile)
                if '-' in imponibile:
                    imponibile.replace('-', '')
                    imponibile = '0'*(11-len(imponibile)) + imponibile + "-"
                else:
                    imponibile = '0'*(11-len(imponibile)) + imponibile + "+"
                linea.append(imponibile)  # TRF-IMPONIB
                if desc != "Bollo":
                    linea.append('308')  # TRF-ALIQ
                else:
                    linea.append('315')  # TRF-ALIQ
                linea.append('0'*16)  # TRF-ALIQ-AGRICOLA + TRF-IVA11 + TRF-IMPOSTA

            for _ in range(8-conta):
                linea.append('0'*31)

            totale = str(fattura["importoTotale"])
            if '-' in totale:
                totale.replace('-', '')
                totale = '0'*(11-len(totale)) + totale + "-"
            else:
                totale = '0'*(11-len(totale)) + totale + "+"
            linea.append(totale)  # TRF-TOT-FAT

            conta = 0
            for desc, imponibile in fattura["righe"].items():
                conta += 1
                imponibile = str(imponibile)
                if '-' in imponibile:
                    imponibile.replace('-', '')
                    imponibile = '0'*(11-len(imponibile)) + imponibile + "-"
                else:
                    imponibile = '0'*(11-len(imponibile)) + imponibile + "+"
                if desc != "Bollo":
                    linea.append('4004300')  # TRF-CONTO-RIC
                else:
                    linea.append('4004500')  # TRF-CONTO-RIC
                linea.append(imponibile)  # TRF-IMP-RIC

            for _ in range(8-conta):
                linea.append('0'*19)

            linea.append('000')  # TRF-CAU-PAG
            linea.append(' '*83)  # TRF-CAU-DES-PAGAM + TRF-CAU-AGG-1-PAGAM + TRF-CAU-AGG-2-PAGAM
            linea.append(('0000000' + ' ' + '0'*12 + ' '*18 + '0'*26)*80)  # TRF-CONTO + TRF-DA + TRF-IMPORTO + TRF-CAU-AGGIUNT + TRF-EC-PARTITA-PAG + TRF-EC-PARTITA-ANNO-PAG + TRF-EC-IMP-VAL
            linea.append((' ' + '0'*18)*10)  # TRF-RIFER-TAB + TRF-IND-RIGA + TRF-DT-INI + TRF-DT-FIN
            linea.append('000000')  # TRF-DOC6
            linea.append('N' + '0')  # TRF-AN-OMONIMI + TRF-AN-TIPO-SOGG
            linea.append('00'*80)  # TRF-EC-PARTITA-SEZ-PAG
            linea.append('0'*15)  # TRF-NUM-DOC-PAG-PROF + TRF-DATA-DOC-PAG-PROF

            if fattura["ritenutaAcconto"] != 0:
                imponibile = str(fattura["ritenutaAcconto"])
                imponibile = '0'*(11-len(imponibile)) + imponibile + "+"
                linea.append(imponibile)  # TRF-RIT-ACC
            else:
                linea.append('0'*12)  # TRF-RIT-ACC

            linea.append('0'*60)  # TRF-RIT-PREV + TRF-RIT-1 + TRF-RIT-2 + TRF-RIT-3 + TRF-RIT-4
            linea.append('00'*8)  # TRF-UNITA-RICAVI
            linea.append('00'*80)  # TRF-UNITA-PAGAM
            linea.append(' '*24)  # TRF-FAX-PREF-1 + TRF-FAX-NUM-1
            linea.append(' ' + ' ')  # TRF-SOLO-CLIFOR + TRF-80-SEGUENTE
            linea.append('0000000')  # TRF-CONTO-RIT-ACC
            linea.append('0'*35)   # TRF-CONTO-RIT-PREV + TRF-CONTO-RIT-1 + TRF-CONTO-RIT-2 + TRF-CONTO-RIT-3 + TRF-CONTO-RIT-4
            linea.append('N' + 'N' + '00000000' + '000')  # TRF-DIFFERIMENTO-IVA + TRF-STORICO + TRF-STORICO-DATA + TRF-CAUS-ORI
            linea.append(' ' + ' ' + '0'*16 + ' ')  # TRF-PREV-TIPOMOV + TRF-PREV-RATRIS + TRF-PREV-DTCOMP-INI + TRF-PREV-DTCOMP-FIN + TRF-PREV-FLAG-CONT
            linea.append(' '*20 + '0'*21 + ' '*44 + '0'*8 + ' ' + '0'*6 + ' ' + '00' + ' ')  # TRF-RIFERIMENTO + TRF-CAUS-PREST-ANA + TRF-EC-TIPO-PAGA + TRF-CONTO-IVA-VEN-ACQ + TRF-PIVA-VECCHIA + TRF-PIVA-ESTERO-VECCHIA + # TRF-RISERVATO + TRF-DATA-IVA-AGVIAGGI + TRF-DATI-AGG-ANA-REC4 + TRF-RIF-IVA-NOTE-CRED + TRF-RIF-IVA-ANNO-PREC + TRF-NATURA-GIURIDICA + TRF-STAMPA-ELENCO
            linea.append('000'*8 + ' '*20 + '0' + ' '*4 + '0'*6 + ' '*20 + 'S' + 'N')  # TRF-PERC-FORF + TRF-SOLO-MOV-IVA + TRF-COFI-VECCHIO + TRF-USA-PIVA-VECCHIA + TRF-USA-PIVA-EST-VECCHIA + TRF-USA-COFI-VECCHIO + TRF-ESIGIBILITA-IVA + TRF-TIPO-MOV-RISCONTI + TRF-AGGIORNA-EC + TRF-BLACKLIST-ANAG + TRF-BLACKLIST-IVA-ANNO + TRF-CONTEA-ESTERO + TRF-ART21-ANAG + TRF-ART21-IVA

            if fattura["tipoFattura"] == "Fattura":
                linea.append('N')  # TRF-RIF-FATTURA
            else:
                linea.append('S')  # TRF-RIF-FATTURA
            linea.append('S' + ' '*2 + 'S' + ' '*2)  # TRF-RISERVATO-B + TRF-MASTRO-CF + TRF-MOV-PRIVATO + TRF-SPESE-MEDICHE + TRF-FILLER
            linea.append('\n')

            #RECORD 5 per Tessera Sanitaria
            linea.append('04103' + '3' + '5')  # TRF5-DITTA + TRF5-VERSIONE + TRF5-TARC
            linea.append(' '*1200)  # TRF-ART21-CONTRATTO
            linea.append('0'*6 + fattura["cf"])  # TRF-A21CO-ANAG + # TRF-A21CO-COFI
            totale = str(fattura["importoTotale"])
            totale = '0'*(13-len(totale)) + totale + "+"
            linea.append(fattura["dataFattura"] + 'S' + '000' + totale + '0'*14 + '0' + fattura["numFattura"][4:9] + '00' + ' '*40)  # TRF-A21CO-DATA + TRF-A21CO-FLAG + TRF-A21CO-ALQ + TRF-A21CO-IMPORTO + TRF-A21CO-IMPOSTA + TRF-A21CO-NDOC + TRF-A21CO-CONTRATTO
            linea.append(('0'*6 + ' '*16 + '0'*8 + ' ' + '000' + '0'*14 + '0'*14 + '0'*8 + ' '*40)*49)  # TRF-A21CO-DATA + TRF-A21CO-FLAG + TRF-A21CO-ALQ + TRF-A21CO-IMPORTO + TRF-A21CO-IMPOSTA + TRF-A21CO-NDOC + TRF-A21CO-CONTRATTO

            if fattura["tipoFattura"] == "Nota di credito":
                linea.append('000' + fattura["rifFattura"][4:9])  # TRF-RIF-FATT-NDOC
                linea.append('0'*8)  # TRF-RIF-FATT-DDOC
            else:
                linea.append('0'*16)  # TRF-RIF-FATT-NDOC + TRF-RIF-FATT-DDOC
            linea.append('F' + 'SR' + '2')  # TRF-A21CO-TIPO + TRF-A21CO-TIPO-SPESA + TRF-A21CO-FLAG-SPESA
            linea.append((' ' + '  ' + ' ')*49)  # TRF-A21CO-TIPO + TRF-A21CO-TIPO-SPESA + TRF-A21CO-FLAG-SPESA
            linea.append(' ' + 'S' + ' '*76)  # TRF-SPESE-FUNEBRI + TRF-A21CO-PAGAM + FILLER + FILLER
            linea.append('\n')

            #RECORD 1 per num. doc. originale
            linea.append('04103' + '3' + '1')  # TRF1-DITTA + TRF1-VERSIONE + TRF1-TARC
            linea.append('0'*7 + ' '*3 + '0'*14)  # TRF-NUM-AUTOFATT + TRF-SERIE-AUTOFATT + TRF-COD-VAL + TRF-TOTVAL
            linea.append((' '*8 + '0'*24 + ' ' + '0'*36 + ' '*2 + '0'*9 + ' '*5)*20)  # TRF-NOMENCLATURA + TRF-IMP-LIRE + TRF-IMP-VAL + TRF-NATURA + TRF-MASSA + TRF-UN-SUPPL + TRF-VAL-STAT + TRF-REGIME + TRF-TRASPORTO + TRF-PAESE-PROV + TRF-PAESE-ORIG + TRF-PAESE-DEST + TRF-PROV-DEST + TRF-PROV-ORIG + TRF-SEGNO-RET
            linea.append(' ' + '0'*6 + ' '*173)  # TRF-INTRA-TIPO + TRF-MESE-ANNO-RIF + SPAZIO
            linea.append('0'*45 + ' '*4 + '0'*20 + ' '*28 + '0'*25)  # TRF-RITA-TIPO + TRF-RITA-IMPON + TRF-RITA-ALIQ + TRF-RITA-IMPRA + TRF-RITA-PRONS + TRF-RITA-MESE + TRF-RITA-CAUSA + TRF-RITA-TRIBU + TRF-RITA-DTVERS + TRF-RITA-IMPAG + TRF-RITA-TPAG + TRF-RITA-SERIE + TRF-RITA-QUIETANZA + TRF-RITA-NUM-BOLL + TRF-RITA-ABI + TRF-RITA-CAB + TRF-RITA-AACOMP + TRF-RITA-CRED
            linea.append(' ' + '0'*44 + ' '*11 + '0'*64)  #TRF-RITA-SOGG + TRF-RITA-BASEIMP + TRF-RITA-FRANCHIGIA + TRF-RITA-CTO-PERC + TRF-RITA-CTO-DITT + FILLER + TRF-RITA-DATA + TRF-RITA-TOTDOC + TRF-RITA-IMPVERS + TRF-RITA-DATA-I + TRF-RITA-DATA-F + TRF-EMENS-ATT + TRF-EMENS-RAP + TRF-EMENS-ASS + TRF-RITA-TOTIVA
            linea.append('0'*6 + ' '*178)  # TRF-CAUS-PREST-ANA-B + TRF-RITA-CAUSA-B + FILLER
            linea.append('0'*13 + ' '*30 + '0'*14)  # TRF-POR-CODPAG + TRF-POR-BANCA + TRF-POR-AGENZIA + TRF-POR-DESAGENZIA + TRF-POR-TOT-RATE + TRF-POR-TOTDOC
            linea.append(('0'*65 + ' '*2)*12)  # TRF-POR-NUM-RATA + TRF-POR-DATASCAD + TRF-POR-TIPOEFF + TRF-POR-IMPORTO-EFF + TRF-POR-IMPORTO-EFFVAL + TRF-POR-IMPORTO-BOLLI + TRF-POR-IMPORTO-BOLLIVAL + TRF-POR-FLAG + TRF-POR-TIPO-RD
            linea.append('0'*4 + ' '*336)  # TRF-POR-CODAGE + TRF-POR-EFFETTO-SOSP + TRF-POR-CIG + TRF-POR-CUP + SPAZIO
            linea.append((' '*3 + '0'*16)*20)  # TRF-COD-VAL-IV + TRF-IMP-VALUTA-IV
            linea.append((' '*6 + '0'*35 + ' '*2 + '0'*20 + ' '*19 + '0'*16)*20)  # TRF-CODICE-SERVIZIO + TRF-STATO-PAGAMENTO + TRF-SERV-IMP-EURO + TRF-SERV-IMP-VAL + TRF-DATA-DOC-ORIG + TRF-MOD-EROGAZIONE + TRF-MOD-INCASSO + TRF-PROT-REG + TRF-PROG-REG + TRF-COD-SEZ-DOG-RET + TRF-ANNO-REG-RET + TRF-NUM-DOC-ORIG + TRF-SERV-SEGNO-RET + TRF-SERV-COD-VAL-IV + TRF-SERV-IMP-VALUTA-IV
            linea.append(' '*1 + '0'*6)  # TRF-INTRA-TIPO-SERVIZIO + TRF-SERV-MESE-ANNO-RIF
            linea.append(' '*8)  # TRF-CK-RCHARGE
            linea.append('0'*(15-len(fattura["numFattura"])) + fattura["numFattura"])  # TRF-XNUM-DOC-ORI
            linea.append(' ' + '00' + ' '*1090)  # TRF-MEM-ESIGIB-IVA + TRF-COD-IDENTIFICATIVO + TRF-ID-IMPORTAZIONE + TRF-XNUM-DOC-ORI-20 + SPAZIO + FILLER

            linea = ''.join(linea) + '\n'

            traf2000_file.write(linea)
