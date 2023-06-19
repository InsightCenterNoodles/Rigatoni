import socket
import re
import threading
import logging


class ByteServer(object):
    """Server to Host URI Bytes.

    This is helpful for large meshes and images that would
    otherwise be too large to send using CBOR and the websocket connection. The server maps
    a tag to a buffer, and the client can request the buffer using the url that includes the
    tag.
    
    Attributes:
        host (str): IP address for server
        port (int): port server is listening on
        socket (socket): socket connection 
        buffers (dict): mapping tag to buffer
        _next_tag (int): next available tag for a buffer
        url (str): base url to reach server without tag
        thread (Thread): background thread server is running in
        running (bool): flag indicating whether server is running
    """

    def __init__(self, port: int = 8000):
        """Constructor to create the server
        
        Args:
            port (int): port to listen and host on
        """

        name = socket.gethostname()
        try:  # supposed to work without .local, but had to add to match system preferences - sharing
            self.host = socket.gethostbyname(name)
        except socket.gaierror:
            self.host = socket.gethostbyname(f"{name}.local")

        self.port = port
        self.socket = None
        self.buffers = {}
        self._next_tag = 0
        self.url = f"http://{self.host}:{port}"

        self.thread = threading.Thread(target=self._run, args=())
        self.running = True
        self.thread.start()

    def _get_tag(self):
        """Helper to get next tag for a buffer"""

        tag = self._next_tag
        self._next_tag += 1
        return str(tag)

    def get_buffer(self, uri: str):
        """Helper to get bytes for a URI
        
        Mostly used in geometry creation for exporting as of right now

        Args:
            uri (str): uri for bytes
        """

        m = re.search(f'(?<={self.port}/).+\Z', uri)
        if m:
            tag = m.group(0)
            buffer_bytes = self.buffers[tag]
            return buffer_bytes
        else:
            raise ValueError("Invalid HTTP Request")

    def _run(self):
        """Main loop to run in thread
        
        Runs the server and listens for byte requests using HTTP protocol
        """

        # Create socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))

        logging.info(f"IP Address for Byte Server: {server_socket.getsockname()}")

        self.socket = server_socket

        server_socket.settimeout(.5)  # timeout to check if still running
        server_socket.listen(1)
        logging.info(f'Byte server listening on port {self.port}...')

        while self.running:
            try:
                # Wait for client connections - this is blocking
                client_connection, client_address = server_socket.accept()

                # Get the client request
                request = client_connection.recv(1024).decode()
                logging.info(f"Request: {request}")

                # Try to get tag from request with regex
                m = re.search('(?<=GET /)(.+?)(?= HTTP)', request)
                try:
                    tag = m.group(0)
                    select_bytes = self.buffers[tag]
                    header = f'HTTP/1.0 200 OK\r\nContent-Type: application/octet-stream\r\n' \
                             f'Content-Length: {len(select_bytes)}\n\n'
                    response = bytearray(header.encode()) + select_bytes
                except Exception:
                    header = f'HTTP/1.0 500 FAIL'
                    response = header.encode()

                # Send HTTP response
                client_connection.sendall(response)
                client_connection.close()

            except socket.timeout:
                pass
        # Clean up and close socket
        self.socket.close()

    def add_buffer(self, buffer) -> str:
        """Add buffer to server and return url to reach it
        
        Args:
            buffer (bytes): bytes to add as buffer
        """

        tag = self._get_tag()
        self.buffers[tag] = buffer
        url = f"{self.url}/{tag}"
        logging.info(f"Adding buffer to byte server: {url}")

        return url

    def shutdown(self):
        """Stop running thread"""

        self.running = False
        self.thread.join()
