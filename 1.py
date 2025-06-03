import socket 
import threading 

host = '127.0.0.1' 
port = 65432 


def handle(conn,addr):
	print(f"connected by {addr}")
	with conn :
		 
		while True:
			data = conn.recv(1024) 
			if not data :
				break 
			
			print("data received: ", data.decode())
			conn.sendall(data)	


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s :
	s.bind((host,port))
	s.listen() 
	print(f"Server listening on {host} : {port}") 
	
	while True:
		conn, addr  = s.accept()
		client_thread = threading.Thread(target=handle, args=(conn,addr))
		client_thread.start()
		
		
			
