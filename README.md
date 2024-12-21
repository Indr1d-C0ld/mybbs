
### Struttura del progetto: ###

/opt/mybbs/
|-- bbs_server.py        # Server BBS (demone)
|-- bbs_cli.py           # Client testuale (lanciato come shell)
|-- modules/
|   |-- __init__.py
|   |-- users.py
|   |-- board.py
|   |-- chat.py
|   |-- files.py
|   |-- textlib.py
|-- data/
|   |-- database.db
|   |-- docs/           # Documenti testuali
|   |   |-- rules.txt
|   |   |-- help.txt
|   |-- uploads/        # File caricati dagli utenti
|
|-- schema.sql
|-- README.md



### Il menu principale del client: ### 

    [1] Bacheca Messaggi
    [2] Chat Pubblica
    [3] Messaggi Privati
    [4] Archivio File
    [5] Archivio Testuale
    [Q] Esci



### Dentro la Bacheca: ### 

    n : nuovo messaggio
    l : lista messaggi
    r <id> : leggi messaggio con ID dato
    reply <id> : rispondi a un messaggio
    back : torna al menu precedente

Seleziona canale bacheca (es. 'generale'): generale
Posta nuovo messaggio? (Y/n): Y
Oggetto: Saluti
Corpo (termina con riga vuota):
Ciao a tutti, sono nuovo!

Messaggio pubblicato.



### Finestra della chat: ### 

    Digitare messaggi e invio per parlare nella chat pubblica
    /msg <utente> <testo> per mandare un messaggio privato a utente
    /quit o CTRL+D per tornare indietro

#main:
[user1]: Ciao a tutti!
[user2]: Ciao user1, come va?
...
/msg user2 ciao in privato
/quit per tornare al menu



### Messaggi Privati: ### 

    l : lista messaggi privati non letti
    r <id> : leggi messaggio privato
    w <utente> : scrivi messaggio privato a utente
    back : torna al menu



### Archivio File: ### 

    l : lista file
    info <id> : info su un file
    register <filename> "<descrizione>" public|private : registra un file precedentemente caricato via scp in uploads/
    back

Per scaricare un file già presente:

    L’utente esce dalla BBS (Q) e da terminale esterno scp bbsuser@my-bbs-server.example.com:/home/bbsuser/uploads/filename.txt .

Per caricare un file:

    scp localfile.txt bbsuser@my-bbs-server.example.com:/home/bbsuser/uploads/ Poi dentro la BBS usa un comando :registerfile localfile.txt "Descrizione" pubblico per rendere il file visibile agli altri.



### Archivio Testuale: ### 

    l : lista documenti
    r <filename> : leggi documento
    back



### Interfaccia Admin: ### 

    :adduser <username> : aggiunge un utente
    :deluser <username> : rimuove un utente
    :listusers : lista utenti
    :promote <username> : promuove utente ad admin
    :demote <username> : revoca admin
    back

    Comandi per:
        Creare/modificare/eliminare utenti.
        Moderare messaggi, bannare utenti.
        Caricare file di sistema.
        Manutenzione del database (backup).

L’amministratore può accedervi tramite un parametro speciale del client (bbs_cli --admin)



### Prerequisiti: ### 

    Python 3
    librerie Python: pip3 install bcrypt or sudo apt install python3-bcrypt
    SSH server attivo sul sistema Debian (openssh-server)
    (sudo apt install python3 python3-pip sqlite3 openssh-server python3-bcrypt)
    Creazione dell’utente di sistema bbsuser
    


### Preparazione directory: ### 

sudo mkdir -p /opt/mybbs/modules
sudo mkdir -p /opt/mybbs/data/docs
sudo mkdir -p /opt/mybbs/data/uploads
cd /opt/mybbs



### Inizializzare il database: ### 

sqlite3 data/database.db < schema.sql



### Crea un utente admin: ### 

python3 bbs_server.py --adduser admin
# Inserire password richiesta
# L'utente admin verrà creato con role=admin



### Crea l’utente di sistema e configura la shell bbs_cli: ### 

sudo adduser --shell /opt/mybbs/bbs_cli.py bbsuser
# Scegliere una password di sistema.
# Questa password serve per accedere via SSH con bbsuser@server
# Non è la stessa password di admin BBS (che è interna al sistema BBS).



### Dare i permessi di esecuzione a bbs_cli.py: ### 

sudo chmod +x /opt/mybbs/bbs_cli.py

(Assicurarsi che bbs_cli.py abbia nella prima riga #!/usr/bin/env python3)



### Lanciare il server BBS come utente bbsuser: ### 

Assicurati che il server BBS (bbs_server.py) stia girando con l'utente corretto, preferibilmente bbsuser. Se il server è eseguito come root o un altro utente, bbsuser potrebbe non avere i permessi per accedere al socket.

Esempio: Esecuzione del Server come bbsuser:

sudo -u bbsuser python3 /opt/mybbs/bbs_server.py &

(oppure creare un servizio systemd ad hoc)



### Connettersi da un altro terminale: ### 

ssh bbsuser@<ip_server>



### Esempio di Utilizzo: ### 

    Avviare il server:
    python3 bbs_server.py &

    Da un altro terminale:
    ssh bbsuser@<server>
    (inserire la password di sistema per l'utente bbsuser)

    Dentro la BBS:
    Username BBS: admin
    Password BBS: (quella scelta durante --adduser)
    Viene mostrato il menu principale.

    Pubblicare un messaggio nella bacheca:
        [1] Bacheca Messaggi
            n
            Oggetto: Test
            Corpo: Messaggio di prova
            (riga vuota)
            Viene confermato "OK Message posted"

    Visualizzare messaggi:
    l per listare, r <id> per leggere.

    Chat pubblica:
    [2] per entrare in chat. Digitare messaggi, /quit per uscire.

    Messaggi privati:
    [3] per entrare, w <utente> per scrivere a un utente.

    File:
    Prima caricare il file con scp:
    scp myfile.txt bbsuser@<server>:/opt/mybbs/data/uploads/
    Poi dentro la BBS:
    [4] Archivio File
    register myfile.txt "File di test" public
    l per listare i file.

    Archivio Testuale:
    [5]
    l per listare, r rules.txt per leggere.

    Uscire:
    [Q]



### *IMPORTANTE* ### 

### Modifica del Percorso del Socket e dei Permessi: ### 

È consigliabile spostare il socket in una directory a cui bbsuser ha accesso diretto, come /opt/mybbs/, invece di /tmp/. Inoltre, assicurati che il socket abbia i permessi corretti.

Modifica in bbs_server.py:

Cambia la variabile SOCKET_PATH da /tmp/bbs_server.sock a /opt/mybbs/bbs_server.sock.

# bbs_server.py
SOCKET_PATH = '/opt/mybbs/bbs_server.sock'

Dopo aver effettuato questa modifica, aggiungi una riga per impostare i permessi del socket in modo che solo bbsuser possa accedervi:

import os

# Dopo self.server_sock.bind(SOCKET_PATH)
os.chmod(SOCKET_PATH, 0o660)  # Permessi di lettura e scrittura per proprietario e gruppo

Assicurati che la directory /opt/mybbs/ sia di proprietà di bbsuser o appartenga a un gruppo a cui bbsuser appartiene.

Comandi per Impostare i Permessi:

# Cambia proprietario della directory e del socket
sudo chown -R bbsuser:bbsuser /opt/mybbs/

# Assicurati che la directory abbia i permessi appropriati
sudo chmod -R 770 /opt/mybbs/

Configurazione del Client:

Assicurati che il client (bbs_cli.py) stia tentando di connettersi al nuovo percorso del socket.

Modifica in bbs_cli.py:

Cambia la variabile SOCKET_PATH da /tmp/bbs_server.sock a /opt/mybbs/bbs_server.sock.

# bbs_cli.py
SOCKET_PATH='/opt/mybbs/bbs_server.sock'



### Considerazioni sulla Sicurezza: ### 

    Permessi del Socket:

    Impostando i permessi del socket a 660, garantisci che solo bbsuser e gli utenti del gruppo bbsuser possano accedervi. Evita permessi troppo permissivi come 666, a meno che non sia strettamente necessario.

    Chroot o Restrizioni SSH:

    Per maggiore sicurezza, potresti voler limitare ulteriormente ciò che gli utenti SSH possono fare. Ad esempio, puoi utilizzare ForceCommand in sshd_config per assicurarti che l'utente bbsuser possa eseguire solo il client BBS.

    Esempio di Configurazione sshd_config:

    Apri il file di configurazione:

sudo nano /etc/ssh/sshd_config

Aggiungi le seguenti righe alla fine del file:

Match User bbsuser
    ForceCommand /opt/mybbs/bbs_cli.py
    X11Forwarding no
    AllowTcpForwarding no
    PermitTTY yes

Riavvia il Servizio SSH:

sudo systemctl restart sshd

Questo assicura che quando bbsuser si connette via SSH, venga eseguito automaticamente il client BBS e non abbia accesso a una shell interattiva.



### Aggiornamenti al Codice (Opzionale) ### 

Per migliorare ulteriormente il sistema, puoi aggiungere controlli più rigidi sui permessi del socket direttamente nel codice del server.

Esempio di Aggiunta di Permessi nel Server:

# bbs_server.py
import os
import stat

# Dopo self.server_sock.bind(SOCKET_PATH)
os.chmod(SOCKET_PATH, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP)  # 660

Questo garantisce che il socket abbia sempre i permessi corretti indipendentemente dalle impostazioni predefinite del sistema.



### Test Manuale del Socket: ### 

Puoi usare socat o nc per verificare se il socket è accessibile.

Esempio con socat:

sudo apt install socat
socat - UNIX-CONNECT:/opt/mybbs/bbs_server.sock

Se tutto è configurato correttamente, dovresti vedere il messaggio di avvio dal server (OK BBS READY).



### *OPZIONALE* ### 

### Configurazione di un Servizio systemd (Consigliato): ### 

Per gestire il server BBS in modo più affidabile, puoi creare un servizio systemd che esegue bbs_server.py come bbsuser.

Crea il File di Servizio:

sudo nano /etc/systemd/system/bbs_server.service

Inserisci il Seguente Contenuto:

[Unit]
Description=Server BBS Testuale
After=network.target

[Service]
Type=simple
User=bbsuser
Group=bbsuser
ExecStart=/usr/bin/python3 /opt/mybbs/bbs_server.py
WorkingDirectory=/opt/mybbs
Restart=on-failure

[Install]
WantedBy=multi-user.target

Abilita e Avvia il Servizio:

sudo systemctl daemon-reload
sudo systemctl enable bbs_server.service
sudo systemctl start bbs_server.service

Verifica lo Stato del Servizio:

sudo systemctl status bbs_server.service

Assicurati che il servizio sia in esecuzione senza errori.