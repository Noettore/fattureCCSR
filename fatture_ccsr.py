"""This utility is used for downloading or converting to TRAF2000 invoices from a .csv or .xml report file"""

import wx

import downloader
import traf2000_converter
import exc
import utils

DOWNLOAD_ACTION = 1
CONVERT_ACTION = 2

class LogDialog(wx.Dialog):
    """logging panel"""
    def __init__(self, parent, title, action):
        super(LogDialog, self).__init__(parent, wx.ID_ANY, title)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.log_text = wx.TextCtrl(self, wx.ID_ANY, size=(300, 200), style=wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)
        log_sizer = wx.BoxSizer(wx.HORIZONTAL)
        log_sizer.Add(self.log_text, 0, wx.ALL, 2)

        self.log_text.Bind(wx.EVT_TEXT, self.on_text_update)

        if action == CONVERT_ACTION:
            self.nc_text = wx.TextCtrl(self, wx.ID_ANY, size=(300, 200), style=wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)
            log_sizer.Add(self.nc_text, 0, wx.ALL, 2)

        main_sizer.Add(log_sizer, 0, wx.ALL, 2)
        self.btn = wx.Button(self, wx.ID_OK, "Chiudi")
        self.btn.Disable()
        main_sizer.Add(self.btn, 0, wx.ALL|wx.CENTER, 2)

        self.SetSizerAndFit(main_sizer)

    def on_text_update(self, event):
        """autoscroll on text update"""
        self.ScrollPages(-1)
        event.Skip()

class LoginDialog(wx.Dialog):
    """login dialog for basic auth download"""
    def __init__(self, parent, title):
        """constructor"""
        super(LoginDialog, self).__init__(parent, wx.ID_ANY, title)

        self.logged_id = False

        user_sizer = wx.BoxSizer(wx.HORIZONTAL)
        user_lbl = wx.StaticText(self, wx.ID_ANY, "Username:")
        user_sizer.Add(user_lbl, 0, wx.ALL|wx.CENTER, 2)
        self.username = wx.TextCtrl(self, size=(265, -1))
        user_sizer.Add(self.username, 0, wx.ALL, 2)

        pass_sizer = wx.BoxSizer(wx.HORIZONTAL)
        pass_lbl = wx.StaticText(self, wx.ID_ANY, "Password:")
        pass_sizer.Add(pass_lbl, 0, wx.ALL|wx.CENTER, 2)
        self.password = wx.TextCtrl(self, size=(265, -1), style=wx.TE_PASSWORD|wx.TE_PROCESS_ENTER)
        pass_sizer.Add(self.password, 0, wx.ALL, 2)

        login_btn = wx.Button(self, label="Login")
        login_btn.SetDefault()
        login_btn.Bind(wx.EVT_BUTTON, self.on_login)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(user_sizer, 0, wx.ALL, 2)
        main_sizer.Add(pass_sizer, 0, wx.ALL, 2)
        main_sizer.Add(login_btn, 0, wx.ALL|wx.CENTER, 2)

        self.SetSizerAndFit(main_sizer)

    def on_login(self, _):
        """check credentials and login"""
        if self.username.GetValue() not in ("", None) and self.password.GetValue() not in ("", None):
            self.logged_id = True
        self.Close()

class FattureCCSRFrame(wx.Frame):
    """main application frame"""
    def __init__(self, parent, title):
        self._initial_locale = wx.Locale(wx.LANGUAGE_DEFAULT, wx.LOCALE_LOAD_DEFAULT)

        self.input_file_path = None
        self.input_file_ext = None
        self.output_file_path = None
        self.log_dialog = None

        super(FattureCCSRFrame, self).__init__(parent, wx.ID_ANY, title, size=(650, 150))
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        input_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        input_file_text = wx.StaticText(panel, wx.ID_ANY, "Seleziona il file scaricato dal portale della CCSR")
        input_file_text.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))

        input_file_doc = wx.StaticText(panel, wx.ID_ANY, "Per scaricare le fatture selezionare il file .xlsx mentre per convertire i record in TRAF2000 selezionare il file .xml o .csv")

        self.input_file_picker = wx.FilePickerCtrl(panel, 101, "", "Seleziona il .xlsx, .csv o .xml", "*.xlsx;*.csv;*.xml", style=wx.FLP_DEFAULT_STYLE)
        input_sizer.Add(self.input_file_picker, 1, wx.ALL|wx.EXPAND, 2)
        self.input_file_picker.Bind(wx.EVT_FILEPICKER_CHANGED, self.file_picker_changed)

        self.download_btn = wx.Button(panel, DOWNLOAD_ACTION, "Scarica Fatture")
        btn_sizer.Add(self.download_btn, 0, wx.ALL|wx.CENTER, 2)
        self.download_btn.Bind(wx.EVT_BUTTON, self.btn_onclick)
        self.download_btn.Disable()

        self.traf2000_btn = wx.Button(panel, CONVERT_ACTION, "Genera TRAF2000")
        btn_sizer.Add(self.traf2000_btn, 0, wx.ALL|wx.CENTER, 2)
        self.traf2000_btn.Bind(wx.EVT_BUTTON, self.btn_onclick)
        self.traf2000_btn.Disable()

        self.login_dlg = LoginDialog(self, "Inserisci le credenziali di login al portale della CCSR")
        self.output_traf2000_dialog = wx.FileDialog(panel, "Scegli dove salvare il file TRAF2000", defaultFile="TRAF2000", style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
        self.output_pdf_dialog = wx.FileDialog(panel, "Scegli dove salvare il .pdf con le fatture scaricate", defaultFile="fatture.pdf", style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)

        main_sizer.Add(input_file_text, 0, wx.ALL|wx.CENTER, 2)
        main_sizer.Add(input_file_doc, 0, wx.ALL|wx.CENTER, 2)
        main_sizer.Add(input_sizer, 0, wx.ALL|wx.EXPAND, 2)
        main_sizer.Add(btn_sizer, 0, wx.ALL|wx.CENTER, 2)

        panel.SetSizer(main_sizer)

        self.Show()

    def file_picker_changed(self, event):
        """event raised when the input file path is changed"""
        self.input_file_path = event.GetEventObject().GetPath()
        #TODO: error frame
        try:
            self.input_file_ext = utils.file_extension(self.input_file_path, (".xml", ".csv", ".xlsx"))
        except exc.NoFileError as handled_exception:
            print(handled_exception.args[0])
        except exc.NoFileExtensionError as handled_exception:
            print(handled_exception.args[0])
        except exc.WrongFileExtensionError as handled_exception:
            print(handled_exception.args[0])
        if self.input_file_ext == ".xlsx":
            self.download_btn.Enable()
            self.traf2000_btn.Disable()
        elif self.input_file_ext in (".csv", ".xml"):
            self.traf2000_btn.Enable()
            self.download_btn.Disable()
        else:
            self.download_btn.Disable()
            self.traf2000_btn.Disable()

    def btn_onclick(self, event):
        """event raised when a button is clicked"""
        btn_id = event.GetEventObject().GetId()
        if btn_id == DOWNLOAD_ACTION:
            self.login_dlg.ShowModal()
            if self.login_dlg.logged_id:
                self.log_dialog = LogDialog(self, "Download delle fatture dal portale CCSR", DOWNLOAD_ACTION)
                self.log_dialog.Show()
                downloader.download_invoices(self)
                self.log_dialog.btn.Enable()
        elif btn_id == CONVERT_ACTION:
            if self.output_traf2000_dialog.ShowModal() == wx.ID_OK:
                self.output_file_path = self.output_traf2000_dialog.GetPath()
            else:
                #TODO: avviso errore file output
                return
            self.log_dialog = LogDialog(self, "Conversione delle fatture in TRAF2000", CONVERT_ACTION)
            self.log_dialog.Show()
            #TODO: error frame
            try:
                traf2000_converter.convert(self.input_file_path, self.output_file_path, self)
            except exc.NoFileError as handled_exception:
                print(handled_exception.args[0])
            except exc.NoFileExtensionError as handled_exception:
                print(handled_exception.args[0])
            except exc.WrongFileExtensionError as handled_exception:
                print(handled_exception.args[0])
            self.log_dialog.btn.Enable()

if __name__ == "__main__":
    app = wx.App()
    FattureCCSRFrame(None, "Utility FattureCCSR")
    app.MainLoop()
