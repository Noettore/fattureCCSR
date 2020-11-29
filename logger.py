"""Create logging handler"""
import logging

#_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

downloader_logger = logging.getLogger("downloader")
downloader_logger.setLevel(logging.DEBUG)

converter_logger = logging.getLogger("converter")
converter_logger.setLevel(logging.DEBUG)
#_converter_ch = logging.StreamHandler()
#_converter_ch.setFormatter(_formatter)
#converter_logger.addHandler(_converter_ch)

note_credito_logger = logging.getLogger("note_credito")
note_credito_logger.setLevel(logging.INFO)
#_note_credito_ch = logging.StreamHandler()
#_note_credito_ch.setFormatter(_formatter)
#note_credito_logger.addHandler(_note_credito_ch)
