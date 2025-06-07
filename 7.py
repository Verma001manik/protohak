import socket 
import threading 
import struct 
import time 
from collections import defaultdict
# weneed to store the session number and also the last time they sent the messgae
#if the currenttime - last sent ? session expiry timeout then delete the session 

session_members =  defaultdict(lambda: defaultdict(dict))

class LRCPServer:
    def __init__(self, host='127.0.0.1', port=12345):
        self.host = host 
        self.port = port 
        self.retransmission_timeout = 3 
        self.session_expiry_timeout = 60 


    def escape_data(self, data):
        return data.replace('\\', '\\\\').replace('/', '\\/')

    def unescape_data(self, data):
        return data.replace('\\/', '/').replace('\\\\', '\\')
    
    def get_or_create_session(self, addr, session_id):
        if session_id not in session_members[addr]:
            session_members[addr][session_id] = {
                'last_activity': time.time(),
                'bytes_sent': 0,
                'bytes_received': 0,
                'last_ack_sent': 0,
                'receive_buffer': {},
                'line_buffer': '',
                'pending_sends': {}
            }
        return session_members[addr][session_id]

    def session_exists(self, addr,session):
        return addr in session_members and session in session_members[addr]
    

    def get_session(self, addr,session):
        if self.session_exists(addr,session):
            return session_members[addr][session]
        
        return None 
    

    def update_activity(self,addr, session):
        if self.session_exists(addr,session):
            session_members[addr][session]['last_activity'] = time.time() 
            return True
        
        return False
    
            
    def connect(self, addr, session):
        session = int(session)
        print("session : ", session)
        if session < 0:  # Changed from < 1
            print("session must be non-negative integer")
            return 
    
        if session not in session_members[addr]:
            session_members[addr][session] = {
            'last_activity': time.time(),
            'bytes_sent': 0,
            'bytes_received': 0,
            'last_ack_sent': 0,
            'receive_buffer': {},
            'line_buffer': '',
            'pending_sends': {}
        }
    
    # Always send ack (even for existing sessions)
        self.update_activity(addr, session)
        message = f'/ack/{session}/0/'  # Removed \n
        self.sock.sendto(message.encode(), addr)



    def ack(self, addr, message):
        if not message or not addr  :
            return 
        if not session_members[addr] or not addr in session_members:
            print("no client with such session")
            return 


        self.sock.sendto(message.encode() , addr)



                

    def data(self, addr, session,pos,data):
        session = int(session)
        pos =  int(pos)
        
        state = session_members[addr][session]
        unescaped = self.unescape_data(data)
        
        expected_pos = state['bytes_received']
        if pos == expected_pos:
            state['bytes_received'] += len(unescaped)
            state['line_buffer'] += unescaped


            while '\n' in state['line_buffer']:
                line, state['line_buffer'] = state['line_buffer'].split('\n', 1)
                reversed_line = line[::-1]
                print(f"Line: '{line}' -> '{reversed_line}'")

                response_data = reversed_line + '\n'
                self.send_data_to_client(addr, session, response_data)
            
        ack_msg = f'/ack/{session}/{state["bytes_received"]}/'
        self.sock.sendto(ack_msg.encode(), addr)
        
        
        

    def close(self,addr, session_number):
        # can be done by client or server 
        #but acc to problem lets assume server will never do that 

        '''
                <-- /close/1234567/
                --> /close/1234567/
        
        '''
        session_number = int(session_number)
        if session_number in session_members[addr]:
            
            
            del session_members[addr][session_number]

            if not session_members[addr]:
                del session_members[addr]
            message  = f"/close/{session_number}/"
            self.sock.sendto(message.encode(),addr)
            return True 
        else:
            print("motherfucker you not even open..")
            return False 



    def check_is_session_expired(self, addr,session):
        curent = time.time() 
        if  curent - session_members[addr][session]['last_activity'] > self.session_expiry_timeout:
            #oh yes
            self.close(addr, session)

            return True 

        else:
            return False 
         
    
    

  
    
        
    def parse(self,data):
        d =data.decode('utf-8', errors='ignore').strip()
        print("d: ", d)
        
        if not d.startswith('/') :
            print("doesnt start with or endswith /")
            return None 
        
        if len(data)> 1000:
            print("message too long")
            return None 
        

        parts = d[1:-1].split('/')
        if not parts or parts[0] not in ['connect', 'close', 'data', 'ack']:
            print("parts not present in required array")
            return None 
        
        return parts 
    
    def timeout_manager(self):
        while True:
            time.sleep(5)
            current_time = time.time() 
            expired_sessions = []

            for addr in list(session_members.keys()):
                for session_id, state in list(session_members[addr].items()):
                    if current_time - state['last_activity'] > self.session_expiry_timeout:
                        expired_sessions.append((addr, session_id))
            
            self.cleanup_expired_sessions(expired_sessions=expired_sessions)
            


    def cleanup_expired_sessions(self, expired_sessions):
        if not expired_sessions:
            return 
        
        for addr, session_id in expired_sessions:
                del session_members[addr][session_id]
                if not session_members[addr]:
                    del session_members[addr]

        
    def send_data_to_client(self, addr,session,data):
        if not self.session_exists(addr,session):
            return 

        state = session_members[addr][session]
        unescaped = self.escape_data(data)

        message = f"/data/{session}/{state['bytes_sent']}/{unescaped}/"

        self.sock.sendto(message.encode() , addr)





        

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
        self.sock.bind((self.host, self.port))
        timeout_thread = threading.Thread(target=self.timeout_manager, daemon=True)
        timeout_thread.start()
        print(f"Server listening on {self.host}:{self.port}")

        try:
            while True:
                data, addr = self.sock.recvfrom(1024)
                print(f"received from {addr}: {data}")

                parsed_data = self.parse(data)
                if parsed_data is None:
                    continue
                    
                print("from parse:", parsed_data)

                msg_type = parsed_data[0]
                print("message type:", msg_type)
                
                if msg_type == 'connect':
                    if len(parsed_data) >= 2:
                        session = parsed_data[1] 
                        self.connect(addr, session)
                        print(f"Sessions: {dict(session_members)}")
                elif msg_type == 'close':
                    if len(parsed_data) >= 2:
                        session = parsed_data[1]
                        self.close(addr, session)
                elif msg_type == 'data':
                    if len(parsed_data) >= 4:
                        session = parsed_data[1]
                        pos = parsed_data[2]
                        data_content = parsed_data[3]
                        self.data(addr, session, pos, data_content) 
                elif msg_type == 'ack':
                    if len(parsed_data) >= 3:
                        session = parsed_data[1]
                        length = parsed_data[2]
                        print(f"Received ACK for session {session}, length {length}")
                        self.update_activity(addr, int(session))
                else:
                    print("unknown message type")

        except KeyboardInterrupt:
            print("\nShutting down server")
        finally:
            if self.sock:
                self.sock.close()


if __name__ == '__main__':
    s  = LRCPServer()
    s.start()
                    

