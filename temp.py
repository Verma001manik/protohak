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
