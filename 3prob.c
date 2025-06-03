#include<stdio.h>
#include<stdlib.h>
#include<string.h> 
#include<unistd.h> 
#include<netinet/in.h>
#include<sys/types.h>
#include<sys/socket.h>
#include<signal.h>

void handle_client(int client_socket){
	char buffer[1024]= {0} ;
	char *ack = "ACK";
	read(client_socket,buffer, sizeof(buffer))  ;
	printf("Client says :%s \n", buffer);
	send(client_socket,ack,strlen(ack), 0 );
	close(client_socket);
	exit(0) ;
	
	


}
int main(){
	int server_fd, client_socket;
	struct sockaddr_in address;
	int addrlen = sizeof(address) ;
	signal(SIGCHLD, SIG_IGN);
	
	server_fd = socket(AF_INET, SOCK_STREAM ,0 );
	
	address.sin_family= AF_INET;
	address.sin_addr.s_addr= INADDR_ANY;
	address.sin_port = htons(12345);
	
	bind(server_fd, (struct sockaddr * )& address, sizeof(address)) ;
	listen(server_fd, 5) ;
	printf("Server listening on 12345 port : \n");
	
	while(1){
		
		client_socket = accept(server_fd, (struct sockaddr * )&address, (socklen_t*)&addrlen) ;
		if (client_socket < 0 ){
			perror("accept failed");
			continue;
			
		}
		pid_t pid = fork();
		if (pid==0 ){
			close(server_fd);
			handle_client(client_socket);
			
		}
		else{
			close(client_socket) ;
			
			
		}
		
	}
	close(server_fd) ;
	return 0 ;
	
	
	
	

}

