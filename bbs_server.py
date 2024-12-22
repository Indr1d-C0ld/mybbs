#!/usr/bin/env python3
import os
import sys
import sqlite3
import bcrypt
import time
import threading
import socket
import argparse
import logging  # Importa il modulo logging
from modules.users import UsersManager
from modules.board import BoardManager
from modules.chat import ChatManager
from modules.files import FilesManager
from modules.textlib import TextLib

# Configurazione per socket TCP
HOST = '0.0.0.0'  # Ascolta su tutte le interfacce di rete
PORT = 12345       # Porta di ascolto

# Configurazione del logging
LOG_FILE = '/opt/mybbs/bbs_server.log'
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

class BBSServer:
    def __init__(self, db_path='/opt/mybbs/data/database.db'):
        self.db_path = db_path
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            logging.info("Connessione al database SQLite stabilita.")
        except sqlite3.Error as e:
            logging.error(f"Errore nella connessione al database: {e}")
            sys.exit(1)
        
        self.users = UsersManager(self.conn)
        self.board = BoardManager(self.conn)
        self.chat = ChatManager(self.conn)
        self.files = FilesManager(self.conn)
        self.textlib = TextLib('/opt/mybbs/data/docs')  # Percorso assoluto
        self.sessions = {}  # session_id -> {user_id, ...}
        self.session_counter = 0
        self.socket_thread = None
        self.running = True

    def start_socket(self):
        try:
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_sock.bind((HOST, PORT))
            self.server_sock.listen(5)
            logging.info(f"BBS Server in ascolto su {HOST}:{PORT}")
            self.socket_thread = threading.Thread(target=self.accept_loop, daemon=True)
            self.socket_thread.start()
        except Exception as e:
            logging.error(f"Errore nell'avvio del socket: {e}")
            sys.exit(1)

    def accept_loop(self):
        while self.running:
            try:
                client, addr = self.server_sock.accept()
                logging.info(f"Connessione accettata da {addr}")
                threading.Thread(target=self.handle_client, args=(client, addr), daemon=True).start()
            except Exception as e:
                logging.error(f"Errore accettando connessione: {e}")

    def handle_client(self, client, addr):
        session_id = None
        user_id = None
        f = client.makefile('r')
        out = client.makefile('w')
        try:
            out.write("OK BBS READY\n")
            out.flush()
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(' ', 2)
                cmd = parts[0].upper()

                logging.debug(f"Ricevuto comando da {addr}: {line}")

                if cmd == 'LOGIN':
                    # LOGIN username password
                    if len(parts) < 3:
                        out.write("ERR Missing args\n")
                        logging.warning(f"LOGIN fallito per {addr}: args mancanti.")
                    else:
                        user, pw = parts[1], parts[2]
                        uid = self.users.authenticate(user, pw)
                        if uid:
                            self.session_counter += 1
                            session_id = self.session_counter
                            self.sessions[session_id] = {'user_id': uid, 'username': user}
                            user_id = uid
                            out.write("OK Logged in\n")
                            logging.info(f"Utente '{user}' autenticato da {addr}.")
                        else:
                            out.write("ERR Invalid credentials\n")
                            logging.warning(f"Autenticazione fallita per utente '{user}' da {addr}.")
                elif cmd == 'LOGOUT':
                    if session_id in self.sessions:
                        del self.sessions[session_id]
                        logging.info(f"Utente ID {user_id} disconnesso da {addr}.")
                    out.write("OK Logged out\n")
                    out.flush()
                    session_id = None
                    user_id = None
                elif user_id is None:
                    out.write("ERR Not logged in\n")
                    logging.warning(f"Comando non autorizzato da {addr}: {line}")
                else:
                    # Passare i comandi ai vari manager
                    try:
                        if cmd == 'WHOAMI':
                            out.write(f"OK {self.sessions[session_id]['username']}\n")
                        elif cmd == 'ROLE':
                            role = self.users.get_role(user_id)
                            out.write(f"OK {role}\n")
                        elif cmd == 'BOARD':
                            # Gestisce comandi come: BOARD LIST, BOARD NEW ecc.
                            if len(parts) < 2:
                                out.write("ERR Missing subcommand\n")
                            else:
                                scmd = parts[1].upper()
                                arg = parts[2] if len(parts) > 2 else None
                                response = self.board.handle_command(scmd, arg, user_id)
                                out.write(response)
                        elif cmd == 'CHAT':
                            # CHAT SEND <msg>
                            # CHAT RECV ...
                            subcmd_line = parts[1] if len(parts) > 1 else ''
                            response = self.chat.handle_command(subcmd_line, user_id)
                            out.write(response)
                        elif cmd == 'PMSG':
                            # PMSG SUBCMD ...
                            if len(parts) < 2:
                                out.write("ERR Missing subcommand\n")
                            else:
                                scmd = parts[1].upper()
                                arg = parts[2] if len(parts) > 2 else ''
                                # Passare l'intera stringa "WRITE test|Messaggio privato di prova."
                                response = self.users.handle_private_message(f"{scmd} {arg}", user_id)
                                out.write(response)
                        elif cmd == 'FILE':
                            # FILE SUBCMD ...
                            subcmd_line = parts[1] if len(parts) > 1 else ''
                            response = self.files.handle_command(subcmd_line, user_id)
                            out.write(response)
                        elif cmd == 'TEXT':
                            # TEXT SUBCMD ...
                            if len(parts) < 2:
                                out.write("ERR Missing subcommand\n")
                            else:
                                # Passare l'intera stringa "READ help.txt"
                                subcmd_line = ' '.join(parts[1:])  # Modifica effettuata qui
                                response = self.textlib.handle_command(subcmd_line)
                                out.write(response)
                        elif cmd == 'ADMIN':
                            # ADMIN SUBCMD...
                            # Controllo ruolo admin
                            if self.users.get_role(user_id) != 'admin':
                                out.write("ERR Not admin\n")
                                logging.warning(f"Accesso ADMIN negato per utente ID {user_id} da {addr}.")
                            else:
                                subcmd_line = parts[1] if len(parts) > 1 else ''
                                response = self.users.handle_admin_command(subcmd_line)
                                out.write(response)
                        else:
                            out.write("ERR Unknown command\n")
                            logging.warning(f"Comando sconosciuto da {addr}: {line}")
                    except Exception as e:
                        out.write("ERR Server error\n")
                        logging.error(f"Errore durante l'elaborazione del comando '{line}' da {addr}: {e}")
                out.flush()
        except Exception as e:
            logging.error(f"Errore durante la gestione del client {addr}: {e}")
        finally:
            client.close()
            logging.info(f"Connessione chiusa da {addr}.")

    def create_user(self, username, password, role='admin'):
        success = self.users.add_user(username, password, role)
        if success:
            logging.info(f"Utente '{username}' creato con ruolo '{role}'.")
        else:
            logging.error(f"Impossibile creare l'utente '{username}'.")

    def remove_user(self, username):
        success = self.users.delete_user(username)
        if success:
            logging.info(f"Utente '{username}' rimosso con successo.")
        else:
            logging.error(f"Impossibile rimuovere l'utente '{username}'.")

    def promote_user(self, username):
        success = self.users.promote_user(username)
        if success:
            logging.info(f"Utente '{username}' promosso a admin.")
        else:
            logging.error(f"Impossibile promuovere l'utente '{username}'.")

    def demote_user(self, username):
        success = self.users.demote_user(username)
        if success:
            logging.info(f"Utente '{username}' retrocesso a user.")
        else:
            logging.error(f"Impossibile retrocedere l'utente '{username}'.")

    def list_users(self):
        users = self.users.list_users()
        if users is not None:
            logging.info("Elenco degli utenti richiesto.")
            print("Lista degli utenti:")
            for user in users:
                print(f"{user['username']} ({user['role']})")
        else:
            logging.error("Impossibile recuperare la lista degli utenti.")

    def backup_database(self, backup_path='/opt/mybbs/data/database_backup.db'):
        success = self.users.backup_database(backup_path)
        if success:
            logging.info(f"Backup del database effettuato con successo in '{backup_path}'.")
            print(f"Backup del database effettuato in '{backup_path}'.")
        else:
            logging.error("Backup del database fallito.")
            print("Backup del database fallito.")

    def stop(self):
        self.running = False
        self.server_sock.close()
        logging.info("BBS Server fermato.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Server BBS Testuale")
    parser.add_argument('--adduser', help='Aggiunge un utente admin')
    parser.add_argument('--adduser-nonadmin', help='Aggiunge un utente non-admin')
    parser.add_argument('--deluser', help='Rimuove un utente')
    parser.add_argument('--promote', help='Promuove un utente a admin')
    parser.add_argument('--demote', help='Revoca lo status admin di un utente')
    parser.add_argument('--listusers', action='store_true', help='Lista degli utenti registrati')
    parser.add_argument('--backup', nargs='?', const='/opt/mybbs/data/database_backup.db', default=None, help='Backup del database (specifica il percorso opzionale)')
    args = parser.parse_args()

    server = BBSServer()

    # Gestione dei comandi amministrativi
    if args.adduser:
        import getpass
        pw = getpass.getpass(f"Inserire password per l'utente admin '{args.adduser}': ")
        server.create_user(args.adduser, pw, role='admin')
        print(f"Utente admin '{args.adduser}' creato.")
        sys.exit(0)
    
    if args.adduser_nonadmin:
        import getpass
        pw = getpass.getpass(f"Inserire password per l'utente '{args.adduser_nonadmin}': ")
        server.create_user(args.adduser_nonadmin, pw, role='user')
        print(f"Utente '{args.adduser_nonadmin}' creato come non-admin.")
        sys.exit(0)
    
    if args.deluser:
        server.remove_user(args.deluser)
        print(f"Utente '{args.deluser}' rimosso.")
        sys.exit(0)
    
    if args.promote:
        server.promote_user(args.promote)
        print(f"Utente '{args.promote}' promosso a admin.")
        sys.exit(0)
    
    if args.demote:
        server.demote_user(args.demote)
        print(f"Utente '{args.demote}' retrocesso a user.")
        sys.exit(0)
    
    if args.listusers:
        server.list_users()
        sys.exit(0)
    
    if args.backup is not None:
        backup_path = args.backup
        server.backup_database(backup_path)
        sys.exit(0)
    
    # Avvio del server se nessun comando amministrativo è stato fornito
    server.start_socket()
    logging.info("BBS Server in esecuzione.")
    print("BBS Server in esecuzione. Controlla il log per dettagli.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()

