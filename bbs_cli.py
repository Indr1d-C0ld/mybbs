#!/usr/bin/env python3
import socket
import sys
import os
import getpass
import argparse

DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 12345

def send_cmd(sock, cmd):
    try:
        sock.sendall((cmd + "\n").encode('utf-8'))
        print(f"Comando inviato: {cmd}")
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
            print(f"Ricevuto: {rx}")
            response.extend(rx.split('\n'))
            if any(r.startswith('OK') or r.startswith('ERR') for r in response):
                break
        except Exception as e:
            print(f"Errore ricevendo la risposta: {e}")
            sys.exit(1)
    return response

def main_menu(sock):
    while True:
        print("\n[1] Bacheca Messaggi")
        print("[2] Chat Pubblica")
        print("[3] Messaggi Privati")
        print("[4] Archivio File")
        print("[5] Archivio Testuale")
        print("[6] Cambio Password")
        print("[7] Utenti Connessi")
        print("[Q] Esci")

        c = input("Seleziona opzione: ").strip().lower()
        if c == '2':
            chat_loop(sock)
        elif c == '3':
            pmsg_menu(sock)  # Se implementato
        elif c == '4':
            file_menu(sock)  # Se implementato
        elif c == '5':
            text_menu(sock)  # Se implementato
        elif c == '6':
            change_password(sock)
        elif c == '7':
            who_is_online(sock)
        elif c == 'q':
            send_cmd(sock, 'LOGOUT')
            print("Disconnesso dalla BBS.")
            sys.exit(0)
        else:
            print("Opzione non valida (demo).")

def chat_loop(sock):
    """
    Chat pubblica. Digita '/quit' per uscire.
    /msg <utente> <testo> per mandare msg privati via 'CHAT SENDPRIVATE'.
    """
    print("Entra in chat pubblica. Digita '/quit' per uscire.")
    print("NOTA: I messaggi in chat vengono aggiornati soltanto dopo aver premuto Invio o aver inviato un messaggio.")

    while True:
        # 1) Ricevi i messaggi correnti
        out_recv = send_cmd(sock, "CHAT RECV")
        for ln in out_recv:
            if ln.startswith("OK") or ln.startswith("ERR"):
                continue
            print(ln)

        line = input("> ")
        if line == '/quit':
            return

        if line.startswith('/msg '):
            # /msg <utente> <testo>
            cmd_part, remainder = line.split(' ', 1)
            out_send = send_cmd(sock, f"CHAT SENDPRIVATE {remainder}")
            for ln in out_send:
                if ln:
                    print(ln)
        else:
            out_send = send_cmd(sock, f"CHAT SEND {line}")
            for ln in out_send:
                if ln:
                    print(ln)

        # 2) Rileggiamo la chat per mostrare l'aggiornamento
        out_after = send_cmd(sock, "CHAT RECV")
        for ln in out_after:
            if ln.startswith("OK") or ln.startswith("ERR"):
                continue
            print(ln)

def change_password(sock):
    old_pw = getpass.getpass("Vecchia password: ")
    new_pw = getpass.getpass("Nuova password: ")
    out = send_cmd(sock, f"PASSWD {old_pw}|{new_pw}")
    for ln in out:
        if ln:
            print(ln)

def who_is_online(sock):
    out = send_cmd(sock, "WHO")
    for ln in out:
        if ln:
            print(ln)

# DEMO: placeholder per le sezioni non implementate (pmsg_menu, file_menu, text_menu)
def pmsg_menu(sock):
    print("Messaggi Privati - Funzione non implementata in questa demo.")

def file_menu(sock):
    print("Archivio File - Funzione non implementata in questa demo.")

def text_menu(sock):
    print("Archivio Testuale - Funzione non implementata in questa demo.")

def main():
    parser = argparse.ArgumentParser(description="Client BBS Testuale")
    parser.add_argument('--host', type=str, default=DEFAULT_HOST)
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    # Connessione
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
    print("Login effettuato!")

    main_menu(sock)

if __name__ == "__main__":
    main()

