"""ask for an input file (.xlsx) and an output file (.pdf) and downloads and unite every invoice"""

import shutil
import tempfile
import requests
import requests_ntlm
import openpyxl
import PyPDF2

import logger

def get_invoices_info(input_file_path: str) -> dict:
    """extract invoices IDs and URLs from xlsx input file"""
    xlsx_file = openpyxl.load_workbook(input_file_path)
    sheet = xlsx_file.active
    invoices = dict()

    for i in range(1, sheet.max_row+1):
        invoice_id = sheet["I"+str(i)].value
        if invoice_id is not None and "CCSR" in invoice_id:
            invoice_id = invoice_id.replace("/", "-")
            invoice_url = sheet["BG"+str(i)].hyperlink.target
            invoice = {
                "id": invoice_id,
                "url": invoice_url,
                "path": None,
                "good": None,
            }
            invoices[invoice_id] = invoice

    return invoices


def download_invoices(input_file_path: str, output_file_path: str, username: str, password: str):
    """download invoices from CCSR"""
    invoices = get_invoices_info(input_file_path)

    session = requests.Session()
    session.auth = requests_ntlm.HttpNtlmAuth("sr\\"+username, password)
    logger.downloader_logger.info("Inizio download fatture dal portale CCSR")

    tmp_dir = tempfile.mkdtemp()

    invoices_count = len(invoices)
    processed_count = 0

    for invoice_id, invoice in invoices.items():
        resp = session.get(invoice["url"])
        processed_count += 1
        if resp.status_code == 200:
            with open(tmp_dir+"/"+invoice_id+".pdf", "wb") as output_file:
                output_file.write(resp.content)
                invoice["path"] = output_file.name
                print(invoice["path"])
                try:
                    PyPDF2.PdfFileReader(open(invoice["path"], "rb"))
                except (PyPDF2.utils.PdfReadError, OSError):
                    logger.downloader_logger.error("%d/%d fattura %s corrotta!", processed_count, invoices_count, invoice_id)
                    invoice["good"] = False
                else:
                    logger.downloader_logger.info("%d/%d scaricata fattura %s in %s", processed_count, invoices_count, invoice_id, invoice["path"])
                    invoice["good"] = True
        else:
            logger.downloader_logger.error("%d/%d impossibile scaricare fattura %s: %d", processed_count, invoices_count, invoice_id, resp.status_code)
            invoice["good"] = False

    merger = PyPDF2.PdfFileMerger()
    for invoice in invoices.values():
        if invoice["good"]:
            merger.append(PyPDF2.PdfFileReader(open(invoice["path"], "rb")))
    merger.write(output_file_path)
    
    shutil.rmtree(tmp_dir, ignore_errors=True)

    logger.downloader_logger.info("Download terminato. Il pdf contenente le fatture si trova in %s", output_file_path)
