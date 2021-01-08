"""This utility is used for downloading or converting to TRAF2000 invoices from a CCSR .xlsx, .csv or .xml report file"""

import os
import sys
import subprocess
import atexit
import wx
import wx.adv
import requests
import requests_ntlm

import downloader
import traf2000_converter

LOGIN_ACTION = 0
LOGOUT_ACTION = 1
DOWNLOAD_ACTION = 10
CONVERT_ACTION = 20

class FattureCCSRFrame(wx.Frame):
    """main application frame"""
    def __init__(self, *args, **kwds):
        atexit.register(self.exit_handler)

        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE | wx.FULL_REPAINT_ON_RESIZE | wx.TAB_TRAVERSAL
        wx.Frame.__init__(self, *args, **kwds)
        self.SetTitle("fattureCCSR")

        self._initial_locale = wx.Locale(wx.LANGUAGE_DEFAULT, wx.LOCALE_LOAD_DEFAULT)

        self.input_files = list()
        self.log_dialog = None
        self.session = requests.Session()

        self.panel = wx.Panel(self, wx.ID_ANY, style=wx.BORDER_NONE | wx.FULL_REPAINT_ON_RESIZE | wx.TAB_TRAVERSAL)
        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        title_lbl = wx.StaticText(self.panel, wx.ID_ANY, "Utility Fatture Casa di Cura San Rossore")
        title_lbl.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, 0, ""))
        self.main_sizer.Add(title_lbl, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 2)

        desc_lbl = wx.StaticText(self.panel, wx.ID_ANY, "Effettua il login poi seleziona le date di inizio e fine periodo delle fatture da gestire ed esegui un'azione")
        self.main_sizer.Add(desc_lbl, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 2)

        self.login_dlg = LoginDialog(self)
        self.output_traf2000_dialog = wx.FileDialog(self.panel, "Scegli dove salvare il file TRAF2000", defaultFile="TRAF2000", style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
        self.output_pdf_dialog = wx.FileDialog(self.panel, "Scegli dove salvare il .pdf con le fatture scaricate", defaultFile="fatture.pdf", style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)

        self.login_btn = wx.Button(self.panel, LOGIN_ACTION, "Login")
        self.login_btn.SetFocus()
        self.login_btn.Bind(wx.EVT_BUTTON, self.btn_onclick)
        self.main_sizer.Add(self.login_btn, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 2)

        self.logout_btn = wx.Button(self.panel, LOGOUT_ACTION, "Logout")
        self.logout_btn.Hide()
        self.logout_btn.Bind(wx.EVT_BUTTON, self.btn_onclick)
        self.main_sizer.Add(self.logout_btn, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 2)

        date_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.main_sizer.Add(date_sizer, 0, wx.ALL | wx.EXPAND, 2)

        start_date_lbl = wx.StaticText(self.panel, wx.ID_ANY, "Dal")
        date_sizer.Add(start_date_lbl, 0, wx.ALL, 2)

        self.start_date_picker = wx.adv.DatePickerCtrl(self.panel, wx.ID_ANY, dt=wx.DateTime.Today().SetDay(1))
        self.start_date_picker.Enable(False)
        date_sizer.Add(self.start_date_picker, 1, wx.ALL, 2)

        end_date_lbl = wx.StaticText(self.panel, wx.ID_ANY, "Al")
        date_sizer.Add(end_date_lbl, 0, wx.ALL, 2)

        self.end_date_picker = wx.adv.DatePickerCtrl(self.panel, wx.ID_ANY, dt=wx.DateTime.Today())
        self.end_date_picker.Enable(False)
        date_sizer.Add(self.end_date_picker, 1, wx.ALL, 2)

        action_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.main_sizer.Add(action_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 2)

        self.download_btn = wx.Button(self.panel, DOWNLOAD_ACTION, "Scarica Fatture")
        self.download_btn.Enable(False)
        self.download_btn.Bind(wx.EVT_BUTTON, self.btn_onclick)
        action_sizer.Add(self.download_btn, 0, wx.ALL, 2)

        self.traf2000_btn = wx.Button(self.panel, CONVERT_ACTION, "Genera TRAF2000")
        self.traf2000_btn.Enable(False)
        self.traf2000_btn.Bind(wx.EVT_BUTTON, self.btn_onclick)
        action_sizer.Add(self.traf2000_btn, 0, wx.ALL, 2)

        self.panel.SetSizer(self.main_sizer)

        self.main_sizer.Fit(self)
        self.Layout()
        self.Centre()

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
            pass
        elif btn_id == LOGIN_ACTION:
            self.login_dlg.ShowModal()
            if self.login_dlg.logged_in:
                self.enable_on_login()

        elif btn_id == LOGOUT_ACTION:
            self.disable_on_logout()

        elif not self.login_dlg.logged_in:
            pass

        elif btn_id == DOWNLOAD_ACTION:
            self.log_dialog = LogDialog(self, "Download delle fatture dal portale CCSR", DOWNLOAD_ACTION)
            self.log_dialog.Show()
            downloader.download_invoices(self)
            self.log_dialog.close_btn.Enable()

        elif btn_id == CONVERT_ACTION:
            self.log_dialog = LogDialog(self, "Conversione delle fatture in TRAF2000", CONVERT_ACTION)
            self.log_dialog.Show()
            traf2000_converter.convert(self)
            self.log_dialog.close_btn.Enable()

    def exit_handler(self):
        """clean the environment befor exiting"""
        for input_file in self.input_files:
            os.remove(input_file)

class LogDialog(wx.Dialog):
    """logging panel"""
    def __init__(self, parent, title, action):
        super(LogDialog, self).__init__(parent, wx.ID_ANY, title, style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        log_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.Add(log_sizer, 1, wx.ALL | wx.EXPAND, 2)

        self.log_text = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.HSCROLL | wx.TE_MULTILINE | wx.TE_READONLY)
        self.log_text.SetMinSize((500, 200))
        self.log_text.Bind(wx.EVT_TEXT, self.on_text_update)
        log_sizer.Add(self.log_text, 0, wx.ALL | wx.EXPAND, 2)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 2)

        self.close_btn = wx.Button(self, wx.ID_OK, "Chiudi")
        self.close_btn.Enable(False)
        btn_sizer.Add(self.close_btn, 0, wx.ALL, 2)

        if action == CONVERT_ACTION:
            self.nc_text = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.HSCROLL | wx.TE_MULTILINE | wx.TE_READONLY)
            self.nc_text.SetMinSize((250, 200))
            log_sizer.Add(self.nc_text, 0, wx.ALL | wx.EXPAND, 2)

        elif action == DOWNLOAD_ACTION:
            self.open_file_btn = wx.Button(self, wx.ID_ANY, "Apri pdf")
            self.open_file_btn.Bind(wx.EVT_BUTTON, self.open_pdf)
            self.open_file_btn.Enable(False)
            btn_sizer.Add(self.open_file_btn, 0, wx.ALL, 2)

        self.SetSizer(main_sizer)
        main_sizer.Fit(self)

        self.Layout()

    def on_text_update(self, event):
        """autoscroll on text update"""
        self.ScrollPages(-1)
        event.Skip()

    def open_pdf(self, _):
        """open a file with the default software"""
        file_path = self.GetParent().output_pdf_dialog.GetPath()
        if sys.platform == "win32":
            os.startfile(file_path) # pylint: disable=maybe-no-member
        else:
            opener = "open" if sys.platform == "darwin" else "xdg-open"
            subprocess.call([opener, file_path])

class LoginDialog(wx.Dialog):
    """login dialog for basic auth download"""
    def __init__(self, *args, **kwds):
        """constructor"""
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)
        self.SetTitle("Login")

        self.logged_in = False

        main_sizer = wx.BoxSizer(wx.VERTICAL)

        user_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.Add(user_sizer, 1, wx.ALL | wx.EXPAND, 2)

        user_lbl = wx.StaticText(self, wx.ID_ANY, "Username:")
        user_sizer.Add(user_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)

        self.username = wx.TextCtrl(self, wx.ID_ANY, "")
        self.username.SetMinSize((250, -1))
        user_sizer.Add(self.username, 0, wx.ALL | wx.EXPAND, 2)

        pass_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.Add(pass_sizer, 1, wx.ALL | wx.EXPAND, 2)

        pass_lbl = wx.StaticText(self, wx.ID_ANY, "Password:")
        pass_sizer.Add(pass_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 2)

        self.password = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_PASSWORD | wx.TE_PROCESS_ENTER)
        self.password.SetMinSize((250, -1))
        pass_sizer.Add(self.password, 0, wx.ALL | wx.EXPAND, 2)

        self.login_btn = wx.Button(self, wx.ID_ANY, "Login")
        self.login_btn.SetFocus()
        self.login_btn.Bind(wx.EVT_BUTTON, self.on_login)
        main_sizer.Add(self.login_btn, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 2)

        self.SetSizer(main_sizer)
        main_sizer.Fit(self)

        self.Layout()

    def disconnect(self):
        """close session and reset input fields"""
        self.GetParent().session.close()
        self.logged_in = False

    def on_login(self, _):
        """check credentials and login"""
        if self.username.GetValue() not in ("", None) and self.password.GetValue() not in ("", None):
            session = self.GetParent().session
            session.auth = requests_ntlm.HttpNtlmAuth("sr\\"+self.username.GetValue(), self.password.GetValue())
            if session.get('https://report.casadicurasanrossore.it:8443/Reports/browse/').status_code == 200:
                self.logged_in = True
                self.username.SetValue('')
                self.password.SetValue('')
                self.Close()

class FattureCCSR(wx.App):
    """main app"""
    def OnInit(self): # pylint: disable=invalid-name
        """execute on app initialization"""
        self.fatture_ccsr_frame = FattureCCSRFrame(None, wx.ID_ANY, "") # pylint: disable=attribute-defined-outside-init
        self.SetTopWindow(self.fatture_ccsr_frame)
        self.fatture_ccsr_frame.Show()
        return True

if __name__ == "__main__":
    fattureCCSR = FattureCCSR(0)
    fattureCCSR.MainLoop()
