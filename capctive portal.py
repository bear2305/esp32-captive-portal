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

        # Answer: name = pointer to question (0xC00C), type A, class IN,
        # short TTL, then the 4 raw IP bytes
        answer = b'\xC0\x0C'
        answer += b'\x00\x01'              # TYPE A
        answer += b'\x00\x01'              # CLASS IN
        answer += b'\x00\x00\x00\x3C'      # TTL = 60s
        answer += b'\x00\x04'              # RDLENGTH = 4 bytes
        answer += bytes(map(int, self.ip.split('.')))

        return header + question + answer

    def poll(self):
        """Call this repeatedly from your main loop — non-blocking."""
        try:
            data, addr = self.sock.recvfrom(512)
        except OSError:
            return  # no packet waiting
        try:
            self.sock.sendto(self._build_response(data), addr)
        except Exception as e:
            print("DNS error:", e)
            
            
#___________________________MAIN______________________________

AP_SSID = "ESP32-Setup"
AP_PASSWORD = ""  # leave blank for open network; use 8+ chars for WPA2

# --- Set up access point ---
ap = network.WLAN(network.AP_IF)
ap.active(True)
if AP_PASSWORD:
    ap.config(essid=AP_SSID, password=AP_PASSWORD, authmode=network.AUTH_WPA_WPA2_PSK)
else:
    ap.config(essid=AP_SSID, authmode=network.AUTH_OPEN)

ap.ifconfig(('192.168.4.1', '255.255.255.0', '192.168.4.1', '192.168.4.1'))
AP_IP = ap.ifconfig()[0]
print("AP started:", AP_SSID, "| IP:", AP_IP)

dns = DNSServer(AP_IP)
#nnededs threadin ________________________________
PORTAL_HTML = """<!DOCTYPE html>
<html><head><title>WiFi Setup</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{font-family:sans-serif;padding:20px;background:#f2f2f2}
h2{color:#333}
input{width:100%;padding:10px;margin:8px 0;box-sizing:border-box}
button{width:100%;padding:12px;background:#0078d7;color:#fff;border:none;border-radius:4px}
</style></head>
<body>
<h2>Connect ESP32 to WiFi</h2>
<form method="POST" action="/connect">
<input type="text" name="ssid" placeholder="WiFi Network Name" required>
<input type="password" name="password" placeholder="WiFi Password">
<button type="submit">Connect</button>
</form>
</body></html>
"""


def url_decode(s):
    s = s.replace('+', ' ')
    result = ''
    i = 0
    while i < len(s):
        if s[i] == '%' and i + 2 < len(s):
            result += chr(int(s[i + 1:i + 3], 16))
            i += 3
        else:
            result += s[i]
            i += 1
    return result


def parse_form(body):
    params = {}
    for pair in body.split('&'):
        if '=' in pair:
            k, v = pair.split('=', 1)
            params[url_decode(k)] = url_decode(v)
    return params


def handle_connect(params):
    ssid = params.get('ssid', '')
    password = params.get('password', '')
    print("Attempting to connect to:", ssid)

    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    sta.connect(ssid, password)

    for _ in range(20):
        if sta.isconnected():
            print("Connected! IP:", sta.ifconfig()[0])
            return True
        time.sleep(0.5)

    print("Failed to connect")
    return False




def serve():
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(4)
    s.setblocking(False)
    print("HTTP server listening on port 80")

    while True:
        dns.poll()  # non-blocking DNS handling each loop tick

        try:
            mt = s.accept()
            client, client_addr = mt
            a=client
            b=client_addr
        except OSError:
            time.sleep_ms(20)
            continue

        client.setblocking(True)
        try:
            request = client.recv(1024).decode()
        except Exception:
            client.close()
            continue

        if not request:
            client.close()
            continue

        try:
            first_line = request.split('\r\n')[0]
            method, path, _ = first_line.split(' ')
        except Exception:
            client.close()
            continue

        if method == 'POST' and path == '/connect':
            body = request.split('\r\n\r\n', 1)[1] if '\r\n\r\n' in request else ''
            params = parse_form(body)
            success = handle_connect(params)
            if success:
                response_body = "<h2>Connected successfully! You can close this page.</h2>"
            else:
                response_body = "<h2>Connection failed. Please <a href='/'>try again</a>.</h2>"
            response = ("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n"
                        "Connection: close\r\n\r\n" + response_body)
        else:
            # ANY other path (including OS captive-portal probe URLs)
            # gets the setup page — this is the redirect trick.
            response = ("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n"
                        "Connection: close\r\n\r\n" + PORTAL_HTML)

        try:
            client.send(response)
            #a,b =s.accept()
            print(f"\n a of is:   {a} and manuel compare a and {mt[0]}is : \n b of is :  {b}")
         
            
        except Exception as e:
            print("Send error:", e)
        client.close()
        
serve()

# s.appct is : (<socket>, ('192.168.4.4', 39664)) 
# a of is:   <socket> 
# b of is :  ('192.168.4.4', 39662)

# s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#  client, client_addr = s.accept()
 # s.accept().send(response)
#  s.accept().close()
