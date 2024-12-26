import sqlite3
import bcrypt
import logging
import time
import shutil

class UsersManager:
    def __init__(self, conn):
        self.conn = conn

    def add_user(self, username, password, role='user'):
        c = self.conn.cursor()
        phash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        try:
            c.execute("""
                INSERT INTO users(username, password_hash, role)
                VALUES (?, ?, ?)
            """, (username, phash.decode('utf-8'), role))
            self.conn.commit()
            logging.info(f"Creato utente '{username}', ruolo={role}.")
            return True
        except sqlite3.IntegrityError:
            logging.warning(f"Utente '{username}' già esistente.")
            return False
        except Exception as e:
            logging.error(f"Errore add_user '{username}': {e}")
            return False

    def authenticate(self, username, password):
        c = self.conn.cursor()
        try:
            c.execute("SELECT id, password_hash FROM users WHERE username=?", (username,))
            row = c.fetchone()
            if row:
                ph = row['password_hash'].encode('utf-8')
                if bcrypt.checkpw(password.encode('utf-8'), ph):
                    return row['id']
            return None
        except Exception as e:
            logging.error(f"Errore authenticate '{username}': {e}")
            return None

    def get_role(self, user_id):
        c = self.conn.cursor()
        try:
            c.execute("SELECT role FROM users WHERE id=?", (user_id,))
            row = c.fetchone()
            if row:
                return row['role']
            return 'user'
        except Exception as e:
            logging.error(f"Errore get_role user_id={user_id}: {e}")
            return 'user'

    def handle_private_message(self, line, user_id):
        # (Come già implementato, con LIST, READ, WRITE)
        # ...
        pass

    def handle_admin_command(self, line):
        parts = line.split(' ')
        cmd = parts[0].lower() if parts else ''
        try:
            if cmd == 'adduser':
                # ADMIN adduser <username>
                if len(parts) < 2:
                    return "ERR adduser <username>\n"
                username = parts[1]
                pw = "admin123"
                ok = self.add_user(username, pw, role='admin')
                if ok:
                    return f"OK User {username} added with default pw 'admin123'\n"
                else:
                    return "ERR Could not add user\n"

            elif cmd == 'adduser-nonadmin':
                if len(parts) < 2:
                    return "ERR adduser-nonadmin <username>\n"
                username = parts[1]
                pw = "user123"
                ok = self.add_user(username, pw, role='user')
                if ok:
                    return f"OK User {username} added with default pw 'user123'\n"
                else:
                    return "ERR Could not add user\n"

            elif cmd == 'deluser':
                if len(parts) < 2:
                    return "ERR deluser <username>\n"
                username = parts[1]
                self.delete_user(username)
                return f"OK User {username} deleted\n"

            elif cmd == 'promote':
                if len(parts) < 2:
                    return "ERR promote <username>\n"
                username = parts[1]
                self.promote_user(username)
                return f"OK {username} is now admin\n"

            elif cmd == 'demote':
                if len(parts) < 2:
                    return "ERR demote <username>\n"
                username = parts[1]
                self.demote_user(username)
                return f"OK {username} is now user\n"

            elif cmd == 'listusers':
                rows = self.list_users()
                out = ""
                for r in rows:
                    out += f"{r['username']} ({r['role']})\n"
                return out + "OK\n"

            elif cmd == 'backup':
                # ADMIN backup <path>?
                if len(parts) > 1:
                    backup_path = ' '.join(parts[1:])
                else:
                    backup_path = '/opt/mybbs/data/database_backup.db'
                ok = self.backup_database(backup_path)
                if ok:
                    return f"OK Backup done in '{backup_path}'\n"
                else:
                    return "ERR Backup failed\n"

            else:
                return "ERR Unknown admin command\n"
        except Exception as e:
            logging.error(f"Errore handle_admin_command: {e}")
            return "ERR Server error\n"

    def change_password(self, user_id, arg):
        if '|' not in arg:
            return "ERR Formato: PASSWD <oldpw>|<newpw>\n"
        oldpw, newpw = arg.split('|', 1)
        c = self.conn.cursor()
        try:
            c.execute("SELECT username, password_hash FROM users WHERE id=?", (user_id,))
            row = c.fetchone()
            if not row:
                return "ERR Utente non trovato\n"
            username = row['username']
            phash = row['password_hash'].encode('utf-8')
            if not bcrypt.checkpw(oldpw.encode('utf-8'), phash):
                return "ERR Vecchia password non corretta\n"
            new_hash = bcrypt.hashpw(newpw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            c.execute("UPDATE users SET password_hash=? WHERE id=?", (new_hash, user_id))
            self.conn.commit()
            return "OK Password aggiornata\n"
        except Exception as e:
            logging.error(f"Errore change_password user_id={user_id}: {e}")
            return "ERR Server error\n"

    # Metodi di supporto admin CLI
    def delete_user(self, username):
        c = self.conn.cursor()
        try:
            c.execute("DELETE FROM users WHERE username=?", (username,))
            self.conn.commit()
        except Exception as e:
            logging.error(f"Errore delete_user '{username}': {e}")

    def promote_user(self, username):
        c = self.conn.cursor()
        try:
            c.execute("UPDATE users SET role='admin' WHERE username=?", (username,))
            self.conn.commit()
        except Exception as e:
            logging.error(f"Errore promote_user '{username}': {e}")

    def demote_user(self, username):
        c = self.conn.cursor()
        try:
            c.execute("UPDATE users SET role='user' WHERE username=?", (username,))
            self.conn.commit()
        except Exception as e:
            logging.error(f"Errore demote_user '{username}': {e}")

    def list_users(self):
        c = self.conn.cursor()
        c.execute("SELECT username, role FROM users")
        rows = c.fetchall()
        return rows

    def backup_database(self, backup_path):
        try:
            c = self.conn.cursor()
            c.execute("PRAGMA database_list")
            row = c.fetchone()
            if row and row[2]:
                db_path = row[2]
                shutil.copy2(db_path, backup_path)
                return True
            return False
        except Exception as e:
            logging.error(f"Errore backup DB: {e}")
            return False

