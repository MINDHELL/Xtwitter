import socket
import threading

HOST = "0.0.0.0"
PORT = 8080

def start_health_check():
    """Start a TCP health check server to prevent bot shutdown on Koyeb."""
    def run_server():
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            server.bind((HOST, PORT))
            server.listen(5)
            print(f"✅ Health check running on port {PORT}")

            while True:
                conn, _ = server.accept()
                conn.sendall(b"HTTP/1.1 200 OK\n\nBot is running")
                conn.close()

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
