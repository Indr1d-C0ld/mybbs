import os
import time
import logging

class FilesManager:
    def __init__(self, conn):
        self.conn = conn
        self.upload_dir = '/opt/mybbs/data/uploads'

    def handle_command(self, line, user_id):
        parts = line.strip().split(' ', 1)
        cmd = parts[0].upper() if parts else ''
        arg = parts[1].strip() if len(parts) > 1 else ''
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
                return out + "OK\n"

            elif cmd == 'INFO':
                if not arg:
                    return "ERR INFO <id>\n"
                fid = arg.strip()
                c.execute("""
                    SELECT f.id, u.username, f.filename, f.description, f.visibility
                    FROM files f
                    JOIN users u ON f.uploader_id = u.id
                    WHERE f.id=?
                """, (fid,))
                row = c.fetchone()
                if not row:
                    return "ERR Not found\n"
                out = (f"ID:{row['id']} File:{row['filename']}\n"
                       f"Uploader:{row['username']}\nVisibility:{row['visibility']}\nDescription:{row['description']}\n")
                return out + "OK\n"

            elif cmd == 'REGISTER':
                if '|' not in arg:
                    return "ERR REGISTER filename|desc|vis\n"
                filename, desc, vis = arg.split('|', 2)
                path = os.path.join(self.upload_dir, filename)
                if not os.path.exists(path):
                    return "ERR file not uploaded\n"
                c.execute("""
                    INSERT INTO files(uploader_id, filename, description, visibility)
                    VALUES (?, ?, ?, ?)
                """, (user_id, filename, desc, vis))
                self.conn.commit()
                return "OK File registered\n"

            else:
                return "ERR Unknown file command\n"

        except Exception as e:
            logging.error(f"Errore FilesManager user_id={user_id}: {e}")
            return "ERR Server error\n"

