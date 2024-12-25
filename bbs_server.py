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

# Configurazione per socket TCP
HOST = '0.0.0.0'
PORT = 12345

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
        
        # Manager vari
        self.users = UsersManager(self.conn)
        self.board = BoardManager(self.conn)
        self.chat = ChatManager(self.conn)
        self.files = FilesManager(self.conn)
        self.textlib = TextLib('/opt/mybbs/data/docs')

        # sessions: session_id -> {"user_id": <int>, "username": <str>}
        self.sessions = {}
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

                logging.debug(f"[{addr}] -> Comando ricevuto: {line}")
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
                            logging.info(f"[{addr}] Utente '{username}' autenticato. session_id={session_id}")
                        else:
                            out.write("ERR Invalid credentials\n")

                elif cmd == 'LOGOUT':
                    if session_id in self.sessions:
                        del self.sessions[session_id]
                        logging.info(f"[{addr}] session_id={session_id} -> Logout.")
                    out.write("OK Logged out\n")
                    session_id = None
                    user_id = None

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

                        elif cmd == 'CHAT':
                            # *** ECCO LA CORREZIONE CRUCIALE ***
                            # Recuperiamo tutto ciò che segue "CHAT" in un'unica stringa:
                            if len(parts) > 1:
                                subcmd_line = ' '.join(parts[1:])
                            else:
                                subcmd_line = ''
                            response = self.chat.handle_command(subcmd_line, user_id)
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
                                response = self.users.change_password(user_id, arg)
                                out.write(response)

                        elif cmd == 'WHO':
                            out.write(self.list_connected_users())

                        elif cmd == 'WHOAMI':
                            uname = self.sessions[session_id]['username']
                            out.write(f"OK {uname}\n")

                        else:
                            out.write("ERR Unknown command\n")

                    except Exception as e:
                        logging.error(f"Errore elaborando '{line}' per user_id={user_id}: {e}")
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
    parser = argparse.ArgumentParser(description="Server BBS Testuale")
    parser.add_argument('--adduser', help='Aggiunge un utente admin')
    args = parser.parse_args()

    server = BBSServer()

    if args.adduser:
        import getpass
        pw = getpass.getpass(f"Password per l'utente admin '{args.adduser}': ")
        server.users.add_user(args.adduser, pw, role='admin')
        sys.exit(0)

    server.start_socket()
    logging.info("BBS Server in esecuzione.")
    print("BBS Server in esecuzione.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()

