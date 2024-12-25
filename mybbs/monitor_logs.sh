#!/bin/bash

# Script per monitorare i file di log utilizzando tmux

# Definire i file di log da monitorare
LOG_FILES=(
    "/opt/mybbs/bbs_server.log"
)

# Nome della sessione tmux
SESSION_NAME="bbs_logs"

# Funzione per verificare se un file esiste
file_exists() {
    if [ -f "$1" ]; then
        return 0
    else
        return 1
    fi
}

# Controllare se tmux è installato
if ! command -v tmux &> /dev/null
then
    echo "tmux non è installato. Installazione in corso..."
    sudo apt update
    sudo apt install -y tmux
    if [ $? -ne 0 ]; then
        echo "Errore durante l'installazione di tmux."
        exit 1
    fi
fi

# Controllare se la sessione tmux esiste già
tmux has-session -t $SESSION_NAME 2>/dev/null

if [ $? -eq 0 ]; then
    echo "Sessione tmux '$SESSION_NAME' esiste già. Attaccando..."
    tmux attach -t $SESSION_NAME
    exit 0
fi

# Creare una nuova sessione tmux in modalità detached
tmux new-session -d -s $SESSION_NAME -n "Server_Log"

# Iniziare a tailare il primo file nella finestra corrente
FIRST_LOG="${LOG_FILES[0]}"
if file_exists "$FIRST_LOG"; then
    tmux send-keys -t $SESSION_NAME:0 "tail -f '$FIRST_LOG'" C-m
else
    tmux send-keys -t $SESSION_NAME:0 "echo 'File non trovato: $FIRST_LOG'" C-m
fi

# Iterare sugli altri file di log e creare nuove finestre per ognuno
for i in "${!LOG_FILES[@]}"; do
    if [ $i -eq 0 ]; then
        continue  # Primo file già gestito
    fi
    LOG_FILE="${LOG_FILES[$i]}"
    WINDOW_NAME=$(basename "$LOG_FILE" | sed 's/\..*$//')  # Rimuove l'estensione
    
    tmux new-window -t $SESSION_NAME -n "$WINDOW_NAME"
    
    if file_exists "$LOG_FILE"; then
        tmux send-keys -t $SESSION_NAME:"$WINDOW_NAME" "tail -f '$LOG_FILE'" C-m
    else
        tmux send-keys -t $SESSION_NAME:"$WINDOW_NAME" "echo 'File non trovato: $LOG_FILE'" C-m
    fi
done

# Selezionare la prima finestra
tmux select-window -t $SESSION_NAME:0

# Attaccare alla sessione tmux
tmux attach -t $SESSION_NAME

