# modules/textlib.py
import os
import logging  # Importa il modulo logging

class TextLib:
    def __init__(self, doc_path='/opt/mybbs/data/docs'):
        self.doc_path = doc_path

    def handle_command(self, line):
        parts = line.strip().split(' ', 1)
        cmd = parts[0].upper() if parts else ''
        arg = parts[1].strip() if len(parts) > 1 else ''
        
        logging.debug(f"Comando TEXT ricevuto: cmd='{cmd}', arg='{arg}'")
        
        try:
            if cmd == 'LIST':
                docs = os.listdir(self.doc_path)
                out = ""
                for d in docs:
                    if d.endswith('.txt'):
                        out += d + "\n"
                logging.debug("Richiesta lista documenti testuali.")
                return out + "OK\n"

            elif cmd == 'READ':
                if not arg:
                    logging.warning("Comando READ senza filename.")
                    return "ERR READ <filename>\n"
                fn = arg
                path = os.path.join(self.doc_path, fn)
                logging.debug(f"Path completo del file da leggere: {path}")
                if not os.path.exists(path):
                    logging.warning(f"Documento '{fn}' non trovato.")
                    return "ERR Not found\n"
                try:
                    with open(path, 'r') as f:
                        data = f.read()
                    logging.info(f"Documento '{fn}' letto con successo.")
                    return data + "\nOK\n"
                except Exception as e:
                    logging.error(f"Errore leggendo documento '{fn}': {e}")
                    return "ERR Unable to read file\n"

            else:
                logging.warning(f"Comando TEXT sconosciuto: '{cmd}'.")
                return "ERR Unknown text command\n"
        except Exception as e:
            logging.error(f"Errore gestendo comandi textlib: {e}")
            return "ERR Server error\n"

