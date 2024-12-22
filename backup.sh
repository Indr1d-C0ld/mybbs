#!/bin/bash

# Definire il percorso del server BBS e dello script
BBS_SERVER="/opt/mybbs/bbs_server.py"
BACKUP_DIR="/opt/mybbs/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="database_backup_$TIMESTAMP.db"

# Eseguire il backup utilizzando lo script del server BBS
sudo -u bbsuser python3 $BBS_SERVER --backup "$BACKUP_DIR/$BACKUP_FILE"

# Verificare se il backup è stato creato con successo
if [ $? -eq 0 ]; then
    echo "Backup effettuato con successo: $BACKUP_FILE"
else
    echo "Errore durante il backup del database."
fi

# Opzionale: Eliminare backup più vecchi di 30 giorni
find $BACKUP_DIR -type f -name "database_backup_*.db" -mtime +30 -exec rm {} \;

