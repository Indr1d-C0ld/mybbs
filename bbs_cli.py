#!/usr/bin/env python3
import socket
import sys
import os
import getpass
import argparse

# Configurazione per connessione TCP
DEFAULT_HOST = '127.0.0.1'  # Cambia con l'IP del server BBS
DEFAULT_PORT = 12345        # Porta su cui il server BBS ascolta

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
            received = data.decode('utf-8')
            print(f"Ricevuto: {received}")  # Debug: mostra la risposta ricevuta
            response.extend(received.split('\n'))
            # Terminiamo quando riceviamo una linea che inizia con "OK" o "ERR"
            if any(line.startswith('OK') or line.startswith('ERR') for line in response):
                break
        except Exception as e:
            print(f"Errore ricevendo la risposta: {e}")
            sys.exit(1)
    return response

def main_menu(sock):
    while True:
        print("\n[1] Bacheca Messaggi\n[2] Chat Pubblica\n[3] Messaggi Privati\n[4] Archivio File\n[5] Archivio Testuale\n[Q] Esci")
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
        elif c == 'q':
            send_cmd(sock, 'LOGOUT')
            print("Disconnesso dalla BBS.")
            sys.exit(0)
        else:
            print("Opzione non valida.")

def board_menu(sock):
    while True:
        print("\nBacheca:\n[n] Nuovo messaggio\n[l] Lista\n[r <id>] Leggi\n[reply <id>] Rispondi\n[back] Indietro")
        line = input("> ").strip()
        if line == 'back':
            return
        elif line == 'n':
            subject = input("Oggetto: ")
            print("Inserire corpo. Terminare con riga vuota.")
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
            print("Inserire corpo. Terminare con riga vuota.")
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
        for ln in out:
            if ln:
                print(ln)

def chat_loop(sock):
    print("Chat pubblica. Scrivi '/quit' per uscire.")
    while True:
        out = send_cmd(sock, "CHAT RECV")
        for ln in out:
            if ln.startswith("OK") or ln.startswith("ERR"):
                continue
            print(ln)
        line = input("> ")
        if line == '/quit':
            return
        elif line.startswith('/msg '):
            out = send_cmd(sock, "CHAT SENDPRIVATE " + line[5:])
            for ln in out:
                if ln:
                    print(ln)
        else:
            out = send_cmd(sock, "CHAT SEND " + line)
            for ln in out:
                if ln:
                    print(ln)

def pmsg_menu(sock):
    while True:
        print("\nMessaggi Privati:\n[l] Lista msg non letti\n[r <id>] Leggi\n[w <user>] Scrivi\n[back] Indietro")
        line = input("> ").strip()
        if line == 'back':
            return
        elif line == 'l':
            out = send_cmd(sock, "PMSG LIST")
        elif line.startswith('r '):
            pid = line.split(' ', 1)[1]
            out = send_cmd(sock, "PMSG READ " + pid)
        elif line.startswith('w '):
            user = line.split(' ', 1)[1]
            print("Scrivi il testo, termina con riga vuota:")
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
        for ln in out:
            if ln:
                print(ln)

def file_menu(sock):
    while True:
        print("\nArchivio File:\n[l] Lista\n[info <id>] Info file\n[register <filename> \"descr\" public|private] Registra\n[back] Indietro")
        line = input("> ").strip()
        if line == 'back':
            return
        elif line == 'l':
            out = send_cmd(sock, "FILE LIST")
        elif line.startswith('info '):
            fid = line.split(' ', 1)[1]
            out = send_cmd(sock, "FILE INFO " + fid)
        elif line.startswith('register '):
            # register filename "desc" visibilità
            # es: register myfile.txt "un file di test" public
            parts = line.split(' ', 3)
            if len(parts) < 4:
                out = ["ERR formattazione: register <filename> \"descrizione\" public|private"]
            else:
                filename = parts[1]
                rest = parts[2] + ' ' + parts[3]
                # estrarre descrizione e visibilità
                import re
                m = re.match(r'^"([^"]+)"\s+(public|private)$', rest)
                if not m:
                    out = ["ERR Formato descrizione/visibilita"]
                else:
                    desc = m.group(1)
                    vis = m.group(2)
                    out = send_cmd(sock, f"FILE REGISTER {filename}|{desc}|{vis}")
        else:
            out = ["ERR Comando non valido"]
        for ln in out:
            if ln:
                print(ln)

def text_menu(sock):
    while True:
        print("\nArchivio Testuale:\n[l] Lista documenti\n[r <filename>] Leggi\n[back] Indietro")
        line = input("> ").strip()
        if line == 'back':
            return
        elif line == 'l':
            out = send_cmd(sock, "TEXT LIST")
        elif line.startswith('r '):
            fn = line.split(' ', 1)[1]
            out = send_cmd(sock, "TEXT READ " + fn)
        else:
            out = ["ERR Comando non valido"]
        for ln in out:
            if ln:
                print(ln)

def main():
    parser = argparse.ArgumentParser(description="Client BBS Testuale")
    parser.add_argument('--host', type=str, default=DEFAULT_HOST, help='Indirizzo IP del server BBS')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='Porta del server BBS')
    args = parser.parse_args()

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((args.host, args.port))
    except Exception as e:
        print(f"Impossibile connettersi al server BBS: {e}")
        sys.exit(1)

    f = sock.makefile('r')
    out_line = f.readline()
    if not out_line.startswith("OK"):
        print("Server non pronto.")
        sys.exit(1)

    # Login BBS
    user = input("Username BBS: ")
    pw = getpass.getpass("Password BBS: ")
    sock.sendall(f"LOGIN {user} {pw}\n".encode('utf-8'))
    resp = f.readline().strip()
    if resp.startswith("ERR"):
        print("Credenziali non valide.")
        sys.exit(1)
    print("Login effettuato.")

    main_menu(sock)

if __name__ == "__main__":
    main()

