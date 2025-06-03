import socket 
import sys
import threading 



HOST = '127.0.0.1'
PORT = 65432
all_clients = {}
room_clients = {}


#do not show this to other users but only the new user
def list_user_names(name):
    names = []
    for n,con in all_clients.items():
        if name != n :
            names.append(n)

    if len(names) ==0 :
        return "\n* There is nobody in the room".encode()
    allnames = ' '.join(n for n in names)
    return f"\n* the room contains {allnames}".encode()
    
def list_only_names_excluding_new_user(name):
    names = []
    for n , con in all_clients.items():
        if name != n :
            names.append(n)

    if len(names)  ==0 :
        return 0 
    
    return names 


def send_message(name, message):
    return f"[{name}] : {message}"

#do not show this to new user but to everyone else in the room
def user_joins(name):
    return f"\n* {name} has entered the room".encode()

def user_leaves(name):
    return f"\n* {name} has left the room".encode()


def send_to(addr, message):
    
    all_clients[addr].sendall(message)
    

def send_user_join_message(names, message):
    if len(names )==0 :
        return 
    print("names: ", names)
    print("message: ", message)
    
    for name in names:
        send_to(name, message)

def register_name(conn):
    while True:
        data = conn.recv(1024)
        if not data:
            return None  # Client disconnected during name input

        name = data.decode().strip()

        if len(name) > 16:
            conn.sendall(b"Name is too long, mate. Try another:\n")
            continue

        if not name.isalnum():
            conn.sendall(b"Name must be alphanumeric. Try another:\n")
            continue

        if name in all_clients:
            conn.sendall(b"Name is taken. Try another:\n")
            continue

        # Valid name
        conn.sendall(b"\nYou're in!\n")
        return name


def chat_loop(conn, name):
    while True:
        data = conn.recv(1024)
        if not data:
            break
        message = f"[{name}] {data.decode().strip()}"
        broadcast_message(name, message)

def broadcast_message(sender_name, message):
    for user, conn in all_clients.items():
        if user != sender_name:
            conn.sendall(message.encode() + b"\n")

def handle_client(conn, addr):
    print(f"\nConnected by {addr}")
    try:
        conn.sendall(b"\nWelcome to budgetchat! What shall I call you?\n")
        name = register_name(conn)
        if not name:
            return  # Registration failed

        all_clients[name] = conn

        # Notify others about this user
        message = list_user_names(name)
        send_to(name, message)

        names_except_user = list_only_names_excluding_new_user(name)
        user_join_message = user_joins(name)
        send_user_join_message(names_except_user, user_join_message)

        # Start chat session
        chat_loop(conn, name)

    except Exception as e:
        print(f"Error with {addr}: {e}")

    finally:
        print("finally():: name : ", name)
        names_except_user = list_only_names_excluding_new_user(name)
        message = user_leaves(name)
        send_user_join_message(names_except_user, message)
        all_clients.pop(name, None)
        conn.close()
        print(f"Disconnected by {addr}")


def start_server():
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 )
        server.bind((HOST, PORT))
        server.listen()
        print(f"Server listening on {HOST}:{PORT}")


        while True:
            conn, addr = server.accept()

            thread = threading.Thread(target=handle_client, args=(conn,addr), daemon=True)
            thread.start()


if __name__ =='__main__':
    start_server()

