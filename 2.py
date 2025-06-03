import socket
import threading
import json

HOST = '127.0.0.1'
PORT = 65432


def is_prime(n):
    """Check if an integer is prime."""
    if not isinstance(n, int):
        return False
    if n <= 1:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True


def parse_request(line):
    """
    Parses a single line JSON request.
    Returns (valid: bool, response: dict).
    """
    try:
        request = json.loads(line)

        # Basic format checks
        if not isinstance(request, dict):
            raise ValueError
        if request.get("method") != "isPrime" or "number" not in request:
            raise ValueError

        number = request["number"]

        if isinstance(number, float) and not number.is_integer():
            prime_result = False
        elif isinstance(number, (int, float)):
            prime_result = is_prime(int(number))
        else:
            raise ValueError

        response = {
            "method": "isPrime",
            "prime": prime_result
        }
        return True, response

    except Exception:
        return False, {"malformed": True}


def handle_client(conn, addr):
    """Handles an individual client connection."""
    print(f"Connected by {addr}")
    buffer = ""

    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            print(f"Data received {data.decode()}")               
            buffer += data.decode()

            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                is_valid, response = parse_request(line)
                conn.sendall((json.dumps(response) + '\n').encode())

                if not is_valid:
                    print(f"Malformed request from {addr}. Disconnecting.")
                    conn.close()
                    return

    except Exception as e:
        print(f"Error with {addr}: {e}")
    finally:
        conn.close()
        print(f"Disconnected from {addr}")


def start_server():
    """Starts the TCP server and accepts clients."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()
        print(f"Server listening on {HOST}:{PORT}")

        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()


if __name__ == "__main__":
    start_server()

