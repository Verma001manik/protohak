import socket
import threading
import time
from collections import defaultdict, deque

class SpeedCameraServer:
    def __init__(self, host='127.0.0.1', port=12345):
        self.host = host
        self.port = port
        
        # Connection tracking
        self.camera_connections = {}      # conn -> camera_info
        self.dispatcher_connections = {}  # conn -> dispatcher_info
        self.road_dispatchers = defaultdict(list)  # road -> [connections]
        
        # Data storage
        self.roads_data = defaultdict(lambda: {
            "limit": None,
            "cameras": {},  # mile -> camera_info
            "observations": defaultdict(list)  # plate -> [(mile, timestamp), ...]
        })
        
        
        self.daily_tickets = defaultdict(set)
        self.queued_tickets = defaultdict(list)

        # Heartbeat tracking
        self.heartbeat_clients = {}  # conn -> (interval, last_sent)
        self.heartbeat_thread = None
        self.running = False

    def heartbeat_worker(self):
        while self.running:
            current_time = time.time()
            for conn,info in  list(self.heartbeat_clients.items()):
                if (current_time- info['last_sent']) >= info['interval']:
                    if (self.send_message(conn, self.build_heartbeat_message())):
                        info['last_sent'] = current_time
                        print(f"Heartbeat sent to client")

                    else:
                        self.disconnect_client(conn)
    

    def parse_u16(self,hexparts,start_idx):
        if start_idx +3 > len(hexparts):
            return 0 , start_idx
        high = int(hexparts[start_idx] , 16)
        low = int(hexparts(start_idx+ 1), 16)
        value = ( high << 8)| low
        return value , start_idx + 2 
    

    def parse_u32(self,hexparts, start_idx):
        if  start_idx + 4 > len(hexparts):
            return 0 , start_idx
        
        by = [int(hexparts[i],16) for i in  range(start_idx, start_idx+4)]
        value = (by[0] << 24 | by[1] << 16 | by[2] << 8| by[3])

        return value, start_idx+4 
    
    def handle_want_heartbeat(self,conn,hexparts):
        if conn in self.heartbeat_clients:
            self.send_error_and_disconnect(conn, "duplicate heartbeat request")
            return 
        if len(hexparts) < 5 :
            self.send_error_and_disconnect(conn, "invalid heartbeat message")
            return 
        
        timee , _ = self.parse_u32(hexparts, 1)

        if timee ==0 :
            return 
        
        self.heartbeat_clients[conn] = {
            'interval': timee/10, 
            'last_sent': time.time()
        }
        print(f"Heartbeat requested: {timee} deciseconds")
    
    def build_error_message(self, conn, message):
        msg_bytes = message.encode('ascii')

        msg = "10 "
        msg += f"{len(msg_bytes):02x}"
        msg +=  f"{len(msg_bytes):02x}" 
        return msg 


    def send_error_and_disconnect(self, conn,error_msg):
        error_hex = self.build_error_message(conn , error_msg)
        self.send_message(conn, error_hex)
        self.disconnect_client(conn)



    def send_message(self,conn,hex_message):
        try:
            conn.send(hex_message.encode('ascii')+ b'\n')
            return True 
        
        except:
            return False 
        
    def build_heartbeat_message(self):
        return "41"
    def disconnect_client(self, conn):
        try:
            conn.close()
        except:
            print("SOmething went wrong")

        
        if conn in self.camera_connections:
            del self.camera_connections[conn]
        
        if  conn in self.heartbeat_clients:
            del self.heartbeat_clients[conn]

        if conn in self.dispatcher_connections:
            dis_info = self.dispatcher_connections[conn]

            for road in dis_info['roads']:
                if conn in self.road_dispatchers[road]:
                    self.road_dispatchers[road].remove(conn)

            del self.dispatcher_connections[conn]

    def parse_string(self,hexparts,start_idx):
        if (start_idx >= len(hexparts)):
            return "", start_idx
        
        '''
            Hexadecimal:                Decoded:
        20                          Plate{  
        04 55 4e 31 58                  plate: "UN1X",
        00 00 03 e8                     timestamp: 1000
                            }
        '''

        #04 55 4e 31 58  is sent here
        # 04 is the length we calculate below 
        length = int(hexparts[start_idx], 16)
        string_start = start_idx +1 
        string_end = string_start+ length 

        if string_end >= len(hexparts):
            return "", start_idx 
        
        char_codes = [int(hexparts[i],16) for i in range(string_start,string_end)]
        value = ''.join(chr(i) for i in char_codes)

        return value, string_end

    def handle_plate(self, conn, hexparts):

        '''
                20                          Plate{
                04 55 4e 31 58                  plate: "UN1X",
                00 00 03 e8    
        '''

        if conn not in self.camera_connections:
            self.send_error_and_disconnect(conn, "not a cam")
            return 
        
        if len(hexparts) < 6 :
            self.send_error_and_disconnect( conn , "invalid plate message")
            return 
        
        plate, nxt_idx = self.parse_string(hexparts,1)
        if (nxt_idx + 4 >= len(hexparts)) or plate == "":
            self.send_error_and_disconnect(conn, "invalid plate message")
            return 

        timestamp , _ = self.parse_u32(hexparts, nxt_idx)

        camera_info = self.camera_connections[conn]

        road = camera_info['road']
        mile= camera_info['mile']

        self.roads_data[road]['observations'][plate].append((mile,timestamp))
        print(f"Plate observation: {plate} at road={road}, mile={mile}, time={timestamp}")
        
    
    def issue_ticket(self, plate, road, mile1, timestamp1, mile2, timestamp2, speed_mph):
        if timestamp1 > timestamp2:
            mile1 ,mile2 = mile2, mile1
            timestamp1, timestamp2 = timestamp2, timestamp1
            speed_100x = int(speed_mph * 100)
            ticket_msg = self.build_ticket_message(
            plate, road, mile1, timestamp1, mile2, timestamp2, speed_100x
            )

            print(f"Ticket issued: {plate} on road {road}, speed {speed_mph:.2f} mph")
            print(f"Ticket message: {ticket_msg}")

        dispatchers = self.road_dispatchers[road]

        if dispatchers:
            for dispatcher_conn in dispatchers:
                if self.send_message(dispatcher_conn, ticket_msg):
                    print(f"Ticket sent to dispatcher for road {road}")
                    return
                else:
                    self.disconnect_client(dispatcher_conn)
            
            self.queued_tickets[road].append(ticket_msg)
            print(f"All dispatchers failed, ticket queued for road {road}")
        else:
            # No dispatcher available, queue the ticket
            self.queued_tickets[road].append(ticket_msg)
            print(f"No dispatcher available, ticket queued for road {road}")

    def build_ticket_message(self, plate, road, mile1, timestamp1, mile2, timestamp2, speed_100x):
        result = "21 "  # Ticket message type
        
        # Plate (str)
        plate_bytes = plate.encode('ascii')
        result += f"{len(plate_bytes):02x} "
        result += ' '.join([f"{b:02x}" for b in plate_bytes]) + " "
        
        # Road (u16)
        result += f"{(road >> 8) & 0xFF:02x} {road & 0xFF:02x} "
        
        # Mile1 (u16)
        result += f"{(mile1 >> 8) & 0xFF:02x} {mile1 & 0xFF:02x} "
        
        # Timestamp1 (u32)
        result += f"{(timestamp1 >> 24) & 0xFF:02x} {(timestamp1 >> 16) & 0xFF:02x} "
        result += f"{(timestamp1 >> 8) & 0xFF:02x} {timestamp1 & 0xFF:02x} "
        
        # Mile2 (u16)
        result += f"{(mile2 >> 8) & 0xFF:02x} {mile2 & 0xFF:02x} "
        
        # Timestamp2 (u32)
        result += f"{(timestamp2 >> 24) & 0xFF:02x} {(timestamp2 >> 16) & 0xFF:02x} "
        result += f"{(timestamp2 >> 8) & 0xFF:02x} {timestamp2 & 0xFF:02x} "
        
        # Speed (u16, 100x mph)
        result += f"{(speed_100x >> 8) & 0xFF:02x} {speed_100x & 0xFF:02x}"
        
        return result.strip()
    def handle_iam_camera(self,conn,hexparts):
        '''
            80              IAmCamera{
            00 42               road: 66,
            00 64               mile: 100,          
            00 3c 
        
        '''
        if conn in self.camera_connections or conn in self.dispatcher_connections:
            self.send_error_and_disconnect(conn , "already identified")
            return         
        if len(hexparts) < 7 :
            self.send_error_and_disconnect(conn, "invalid camera")
            return  


        road, _  = self.parse_u16(hexparts,1)
        mile, _  = self.parse_u16(hexparts,3)
        limit, _= self.parse_u16(hexparts,5)


        self.camera_connections[conn]= {
            "road": road,
            "mile": mile,
            "limit": limit
        }
        road_data = self.roads_data[conn]
        if road_data['limit'] is None:
            road_data['limit'] = limit 

        road_data["cameras"][mile] = {'conn': conn, 'limit':limit}
        print(f"Camera registered: road={road}, mile={mile}, limit={limit}")



    def handle_iam_dispatcher(self, conn,hexparts):
        if conn in self.camera_connections or conn in self.dispatcher_connections:
            self.send_error_and_disconnect(conn, "already present")
            return 
        
        if(len(hexparts) < 2):
            self.send_error_and_disconnect(conn, "invalid dispatcher message")

            return


        num_roads =int(hexparts[1], 16) 
        if len(hexparts) < 2 + num_roads*2:
            self.send_error_and_disconnect(conn, "invalid dispatcher message")

            return 
        
        roads = []

        for i in range(num_roads):
            road, _   = self.parse_u16(hexparts, 2+ (i*2))
            roads.append(road)

        self.dispatcher_connections[conn] = {'roads': roads}

        for road in roads:
            self.road_dispatchers[road].append(conn)
            while self.queued_tickets[road]:
                tkt_msg = self.queued_tickets[road].popleft()

                if self.send_message(conn, tkt_msg):
                    print(f"Sent queued ticket for road {road}")

                else:
                    self.queued_tickets[road].appendleft(tkt_msg)
                    break
    def check_speeding_violation(self,road,plate):
        
        road_data = self.roads_data[road]
        limit = road_data['limit']
        if limit is None :
            return 
        

        observations = road_data['observations'][plate]

        if len(observations)< 2:
            
            return 


        observations = observations.sort(key=lambda x: x[1])
        for i in range(len(observations)):
            for j in range(i+1, len(observations)):
                m1,t1 = observations[i]
                m2,t2 = observations[j]

                if t1 == t2:
                    continue

                distance = abs(m1-m2)
                tim = abs(t2-t1)/3600
                if tim == 0 :
                    continue
                speed_mph = distance/tim


                print(f"Speed check: {plate} - {speed_mph:.2f} mph (limit: {limit})") 
                

                if speed_mph >= limit + 0.5:
                    day1 = t1//86400
                    day2 = t2//86400
                    tickets_issed = False
                    
                    for day in range(int(day1) , int(day2)+1):
                        if (plate,road) in self.daily_tickets[road]:
                            tickets_issed = True 
                            break 
                    
                    if not tickets_issed:
                        self.issue_ticket(plate, road, m1, t1, m2, t2, speed_mph)
                        
                        for day in range(int(day1), int(day2) + 1):
                            self.daily_tickets[day].add((plate, road))
                        
                        return


        
    def handle_client(self, conn, addr):
        print(f"Client connected from {addr}")
        
        try:
            buffer = ""
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                
                try:
                    buffer += data.decode('ascii')
                except:
                    self.send_error_and_disconnect(conn, "invalid data")
                    break
                
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    
                    if not line:
                        continue
                    
                    print(f"Received from {addr}: {line}")
                    
                    hex_parts = line.split()
                    if not hex_parts:
                        continue
                    
                    msg_type = hex_parts[0].lower()
                    
                    if msg_type == '20':  # Plate
                        self.handle_plate(conn, hex_parts)
                    elif msg_type == '40':  # WantHeartbeat
                        self.handle_want_heartbeat(conn, hex_parts)
                    elif msg_type == '80':  # IAmCamera
                        self.handle_iam_camera(conn, hex_parts)
                    elif msg_type == '81':  # IAmDispatcher
                        self.handle_iam_dispatcher(conn, hex_parts)
                    else:
                        # Unknown message type
                        self.send_error_and_disconnect(conn, "illegal msg")
                        return
                        
        except Exception as e:
            print(f"Error handling client {addr}: {e}")
        finally:
            self.disconnect_client(conn)
            print(f"Client {addr} disconnected")

    def start(self):
        self.running = True
        
        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(target=self.heartbeat_worker, daemon=True)
        self.heartbeat_thread.start()
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self.host, self.port))
            server.listen(150) 
            
            print(f"Speed camera server listening on {self.host}:{self.port}")
            
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

def main():
    server = SpeedCameraServer()
    server.start()

if __name__ == '__main__':
    main()







'''

host = '127.0.0.1'
port = 12345 
plates = {}
camera_connections = {}

roads_with_camera = defaultdict(lambda:{
    "limit": None , 
    "mile": set(), 
    "vehicles": defaultdict(list)
})

def error():
    return b"41"

def speed(dist, timestamp):
    s = dist/timestamp
    print("speed : ", s)
    return s
def handle_plates( conn,name,timestamp):
    camera = camera_connections[conn]

    road = camera['road']
    mile  = camera['mile']
    roads_with_camera[road]['vehicles'][mile].append({
        "plate": name, 
        "timestamp": timestamp
    })
    

def parse_plates(hex_str):
    data = hex_str.strip().split()

    timestamp_bytes = bytes.fromhex(' '.join(data[-4:]))
    timestamp = int.from_bytes(timestamp_bytes, byteorder='big')

    plate_bytes = bytes.fromhex(' '.join(data[:-4]))
    try:
        plate = plate_bytes.decode('utf-8', errors='replace')
    except:
        plate = ''

    
    return plate,timestamp
    


def send_heartbeat():
    return b"\nworking!"
import time
def get_heartbeat_data(data):
    
    if not data:
        return 
    d = bytes.fromhex(data)
    number = int.from_bytes(d, byteorder='big')
    totaltime = number *0.1 

    for _ in range(5):
        yield send_heartbeat()
        time.sleep(totaltime)






def handle_camera(conn,road,mile,limit):
    
    camera_connections[conn]  = {"road": road, "mile":mile, "limit": limit}

    if roads_with_camera[road]['limit'] is None:
        roads_with_camera[road]['limit'] = limit 

    roads_with_camera[road]['mile'].add(mile)




    

    


def parse_camera(data):
    data = data.strip().split() 

    road_bytes = bytes.fromhex(' '.join(data[0:2]))  
    road = int.from_bytes(road_bytes,byteorder='big')
    mile_bytes = bytes.fromhex(' '.join(data[2:4])) 
    mile = int.from_bytes(mile_bytes, byteorder='big')
    limit_bytes = bytes.fromhex(' '.join(data[4:6])) 
    limit = int.from_bytes(limit_bytes, byteorder='big')


    

    return road , mile, limit

def handle_roads(roads):
    if  not roads:
        return 
    
    #print("num roads : ", num_roads)
    print("roads : ", roads)




def parse_roads(data):
    data = data.strip().split()

    roads = []
    for i in range(0, len(data), 2):
        two_bytes = bytes.fromhex(f"{data[i]}{data[i+1]}")
        road = int.from_bytes(two_bytes, byteorder='big')
        roads.append(road)
    return   roads 

from collections import defaultdict

def speeding_vehicle(road):
    violators = []
    data = roads_with_camera[road]
    limit = data['limit']  # assumed in miles per hour
    veh_by_mile = data['vehicles']
    plate_timestamps = defaultdict(list)

    # Group all (mile, timestamp) records per plate
    for mile, veh in veh_by_mile.items():
        for v in veh:
            plate = v['plate']
            timestamp = v['timestamp']
            plate_timestamps[plate].append((mile, timestamp))

    for plate, records in plate_timestamps.items():
        records.sort()
        for i in range(len(records) - 1):
            mile1, t1 = records[i]
            mile2, t2 = records[i + 1]

            if t1 == t2:
                continue  

            distance = abs(mile2 - mile1) 
            time_seconds = abs(t2 - t1)
            speed_mph = (distance / time_seconds)  *3600 # convert to miles/hour
            print("distance: ", distance)
            print("time : ", speed_mph)

            print(f"[{plate}] Speed: {speed_mph:.2f} mph")

            if speed_mph > limit:
                violators.append({
                    'plate': plate,
                    'road': road,
                    'mile1': mile1,
                    'timestamp1': t1,
                    'mile2': mile2,
                    'timestamp2': t2,
                    'speed': round(speed_mph, 2)
                })
                break 

    print("violators: ", violators)
    return violators


def handle_client(conn,addr):
    print(f"Connected to : {addr}")
    try:
        while True:
            data = conn.recv(4096)
            print("data : ", data.decode())
            temp  = data.decode() 
            
            first = temp.split()[0]

            print("first byte : ", first)

            if first == '40' :
                
                for heartbeat_msg in get_heartbeat_data(' '.join(temp.split()[1:])):
                    print("Sending:", heartbeat_msg)
                    conn.sendall(heartbeat_msg)

            elif first == '10':
                m =  error()
                conn.sendall(m)
            elif first== '20':
                name,timestamp =parse_plates(' '.join(temp.split()[2:]))
                handle_plates(conn, name,timestamp)
                print("connections: ", camera_connections)
                print("roads_with camera: ", roads_with_camera)

            elif first == '21':
                pass 

                
            elif first == '80':
                road,mile,limit = parse_camera(' '.join(temp.split()[1:]))
                handle_camera(conn,road,mile,limit)

            elif first == '81':
                roads = parse_roads(' '.join(temp.split()[2:]))
                handle_roads( roads)
                r  = roads[0]
                v = speeding_vehicle(r)




                
    except Exception as  e :
        print(f"Error with {addr}: {e}")

    finally:
        conn.close()

def start_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host,port))
        server.listen()
        print(f"Server listening {host} : {port}")
        
        while True:
            conn, addr = server.accept() 
            thread = threading.Thread(target=handle_client, args=(conn,addr), daemon=True)
            thread.start()



if __name__ == '__main__':
    start_server()



'''