import socket
import threading
import time
from collections import defaultdict


session_members = defaultdict(lambda: defaultdict(dict))


class LRCPServer:
    def __init__(self, host='127.0.0.1', port=12345):
        self.host = host
        self.port = port
        self.retransmission_timeout = 3
        self.session_expiry_timeout = 60

    def escape_data(self, data):
        return data.replace('\\', '\\\\').replace('/', '\\/')

    def unescape_data(self, data):
        return data.replace('\\\\', '\\').replace('\\/', '/')

    def session_exists(self, addr, session):
        return addr in session_members and session in session_members[addr]

    def get_session(self, addr, session):
        return session_members[addr].get(session) if self.session_exists(addr, session) else None

    def update_activity(self, addr, session):
        if self.session_exists(addr, session):
            session_members[addr][session]['last_activity'] = time.time()
            return True
        return False

    def connect(self, addr, session):
        session = int(session)
        if session < 0:
            print("Invalid session ID")
            return

        if not self.session_exists(addr, session):
            session_members[addr][session] = {
                'last_activity': time.time(),
                'bytes_sent': 0,
                'bytes_received': 0,
                'last_ack_sent': 0,
                'receive_buffer': {},
                'line_buffer': '',
                'pending_sends': {}
            }

        self.update_activity(addr, session)
        ack_message = f'/ack/{session}/0/'
        self.sock.sendto(ack_message.encode(), addr)

    def data(self, addr, session, pos, content):
        session = int(session)
        pos = int(pos)

        if not self.session_exists(addr, session):
            print(f"Unknown session {session} from {addr}")
            return

        self.update_activity(addr, session)
        state = session_members[addr][session]
        unescaped = self.unescape_data(content)
        expected_pos = state['bytes_received']

        if pos == expected_pos:
            state['bytes_received'] += len(unescaped)
            state['line_buffer'] += unescaped

            while '\n' in state['line_buffer']:
                line, state['line_buffer'] = state['line_buffer'].split('\n', 1)
                reversed_line = line[::-1]
                print(f"Line: '{line}' -> '{reversed_line}'")
                response = reversed_line + '\n'
                self.send_data_to_client(addr, session, response)

        ack_msg = f'/ack/{session}/{state["bytes_received"]}/'
        self.sock.sendto(ack_msg.encode(), addr)

    def close(self, addr, session):
        session = int(session)
        if self.session_exists(addr, session):
            session_members[addr].pop(session, None)
            if not session_members[addr]:
                session_members.pop(addr, None)
            message = f"/close/{session}/"
            self.sock.sendto(message.encode(), addr)
            print(f"Session {session} closed for {addr}")
        else:
            print(f"Attempted to close unknown session {session} from {addr}")

    def parse(self, data):
        d = data.decode('utf-8', errors='ignore').strip()
        if not d.startswith('/') or not d.endswith('/') or len(d) > 1000:
            return None
        parts = d[1:-1].split('/')
        return parts if parts[0] in ['connect', 'close', 'data', 'ack'] else None

    def timeout_manager(self):
        while True:
            time.sleep(5)
            current_time = time.time()
            expired_sessions = []

            for addr in list(session_members.keys()):
                for session_id, state in list(session_members[addr].items()):
                    if current_time - state['last_activity'] > self.session_expiry_timeout:
                        expired_sessions.append((addr, session_id))

            self.cleanup_expired_sessions(expired_sessions)

    def cleanup_expired_sessions(self, expired_sessions):
        for addr, session_id in expired_sessions:
            session_members[addr].pop(session_id, None)
            if not session_members[addr]:
                session_members.pop(addr, None)
            print(f"[Session Timeout] Removed session {session_id} from {addr}")

    def send_data_to_client(self, addr, session, data):
        if not self.session_exists(addr, session):
            return
        state = session_members[addr][session]
        escaped = self.escape_data(data)
        message = f"/data/{session}/{state['bytes_sent']}/{escaped}/"
        self.sock.sendto(message.encode(), addr)
        state['bytes_sent'] += len(data)

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))
        threading.Thread(target=self.timeout_manager, daemon=True).start()
        print(f"Server listening on {self.host}:{self.port}")

        try:
            while True:
                data, addr = self.sock.recvfrom(1024)
                parsed = self.parse(data)
                if not parsed:
                    continue

                msg_type = parsed[0]

                if msg_type == 'connect' and len(parsed) >= 2:
                    self.connect(addr, parsed[1])
                elif msg_type == 'close' and len(parsed) >= 2:
                    self.close(addr, parsed[1])
                elif msg_type == 'data' and len(parsed) >= 4:
                    self.data(addr, parsed[1], parsed[2], parsed[3])
                elif msg_type == 'ack' and len(parsed) >= 3:
                    print(f"Received ACK for session {parsed[1]}, length {parsed[2]}")
                    self.update_activity(addr, int(parsed[1]))
        except KeyboardInterrupt:
            print("\nServer shutting down...")
        finally:
            self.sock.close()


if __name__ == '__main__':
    server = LRCPServer()
    server.start()
