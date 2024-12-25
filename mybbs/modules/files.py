# modules/files.py
import os
import time
import logging  # Importa il modulo logging

class FilesManager:
    def __init__(self, conn):
        self.conn = conn
        self.upload_dir = '/opt/mybbs/data/uploads'  # Percorso assoluto

    def handle_command(self, line, user_id):
        parts = line.split(' ', 1)
        cmd = parts[0].upper() if parts else ''
        arg = parts[1] if len(parts) > 1 else ''
        c = self.conn.cursor()
        try:
            if cmd == 'LIST':
                c.execute("""
                    SELECT f.id, u.username, f.filename, f.visibility 
                    FROM files f 
                    JOIN users u ON f.uploader_id = u.id 
                    ORDER BY f.id
                """)
                rows = c.fetchall()
                out = ""
                for r in rows:
                    out += f"{r['id']} {r['filename']} by {r['username']} [{r['visibility']}]\n"
                logging.debug(f"Utente ID {user_id} ha richiesto la lista dei file.")
                return out + "OK\n"

            elif cmd == 'INFO':
                if not arg:
                    logging.warning("Comando INFO senza ID.")
                    return "ERR INFO <id>\n"
                fid = arg
                c.execute("""
                    SELECT f.id, u.username, f.filename, f.description, f.visibility 
                    FROM files f 
                    JOIN users u ON f.uploader_id = u.id 
                    WHERE f.id = ?
                """, (fid,))
                r = c.fetchone()
                if not r:
                    logging.warning(f"File ID {fid} non trovato.")
                    return "ERR Not found\n"
                out = f"ID:{r['id']} File:{r['filename']}\nUploader:{r['username']}\nVisibility:{r['visibility']}\nDescription:{r['description']}\n"
                logging.debug(f"Utente ID {user_id} ha richiesto info sul file ID {fid}.")
                return out + "OK\n"

            elif cmd == 'REGISTER':
                # REGISTER filename|desc|visibility
                if '|' not in arg:
                    logging.warning("Comando REGISTER con formato errato.")
                    return "ERR REGISTER filename|desc|vis\n"
                parts = arg.split('|')
                if len(parts) < 3:
                    logging.warning("Comando REGISTER con numero di argomenti insufficiente.")
                    return "ERR REGISTER filename|desc|vis\n"
                filename, desc, vis = parts
                # Controllare esistenza file
                path = os.path.join(self.upload_dir, filename)
                if not os.path.exists(path):
                    logging.warning(f"Tentativo di registrare file inesistente: '{filename}'.")
                    return "ERR file not uploaded\n"
                c.execute("""
                    INSERT INTO files(uploader_id, filename, description, visibility) 
                    VALUES (?, ?, ?, ?)
                """, (user_id, filename, desc, vis))
                self.conn.commit()
                logging.info(f"Utente ID {user_id} ha registrato il file '{filename}' con visibilità '{vis}'.")
                return "OK File registered\n"

            else:
                logging.warning(f"Comando file sconosciuto: '{cmd}'.")
                return "ERR Unknown file command\n"
        except Exception as e:
            logging.error(f"Errore gestendo comandi file per utente ID {user_id}: {e}")
            return "ERR Server error\n"

