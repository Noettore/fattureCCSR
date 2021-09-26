"""ask for an input file (.xlsx) and an output file (.pdf) and downloads and unite every invoice"""

import os
import shutil
import tempfile
import openpyxl
import PyPDF2
import wx

def download_input_file(parent):
    """download input file"""
    start_date = parent.start_date_picker.GetValue().Format("%d/%m/%Y")
    end_date = parent.end_date_picker.GetValue().Format("%d/%m/%Y")
    input_file_url = 'https://report.casadicurasanrossore.it:8443/reportserver?/STAT_FATTURATO_CTERZI&dataI='+start_date+'&dataF='+end_date+'&rs:Format=EXCELOPENXML'
    downloaded_input_file = parent.session.get(input_file_url)
    if downloaded_input_file.status_code != 200:
        parent.log_dialog.log_text.SetDefaultStyle(wx.TextAttr(wx.RED, font=wx.Font(wx.FontInfo(8).Bold())))
        parent.log_dialog.log_text.AppendText("ERRORE: impossibile scaricare il file di input.\nControllare la connessione ad internet e l'operatività del portale CCSR. Code %d\n" % downloaded_input_file.status_code)
        parent.log_dialog.log_text.SetDefaultStyle(wx.TextAttr())
        wx.Yield()
        return

    input_file_descriptor, parent.input_file_path = tempfile.mkstemp(suffix='.xlsx')
    parent.input_files.append(parent.input_file_path)
    with open(input_file_descriptor, 'wb') as input_file:
        input_file.write(downloaded_input_file.content)

def get_invoices_info(input_file_path: str) -> tuple:
    """extract invoices IDs and URLs from xlsx input file"""
    xlsx_file = openpyxl.load_workbook(input_file_path)
    sheet = xlsx_file.active
    invoices = dict()

    owner_name = '_'.join(sheet["B1"].value.split()[2:])

    for i in range(1, sheet.max_row+1):
        row = str(i)
        invoice_id = sheet["I"+row].value
        if invoice_id is not None and "CCSR" in invoice_id:
            invoice_id = invoice_id.replace("/", "-")
            invoice_type = sheet["AP"+row].value
            invoice_url = sheet["BG"+row].hyperlink.target
            invoice = {
                "id": invoice_id,
                "type": invoice_type,
                "url": invoice_url,
                "path": None,
                "good": None,
            }
            invoices[invoice_id] = invoice
    invoices_info = (owner_name, invoices)
    return invoices_info

def download_invoices(parent):
    """download invoices from CCSR"""
    output_all_file_path = None
    output_ft_file_path = None
    output_nc_file_path = None

    parent.log_dialog.log_text.AppendText("Download file input\n")
    wx.Yield()
    download_input_file(parent)

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
                    parent.log_dialog.log_text.SetDefaultStyle(wx.TextAttr(wx.RED, font=wx.Font(wx.FontInfo(8).Bold())))
                    parent.log_dialog.log_text.AppendText("Errore: fattura %s corrotta!\n" % invoice_id)
                    parent.log_dialog.log_text.SetDefaultStyle(wx.TextAttr())
                    wx.Yield()
                    invoice["good"] = False
                else:
                    downloaded_count += 1
                    if parent.verbose:
                        parent.log_dialog.log_text.AppendText("%d/%d scaricata fattura %s in %s\n" % (downloaded_count, invoices_count, invoice_id, invoice["path"]))
                        wx.Yield()
                    invoice["good"] = True
        else:
            parent.log_dialog.log_text.SetDefaultStyle(wx.TextAttr(wx.RED, font=wx.Font(wx.FontInfo(8).Bold())))
            parent.log_dialog.log_text.AppendText("Errore: impossibile scaricare fattura %s: %d\n" % (invoice_id, resp.status_code))
            parent.log_dialog.log_text.SetDefaultStyle(wx.TextAttr())
            wx.Yield()
            invoice["good"] = False

    parent.log_dialog.log_text.SetDefaultStyle(wx.TextAttr(wx.BLACK, font=wx.Font(wx.FontInfo(8).Bold())))
    parent.log_dialog.log_text.AppendText("Download terminato.\n")
    parent.log_dialog.log_text.SetDefaultStyle(wx.TextAttr())
    wx.Yield()

    parent.output_pdf_dialog.SetFilename("fatture_%s.pdf" % invoices_info[0])

    if parent.output_pdf_dialog.ShowModal() == wx.ID_OK:
        output_all_file_path = parent.output_pdf_dialog.GetPath()
        path, ext = os.path.splitext(output_all_file_path)
        output_ft_file_path = path+"_ft"+ext
        output_nc_file_path = path+"_nc"+ext

        merger_ft = PyPDF2.PdfFileMerger()
        merger_nc = PyPDF2.PdfFileMerger()
        merger_all = PyPDF2.PdfFileMerger()
        for invoice_id, invoice in invoices.items():
            if invoice["good"]:
                merger_all.append(PyPDF2.PdfFileReader(open(invoice["path"], "rb")))
                if invoice["type"] == "Fattura":
                    merger_ft.append(PyPDF2.PdfFileReader(open(invoice["path"], "rb")))
                elif invoice["type"] == "Nota di credito":
                    merger_nc.append(PyPDF2.PdfFileReader(open(invoice["path"], "rb")))
                else:
                    parent.log_dialog.log_text.SetDefaultStyle(wx.TextAttr(wx.RED, font=wx.Font(wx.FontInfo(8).Bold())))
                    parent.log_dialog.log_text.AppendText("Errore: la fattura %s ha tipo sconosciuto %s\n" % (invoice_id, invoice["type"]))
                    parent.log_dialog.log_text.SetDefaultStyle(wx.TextAttr())
        merger_all.write(output_all_file_path)
        merger_ft.write(output_ft_file_path)
        merger_nc.write(output_nc_file_path)
        shutil.rmtree(tmp_dir, ignore_errors=True)

        parent.log_dialog.log_text.SetDefaultStyle(wx.TextAttr(wx.BLACK, font=wx.Font(wx.FontInfo(8).Bold())))
        parent.log_dialog.log_text.AppendText("Il pdf contenente tutti i documenti si trova in %s\n" % output_all_file_path)
        parent.log_dialog.log_text.AppendText("Il pdf contenente tutti le fatture si trova in %s\n" % output_ft_file_path)
        parent.log_dialog.log_text.AppendText("Il pdf contenente tutti le note di credito si trova in %s\n" % output_nc_file_path)
        parent.log_dialog.log_text.SetDefaultStyle(wx.TextAttr())
        wx.Yield()
        parent.log_dialog.open_file_btn.Enable()

    else:
        parent.log_dialog.log_text.SetDefaultStyle(wx.TextAttr(wx.RED, font=wx.Font(wx.FontInfo(8).Bold())))
        parent.log_dialog.log_text.AppendText("Non è stata eseguita l'unione delle fatture in un singolo pdf.\nLe singole fatture si trovano in %s\n" % tmp_dir)
        parent.log_dialog.log_text.SetDefaultStyle(wx.TextAttr())
        wx.Yield()
