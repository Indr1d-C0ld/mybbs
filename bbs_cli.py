#!/usr/bin/env python3
import socket
import sys
import os
import getpass
import argparse
import time

DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 12345

def send_cmd(sock, cmd):
    try:
        sock.sendall((cmd + "\n").encode('utf-8'))
    except Exception as e:
        print(f"Errore inviando il comando: {e}")
        sys.exit(1)

    response = []
    while True:
        try:
            data = sock.recv(4096)
            if not data:
                break
            rx = data.decode('utf-8')
            response.extend(rx.split('\n'))
            if any(r.startswith('OK') or r.startswith('ERR') for r in response):
                break
        except Exception as e:
            print(f"Errore ricevendo la risposta: {e}")
            sys.exit(1)
    return response

def get_role(sock):
    """
    Richiede al server il ruolo dell'utente corrente (admin o user).
    """
    resp = send_cmd(sock, "ROLE")
    for r in resp:
        if r.startswith("OK "):
            return r.split(' ', 1)[1]  # "admin" o "user"
    return "user"  # fallback

def admin_menu(sock):
    """
    Menu dedicato agli admin, con comandi di gestione BBS.
    """
    while True:
        print("\n=== Admin Panel ===")
        print("[1] Aggiungi utente admin")
        print("[2] Aggiungi utente non-admin")
        print("[3] Rimuovi utente")
        print("[4] Promuovi utente ad admin")
        print("[5] Revoca admin da utente")
        print("[6] Lista utenti registrati")
        print("[7] Backup database")
        print("[back] Torna indietro")

        choice = input("> ").strip().lower()
        if choice == '1':
            username = input("Username admin da creare: ")
            # Esegui: ADMIN adduser <username>
            # user creato con default pw=admin123
            out = send_cmd(sock, f"ADMIN adduser {username}")
            for r in out:
                if r.strip():
                    print(r)
        elif choice == '2':
            username = input("Username non-admin: ")
            out = send_cmd(sock, f"ADMIN adduser-nonadmin {username}")
            # NOTA: Nel server, non c'è "adduser-nonadmin" di default. 
            # Possiamo interpretare con 'role=user' e opportune funzioni. 
            # Per semplicità, potremmo in handle_admin_command implementare 
            # "addusernonadmin" ...
            # Oppure usiamo client-side un hack: user creato con password predefinita.
            # In un contesto più ampio, modificheremo handle_admin_command. 
            for r in out:
                if r.strip():
                    print(r)
        elif choice == '3':
            username = input("Username da rimuovere: ")
            out = send_cmd(sock, f"ADMIN deluser {username}")
            for r in out:
                if r.strip():
                    print(r)
        elif choice == '4':
            username = input("Username da promuovere: ")
            out = send_cmd(sock, f"ADMIN promote {username}")
            for r in out:
                if r.strip():
                    print(r)
        elif choice == '5':
            username = input("Username da demotare: ")
            out = send_cmd(sock, f"ADMIN demote {username}")
            for r in out:
                if r.strip():
                    print(r)
        elif choice == '6':
            out = send_cmd(sock, "ADMIN listusers")
            for r in out:
                if r.strip():
                    print(r)
        elif choice == '7':
            # Esegui backup
            path = input("Percorso backup (Invio per default): ").strip()
            if path:
                out = send_cmd(sock, f"ADMIN backup {path}")
            else:
                out = send_cmd(sock, "ADMIN backup")
            for r in out:
                if r.strip():
                    print(r)
        elif choice == 'back':
            return
        else:
            print("Opzione non valida.")

def main_menu(sock, role):
    while True:
        print("\n[1] Bacheca Messaggi")
        print("[2] Chat Pubblica")
        print("[3] Messaggi Privati")
        print("[4] Archivio File")
        print("[5] Archivio Testuale")
        print("[6] Cambio Password")
        print("[7] Utenti Connessi")
        if role == 'admin':
            print("[8] Admin Panel")
        print("[Q] Esci")

        c = input("Seleziona opzione: ").strip().lower()
        if c == '1':
            board_menu(sock)
        elif c == '2':
            chat_loop(sock)
        elif c == '3':
            pmsg_menu(sock)
        elif c == '4':
            file_menu(sock)
        elif c == '5':
            text_menu(sock)
        elif c == '6':
            change_password(sock)
        elif c == '7':
            who_is_online(sock)
        elif c == '8' and role == 'admin':
            admin_menu(sock)
        elif c == 'q':
            send_cmd(sock, 'LOGOUT')
            print("Disconnesso dalla BBS.")
            sys.exit(0)
        else:
            print("Opzione non valida.")

def board_menu(sock):
    # Invariato rispetto alle versioni precedenti
    while True:
        print("\nBacheca Messaggi:")
        print("[n] Nuovo messaggio")
        print("[l] Lista")
        print("[r <id>] Leggi")
        print("[reply <id>] Rispondi")
        print("[back] Indietro")

        line = input("> ").strip()
        if line == 'back':
            return
        elif line == 'n':
            subject = input("Oggetto: ")
            print("Inserisci corpo. Termina con riga vuota:")
            lines = []
            while True:
                l = input()
                if l.strip() == '':
                    break
                lines.append(l)
            body = "\n".join(lines)
            out = send_cmd(sock, f"BOARD NEW {subject}|{body}")
        elif line == 'l':
            out = send_cmd(sock, "BOARD LIST")
        elif line.startswith('r '):
            msg_id = line.split(' ', 1)[1]
            out = send_cmd(sock, f"BOARD READ {msg_id}")
        elif line.startswith('reply '):
            msg_id = line.split(' ', 1)[1]
            subject = input("Oggetto: ")
            print("Inserisci corpo. Termina con riga vuota:")
            lines = []
            while True:
                l = input()
                if l.strip() == '':
                    break
                lines.append(l)
            body = "\n".join(lines)
            out = send_cmd(sock, f"BOARD REPLY {msg_id}|{subject}|{body}")
        else:
            print("Comando non valido.")
            out = []
        
        for r in out:
            if r.strip():
                print(r)

def chat_loop(sock):
    REFRESH_INTERVAL = 5
    chat_lines = []

    print("\n=== Chat Pubblica ===")
    print("Digita '/quit' per uscire.")
    print("Aggiornamento ogni TOT secondi, ultime 30 righe. /msg <utente> <testo> per privato.")

    while True:
        os.system('clear' if os.name != 'nt' else 'cls')

        resp = send_cmd(sock, "CHAT RECV")
        new_lines = []
        for r in resp:
            if r.startswith("OK") or r.startswith("ERR") or not r.strip():
                continue
            new_lines.append(r)
        chat_lines = new_lines
        if len(chat_lines) > 30:
            chat_lines = chat_lines[-30:]

        print("=== Chat (ultimi 30 msg) ===")
        for line in chat_lines:
            print(line)

        msg = input("(Invio per saltare, /quit per uscire)\n> ").strip()
        if msg.lower() == '/quit':
            return
        elif msg.startswith('/msg '):
            _, remainder = msg.split(' ', 1)
            send_cmd(sock, f"CHAT SENDPRIVATE {remainder}")
        elif msg:
            send_cmd(sock, f"CHAT SEND {msg}")

        time.sleep(REFRESH_INTERVAL)

def pmsg_menu(sock):
    while True:
        print("\nMessaggi Privati:")
        print("[l] Lista msg non letti")
        print("[r <id>] Leggi")
        print("[w <user>] Scrivi")
        print("[back] Indietro")

        line = input("> ").strip()
        if line == 'back':
            return
        elif line == 'l':
            out = send_cmd(sock, "PMSG LIST")
        elif line.startswith('r '):
            pid = line.split(' ', 1)[1]
            out = send_cmd(sock, f"PMSG READ {pid}")
        elif line.startswith('w '):
            user = line.split(' ', 1)[1]
            print("Testo del messaggio, termina con riga vuota:")
            lines = []
            while True:
                l = input()
                if l.strip() == '':
                    break
                lines.append(l)
            body = "\n".join(lines)
            out = send_cmd(sock, f"PMSG WRITE {user}|{body}")
        else:
            out = ["ERR Comando non valido."]
        
        for r in out:
            if r.strip():
                print(r)

def file_menu(sock):
    while True:
        print("\nArchivio File:")
        print("[l] Lista")
        print("[info <id>] Info file")
        print("[register <filename> \"descr\" public|private] Registra file")
        print("[back] Indietro")

        line = input("> ").strip()
        if line == 'back':
            return
        elif line == 'l':
            out = send_cmd(sock, "FILE LIST")
        elif line.startswith('info '):
            fid = line.split(' ', 1)[1]
            out = send_cmd(sock, f"FILE INFO {fid}")
        elif line.startswith('register '):
            parts = line.split(' ', 3)
            if len(parts) < 4:
                out = ["ERR Uso: register <filename> \"descr\" public|private"]
            else:
                filename = parts[1]
                rest = parts[2] + ' ' + parts[3]
                import re
                m = re.match(r'^"([^"]+)"\s+(public|private)$', rest)
                if not m:
                    out = ["ERR Formato descr/vis"]
                else:
                    desc = m.group(1)
                    vis = m.group(2)
                    out = send_cmd(sock, f"FILE REGISTER {filename}|{desc}|{vis}")
        else:
            out = ["ERR Comando non valido"]

        for r in out:
            if r.strip():
                print(r)

def text_menu(sock):
    while True:
        print("\nArchivio Testuale:")
        print("[l] Lista documenti")
        print("[r <filename>] Leggi documento")
        print("[back] Indietro")

        line = input("> ").strip()
        if line == 'back':
            return
        elif line == 'l':
            out = send_cmd(sock, "TEXT LIST")
        elif line.startswith('r '):
            fn = line.split(' ', 1)[1]
            out = send_cmd(sock, f"TEXT READ {fn}")
        else:
            out = ["ERR Comando non valido"]
        
        for r in out:
            if r.strip():
                print(r)

def change_password(sock):
    old_pw = getpass.getpass("Vecchia password: ")
    new_pw = getpass.getpass("Nuova password: ")
    resp = send_cmd(sock, f"PASSWD {old_pw}|{new_pw}")
    for r in resp:
        if r.strip():
            print(r)

def who_is_online(sock):
    resp = send_cmd(sock, "WHO")
    for r in resp:
        if r.strip():
            print(r)

def main():
    parser = argparse.ArgumentParser(description="Client BBS Testuale")
    parser.add_argument('--host', type=str, default=DEFAULT_HOST)
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    # Connetti al server
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((args.host, args.port))
    except Exception as e:
        print(f"Impossibile connettersi al server: {e}")
        sys.exit(1)

    f = sock.makefile('r')
    line = f.readline()
    if not line.startswith("OK"):
        print("Server non pronto.")
        sys.exit(1)

    # Login
    user = input("Username BBS: ")
    pw = getpass.getpass("Password BBS: ")
    sock.sendall(f"LOGIN {user} {pw}\n".encode('utf-8'))
    resp = f.readline().strip()
    if resp.startswith("ERR"):
        print("Credenziali non valide.")
        sys.exit(1)
    print("Login effettuato.")

    # Determina se l'utente è admin
    role = get_role(sock)
    if role == 'admin':
        print("Sei connesso come admin!")
    else:
        print("Sei connesso come utente (non-admin).")

    main_menu(sock, role)

if __name__ == "__main__":
    main()

