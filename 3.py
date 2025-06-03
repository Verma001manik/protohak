import socket
import threading
import struct
from collections import defaultdict

HOST = '127.0.0.1'
PORT = 65432

# Each client gets its own list of (timestamp, price) entries
client_data = defaultdict(list)

def insert(addr, timestamp, price):
    client_data[addr].append((timestamp, price))

def query(addr, mintime, maxtime):
    if mintime > maxtime:
        return 0

    prices = [price for (ts, price) in client_data[addr] if mintime <= ts <= maxtime]

    if not prices:
        return 0

    return sum(prices) // len(prices)  # integer mean

def handle_client(conn, addr):
    print(f"Connected by {addr}")
    try:
        while True:
            data = b''
            while len(data) < 9:
                packet = conn.recv(9 - len(data))
                if not packet:
                    return
                data += packet

            msg_type = data[0:1]
            int1 = struct.unpack('>i', data[1:5])[0]
            int2 = struct.unpack('>i', data[5:9])[0]
            msg = msg_type.decode('ascii')

            if msg == 'I':
                insert(addr, int1, int2)
                print("client data.......")
                print(client_data)

            elif msg == 'Q':
                result = query(addr, int1, int2)
                conn.sendall(struct.pack('>i', result))
            else:
                print("Unknown message type:", msg)
                return  # undefined behavior

    except Exception as e:
        print(f"Error with {addr}: {e}")
    finally:
        conn.close()
        print(f"Disconnected from {addr}")

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()
        print(f"Server listening on {HOST}:{PORT}")

        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            thread.start()

if __name__ == "__main__":
    start_server()
