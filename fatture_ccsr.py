"""This utility is used for downloading or converting to TRAF2000 invoices from a .xlsx, .csv or .xml report file"""

import os
import tempfile
import wx
import wx.adv
import requests
import requests_ntlm
import atexit

import downloader
import traf2000_converter
import exc

LOGIN_ACTION = 0
LOGOUT_ACTION = 1
DOWNLOAD_ACTION = 10
CONVERT_ACTION = 20

def file_extension(file_path: str, allowed_ext: set = None) -> str:
    """Return the file extension if that's in the allowed extension set"""
    if file_path in (None, ""):
        raise exc.NoFileError()
    file_ext = os.path.splitext(file_path)[1]
    if file_ext in (None, ""):
        raise exc.NoFileExtensionError
    if allowed_ext is not None and file_ext not in allowed_ext:
        raise exc.WrongFileExtensionError
    return file_ext

class LogDialog(wx.Dialog):
    """logging panel"""
    def __init__(self, parent, title, action):
        super(LogDialog, self).__init__(parent, wx.ID_ANY, title, style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        self.log_text = wx.TextCtrl(self, wx.ID_ANY, size=(500, 200), style=wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL|wx.EXPAND)
        log_sizer = wx.BoxSizer(wx.HORIZONTAL)
        log_sizer.Add(self.log_text, 1, wx.ALL|wx.EXPAND, 2)

        self.log_text.Bind(wx.EVT_TEXT, self.on_text_update)

        if action == CONVERT_ACTION:
            self.nc_text = wx.TextCtrl(self, wx.ID_ANY, size=(300, 200), style=wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)
            self.nc_text.Bind(wx.EVT_TEXT, self.on_text_update)
            log_sizer.Add(self.nc_text, 1, wx.ALL|wx.EXPAND, 2)

        main_sizer.Add(log_sizer, 1, wx.ALL|wx.EXPAND, 2)
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
        super(LoginDialog, self).__init__(parent, wx.ID_ANY, title, style=wx.DEFAULT_DIALOG_STYLE)

        self.logged_in = False

        user_sizer = wx.BoxSizer(wx.HORIZONTAL)
        user_lbl = wx.StaticText(self, wx.ID_ANY, "Username:")
        user_sizer.Add(user_lbl, 0, wx.ALL|wx.CENTER|wx.EXPAND, 2)
        self.username = wx.TextCtrl(self, size=(265, -1))
        user_sizer.Add(self.username, 0, wx.ALL|wx.EXPAND, 2)

        pass_sizer = wx.BoxSizer(wx.HORIZONTAL)
        pass_lbl = wx.StaticText(self, wx.ID_ANY, "Password:")
        pass_sizer.Add(pass_lbl, 0, wx.ALL|wx.CENTER|wx.EXPAND, 2)
        self.password = wx.TextCtrl(self, size=(265, -1), style=wx.TE_PASSWORD|wx.TE_PROCESS_ENTER)
        pass_sizer.Add(self.password, 0, wx.ALL|wx.EXPAND, 2)

        login_btn = wx.Button(self, label="Login")
        login_btn.SetDefault()
        login_btn.Bind(wx.EVT_BUTTON, self.on_login)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(user_sizer, 1, wx.ALL|wx.EXPAND, 2)
        main_sizer.Add(pass_sizer, 1, wx.ALL|wx.EXPAND, 2)
        main_sizer.Add(login_btn, 0, wx.ALL|wx.CENTER, 2)

        self.SetSizerAndFit(main_sizer)

    def disconnect(self):
        """close session and reset input fields"""
        self.username.SetValue('')
        self.password.SetValue('')
        self.GetParent().session.close()
        self.logged_in = False

    def on_login(self, _):
        """check credentials and login"""
        if self.username.GetValue() not in ("", None) and self.password.GetValue() not in ("", None):
            session = self.GetParent().session
            session.auth = requests_ntlm.HttpNtlmAuth("sr\\"+self.username.GetValue(), self.password.GetValue())
            if session.get('https://report.casadicurasanrossore.it:8443/Reports/browse/').status_code == 200:
                self.logged_in = True
                self.Close()

class FattureCCSRFrame(wx.Frame):
    """main application frame"""
    def __init__(self, parent, title):
        atexit.register(self.exit_handler)

        self._initial_locale = wx.Locale(wx.LANGUAGE_DEFAULT, wx.LOCALE_LOAD_DEFAULT)

        self.input_file_path = None
        self.input_file_ext = None
        self.input_files = list()
        self.log_dialog = None
        self.session = requests.Session()

        super(FattureCCSRFrame, self).__init__(parent, wx.ID_ANY, title, size=(520, 180))
        panel = wx.Panel(self)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        date_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.login_dlg = LoginDialog(self, "Inserisci le credenziali di login al portale della CCSR")
        self.output_traf2000_dialog = wx.FileDialog(panel, "Scegli dove salvare il file TRAF2000", defaultFile="TRAF2000", style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
        self.output_pdf_dialog = wx.FileDialog(panel, "Scegli dove salvare il .pdf con le fatture scaricate", defaultFile="fatture.pdf", style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)

        title_text = wx.StaticText(panel, wx.ID_ANY, "Utility Fatture Casa di Cura San Rossore")
        title_text.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))

        desc_text = wx.StaticText(panel, wx.ID_ANY, "Effettua il login poi seleziona le date di inizio e fine periodo delle fatture da gestire ed esegui un'azione")

        start_date_lbl = wx.StaticText(self, wx.ID_ANY, "Dal:")
        end_date_lbl = wx.StaticText(self, wx.ID_ANY, "Al:")
        self.start_date_picker = wx.adv.DatePickerCtrl(panel, dt=wx.DateTime.Today().SetDay(1))
        self.end_date_picker = wx.adv.DatePickerCtrl(panel, dt=wx.DateTime.Today())
        date_sizer.Add(start_date_lbl, 0, wx.ALL|wx.CENTER, 2)
        date_sizer.Add(self.start_date_picker, 1, wx.ALL|wx.CENTER, 2)
        date_sizer.Add(end_date_lbl, 0, wx.ALL|wx.CENTER, 2)
        date_sizer.Add(self.end_date_picker, 1, wx.ALL|wx.CENTER, 2)
        self.start_date_picker.Disable()
        self.end_date_picker.Disable()

        self.login_btn = wx.Button(panel, LOGIN_ACTION, "Login")
        self.login_btn.SetDefault()
        self.login_btn.Bind(wx.EVT_BUTTON, self.btn_onclick)

        self.logout_btn = wx.Button(panel, LOGOUT_ACTION, "Logout")
        self.logout_btn.Hide()
        self.logout_btn.Bind(wx.EVT_BUTTON, self.btn_onclick)

        self.download_btn = wx.Button(panel, DOWNLOAD_ACTION, "Scarica Fatture")
        btn_sizer.Add(self.download_btn, 0, wx.ALL|wx.CENTER, 2)
        self.download_btn.Bind(wx.EVT_BUTTON, self.btn_onclick)
        self.download_btn.Disable()

        self.traf2000_btn = wx.Button(panel, CONVERT_ACTION, "Genera TRAF2000")
        btn_sizer.Add(self.traf2000_btn, 0, wx.ALL|wx.CENTER, 2)
        self.traf2000_btn.Bind(wx.EVT_BUTTON, self.btn_onclick)
        self.traf2000_btn.Disable()

        self.main_sizer.Add(title_text, 0, wx.ALL|wx.CENTER, 2)
        self.main_sizer.Add(desc_text, 0, wx.ALL|wx.CENTER, 2)
        self.main_sizer.Add(self.login_btn, 0, wx.ALL|wx.CENTER, 4)
        self.main_sizer.Add(self.logout_btn, 0, wx.ALL|wx.CENTER, 4)
        self.main_sizer.Add(date_sizer, 0, wx.ALL|wx.EXPAND, 2)
        self.main_sizer.Add(btn_sizer, 0, wx.ALL|wx.CENTER, 2)

        panel.SetSizerAndFit(self.main_sizer)

        self.Show()

    def enable_on_login(self):
        """enable and show what needed after login"""
        self.download_btn.Enable()
        self.traf2000_btn.Enable()
        self.start_date_picker.Enable()
        self.end_date_picker.Enable()
        self.login_btn.Hide()
        self.logout_btn.Show()
        self.main_sizer.Layout()

    def disable_on_logout(self):
        """disable and hide what needed after logout"""
        self.download_btn.Disable()
        self.traf2000_btn.Disable()
        self.start_date_picker.Disable()
        self.end_date_picker.Disable()
        self.login_dlg.disconnect()
        self.logout_btn.Hide()
        self.login_btn.Show()
        self.main_sizer.Layout()

    def btn_onclick(self, event):
        """event raised when a button is clicked"""
        btn_id = event.GetEventObject().GetId()

        if btn_id not in (LOGIN_ACTION, LOGOUT_ACTION, DOWNLOAD_ACTION, CONVERT_ACTION):
            #TODO: error
            return
        elif btn_id == LOGIN_ACTION:
            self.login_dlg.ShowModal()
            if self.login_dlg.logged_in:
                self.enable_on_login()
            return
        elif btn_id == LOGOUT_ACTION:
            self.disable_on_logout()
            return
        elif not self.login_dlg.logged_in:
            #TODO: error
            return

        start_date = self.start_date_picker.GetValue().Format("%d/%m/%Y")
        end_date = self.end_date_picker.GetValue().Format("%d/%m/%Y")
        input_file_url = 'https://report.casadicurasanrossore.it:8443/reportserver?/STAT_FATTURATO_CTERZI&dataI='+start_date+'&dataF='+end_date+'&rs:Format='
        input_file_url += ('EXCELOPENXML' if btn_id == DOWNLOAD_ACTION else 'XML' if btn_id == CONVERT_ACTION else None)

        downloaded_input_file = self.session.get(input_file_url)
        if downloaded_input_file.status_code != 200:
            #TODO: error
            return

        input_file_descriptor, self.input_file_path = tempfile.mkstemp(suffix=('.xlsx' if btn_id == DOWNLOAD_ACTION else '.xml' if btn_id == CONVERT_ACTION else None))
        self.input_files.append(self.input_file_path)
        with open(input_file_descriptor, 'wb') as input_file:
            input_file.write(downloaded_input_file.content)

        try:
            self.input_file_ext = file_extension(self.input_file_path, (".xml", ".csv", ".xlsx"))
        except exc.NoFileError as handled_exception:
            print(handled_exception.args[0])
            return
        except exc.NoFileExtensionError as handled_exception:
            print(handled_exception.args[0])
            return
        except exc.WrongFileExtensionError as handled_exception:
            print(handled_exception.args[0])
            return

        if btn_id == DOWNLOAD_ACTION:
            self.log_dialog = LogDialog(self, "Download delle fatture dal portale CCSR", DOWNLOAD_ACTION)
            self.log_dialog.Show()
            downloader.download_invoices(self)
            self.log_dialog.btn.Enable()

        elif btn_id == CONVERT_ACTION:
            self.log_dialog = LogDialog(self, "Conversione delle fatture in TRAF2000", CONVERT_ACTION)
            self.log_dialog.Show()
            #TODO: error frame
            try:
                traf2000_converter.convert(self)
            except exc.NoFileError as handled_exception:
                print(handled_exception.args[0])
            except exc.NoFileExtensionError as handled_exception:
                print(handled_exception.args[0])
            except exc.WrongFileExtensionError as handled_exception:
                print(handled_exception.args[0])
            self.log_dialog.btn.Enable()

    def exit_handler(self):
        """clean the environment befor exiting"""
        for input_file in self.input_files:
            os.remove(input_file)

if __name__ == "__main__":
    app = wx.App()
    FattureCCSRFrame(None, "Utility FattureCCSR")
    app.MainLoop()
