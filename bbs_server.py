#!/usr/bin/env python3
import os
import sys
import sqlite3
import bcrypt
import time
import threading
import socket
import argparse
import logging

from modules.users import UsersManager
from modules.board import BoardManager
from modules.chat import ChatManager
from modules.files import FilesManager
from modules.textlib import TextLib

HOST = '0.0.0.0'
PORT = 12345

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
            logging.error(f"Errore connessione DB: {e}")
            sys.exit(1)
        
        self.users = UsersManager(self.conn)
        self.board = BoardManager(self.conn)
        self.chat = ChatManager(self.conn)
        self.files = FilesManager(self.conn)
        self.textlib = TextLib('/opt/mybbs/data/docs')

        self.sessions = {}  # session_id -> {"user_id":..., "username":...}
        self.session_counter = 0
        self.running = True

    def start_socket(self):
        try:
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_sock.bind((HOST, PORT))
            self.server_sock.listen(5)
            logging.info(f"BBS Server in ascolto su {HOST}:{PORT}")
            threading.Thread(target=self.accept_loop, daemon=True).start()
        except Exception as e:
            logging.error(f"Errore avvio socket: {e}")
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

                logging.debug(f"[{addr}] -> Comando: {line}")
                parts = line.split(' ', 2)
                cmd = parts[0].upper()

                if cmd == 'LOGIN':
                    if len(parts) < 3:
                        out.write("ERR Missing args\n")
                    else:
                        username, pw = parts[1], parts[2]
                        uid = self.users.authenticate(username, pw)
                        if uid:
                            self.session_counter += 1
                            session_id = self.session_counter
                            self.sessions[session_id] = {'user_id': uid, 'username': username}
                            user_id = uid
                            out.write("OK Logged in\n")
                            logging.info(f"[{addr}] Utente '{username}' -> session_id={session_id}")
                        else:
                            out.write("ERR Invalid credentials\n")

                elif cmd == 'LOGOUT':
                    if session_id in self.sessions:
                        del self.sessions[session_id]
                        logging.info(f"[{addr}] Logout session_id={session_id}")
                    out.write("OK Logged out\n")
                    session_id = None
                    user_id = None

                elif cmd == 'ROLE':
                    # Fornisce il ruolo dell'utente
                    if user_id is None:
                        out.write("ERR Not logged in\n")
                    else:
                        role = self.users.get_role(user_id)
                        out.write(f"OK {role}\n")

                elif user_id is None:
                    out.write("ERR Not logged in\n")

                else:
                    # Utente autenticato
                    try:
                        if cmd == 'BOARD':
                            scmd = parts[1].upper() if len(parts) > 1 else ''
                            arg = parts[2] if len(parts) > 2 else None
                            response = self.board.handle_command(scmd, arg, user_id)
                            out.write(response)

                        elif cmd == 'PMSG':
                            scmd = parts[1].upper() if len(parts) > 1 else ''
                            arg = parts[2] if len(parts) > 2 else ''
                            response = self.users.handle_private_message(f"{scmd} {arg}", user_id)
                            out.write(response)

                        elif cmd == 'FILE':
                            subcmd_line = parts[1] if len(parts) > 1 else ''
                            response = self.files.handle_command(subcmd_line, user_id)
                            out.write(response)

                        elif cmd == 'TEXT':
                            if len(parts) < 2:
                                out.write("ERR Missing subcommand\n")
                            else:
                                subcmd_line = ' '.join(parts[1:])
                                response = self.textlib.handle_command(subcmd_line)
                                out.write(response)

                        elif cmd == 'CHAT':
                            if len(parts) > 1:
                                subcmd_line = ' '.join(parts[1:])
                            else:
                                subcmd_line = ''
                            response = self.chat.handle_command(subcmd_line, user_id)
                            out.write(response)

                        elif cmd == 'ADMIN':
                            role = self.users.get_role(user_id)
                            if role != 'admin':
                                out.write("ERR Not admin\n")
                            else:
                                subcmd_line = parts[1] if len(parts) > 1 else ''
                                response = self.users.handle_admin_command(subcmd_line)
                                out.write(response)

                        elif cmd == 'PASSWD':
                            if len(parts) < 2:
                                out.write("ERR Missing args\n")
                            else:
                                arg = parts[1]
                                resp = self.users.change_password(user_id, arg)
                                out.write(resp)

                        elif cmd == 'WHO':
                            out.write(self.list_connected_users())

                        elif cmd == 'WHOAMI':
                            uname = self.sessions[session_id]['username']
                            out.write(f"OK {uname}\n")

                        else:
                            out.write("ERR Unknown command\n")

                    except Exception as e:
                        logging.error(f"Errore elaborando '{line}' user_id={user_id}: {e}")
                        out.write("ERR Server error\n")

                out.flush()

        except Exception as e:
            logging.error(f"Errore generico con {addr}: {e}")
        finally:
            if session_id and session_id in self.sessions:
                del self.sessions[session_id]
                logging.info(f"[{addr}] session_id={session_id} -> disconnessione.")
            client.close()

    def list_connected_users(self):
        if not self.sessions:
            return "Nessun utente connesso.\nOK\n"
        out = "Utenti attualmente connessi:\n"
        for sid, info in self.sessions.items():
            out += f"- {info['username']}\n"
        return out + "OK\n"

    def stop(self):
        self.running = False
        self.server_sock.close()
        logging.info("BBS Server fermato.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Server BBS Testuale",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--adduser', help='Aggiunge un utente admin')
    parser.add_argument('--adduser-nonadmin', help='Aggiunge un utente non-admin')
    parser.add_argument('--deluser', help='Rimuove un utente')
    parser.add_argument('--promote', help='Promuove un utente a admin')
    parser.add_argument('--demote', help='Revoca lo status admin di un utente')
    parser.add_argument('--listusers', action='store_true', help='Lista degli utenti registrati')
    parser.add_argument('--backup', nargs='?', const='/opt/mybbs/data/database_backup.db', default=None,
                        help='Backup del database (percorso opzionale)')
    args = parser.parse_args()

    server = BBSServer()

    # Comandi admin da riga di comando
    if args.adduser:
        import getpass
        pw = getpass.getpass(f"Inserire password per l'utente admin '{args.adduser}': ")
        server.users.add_user(args.adduser, pw, role='admin')
        print(f"Utente admin '{args.adduser}' creato.")
        sys.exit(0)

    if args.adduser_nonadmin:
        import getpass
        pw = getpass.getpass(f"Inserire password per l'utente '{args.adduser_nonadmin}': ")
        server.users.add_user(args.adduser_nonadmin, pw, role='user')
        print(f"Utente '{args.adduser_nonadmin}' creato (non-admin).")
        sys.exit(0)

    if args.deluser:
        server.users.delete_user(args.deluser)
        print(f"Utente '{args.deluser}' rimosso.")
        sys.exit(0)

    if args.promote:
        server.users.promote_user(args.promote)
        print(f"Utente '{args.promote}' promosso a admin.")
        sys.exit(0)

    if args.demote:
        server.users.demote_user(args.demote)
        print(f"Utente '{args.demote}' revocato da admin.")
        sys.exit(0)

    if args.listusers:
        users = server.users.list_users()
        if users:
            print("Lista utenti registrati:")
            for u in users:
                print(f" - {u['username']} ({u['role']})")
        sys.exit(0)

    if args.backup is not None:
        backup_path = args.backup
        ok = server.users.backup_database(backup_path)
        if ok:
            print(f"Backup DB effettuato in '{backup_path}'")
        else:
            print("Backup DB fallito.")
        sys.exit(0)

    # Avvia il server
    server.start_socket()
    logging.info("BBS Server in esecuzione.")
    print("BBS Server in esecuzione.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()

