"""This utility is used for downloading or converting to TRAF2000 invoices from a .csv or .xml report file"""

import os
import wx

import converter
import exc

class FattureCCSRFrame(wx.Frame):
    """main application frame"""
    def __init__(self, parent, title):
        self.input_file_path = None
        self.input_file_ext = None
        self.output_file_path = None

        super(FattureCCSRFrame, self).__init__(parent, title=title, size=(500, 150))
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)

        self.input_file_picker = wx.FilePickerCtrl(panel, 101, "", "Seleziona il .csv o .xml", "*.csv;*.xml", style=wx.FLP_DEFAULT_STYLE|wx.FLP_USE_TEXTCTRL)
        hbox1.Add(self.input_file_picker, 1, wx.EXPAND, 0)
        self.input_file_picker.Bind(wx.EVT_FILEPICKER_CHANGED, self.file_picker_changed)

        self.download_btn = wx.Button(panel, 201, "Scarica Fatture")
        hbox2.Add(self.download_btn, 0, wx.ALIGN_CENTER)
        self.download_btn.Bind(wx.EVT_BUTTON, self.btn_onclick)

        self.traf2000_btn = wx.Button(panel, 202, "Genera TRAF2000")
        hbox2.Add(self.traf2000_btn, 0, wx.ALIGN_CENTER)
        self.traf2000_btn.Bind(wx.EVT_BUTTON, self.btn_onclick)
        self.traf2000_btn.Disable()

        self.output_file_dialog = wx.FileDialog(panel, "Scegli dove salvare il file TRAF2000", defaultFile="TRAF2000", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)

        vbox.Add(hbox1, 0, wx.EXPAND)
        vbox.Add(hbox2, 0, wx.ALIGN_CENTER_HORIZONTAL)

        panel.SetSizer(vbox)

        self.Centre()
        self.Show()

    def file_picker_changed(self, event):
        """event raised when the input file path is changed"""
        self.input_file_path = event.GetEventObject().GetPath()
        if self.input_file_path in (None, ""):
            print("ERROR: No input file selected!")
            return
        self.input_file_ext = os.path.splitext(self.input_file_path)[1]
        if self.input_file_ext not in (".csv", ".xml"):
            print("ERROR: wrong file extension: " + self.input_file_ext)
            return
        self.traf2000_btn.Enable()

    def btn_onclick(self, event):
        """event raised when a button is clicked"""
        btn_id = event.GetEventObject().GetId()
        if btn_id == 202:
            if self.output_file_dialog.ShowModal() == wx.ID_OK:
                self.output_file_path = self.output_file_dialog.GetPath()
            try:
                converter.convert(self.input_file_path, self.output_file_path)
            except exc.WrongFileExtension as e:
                print(e.args[0])

if __name__ == "__main__":
    app = wx.App()
    FattureCCSRFrame(None, "Utility FattureCCSR")
    app.MainLoop()
