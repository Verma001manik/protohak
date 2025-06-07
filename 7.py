import socket 
import threading 
import struct 


class LRCPServer:
    def __init__(self, host='127.0.0.1', port=12345):
        self.host = host 
        self.port = port 





    def start(self):
        sock =  socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
        sock.bind((self.host,self.port))

        print(f"Server listening on {self.host}: {self.port}")


        try:
            while True:
                data, addr = sock.recvfrom(1024)
                print(f"received from :{addr} :{data} ")


        except KeyboardInterrupt:
            print("\nSHutting down server")

        finally :
            pass 




if __name__ == '__main__':
    s  = LRCPServer()
    s.start()
                    

