import socket 
import threading 
import json 
from collections import defaultdict
import heapq

job_store = {}
queues = defaultdict(list) 
aborted_jobs = set()
deleted_jobs = set()
client_jobs = defaultdict(set) 
waiting_clients = defaultdict(list)  
lock = threading.Lock()  

class JobServer:

    def __init__(self, host='127.0.0.1', port=12345):
        self.host = host 
        self.port = port 
        self.request_type = ['put', 'get','delete','abort']
        self.response_type = ['ok','error','no-job']
        self.unique_job_id = 1 
        self.client_counter = 0  

    def get_next_client_id(self):  
        self.client_counter += 1
        return self.client_counter

    def error_request(self):
        msg = {"status":"error","error":"Unrecognised request type."}
        return msg 

    def is_valid(self,data):
        try: 
            data = json.loads(data)
            return 'request' in data and data['request'] in self.request_type
        except:
            return False
    
    def put(self,queue_name, job_data, pri):
        with lock: 
            job_id = self.unique_job_id
            self.unique_job_id += 1 
            job = {
                "id":job_id,
                "job": job_data,
                "pri": pri, 
                "queue": queue_name,
                "status": "active"
            }
            job_store[job_id] = job 
            heapq.heappush(queues[queue_name], (-pri, job_id))
            
            self.notify_waiting_clients(queue_name)
            
            return {"status": "ok", "id": job_id}

    def notify_waiting_clients(self, queue_name):  
        if queue_name in waiting_clients and waiting_clients[queue_name]:
            while waiting_clients[queue_name] and queues[queue_name]:
                client_id, conn = waiting_clients[queue_name].pop(0)
                job = self.get_for_client([queue_name], client_id)
                if job and job["status"] == "ok":
                    try:
                        response = json.dumps(job) + "\n" 
                        conn.sendall(response.encode())
                    except:
                        self.abort_job_internal(job["id"], client_id)

    def get_for_client(self, queue_list, client_id): 
        for queue_name in queue_list:
            heap = queues[queue_name]
            while heap:
                _, job_id = heapq.heappop(heap)
                if job_id in deleted_jobs:
                    continue
                
                # NEW: assign job to client
                client_jobs[client_id].add(job_id)
                
                msg = {"status": "ok","id": job_id, "job": job_store[job_id]['job'], 
                       "pri": job_store[job_id]['pri'], "queue":job_store[job_id]['queue']}
                return msg 
        return {"status": "no-job"}

    def get(self, queue_list, wait=False, client_id=None, conn=None):  
        with lock:  
            if not queue_list or len(queue_list) < 1:
                print("no queue is given")
                return {"status": "error", "error": "No queues specified"}
            
            result = self.get_for_client(queue_list, client_id)
            
            if result["status"] == "ok" or not wait:
                return result
            
            for queue_name in queue_list:
                waiting_clients[queue_name].append((client_id, conn))
            return None  # Signal to wait

    def abort_job_internal(self, job_id, client_id): 
        if job_id not in job_store or job_id in deleted_jobs:
            return {"status": "no-job"}
        
        if job_id not in client_jobs[client_id]:
            return {"status": "error", "error": "Not your job"}
        
        client_jobs[client_id].discard(job_id)
        job = job_store[job_id]
        heapq.heappush(queues[job["queue"]], (-job["pri"], job_id))
        self.notify_waiting_clients(job["queue"])
        
        return {"status": "ok"}

    def abort(self, job_id, client_id=None):  
        with lock:  
            return self.abort_job_internal(job_id, client_id)

    def delete(self, job_id):
        with lock:  # FIX: thread safety
            if not job_id:
                print("need to provide job id ")
                return {"status": "error", "error": "No job ID provided"}
            
            if job_id in job_store and job_id not in deleted_jobs:  
                job_store[job_id]["status"] = "deleted"
                deleted_jobs.add(job_id)
                
                for client_id in client_jobs:
                    client_jobs[client_id].discard(job_id)
                
                return {"status": "ok"}
            return {"status": "no-job"} 

    def cleanup_client(self, client_id):  
        with lock:
            jobs_to_abort = list(client_jobs[client_id])
            for job_id in jobs_to_abort:
                if job_id in job_store and job_id not in deleted_jobs:
                    job = job_store[job_id]
                    heapq.heappush(queues[job["queue"]], (-job["pri"], job_id))
                    self.notify_waiting_clients(job["queue"])
            
            client_jobs[client_id].clear()
            
            # Remove from waiting lists
            for queue_name in waiting_clients:
                waiting_clients[queue_name] = [
                    (cid, conn) for cid, conn in waiting_clients[queue_name] 
                    if cid != client_id
                ]
    
    def get_request_type(self,data):
        if not data:
            return
        print("parse_data: initial ", data)
        data = json.loads(data)
        return data.get('request') 
            
    def handle_put(self,data):
        data = json.loads(data)
        queue_name = data.get('queue')
        pri = data.get('pri') 
        job_data = data.get('job')
        
        if not queue_name or pri is None or not job_data: 
            return {"status": "error", "error": "Missing required fields"}
            
        res = self.put(queue_name, job_data, pri)
        return res 
        
    def handle_abort(self, data, client_id): 
        data = json.loads(data)
        job_id = data.get('id')

        if not job_id:
            return {"status": "error", "error": "Missing job ID"}
        
        res = self.abort(job_id, client_id)  
        return res 
    
    def handle_delete(self,data):
        data = json.loads(data)
        job_id = data.get('id')

        if not job_id:
            return {"status": "error", "error": "Missing job ID"}
            
        print("jobs before deleting  : ",job_store)
        res = self.delete(job_id)
        print("jobs after deleting : ",job_store)
        return res 

    def handle_get(self, data, client_id, conn):  
        data = json.loads(data)
        queue_list = data.get('queues', [])
        wait = data.get('wait', False)  
        
        if not queue_list or len(queue_list) < 1:
            return {"status": "error", "error": "No queues specified"}
        
        res = self.get(queue_list, wait, client_id, conn)  
        print("res from self.get(): ", res)
        return res 

    def handle_client(self, conn, addr):
        client_id = self.get_next_client_id()  
        print(f"Client {client_id} Connected from {addr}")
        
        try:
            while True:
                data = conn.recv(4096)
                if not data:
                    return 
                print("data received : ", data.decode())
                
                if not self.is_valid(data.decode()):
                    msg = self.error_request()
                    msg = json.dumps(msg) + "\n" 
                    conn.sendall(msg.encode())
                    continue

                data = data.decode()
                request_type = self.get_request_type(data)
                
                if request_type == 'put':
                    res = self.handle_put(data)
                    res = json.dumps(res) + "\n"  
                    conn.sendall(res.encode())
                    
                elif request_type == 'get':
                    res = self.handle_get(data, client_id, conn)  
                    if res is not None:  
                        res = json.dumps(res) + "\n"  
                        conn.sendall(res.encode())

                elif request_type == 'abort':
                    res = self.handle_abort(data, client_id) 
                    res = json.dumps(res) + "\n"  
                    conn.sendall(res.encode())

                elif request_type == 'delete':
                    res = self.handle_delete(data)
                    res = json.dumps(res) + "\n"  
                    conn.sendall(res.encode())

        except Exception as e: 
            print(f"Error handling client {client_id} {addr}: {e}")

        finally:
            print(f"Closing connection to client {client_id} {addr}")
            self.cleanup_client(client_id)  
            conn.close()

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
    s = JobServer()
    s.start()