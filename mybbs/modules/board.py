# modules/board.py
import time
import logging  # Importa il modulo logging

class BoardManager:
    def __init__(self, conn):
        self.conn = conn

    def handle_command(self, cmd, arg, user_id):
        c = self.conn.cursor()
        try:
            if cmd == 'LIST':
                c.execute("""
                    SELECT b.id, u.username, b.timestamp, b.subject 
                    FROM board_messages b 
                    JOIN users u ON b.author_id = u.id 
                    WHERE b.parent_id IS NULL 
                    ORDER BY b.id DESC
                """)
                rows = c.fetchall()
                out = ""
                for r in rows:
                    out += f"{r['id']} [{r['subject']}] by {r['username']} at {r['timestamp']}\n"
                logging.debug(f"Utente ID {user_id} ha richiesto la lista della bacheca.")
                return out + "OK\n"

            elif cmd == 'READ':
                if not arg:
                    logging.warning("Comando READ senza ID.")
                    return "ERR Need id\n"
                msg_id = arg.strip()
                c.execute("""
                    SELECT b.id, u.username, b.timestamp, b.subject, b.body 
                    FROM board_messages b 
                    JOIN users u ON b.author_id = u.id 
                    WHERE b.id = ?
                """, (msg_id,))
                row = c.fetchone()
                if not row:
                    logging.warning(f"Messaggio ID {msg_id} non trovato.")
                    return "ERR Not found\n"
                out = f"ID:{row['id']} Subject:{row['subject']}\nAuthor:{row['username']} At:{row['timestamp']}\n{row['body']}\n"
                # Mostra eventuali risposte
                c.execute("""
                    SELECT b.id, u.username, b.timestamp, b.subject, b.body 
                    FROM board_messages b 
                    JOIN users u ON b.author_id = u.id 
                    WHERE b.parent_id = ? 
                    ORDER BY b.id
                """, (msg_id,))
                replies = c.fetchall()
                for rp in replies:
                    out += f"\n  >> Reply ID:{rp['id']} [{rp['subject']}] by {rp['username']} at {rp['timestamp']}\n{rp['body']}\n"
                logging.info(f"Utente ID {user_id} ha letto il messaggio ID {msg_id}.")
                return out + "OK\n"

            elif cmd == 'NEW':
                # NEW subject|body
                if not arg:
                    logging.warning("Comando NEW senza argomenti.")
                    return "ERR Need subject|body\n"
                if '|' not in arg:
                    logging.warning("Comando NEW con formato errato.")
                    return "ERR Need subject|body\n"
                try:
                    logging.debug(f"Divido arg: {arg}")
                    subject, body = arg.split('|', 1)
                    logging.debug(f"Oggetto: {subject}, Corpo: {body}")
                    ts = time.strftime("%Y-%m-%d %H:%M:%S")
                    c.execute("""
                        INSERT INTO board_messages(author_id, timestamp, subject, body) 
                        VALUES (?, ?, ?, ?)
                    """, (user_id, ts, subject, body))
                    self.conn.commit()
                    logging.info(f"Utente ID {user_id} ha postato un nuovo messaggio: '{subject}'.")
                    return "OK Message posted\n"
                except Exception as e:
                    logging.error(f"Errore inserendo messaggio nella bacheca: {e}")
                    return "ERR Server error\n"

            elif cmd == 'REPLY':
                # REPLY parent_id|subject|body
                if not arg:
                    logging.warning("Comando REPLY senza argomenti.")
                    return "ERR Format: REPLY pid|subj|body\n"
                if '|' not in arg:
                    logging.warning("Comando REPLY con formato errato.")
                    return "ERR Format: REPLY pid|subj|body\n"
                parts = arg.split('|')
                if len(parts) < 3:
                    logging.warning("Comando REPLY con numero di argomenti insufficiente.")
                    return "ERR Format: REPLY pid|subj|body\n"
                pid, subject, body = parts
                ts = time.strftime("%Y-%m-%d %H:%M:%S")
                try:
                    c.execute("""
                        INSERT INTO board_messages(author_id, timestamp, subject, body, parent_id) 
                        VALUES (?, ?, ?, ?, ?)
                    """, (user_id, ts, subject, body, pid))
                    self.conn.commit()
                    logging.info(f"Utente ID {user_id} ha risposto al messaggio ID {pid}: '{subject}'.")
                    return "OK Reply posted\n"
                except Exception as e:
                    logging.error(f"Errore inserendo risposta nella bacheca: {e}")
                    return "ERR Server error\n"

            else:
                logging.warning(f"Comando BOARD sconosciuto: '{cmd}'.")
                return "ERR Unknown BOARD command\n"
        except Exception as e:
            logging.error(f"Errore gestendo comandi BOARD per utente ID {user_id}: {e}")
            return "ERR Server error\n"

