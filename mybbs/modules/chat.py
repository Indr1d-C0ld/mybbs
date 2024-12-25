import time
import logging

class ChatManager:
    def __init__(self, conn):
        self.conn = conn
        self.messages = []  # Buffer in memoria per la chat pubblica

    def handle_command(self, line, user_id):
        """
        line: es. "SEND Hello?" o "RECV" o "SENDPRIVATE user ciao"
        """
        parts = line.strip().split(' ', 1)
        cmd = parts[0].upper() if parts else ''
        arg = parts[1] if len(parts) > 1 else ''
        logging.debug(f"[ChatManager] cmd={cmd}, arg={arg}, user_id={user_id}")

        try:
            if cmd == 'RECV':
                out = ""
                for m in self.messages:
                    out += m + "\n"
                return out + "OK\n"

            elif cmd == 'SEND':
                msg = arg.strip()
                if not msg:
                    logging.warning(f"Messaggio vuoto inviato in chat. user_id={user_id}")
                    return "OK\n"

                c = self.conn.cursor()
                c.execute("SELECT username FROM users WHERE id=?", (user_id,))
                row = c.fetchone()
                uname = row['username'] if row else '???'
                timestamp = time.strftime('%H:%M:%S')
                line_to_add = f"[{uname}] {msg} ({timestamp})"
                self.messages.append(line_to_add)
                logging.info(f"ChatManager: Utente '{uname}' ha inviato in chat: {msg}")
                return "OK\n"

            elif cmd == 'SENDPRIVATE':
                # /msg user msg
                if ' ' not in arg:
                    return "ERR SENDPRIVATE <user> <msg>\n"
                to_user, message = arg.split(' ', 1)

                c = self.conn.cursor()
                c.execute("SELECT id FROM users WHERE username=?", (to_user,))
                row = c.fetchone()
                if not row:
                    logging.warning(f"Destinatario '{to_user}' inesistente.")
                    return "ERR user not found\n"

                to_id = row['id']
                ts = time.strftime('%Y-%m-%d %H:%M:%S')
                c.execute("""
                    INSERT INTO private_messages(from_id, to_id, timestamp, body)
                    VALUES (?, ?, ?, ?)
                """, (user_id, to_id, ts, message))
                self.conn.commit()

                c.execute("SELECT username FROM users WHERE id=?", (user_id,))
                srow = c.fetchone()
                uname = srow['username'] if srow else '???'
                logging.info(f"ChatManager: '{uname}'(id={user_id}) -> privato a '{to_user}'(id={to_id}): {message}")
                return "OK Private message sent\n"

            else:
                logging.warning(f"Comando chat sconosciuto: '{cmd}' user_id={user_id}")
                return "ERR Unknown chat command\n"

        except Exception as e:
            logging.error(f"Errore chat user_id={user_id}: {e}")
            return "ERR Server error\n"

