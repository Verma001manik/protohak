import socket
import threading
import json
import random

host = '127.0.0.1'
port = 65432

def sim_client(id):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))

        # Send a valid JSON message with newline at the end
        number = random.randint(1, 1000)
        message = {
            "method": "isPrime",
            "number": number
        }
        message_str = json.dumps(message) + '\n'  # <-- Add newline!
        print(f"Client {id} sending number {number}")
        s.sendall(message_str.encode())

        # Receive one line response (ending with '\n')
        data = ""
        while not data.endswith('\n'):
            part = s.recv(1024)
            if not part:
                break
            data += part.decode()

        print(f"Client {id} received: {data.strip()}")


def launch_threads(n):
    threads = []
    for i in range(1, n + 1):
        thread = threading.Thread(target=sim_client, args=(i,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

# Launch 5 clients
launch_threads(5)

