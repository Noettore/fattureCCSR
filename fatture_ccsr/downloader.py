"""ask for an input file (.xlsx) and an output file (.pdf) and downloads and unite every invoice"""

import sys
import os
import subprocess
import shutil
import tempfile
import openpyxl
import PyPDF2
import wx

def get_invoices_info(input_file_path: str) -> tuple:
    """extract invoices IDs and URLs from xlsx input file"""
    xlsx_file = openpyxl.load_workbook(input_file_path)
    sheet = xlsx_file.active
    invoices = dict()

    owner_name = '_'.join(sheet["B1"].value.split()[2:])

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
    invoices_info = (owner_name, invoices)
    return invoices_info

def open_file(file_path):
    """open a file with the default software"""
    if sys.platform == "win32":
        os.startfile(file_path) # pylint: disable=maybe-no-member
    else:
        opener = "open" if sys.platform == "darwin" else "xdg-open"
        subprocess.call([opener, file_path])

def download_invoices(parent):
    """download invoices from CCSR"""
    output_file_path = None

    invoices_info = get_invoices_info(parent.input_file_path)
    invoices = invoices_info[1]

    parent.log_dialog.log_text.AppendText("Inizio download fatture dal portale CCSR\n")
    wx.Yield()

    tmp_dir = tempfile.mkdtemp()

    invoices_count = len(invoices)
    downloaded_count = 0

    for invoice_id, invoice in invoices.items():
        resp = parent.session.get(invoice["url"])
        if resp.status_code == 200:
            with open(tmp_dir+"/"+invoice_id+".pdf", "wb") as output_file:
                output_file.write(resp.content)
                invoice["path"] = output_file.name
                try:
                    PyPDF2.PdfFileReader(open(invoice["path"], "rb"))
                except (PyPDF2.utils.PdfReadError, OSError):
                    parent.log_dialog.log_text.AppendText("Errore: fattura %s corrotta!\n" % invoice_id)
                    wx.Yield()
                    invoice["good"] = False
                else:
                    downloaded_count += 1
                    parent.log_dialog.log_text.AppendText("%d/%d scaricata fattura %s in %s\n" % (downloaded_count, invoices_count, invoice_id, invoice["path"]))
                    wx.Yield()
                    invoice["good"] = True
        else:
            parent.log_dialog.log_text.AppendText("Errore: impossibile scaricare fattura %s: %d\n" % (invoice_id, resp.status_code))
            wx.Yield()
            invoice["good"] = False

    parent.output_pdf_dialog.SetFilename("fatture_%s.pdf" % invoices_info[0])

    if parent.output_pdf_dialog.ShowModal() == wx.ID_OK:
        output_file_path = parent.output_pdf_dialog.GetPath()
    else:
        #TODO: avviso errore file output
        return

    merger = PyPDF2.PdfFileMerger()
    for invoice in invoices.values():
        if invoice["good"]:
            merger.append(PyPDF2.PdfFileReader(open(invoice["path"], "rb")))
    merger.write(output_file_path)

    open_file(output_file_path)

    shutil.rmtree(tmp_dir, ignore_errors=True)

    parent.log_dialog.log_text.AppendText("Download terminato.\nIl pdf contenente le fatture si trova in %s\n" % output_file_path)
    wx.Yield()
