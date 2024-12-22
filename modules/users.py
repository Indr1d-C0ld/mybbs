# modules/users.py
import sqlite3
import bcrypt
import time
import logging  # Importa il modulo logging
import shutil

class UsersManager:
    def __init__(self, conn):
        self.conn = conn

    def add_user(self, username, password, role='user'):
        c = self.conn.cursor()
        phash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        try:
            c.execute(
                "INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",
                (username, phash.decode('utf-8'), role)
            )
            self.conn.commit()
            logging.info(f"Utente '{username}' aggiunto con ruolo '{role}'.")
            return True
        except sqlite3.IntegrityError:
            logging.warning(f"Tentativo di aggiungere un utente esistente: '{username}'.")
            return False
        except Exception as e:
            logging.error(f"Errore aggiungendo utente '{username}': {e}")
            return False

    def authenticate(self, username, password):
        c = self.conn.cursor()
        try:
            c.execute(
                "SELECT id, password_hash FROM users WHERE username=?",
                (username,)
            )
            row = c.fetchone()
            if row:
                ph = row['password_hash'].encode('utf-8')
                if bcrypt.checkpw(password.encode('utf-8'), ph):
                    logging.info(f"Utente '{username}' autenticato con successo.")
                    return row['id']
            logging.warning(f"Autenticazione fallita per utente '{username}'.")
            return None
        except Exception as e:
            logging.error(f"Errore durante l'autenticazione di '{username}': {e}")
            return None

    def get_role(self, user_id):
        c = self.conn.cursor()
        try:
            c.execute(
                "SELECT role FROM users WHERE id=?",
                (user_id,)
            )
            row = c.fetchone()
            if row:
                logging.debug(f"Ruolo dell'utente ID {user_id}: {row['role']}")
                return row['role']
            logging.warning(f"Nessun ruolo trovato per utente ID {user_id}.")
            return 'user'
        except Exception as e:
            logging.error(f"Errore ottenendo il ruolo per utente ID {user_id}: {e}")
            return 'user'

    def handle_private_message(self, line, user_id):
        c = self.conn.cursor()
        parts = line.split(' ', 1)
        cmd = parts[0].upper() if parts else ''
        arg = parts[1] if len(parts) > 1 else ''
        try:
            if cmd == 'LIST':
                # Lista messaggi privati non letti
                c.execute("""
                    SELECT pm.id, u.username AS sender, pm.timestamp 
                    FROM private_messages pm 
                    JOIN users u ON pm.from_id = u.id 
                    WHERE pm.to_id = ? AND pm.read_flag = 0 
                    ORDER BY pm.id DESC
                """, (user_id,))
                rows = c.fetchall()
                out = ""
                for r in rows:
                    out += f"ID:{r['id']} Da:{r['sender']} Data:{r['timestamp']}\n"
                logging.debug(f"Utente ID {user_id} ha richiesto la lista dei messaggi privati non letti.")
                return out + "OK End\n"

            elif cmd == 'READ':
                # PMSG READ <id>
                if not arg:
                    logging.warning("Comando READ senza ID.")
                    return "ERR READ <id>\n"
                msg_id = arg
                c.execute("""
                    SELECT pm.id, u.username AS sender, pm.timestamp, pm.body 
                    FROM private_messages pm 
                    JOIN users u ON pm.from_id = u.id 
                    WHERE pm.id = ? AND pm.to_id = ?
                """, (msg_id, user_id))
                row = c.fetchone()
                if row:
                    c.execute("UPDATE private_messages SET read_flag = 1 WHERE id = ?", (msg_id,))
                    self.conn.commit()
                    logging.info(f"Utente ID {user_id} ha letto il messaggio privato ID {msg_id}.")
                    return f"From:{row['sender']} At:{row['timestamp']}\n{row['body']}\nOK\n"
                else:
                    logging.warning(f"Messaggio privato ID {msg_id} non trovato per utente ID {user_id}.")
                    return "ERR Not found\n"

            elif cmd == 'WRITE':
                # PMSG WRITE <username>|<body>
                if '|' not in arg:
                    logging.warning("Comando WRITE con formato errato.")
                    return "ERR Format: WRITE user|body\n"
                try:
                    logging.debug(f"Divido arg: {arg}")
                    user, body = arg.split('|', 1)
                    logging.debug(f"Utente destinatario: {user}, Corpo: {body}")
                    # Trovare user_id
                    c.execute("SELECT id FROM users WHERE username = ?", (user,))
                    u = c.fetchone()
                    if not u:
                        logging.warning(f"Tentativo di inviare messaggio a utente inesistente: '{user}'.")
                        return "ERR User not found\n"
                    to_id = u['id']
                    ts = time.strftime("%Y-%m-%d %H:%M:%S")
                    c.execute("""
                        INSERT INTO private_messages(from_id, to_id, timestamp, body) 
                        VALUES (?, ?, ?, ?)
                    """, (user_id, to_id, ts, body))
                    self.conn.commit()
                    logging.info(f"Utente ID {user_id} ha inviato un messaggio privato a ID {to_id}.")
                    return "OK Message sent\n"
                except Exception as e:
                    logging.error(f"Errore gestendo WRITE: {e}")
                    return "ERR Server error\n"
            else:
                logging.warning(f"Comando privato sconosciuto: '{cmd}'.")
                return "ERR Unknown subcommand\n"
        except Exception as e:
            logging.error(f"Errore gestendo messaggi privati per utente ID {user_id}: {e}")
            return "ERR Server error\n"

    def handle_admin_command(self, line):
        c = self.conn.cursor()
        parts = line.split(' ')
        cmd = parts[0].lower() if parts else ''
        try:
            if cmd == 'adduser':
                if len(parts) < 2:
                    logging.warning("Comando adduser senza username.")
                    return "ERR adduser <username>\n"
                username = parts[1]
                pw = "admin123"  # In un vero sistema, si dovrebbe richiedere all'admin
                success = self.add_user(username, pw, role='admin')
                if success:
                    logging.info(f"Admin ha aggiunto l'utente '{username}'.")
                    return f"OK User {username} added with default pw 'admin123'\n"
                else:
                    logging.error(f"Admin ha fallito nell'aggiungere l'utente '{username}'.")
                    return "ERR Could not add user\n"

            elif cmd == 'deluser':
                if len(parts) < 2:
                    logging.warning("Comando deluser senza username.")
                    return "ERR deluser <username>\n"
                username = parts[1]
                success = self.delete_user(username)
                if success:
                    logging.info(f"Admin ha eliminato l'utente '{username}'.")
                    return f"OK User {username} deleted\n"
                else:
                    logging.error(f"Admin ha fallito nell'eliminare l'utente '{username}'.")
                    return "ERR Could not delete user\n"

            elif cmd == 'listusers':
                c.execute("SELECT username, role FROM users")
                rows = c.fetchall()
                out = ""
                for r in rows:
                    out += f"{r['username']} ({r['role']})\n"
                logging.debug("Admin ha richiesto la lista degli utenti.")
                return out + "OK\n"

            elif cmd == 'promote':
                if len(parts) < 2:
                    logging.warning("Comando promote senza username.")
                    return "ERR promote <username>\n"
                username = parts[1]
                success = self.promote_user(username)
                if success:
                    logging.info(f"Admin ha promosso l'utente '{username}' a admin.")
                    return f"OK {username} is now admin\n"
                else:
                    logging.error(f"Admin ha fallito nel promuovere l'utente '{username}'.")
                    return "ERR Could not promote user\n"

            elif cmd == 'demote':
                if len(parts) < 2:
                    logging.warning("Comando demote senza username.")
                    return "ERR demote <username>\n"
                username = parts[1]
                success = self.demote_user(username)
                if success:
                    logging.info(f"Admin ha retrocesso l'utente '{username}' a user.")
                    return f"OK {username} is now user\n"
                else:
                    logging.error(f"Admin ha fallito nel retrocedere l'utente '{username}'.")
                    return "ERR Could not demote user\n"

            else:
                logging.warning(f"Comando admin sconosciuto: '{cmd}'.")
                return "ERR Unknown admin command\n"
        except Exception as e:
            logging.error(f"Errore gestendo comandi admin: {e}")
            return "ERR Server error\n"

    def delete_user(self, username):
        c = self.conn.cursor()
        try:
            c.execute("DELETE FROM users WHERE username = ?", (username,))
            if c.rowcount == 0:
                logging.warning(f"Utente '{username}' non trovato per la rimozione.")
                return False
            self.conn.commit()
            logging.info(f"Utente '{username}' rimosso dal database.")
            return True
        except Exception as e:
            logging.error(f"Errore rimuovendo utente '{username}': {e}")
            return False

    def promote_user(self, username):
        c = self.conn.cursor()
        try:
            c.execute("UPDATE users SET role = 'admin' WHERE username = ?", (username,))
            if c.rowcount == 0:
                logging.warning(f"Utente '{username}' non trovato per la promozione.")
                return False
            self.conn.commit()
            logging.info(f"Utente '{username}' promosso a admin.")
            return True
        except Exception as e:
            logging.error(f"Errore promuovendo utente '{username}': {e}")
            return False

    def demote_user(self, username):
        c = self.conn.cursor()
        try:
            c.execute("UPDATE users SET role = 'user' WHERE username = ?", (username,))
            if c.rowcount == 0:
                logging.warning(f"Utente '{username}' non trovato per la retrocessione.")
                return False
            self.conn.commit()
            logging.info(f"Utente '{username}' retrocesso a user.")
            return True
        except Exception as e:
            logging.error(f"Errore retrocedendo utente '{username}': {e}")
            return False

    def list_users(self):
        c = self.conn.cursor()
        try:
            c.execute("SELECT username, role FROM users")
            rows = c.fetchall()
            return rows
        except Exception as e:
            logging.error(f"Errore recuperando la lista degli utenti: {e}")
            return None

    def backup_database(self, backup_path):
        try:
            c = self.conn.cursor()
            c.execute("PRAGMA database_list")
            db_info = c.fetchone()
            if db_info and db_info[2]:  # db_info[2] è il file path
                db_path = db_info[2]
                shutil.copy2(db_path, backup_path)
                logging.info(f"Backup del database creato in '{backup_path}'.")
                return True
            else:
                logging.error("Impossibile ottenere il percorso del database.")
                return False
        except Exception as e:
            logging.error(f"Errore creando il backup del database: {e}")
            return False

