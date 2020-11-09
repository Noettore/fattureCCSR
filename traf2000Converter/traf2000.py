"""This script ask for an input file and an output file and generates the TRAF2000 records from a .csv or .xml"""

import sys
import os
import wx

import fatture_import
import traf2000_convert

def get_input_file(wildcard):
    """Return the input file path"""
    _ = wx.App(None)
    style = wx.FD_OPEN | wx.FD_FILE_MUST_EXIST
    dialog = wx.FileDialog(None, "Scegli il .csv o .xml contenente le informazioni sulle fatture da importare", wildcard=wildcard, style=style)
    if dialog.ShowModal() == wx.ID_OK:
        path = dialog.GetPath()
    else:
        path = None
    dialog.Destroy()
    return path

def get_output_file(default_output_filename):
    """Return the output file path"""
    _ = wx.App(None)
    style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
    dialog = wx.FileDialog(None, "Scegli dove salvare il file TRAF2000", defaultFile=default_output_filename, style=style)
    if dialog.ShowModal() == wx.ID_OK:
        path = dialog.GetPath()
    else:
        path = None
    dialog.Destroy()
    return path

input_file_path = get_input_file("*.csv;*.xml")
if input_file_path is None:
    sys.exit("ERROR: No input file selected!")

fattureFileExtension = os.path.splitext(input_file_path)[1]

output_file_path = get_output_file("TRAF2000")
if output_file_path is None:
    sys.exit("ERROR: No output file selected!")

if fattureFileExtension == ".csv":
    fatture = fatture_import.import_csv(input_file_path)

elif fattureFileExtension == ".xml":
    fatture = fatture_import.import_xml(input_file_path)

else:
    sys.exit("ERROR: file extension not supported")

traf2000_convert.convert(fatture, output_file_path)
