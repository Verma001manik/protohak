import socket
import threading

tony_address = b'7YWHMfk9JZe0LM0g1ZauHuiSxhI'
UPSTREAM_HOST = 'chat.protohackers.com'
UPSTREAM_PORT = 16963
HOST = '127.0.0.1'
PORT = 12345

def connect_to_upstream(conn):
    try:
        with socket.create_connection((UPSTREAM_HOST, UPSTREAM_PORT)) as upstream_sock:
            print(f"Connected to {UPSTREAM_HOST}:{UPSTREAM_PORT}")
            
            def forward_data(source, destination, name):
                try:
                    while True:
                        data = source.recv(4096)
                        if not data:
                            print(f"{name} closed the connection.")
                            break
                        
                        if data.find(b'7') >= 0:
                            indx = data.find(b'7')
                            
                            end_markers = [b' ', b'\n', b'\r', b'\t']
                            end_idx = len(data)
                            for marker in end_markers:
                                marker_pos = data.find(marker, indx)
                                if marker_pos != -1:
                                    end_idx = min(end_idx, marker_pos)
                            
                            address = data[indx:end_idx]
                            
                            try:
                                address_str = address.decode('utf-8')
                                if is_bogus_address(address_str):
                                    data = data[:indx] + tony_address + data[end_idx:]
                            except UnicodeDecodeError:
                                pass
                        
                        try:
                            destination.sendall(data)
                        except Exception as send_error:
                            break
                except Exception as e:
                    print(f"Error in {name}:", e)
                finally:
                    try:
                        source.close()
                    except:
                        pass
                    try:
                        destination.close()
                    except:
                        pass
            
            client_to_upstream = threading.Thread(
                target=forward_data,
                args=(conn, upstream_sock, "Client")
            )
            upstream_to_client = threading.Thread(
                target=forward_data,
                args=(upstream_sock, conn, "Upstream")
            )
            
            client_to_upstream.start()
            upstream_to_client.start()
            
            client_to_upstream.join()
            upstream_to_client.join()
            
    except Exception as e:
        print("Error in proxying:", e)
    finally:
        try:
            conn.close()
        except:
            pass

def is_bogus_address(address):
    if not address:
        return False
    if not address[0] == '7':
        return False
    if len(address) < 26 or len(address) > 35:
        return False
    if not address.isalnum():
        return False 
        
    return True

def handle_client(conn, addr):
    print(f"Connected by {addr}")
    try:
        connect_to_upstream(conn)
    except Exception as e:
        print(f"Error with {addr}: {e}")
    finally:
        try:
            conn.close()
            print(f"Disconnected by {addr}")
        except:
            pass

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

if __name__ == '__main__':
    start_server()