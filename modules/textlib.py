import os
import logging

class TextLib:
    def __init__(self, doc_path='/opt/mybbs/data/docs'):
        self.doc_path = doc_path

    def handle_command(self, line):
        parts = line.strip().split(' ', 1)
        cmd = parts[0].upper() if parts else ''
        arg = parts[1].strip() if len(parts) > 1 else ''
        try:
            if cmd == 'LIST':
                docs = os.listdir(self.doc_path)
                out = ""
                for d in docs:
                    if d.endswith('.txt'):
                        out += d + "\n"
                return out + "OK\n"

            elif cmd == 'READ':
                if not arg:
                    return "ERR READ <filename>\n"
                fn = arg.strip()
                path = os.path.join(self.doc_path, fn)
                if not os.path.exists(path):
                    return "ERR Not found\n"
                with open(path, 'r') as f:
                    data = f.read()
                return data + "\nOK\n"

            else:
                return "ERR Unknown text command\n"
        except Exception as e:
            logging.error(f"Errore TextLib cmd={cmd}, arg={arg}: {e}")
            return "ERR Server error\n"

