import _thread
import socket
import network
import time
#_thread.start_new_thread(background_task, ())


class DNSServer:
    def __init__(self, ip):
        self.ip = ip
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        self.sock.bind(('0.0.0.0', 53))   
    def _build_response(self, data):
        tid = data[:2]                     # transaction ID, echoed back
        flags = b'\x81\x80'                # standard response, no error
        qdcount = data[4:6]                # question count, echoed back
        ancount = b'\x00\x01'              # 1 answer
        nscount = b'\x00\x00'
        arcount = b'\x00\x00'
        header = tid + flags + qdcount + ancount + nscount + arcount

        question = data[12:]               # copy question section as-is


