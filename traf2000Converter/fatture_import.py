"""This script provides two functions to import invoices from .csv or .xml into a dict"""

import csv
import xml.etree.ElementTree
import datetime
import unidecode

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
            # TODO: if Nota di Credito set correct sign
            importo = int(linea[15].replace("€", "").replace(",", "").replace(".", "").replace("(", "").replace(")", ""))
            if num_fattura not in fatture:
                fattura = {
                    "numFattura": num_fattura,
                    "tipoFattura": linea[8],
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
        rif_fattura = fattura.get('protocollo_fatturatestata1')
        data_fattura = datetime.datetime.fromisoformat(fattura.get('data_fatturatestata')).strftime("%d%m%Y")
        tipo_fattura = fattura.get('fat_ndc')
        ragione_sociale = unidecode.unidecode(fattura.get('cognome_cliente') + ' ' + ' '.join(fattura.get('nome_cliente').split(' ')[0:2]))
        pos_divide = str(len(fattura.get('cognome_cliente')) + 1)
        cf_piva = fattura.get('cf_piva_cliente')
        importo_totale = 0
        ritenuta_acconto = 0

        for riga in fattura.iter('{STAT_FATTURATO_CTERZI}Dettagli2'):
            desc = riga.get('descrizione_fatturariga1')
            # TODO: if Nota di Credito set correct sign
            importo = int(format(round(float(riga.get('prezzounitario_fatturariga1')), 2), '.2f').replace('.', '').replace('-', ''))
            if desc == "Ritenuta d'acconto":
                ritenuta_acconto = importo
            else:
                righe[desc] = importo
                importo_totale += importo

        fattura_elem = {
            "numFattura": num_fattura,
            "tipoFattura": tipo_fattura,
            "rifFattura": rif_fattura,
            "dataFattura": data_fattura,
            "ragioneSociale": ragione_sociale,
            "posDivide": pos_divide,
            "cf": cf_piva,
            "importoTotale": importo_totale,
            "ritenutaAcconto": ritenuta_acconto,
            "righe": righe,
        }
        fatture[num_fattura] = fattura_elem
    return fatture
