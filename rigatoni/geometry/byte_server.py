import socket
import re
import threading


class ByteServer(object):
    """Server to Host URI Bytes
    
    Attributes:
        host (str): IP address for server
        port (int): port server is listening on
        socket (socket): socket connection 
        buffers (dict): mapping tag to buffer
        next_tag (int): next available tag for a buffer
        url (str): base url to reach server without tag
        thread (Thread): background thread server is running in
        running (bool): flag indicating whether server is running
    """


    def __init__(self, port: int=8000):
        """Constructor
        
        Args:
            port (int): port to listen on
        """

        name = socket.gethostname()
        self.host = socket.gethostbyname(f"{name}.local") 
        # supposed to work without this local thing, but I had to add so 
        # it would match the sharing name in system preferences
        self.port = port
        self.socket = None
        self.buffers = {}
        self.next_tag = 0
        self.url = f"http://{self.host}:{port}"

        self.thread = threading.Thread(target=self.run, args=())
        self.running = True
        self.thread.start()

    def get_tag(self):
        """Helper to get next tag"""

        tag = self.next_tag
        self.next_tag += 1
        return str(tag)


    def get_buffer(self, uri: str):
        """Helper to get bytes for a uri
        
        Mostly used in geometry creation for exporting as of right now

        Args:
            uri (str): uri for bytes
        """

        m = re.search(f'(?<={self.port}\/).+\Z', uri)
        if m:
            tag = m.group(0)
            bytes = self.buffers[tag]
            return bytes
        else:
            raise Exception("Invalid HTTP Request")
        


    def run(self):
        """Main loop to run in thread
        
        Runs the server and listens for byte requests
        Uses HTTP protocol 
        """

        # Create socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))

        print(f"IP Address: {server_socket.getsockname()}")

        self.socket = server_socket

        server_socket.listen(1)
        print(f'Listening on port {self.port} ...')

        while self.running:
            # Wait for client connections
            print("Waiting for connection...")
            client_connection, client_address = server_socket.accept()

            # Get the client request
            request = client_connection.recv(1024).decode()
            print(f"Request: {request}")

            # Try to get tag from request with regex
            m = re.search('(?<=GET \/)(.+?)(?= HTTP)', request)
            if m:
                tag = m.group(0)
                bytes = self.buffers[tag]
                # response = f'HTTP/1.0 200 OK\n\n{bytes}'
                header = f'HTTP/1.0 200 OK\r\nContent-Type: application/octet-stream\r\nContent-Length: {len(bytes)}\n\n'
                response = bytearray(header.encode()) + bytes
            else:
                header = f'HTTP/1.0 500 FAIL'
                response = header.encode()

            # Send HTTP response
            # client_connection.sendall(response.encode())
            # print(f'Response:\n{response}')
            client_connection.sendall(response)
            client_connection.close()

        # Clean up and close socket
        self.socket.close()

    
    def add_buffer(self, buffer) -> str:
        """Add buffer to server and return url to reach it
        
        Args:
            buffer (bytes): bytes to add as buffer
        """

        tag = self.get_tag()
        self.buffers[tag] = buffer
        url = f"{self.url}/{tag}"
        print(f"Adding Buffer: {url}")

        return url


    def shutdown(self):
        """Stop running thread"""

        self.running = False
        self.thread.join()


def main():
    """Main method for testing"""

    server = ByteServer(port=60000)
    server.add_buffer('HTTP/1.0 200 OK\n\nTEST TEST TEST'.encode())
    server.add_buffer(b'TESTING BYTES')


if __name__ == "__main__":
    main()
