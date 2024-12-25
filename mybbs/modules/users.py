import sqlite3
import bcrypt
import logging
import time

class UsersManager:
    def __init__(self, conn):
        self.conn = conn

    def add_user(self, username, password, role='user'):
        c = self.conn.cursor()
        phash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        try:
            c.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",
                      (username, phash.decode('utf-8'), role))
            self.conn.commit()
            logging.info(f"UsersManager: Aggiunto utente '{username}', ruolo={role}.")
            return True
        except sqlite3.IntegrityError:
            logging.warning(f"Utente '{username}' esiste già.")
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
                phash = row['password_hash'].encode('utf-8')
                if bcrypt.checkpw(password.encode('utf-8'), phash):
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
        # Esempio di placeholder
        return "OK\n"

    def handle_admin_command(self, line):
        # Esempio placeholder
        return "OK\n"

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
            logging.info(f"UsersManager: Password aggiornata per '{username}'.")
            return "OK Password aggiornata\n"
        except Exception as e:
            logging.error(f"Errore cambio pw user_id={user_id}: {e}")
            return "ERR Server error\n"

    def backup_database(self, backup_path):
        return True

