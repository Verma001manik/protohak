import socket 
import threading 
import json 
from collections import defaultdict
import heapq
job_store ={}
queues = defaultdict(list) 
aborted_jobs = set()
deleted_jobs = set()

class JobServer:

    def __init__(self, host='127.0.0.1', port=12345):
        self.host = host 
        self.port = port 

        #request contain field name : request and type as one of the below
        self.request_type = ['put', 'get','delete','abort']
        #contains status field and one of the below
        self.response_type = ['ok','error','no-job']
        self.unique_job_id = 1 

    

    def error_request(self):
        #do not close connect if even invalid request
        msg = {"status":"error","error":"Unrecognised request type."}
        return msg 
    

    def is_valid(self,data):
        #only for request validation not response
        #print("is_valid : data ", data)
        data = json.loads(data)

        for k,v in data.items():
            #print("key : ", k)
            #print("value: ", v)
            if k == 'request':
                return True
            
            if v  in self.request_type:
                return True
            
        
        return False
    
    def put(self,queue_name, job_data, pri):
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
        return {"status": "ok", "id": job_id}
    

    def get(self,queue_list):
        if not queue_list or len(queue_list) < 1 :
            print("no queue is given")
            return 
        for queue_name in queue_list:
            heap = queues[queue_name]

            while heap :
                _, job_id = heapq.heappop(heap)
                if job_id in deleted_jobs:
                    continue
                return job_store[job_id]

        return {"status": "no-job"}
    

    def abort(self,job_id):
        if job_id in job_store:
            job_store[job_id]["status"] = "aborted"
            aborted_jobs.add(job_id)
            return {"status": "ok"}
        return  {"status": "not-found"}
    def delete(self,job_id):
        if job_id in job_store:
            job_store[job_id]["status"] = "deleted"

            deleted_jobs.add(job_id)
            return {"status": "ok"}
        return  {"status": "not-found"}
    
    def get_request_type(self,data):
        if not data:
            return
        print("parse_data: initial ", data)
        data = json.loads(data)
        for k , v in data.items():
            if v == 'put':
                return "put"
            elif v== 'get':
                return "get"
            elif v== 'abort':
                return "abort"
            
            else:
                return "delete"
            
    def handle_put(self,data):
        #{"request":"put","queue":"queue1","job":{"title":"example-job"},"pri":123}
        data =json.loads(data)
        queue_name = None 
        pri = None 
        job_data  = None 

        for k,v in data.items():
            if k== 'queue':
                queue_name = v 
            elif k == 'job':
                job_data = v 
            elif k == 'pri':
                pri = v 

        
        if not queue_name or not pri or not job_data :
            print("name or pri or job data not available")
            return 
        res = self.put(queue_name,job_data,pri)
        #print("handle_put() res ::", res)

        #print("queues : ", queues)
        return res 
        
    def handle_abort(self,data):
        data = json.loads(data)
        #{"request":"abort","id":12345}
        job_id  =None 
        for k,v in data.items():
            if k== "id":
                job_id = v 

        if not job_id:
            print("job id not given :")
            return 
        
        res = self.abort(job_id)
        print("jobs  : ",job_store  )
        return res 
    

    def handle_client(self,conn,addr):
        print(f"Client Connected from {addr}")
        try:
            while True:

                data = conn.recv(4096)
                if not data :
                    return 
                print("data received : ", data.decode())
                if not self.is_valid(data.decode()):
                    msg = self.error_request()
                    msg = json.dumps(msg)
                    conn.sendall(msg.encode())

                data =data.decode()
                request_type = self.get_request_type(data)
                #print("request_type : ", request_type)
                if request_type == 'put':
                    res=  self.handle_put(data)
                    res = json.dumps(res)
                    res = res.encode()
                    conn.sendall(res)
                elif request_type == 'get':
                    pass 

                elif request_type == 'abort':
                    res =self.handle_abort(data)
                    res =json.dumps(res)
                    res = res.encode()
                    conn.sendall(res)

                elif request_type == 'delete':
                    pass 
            
        except Exception as e : 
            print(f"Error handling client {addr}: {e}")

        finally :
            print(f"Closing connection to {addr}")
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