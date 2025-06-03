import asyncio 
host = '127.0.0.1' 
port = 65432 


async def handle_client(reader,writer):
	addr = writer.get_extra_info('peername') 
	print(f"Connected by {addr}" ) 
	try :
		while True:
			data = await reader.read(1024) 
			if not data :
				break 
			print(f"received: {data.decode()}") 
			writer.write(data) 
			await writer.drain()
	except Exception as e :
		print(f"Error: {e}") 
	
	finally:
		print(f"Closing connection to {addr} " ) 
		writer.close()
		await writer.wait_closed()
		
		
async def main():
	server = await asyncio.start_server(handle_client, host,port) 
	addr  = server.sockets[0].getsockname()
	print(f"Serving on {addr} ")
	
	async with server:
		await server.serve_forever()


asyncio.run(main()) 

