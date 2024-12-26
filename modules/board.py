import time
import logging

class BoardManager:
    def __init__(self, conn):
        self.conn = conn

    def handle_command(self, cmd, arg, user_id):
        c = self.conn.cursor()
        try:
            if cmd == 'LIST':
                c.execute("""
                    SELECT b.id, u.username, b.timestamp, b.subject
                    FROM board_messages b
                    JOIN users u ON b.author_id = u.id
                    WHERE b.parent_id IS NULL
                    ORDER BY b.id DESC
                """)
                rows = c.fetchall()
                out = ""
                for r in rows:
                    out += f"{r['id']} [{r['subject']}] by {r['username']} at {r['timestamp']}\n"
                return out + "OK\n"

            elif cmd == 'READ':
                if not arg:
                    return "ERR Need id\n"
                msg_id = arg.strip()
                c.execute("""
                    SELECT b.id, u.username, b.timestamp, b.subject, b.body
                    FROM board_messages b
                    JOIN users u ON b.author_id = u.id
                    WHERE b.id=?
                """, (msg_id,))
                row = c.fetchone()
                if not row:
                    return "ERR Not found\n"
                out = f"ID:{row['id']} Subject:{row['subject']}\nAuthor:{row['username']} At:{row['timestamp']}\n{row['body']}\n"
                # Leggi eventuali reply
                c.execute("""
                    SELECT b.id, u.username, b.timestamp, b.subject, b.body
                    FROM board_messages b
                    JOIN users u ON b.author_id = u.id
                    WHERE b.parent_id=?
                    ORDER BY b.id
                """, (msg_id,))
                rep = c.fetchall()
                for rp in rep:
                    out += f"\n  >> Reply ID:{rp['id']} [{rp['subject']}] by {rp['username']} at {rp['timestamp']}\n{rp['body']}\n"
                return out + "OK\n"

            elif cmd == 'NEW':
                if '|' not in arg:
                    return "ERR Need subject|body\n"
                subject, body = arg.split('|', 1)
                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                c.execute("""
                    INSERT INTO board_messages(author_id, timestamp, subject, body, parent_id)
                    VALUES (?, ?, ?, ?, NULL)
                """, (user_id, ts, subject, body))
                self.conn.commit()
                return "OK Message posted\n"

            elif cmd == 'REPLY':
                if '|' not in arg:
                    return "ERR Need pid|subj|body\n"
                parts = arg.split('|', 2)
                if len(parts) < 3:
                    return "ERR Need pid|subj|body\n"
                pid, subject, body = parts
                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                c.execute("""
                    INSERT INTO board_messages(author_id, timestamp, subject, body, parent_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, ts, subject, body, pid))
                self.conn.commit()
                return "OK Reply posted\n"

            else:
                return "ERR Unknown BOARD command\n"

        except Exception as e:
            logging.error(f"BoardManager errore cmd={cmd}, user_id={user_id}: {e}")
            return "ERR Server error\n"

