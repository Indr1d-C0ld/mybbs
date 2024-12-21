# modules/chat.py
import time
import logging  # Importa il modulo logging

class ChatManager:
    def __init__(self, conn):
        self.conn = conn
        self.messages = []  # Buffer semplice in memoria

    def handle_command(self, line, user_id):
        parts = line.split(' ', 1)
        cmd = parts[0].upper() if parts else ''
        arg = parts[1] if len(parts) > 1 else ''
        try:
            if cmd == 'RECV':
                out = ""
                for m in self.messages:
                    out += f"{m}\n"
                logging.debug(f"Utente ID {user_id} ha richiesto la chat pubblica.")
                return out + "OK\n"

            elif cmd == 'SEND':
                # SEND <msg>
                msg = arg
                # Ottenere username dell'utente
                c = self.conn.cursor()
                c.execute("SELECT username FROM users WHERE id = ?", (user_id,))
                u = c.fetchone()
                uname = u['username'] if u else '???'
                timestamp = time.strftime('%H:%M:%S')
                line = f"[{uname}] {msg} ({timestamp})"
                self.messages.append(line)
                logging.info(f"Utente '{uname}' ha inviato un messaggio nella chat pubblica.")
                return "OK\n"

            elif cmd == 'SENDPRIVATE':
                # SENDPRIVATE user msg
                if ' ' not in arg:
                    logging.warning("Comando SENDPRIVATE con formato errato.")
                    return "ERR SENDPRIVATE <user> <msg>\n"
                to_user, msg = arg.split(' ', 1)
                c = self.conn.cursor()
                c.execute("SELECT id FROM users WHERE username = ?", (to_user,))
                row = c.fetchone()
                if not row:
                    logging.warning(f"Tentativo di inviare messaggio privato a utente inesistente: '{to_user}'.")
                    return "ERR user not found\n"
                to_id = row['id']
                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                c.execute("""
                    INSERT INTO private_messages(from_id, to_id, timestamp, body) 
                    VALUES (?, ?, ?, ?)
                """, (user_id, to_id, ts, msg))
                self.conn.commit()
                logging.info(f"Utente ID {user_id} ha inviato un messaggio privato a ID {to_id}.")
                return "OK Private message sent\n"

            else:
                logging.warning(f"Comando chat sconosciuto: '{cmd}'.")
                return "ERR Unknown chat command\n"
        except Exception as e:
            logging.error(f"Errore gestendo comandi chat per utente ID {user_id}: {e}")
            return "ERR Server error\n"

