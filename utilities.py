import wx

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