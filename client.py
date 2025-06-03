import socket 
import threading 

host = '127.0.0.1' 
port = 65432 

def sim_client(id):
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s :
		s.connect((host,port))
		message = f"Hello from client {id}"
		s.sendall(message.encode())
		data = s.recv(1024)
		print(f"Client {id} received data {data}")
		

def launch_threads(n) :
	threads = []
	for i in range(1, n+1) :
		thread = threading.Thread(target=sim_client, args= (i,)) 
		threads.append(thread) 
		thread.start()
		
	for thread in threads:
		thread.join() 
	

launch_threads(5)
