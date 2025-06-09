import socket 
import threading 
from collections import defaultdict

clients = defaultdict(lambda: {"cipher": None, "data": [], "encode_pos": 0, "decode_pos": 0})

class InsecureSocketLayer:
    def __init__(self, host='127.0.0.1', port=12345):
        self.host = host 
        self.port = port 
        self.methods = ['00', '01', '02', '03', '04', '05']

    def encode(self, conn, data):
        """Apply cipher to encode the data"""
        cipher = clients[conn]['cipher']
        if not cipher:
            print("encode(): no cipher found")
            return None 
        
        if isinstance(data, str):
            data = data.encode('ascii')
        
        data_list = list(data)
        start_pos = clients[conn]['encode_pos']

        for fname, argu in cipher:
            if fname == 'reverse_bits':
                data_list = self.reverse_bits(data_list)
            elif fname == 'xor':
                data_list = self.xor(argu, data_list)
            elif fname == 'xorpos':
                data_list = self.xorpos_encode(data_list, start_pos)
            elif fname == 'add':
                data_list = self.add(argu, data_list)
            elif fname == 'addpos':
                data_list = self.addpos_encode(data_list, start_pos)
        
        clients[conn]['encode_pos'] += len(data)
        
        final_data = bytes(data_list)
        print("final encoded data:", final_data.hex())
        return final_data

    def decode(self, conn, data):
        """Apply inverse cipher operations to decode the data"""
        cipher = clients[conn]['cipher']
        if not cipher:
            print("decode(): no cipher found")
            return None

        data_list = list(data)
        start_pos = clients[conn]['decode_pos']
    
        for fname, argu in reversed(cipher):
            if fname == 'reverse_bits':
                data_list = self.reverse_bits(data_list)
            elif fname == 'xor':
                data_list = self.xor(argu, data_list)
            elif fname == 'xorpos':
                data_list = self.xorpos_decode(data_list, start_pos)
            elif fname == 'add':
                data_list = self.subtract(argu, data_list)
            elif fname == 'addpos':
                data_list = self.subtractpos_decode(data_list, start_pos)

        # Update position counter
        clients[conn]['decode_pos'] += len(data)
        
        final_data = bytes(data_list)
        print("final decoded data:", final_data.hex())
        return final_data

    def subtract(self, n, data):
        """Subtract a fixed number n from each byte (modulo 256) - inverse of add"""
        result = [(c - n) % 256 for c in data]
        print("Data after subtract:", result)
        return result

    def subtractpos_decode(self, data, start_pos):
        """Subtract position from each byte (modulo 256) - inverse of addpos for decoding"""
        result = [(data[i] - (start_pos + i)) % 256 for i in range(len(data))]
        print("Data after subtractpos_decode:", result)
        return result

    def reverse_bits(self, data):
        """Reverse bits of each byte in a list of ints"""
        def reverse_byte(n):
            result = 0
            for _ in range(8):
                result = (result << 1) | (n & 1)
                n >>= 1
            return result

        result = [reverse_byte(b) for b in data]
        print("Data after reverse_bits:", result)
        return result

    def xor(self, n, data):
        """XOR each byte in data with fixed number n"""
        result = [c ^ n for c in data]
        print("Data after xor:", result)
        return result

    def xorpos_encode(self, data, start_pos):
        """XOR each byte with its position in the stream for encoding"""
        result = [data[i] ^ (start_pos + i) for i in range(len(data))]
        print("Data after xorpos_encode:", result)
        return result

    def xorpos_decode(self, data, start_pos):
        """XOR each byte with its position in the stream for decoding"""
        result = [data[i] ^ (start_pos + i) for i in range(len(data))]
        print("Data after xorpos_decode:", result)
        return result

    def add(self, n, data):
        """Add a fixed number n to each byte (modulo 256)"""
        result = [(c + n) % 256 for c in data]
        print("Data after add:", result)
        return result

    def addpos_encode(self, data, start_pos):
        """Add position to each byte (modulo 256) for encoding"""
        result = [(data[i] + start_pos + i) % 256 for i in range(len(data))]
        print("Data after addpos_encode:", result)
        return result

    def parse_cipher_spec(self, data_list):
        """Parse cipher spec from list of hex strings like ['02', '7b', '05', '01', '00']"""
        operations = []
        i = 0
    
        while i < len(data_list):
            op_code = data_list[i]
        
            if op_code == '00':  # End of cipher spec
                break
            elif op_code == '01':  # reversebits
                operations.append(('reverse_bits', None))
                i += 1
            elif op_code == '02':  # xor(N)
                if i + 1 < len(data_list):
                    operand = int(data_list[i + 1], 16)
                    operations.append(('xor', operand))
                    i += 2
                else:
                    break
            elif op_code == '03':  # xorpos
                operations.append(('xorpos', None))
                i += 1
            elif op_code == '04':  # add(N)
                if i + 1 < len(data_list):
                    operand = int(data_list[i + 1], 16)
                    operations.append(('add', operand))
                    i += 2
                else:
                    break
            elif op_code == '05':  # addpos
                operations.append(('addpos', None))
                i += 1
            else:
                return None
    
        return operations

    def is_noop_cipher(self, cipher_ops):
        """Check if cipher operations result in no change to input data"""
        if not cipher_ops: 
            return True
        
        test_data = list(range(256))  
        original_data = test_data.copy()
        
        pos = 0
        for fname, argu in cipher_ops:
            if fname == 'reverse_bits':
                test_data = self.reverse_bits(test_data)
            elif fname == 'xor':
                test_data = self.xor(argu, test_data)
            elif fname == 'xorpos':
                test_data = self.xorpos_encode(test_data, pos)
            elif fname == 'add':
                test_data = self.add(argu, test_data)
            elif fname == 'addpos':
                test_data = self.addpos_encode(test_data, pos)
        
        # If the result is identical to original, it's a no-op
        return test_data == original_data

    def parse_decoded_message(self, data):
        """Parse decoded message and find the toy with maximum count"""
        data = data.rstrip('\n')
        items = data.split(',') 
        max_count = -1 
        max_item = ""

        for item in items:
            item = item.strip()
            if 'x' not in item:
                continue
            count_str, toy = item.split('x', 1)
            count = int(count_str.strip())
            if count > max_count:
                max_count = count 
                max_item = f"{count}x {toy.strip()}"

        print("max item:", max_item)
        return max_item + '\n' 

    def handle_client(self, conn, addr):
        print(f"Client connected from {addr}")
    
        try:
            buffer = b""
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                
                buffer += data
                
                if clients[conn]['cipher'] is None:
                    hex_data = buffer.decode().strip().split()
                    print("Received cipher spec data:", hex_data)
                    
                    if '00' in hex_data:
                        end_idx = hex_data.index('00')
                        cipher_spec = hex_data[:end_idx + 1]
                        
                        cipher_ops = self.parse_cipher_spec(cipher_spec)
                        if cipher_ops is None:
                            print("Invalid cipher spec")
                            conn.close()
                            break
                        
                        if self.is_noop_cipher(cipher_ops):
                            print("No-op cipher detected, disconnecting")
                            conn.close()
                            break
                        
                        clients[conn]['cipher'] = cipher_ops
                        print("Cipher spec set:", cipher_ops)
                        
                        remaining = ' '.join(hex_data[end_idx + 1:])
                        buffer = remaining.encode() if remaining.strip() else b""
                else:
                    try:
                        hex_str = buffer.decode().strip()
                        if not hex_str:
                            continue
                        hex_data = hex_str.split()
                        encoded_bytes = bytes([int(x, 16) for x in hex_data])
                        print("Encoded bytes:", encoded_bytes.hex())
                        
                        decoded_bytes = self.decode(conn, encoded_bytes)
                        if decoded_bytes is None:
                            continue
                        
                        try:
                            decoded_message = decoded_bytes.decode('ascii')
                            print("Decoded message:", repr(decoded_message))
                            
                            response = self.parse_decoded_message(decoded_message)
                            
                            encoded_response = self.encode(conn, response)
                            if encoded_response:
                                conn.send(encoded_response)
                                print("Sent encoded response:", encoded_response.hex())
                            
                        except UnicodeDecodeError:
                            print("Could not decode as ASCII")
                            continue
                        
                        buffer = b""
                        
                    except (ValueError, IndexError) as e:
                        print(f"Error parsing hex data: {e}")
                        continue

        except Exception as e:
            print(f"Error handling client {addr}: {e}")
            import traceback
            traceback.print_exc()
    
        finally:
            if conn in clients:
                del clients[conn]
            conn.close()
            print(f"Client {addr} disconnected")

    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.port))
            server.listen()

            print(f"Server listening on {self.host}:{self.port}")

            try:
                while True:
                    conn, addr = server.accept()
                    thread = threading.Thread(
                        target=self.handle_client,
                        args=(conn, addr),
                        daemon=True
                    )
                    thread.start()
            except KeyboardInterrupt:
                print("\nShutting down server...")

if __name__ == '__main__':
    s = InsecureSocketLayer()
    s.start()