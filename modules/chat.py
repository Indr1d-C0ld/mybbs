import time
import logging

class ChatManager:
    def __init__(self, conn):
        self.conn = conn
        self.messages = []

    def handle_command(self, line, user_id):
        parts = line.strip().split(' ', 1)
        cmd = parts[0].upper() if parts else ''
        arg = parts[1].strip() if len(parts) > 1 else ''

        try:
            if cmd == 'RECV':
                out = ""
                for m in self.messages:
                    out += m + "\n"
                return out + "OK\n"

            elif cmd == 'SEND':
                msg = arg.strip()
                if not msg:
                    return "OK\n"
                c = self.conn.cursor()
                c.execute("SELECT username FROM users WHERE id=?", (user_id,))
                row = c.fetchone()
                uname = row['username'] if row else '???'
                timestamp = time.strftime('%H:%M:%S')
                line_to_add = f"[{uname}] {msg} ({timestamp})"
                self.messages.append(line_to_add)
                return "OK\n"

            elif cmd == 'SENDPRIVATE':
                if ' ' not in arg:
                    return "ERR SENDPRIVATE <user> <msg>\n"
                to_user, message = arg.split(' ', 1)
                c = self.conn.cursor()
                c.execute("SELECT id FROM users WHERE username=?", (to_user,))
                row = c.fetchone()
                if not row:
                    return "ERR user not found\n"
                to_id = row['id']
                ts = time.strftime('%Y-%m-%d %H:%M:%S')
                c.execute("""
                    INSERT INTO private_messages(from_id, to_id, timestamp, body)
                    VALUES (?, ?, ?, ?)
                """, (user_id, to_id, ts, message))
                self.conn.commit()
                return "OK Private message sent\n"

            else:
                return "ERR Unknown chat command\n"

        except Exception as e:
            logging.error(f"Errore chat user_id={user_id}: {e}")
            return "ERR Server error\n"

