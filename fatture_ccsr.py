"""This script prompts for downloading or converting to TRAF2000 from a .csv or .xml report file"""

import sys
import os

import wx

import converter
import utilities

class FattureCCSRFrame(wx.Frame):
    def __init__(self, parent, title):
        super(FattureCCSRFrame, self).__init__(parent, title=title, size=(500, 150))
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)

        self.input_file_picker = wx.FilePickerCtrl(panel, 101, "", "Seleziona il .csv o .xml", "*.csv;*.xml")
        hbox1.Add(self.input_file_picker, 1, wx.EXPAND, 0)

        self.download_btn = wx.Button(panel, 201, "Scarica Fatture")
        hbox2.Add(self.download_btn, 0, wx.ALIGN_CENTER)
        self.download_btn.Bind(wx.EVT_BUTTON, self.btn_onclick)

        self.traf2000_btn = wx.Button(panel, 202, "Genera TRAF2000")
        hbox2.Add(self.traf2000_btn, 0, wx.ALIGN_CENTER)
        self.traf2000_btn.Bind(wx.EVT_BUTTON, self.btn_onclick)

        vbox.Add(hbox1, 0, wx.EXPAND)
        vbox.Add(hbox2, 0, wx.ALIGN_CENTER_HORIZONTAL)

        panel.SetSizer(vbox)

        self.Centre()
        self.Show()

    def btn_onclick(self, event):
        btn_id = event.GetEventObject().GetId()
        if btn_id == 202:
            input_file_path = utilities.get_input_file("*.csv;*.xml")
            if input_file_path is None:
                sys.exit("ERROR: No input file selected!")

            fatture_file_extension = os.path.splitext(input_file_path)[1]

            output_file_path = utilities.get_output_file("TRAF2000")
            if output_file_path is None:
                sys.exit("ERROR: No output file selected!")

            if fatture_file_extension == ".csv":
                fatture = converter.import_csv(input_file_path)

            elif fatture_file_extension == ".xml":
                fatture = converter.import_xml(input_file_path)

            else:
                sys.exit("ERROR: file extension not supported")

            converter.convert(fatture, output_file_path)


if __name__ == "__main__":
    app = wx.App()
    FattureCCSRFrame(None, "Utility FattureCCSR")
    app.MainLoop()
