import socket 

import threading 

from collections import defaultdict
clients = defaultdict(lambda: {"cipher": None, "data": []})
class InsecureSocketLayer:

    def __init__(self, host='127.0.0.1', port=12345):
        self.host = host 
        self.port = port 
        self.methods = ['00', '01', '02', '03', '04', '05']

        


    def encode(self,conn,  data):
        # apply non inverse to encode the data 

        pass 

    def decode(self, conn, data):
        cipher = clients[conn]['cipher']
        if not cipher:
            print("decode(): no cipher found")
            return None

    # Convert bytes to list of ints for transformation
        data_list = list(data)
    
    # Apply inverse operations in REVERSE order
        for fname, argu in reversed(cipher):
            if fname == 'reverse_bits':
            # reverse_bits is its own inverse
                data_list = self.reverse_bits(data_list)
            elif fname == 'xor':
            # xor is its own inverse
                data_list = self.xor(argu, data_list)
            elif fname == 'xorpos':
            # xorpos is its own inverse
                data_list = self.xorpos(data_list)
            elif fname == 'add':
            # inverse of add is subtract
                data_list = self.subtract(argu, data_list)
            elif fname == 'addpos':
            # inverse of addpos is subtractpos
                data_list = self.subtractpos(data_list)

        # Convert list[int] back to bytes
        final_data = bytes(data_list)

        print("final decoded data: ", final_data)
        return final_data

    def subtract(self, n, data):
        """
        Subtract a fixed number n from each byte (modulo 256) - inverse of add
     """
        result = [(c - n) % 256 for c in data]
        print("Data before subtract: ", data)
        print("Data after subtract: ", result)
        return result

    def subtractpos(self, data):
        """
        Subtract position from each byte (modulo 256) - inverse of addpos
        """
        result = [(data[i] - i) % 256 for i in range(len(data))]
        print("Data before subtractpos: ", data)
        print("Data after subtractpos: ", result)
        return result


        
    def reverse_bits(self, data):
        """
            Reverse bits of each byte in a list of ints
        """
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
        """
        XOR each byte in data with fixed number n
        """
        result = [c ^ n for c in data]

        print("Data before xor: ", data)
        print("Data after xor: ", result)
        return result

    def xorpos(self, data):
        """
        XOR each byte with its position in the list
        """
        result = [data[i] ^ i for i in range(len(data))]

        print("Data before xorpos: ", data)
        print("Data after xorpos: ", result)
        return result

    def add(self, n, data):
        """
        Add a fixed number n to each byte (modulo 256)
        """
        result = [(c + n) % 256 for c in data]

        print("Data before add: ", data)
        print("Data after add: ", result)
        return result

    def addpos(self, data):
        """
        Add position to each byte (modulo 256)
        """
        result = [(data[i] + i) % 256 for i in range(len(data))]

        print("Data before addpos: ", data)
        print("Data after addpos: ", result)
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
                    operand = int(data_list[i + 1], 16)  # Convert hex string to int
                    operations.append(('xor', operand))
                    i += 2
                else:
                    break
            elif op_code == '03':  # xorpos
                operations.append(('xorpos', None))
                i += 1
            elif op_code == '04':  # add(N)
                if i + 1 < len(data_list):
                    operand = int(data_list[i + 1], 16)  # Convert hex string to int
                    operations.append(('add', operand))
                    i += 2
                else:
                    break
            elif op_code == '05':  # addpos
                operations.append(('addpos', None))
                i += 1
            else:
            # Invalid operation
                return None
    
        return operations
    def is_noop_cipher(self,cipher_ops):
        
        if len(cipher_ops) < 2:
            return True 
        
        #or we could just decode the message from the client , 
        #if the decoded data and pre decoded data are same then it is a no op right
        # we just can do search of all things 
        #because in the question they said it is not limited to few if's



    def handle_client(self, conn, addr):
        print(f"Client connected from {addr}")
    
        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                
                print("data received:", data.decode()) 
                data = data.decode()
                data = data.strip().split() 
                print("data after stripping splitting:", data)

                if not data:  # Empty data
                    continue

                msg_type = data[0]
                print("msg type:", msg_type)
            
                if msg_type in self.methods:  # ['00', '01', '02', '03', '04', '05']
                # This is a cipher spec
                    if clients[conn]['cipher'] is not None:
                        print("cipher already available")
                        continue
                
                    cipher_ops = self.parse_cipher_spec(data)
                    if cipher_ops is None:
                        print("Invalid cipher spec")
                        conn.close()
                        break
                
                # Check for no-op cipher here
                    if self.is_noop_cipher(cipher_ops):
                        conn.close()
                        break
                
                    clients[conn]['cipher'] = cipher_ops
                    print("Cipher spec set:", cipher_ops)
                
                else:
                # This is an encoded message
                    if clients[conn]['cipher'] is None:
                        print("No cipher spec available")
                        conn.close()
                        break
                
                    print("Received encoded message")
                
                    try:
                        encoded_bytes = bytes([int(x, 16) for x in data])
                        print("Encoded bytes:", encoded_bytes.hex())
                    except ValueError:
                        print("Invalid hex data")
                        continue
                
                    decoded_bytes = self.decode(conn, encoded_bytes)
                    if decoded_bytes is None:
                        continue
                
                # Convert decoded bytes to ASCII string
                    try:
                            print("Decoded hex:", decoded_bytes.hex())
                            decoded_message = decoded_bytes.decode('ascii')  # Convert to ASCII text, not hex!
                            print("Decoded message:", repr(decoded_message))
                        
                    except UnicodeDecodeError:
                        continue
                        
                
                
                
                    clients[conn]['data'].append(decoded_message)
    
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

            print(f"Server listening on {self.host} : {self.port}")

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
                self.running = False



if __name__ == '__main__':
    s =InsecureSocketLayer()
    s.start()

