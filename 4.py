import socket

UDP_IP = "127.0.0.1"
UDP_PORT = 12345

# Global store for all clients
store = {}

def insert(key, value):
    if key == 'version':
        return
    
    store[key] = value
    print(f"Stored: {key}={value}")

def retrieve(key):
    if key in store:
        return f"{key}={store[key]}".encode()
    else:
        return f"{key}=".encode()

def get_version():
    return "version=Ken's Key-Value Store 1.0".encode()

def parse_key_value(data):
    index = data.find('=')
    if index == -1:
        return None, None
    
    key = data[:index]
    value = data[index+1:]
    return key, value

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    print(f"UDP server running on {UDP_IP}:{UDP_PORT}")
    
    try:
        while True:
            raw_data, addr = sock.recvfrom(1024)
            msg = raw_data.decode().strip()
            print(f"Received from {addr}: '{msg}'")
            
            response = None
            
            if msg == "version":
                response = get_version()
            elif '=' in msg:
                key, value = parse_key_value(msg)
                if key is not None:
                    insert(key, value)
                    print(f"Insert complete: {key}={value}")
                    continue
            else:
                response = retrieve(msg)
            
            if response is not None:
                sock.sendto(response, addr)
                print(f"Sent to {addr}: '{response.decode()}'")
    
    except KeyboardInterrupt:
        print("\nServer shutting down...")
    finally:
        sock.close()

if __name__ == "__main__":
    main()