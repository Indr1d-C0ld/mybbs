### Struttura del progetto ###

mybbs/
├── backups
│   ├── backup.log
├── backup.sh
├── bbs_cli.py
├── bbs_server.log
├── bbs_server.py
├── bbs_server.sock
├── data
│   ├── database.db
│   └── docs
│       ├── help.txt
│       └── rules.txt
├── modules
│   ├── board.py
│   ├── chat.py
│   ├── files.py
│   ├── textlib.py
│   └── users.py
├── monitor_logs.sh
├── readme.txt
├── schema.sql
└── win_client
    ├── bbs_cli.bat
    └── bbs_cli.exe



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



### Finestra della chat: ### 

    Digitare messaggi e invio per parlare nella chat pubblica
    /msg <utente> <testo> per mandare un messaggio privato a utente
    /quit o CTRL+D per tornare indietro



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

    scp localfile.txt bbsuser@my-bbs-server.example.com:/home/bbsuser/uploads/ Poi dentro la BBS usa un comando :registerfile 
    localfile.txt "Descrizione" pubblico per rendere il file visibile agli altri.



### Archivio Testuale: ### 

    l : lista documenti
    r <filename> : leggi documento
    back



### Interfaccia Admin: ###

    Direttamente da riga di comando:

    sudo -u bbsuser python3 /opt/mybbs/bbs_server.py <opzione> 

    -h, --help                              Mostra questo messaggio di aiuto ed esce
    --adduser <username>                    Aggiunge un utente admin
    --adduser-nonadmin <username>           Aggiunge un utente non-admin
    --deluser <username>                    Rimuove un utente
    --promote <username>                    Promuove un utente a admin
    --demote <username>                     Revoca lo status admin di un utente
    --listusers                             Lista degli utenti registrati
    --backup <backup>                       Backup del database (specifica il percorso opzionale)
    
    Oppure direttamente da BBS se si ha status di *admin*: quando l'utente fa login, il client richiede
    il ruolo (ROLE) e, se è admin, mostra un menu aggiuntivo (voce [8] Admin Panel) accessibile solo agli admin:

    Aggiungere utenti (admin o non-admin)
    Rimuovere utenti
    Promuovere utenti ad admin
    Revocare admin (demote)
    Listare tutti gli utenti
    Fare il backup del database (chiamando internamente server.users.backup_database(...))

    NB: Per automatizzare il processo di backup, è possibile utilizzare lo script "backup,sh", che 
    esegue il backup utilizzando il comando già implementato nel server BBS. Questo script aggiungerà 
    anche un timestamp al nome del file di backup per identificarlo facilmente.
    
    Per aggiungere lo script a cron, come utente bbsuser:
    
    sudo crontab -u bbsuser -e

    Inserisci la seguente linea nel file crontab per eseguire il backup ogni giorno alle 2:00 AM:

    0 2 * * * /opt/mybbs/backup.sh >> /opt/mybbs/backups/backup.log 2>&1




### Prerequisiti: ### 

    Python 3 + libs, SQLite3, SSH Server, tmux (per lo script log monitor):
    sudo apt install python3 python3-pip sqlite3 openssh-server python3-bcrypt tmux
    Creazione dell’utente di sistema "bbsuser"
    


### Preparazione directory: ### 

    sudo mkdir -p /opt/mybbs/modules
    sudo mkdir -p /opt/mybbs/data/docs
    sudo mkdir -p /opt/mybbs/data/uploads
    cd /opt/mybbs



### Inizializzare il database: ### 

    sqlite3 data/database.db < schema.sql



### Crea un utente admin: ### 

    python3 bbs_server.py --adduser admin



### Crea l’utente di sistema e configura la shell bbs_cli: ### 

    sudo adduser --shell /opt/mybbs/bbs_cli.py bbsuser



### Dare i permessi di esecuzione a bbs_cli.py: ### 

    sudo chmod +x /opt/mybbs/bbs_cli.py

   (assicurarsi che bbs_cli.py abbia nella prima riga #!/usr/bin/env python3)



### Lanciare il server BBS come utente bbsuser: ### 

    Assicurati che il server BBS (bbs_server.py) stia girando con l'utente corretto, bbsuser. Se il server è eseguito come 
    root o un altro utente, bbsuser potrebbe non avere i permessi per accedere al socket.

    Esempio: Esecuzione del Server come bbsuser:

    sudo -u bbsuser python3 /opt/mybbs/bbs_server.py &

    (oppure creare un servizio systemd ad hoc)



### Connettersi da un altro terminale: ### 

    ssh bbsuser@<ip_server> oppure il client Windows in /mybbs/win_client (editare prima il file bbs_cli.bat nella directory)



### Esempio di Utilizzo: ### 

    Avviare il server:
    sudo -u bbsuser python3 /opt/mybbs/bbs_server.py &

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
        [5] l per listare, r rules.txt per leggere.

    Uscire:
        [Q]



### *IMPORTANTE* ### 

Assicurati che la directory /opt/mybbs/ sia di proprietà di bbsuser o appartenga a un gruppo a cui bbsuser appartiene.

Comandi per Impostare i Permessi:

# Cambia proprietario della directory e del socket
sudo chown -R bbsuser:bbsuser /opt/mybbs/

# Assicurati che la directory abbia i permessi appropriati
sudo chmod -R 770 /opt/mybbs/



### Considerazioni sulla Sicurezza: ### 

    Permessi del Socket:

    Impostando i permessi del socket (/opt/mybbs/bbs_server.sock) a 660, garantisci che solo bbsuser e gli utenti del 
    gruppo bbsuser possano accedervi. Evita permessi troppo permissivi come 666, a meno che non sia strettamente necessario.
    


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
