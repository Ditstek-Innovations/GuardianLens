import socket
import ipaddress
import concurrent.futures

def scan_port(ip, port, timeout=0.5):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        result = sock.connect_ex((str(ip), port))
        if result == 0:
            return ip, port
    except Exception:
        pass
    finally:
        sock.close()
    return None

def scan_subnet(subnet):
    network = ipaddress.IPv4Network(subnet, strict=False)
    hosts = list(network.hosts())
    ports = [554, 8554, 8080]
    
    found = []
    print(f"Scanning {len(hosts)} hosts...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = []
        for host in hosts:
            for port in ports:
                futures.append(executor.submit(scan_port, host, port))
                
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                found.append(res)
                print(f"Open port found: {res[0]}:{res[1]}")
                
    print(f"Total open ports found: {len(found)}")

if __name__ == "__main__":
    scan_subnet("192.168.0.0/24")
