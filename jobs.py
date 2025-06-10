import socket 
import threading 
import json 


class JobServer:

    def __init__(self, host='127.0.0.1', port=12345):
        self.host = host 
        self.port = port 

        #request contain field name : request and type as one of the below
        self.request_type = ['put', 'get','delete','abort']
        #contains status field and one of the below
        self.response_type = ['ok','error','no-job']

    

    def error_request(self):
        #do not close connect if even invalid request
        msg = {"status":"error","error":"Unrecognised request type."}
        return msg 
    
    def handle_client(self,conn,addr):
        print(f"Client Connected from {addr}")
        try:
            while True:

                data = conn.recv(4096)
                print("data received : ", data.decode())

        except Exception as e : 
            print(f"Error handling client {addr}: {e}")

        finally :
            print("in tne final block mate")
    def start(self):
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as server:

            server.bind((self.host, self.port))
            server.listen()
            print(f"Server listening on {self.host} : {self.port}")

            while True :
                conn,addr = server.accept()

                thread  = threading.Thread(target=self.handle_client, args=(conn,addr), daemon=True)

                thread.start() 


if __name__ == '__main__':
    s = JobServer()
    s.start()