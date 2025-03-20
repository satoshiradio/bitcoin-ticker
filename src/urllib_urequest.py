import socket
import gc

def urlopen(url, data=None, method="GET"):
    gc.collect()  
    if data is not None and method == "GET":
        method = "POST"
        
    try:
        proto, dummy, host, path = url.split("/", 3)
    except ValueError:
        proto, dummy, host = url.split("/", 2)
        path = ""
        
    if proto == "http:":
        port = 80
    elif proto == "https:":
        import tls
        port = 443
    else:
        raise ValueError("Unsupported protocol: " + proto)

    if ":" in host:
        host, port = host.split(":", 1)
        port = int(port)

    ai = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)
    ai = ai[0]  

    s = socket.socket(ai[0], ai[1], ai[2])
    
    try:
        s.connect(ai[-1])
        if proto == "https:":
            context = tls.SSLContext(tls.PROTOCOL_TLS_CLIENT)
            context.verify_mode = tls.CERT_NONE
            s = context.wrap_socket(s, server_hostname=host)

        s.write(b"%s /%s HTTP/1.0\r\nHost: %s\r\n" % (method.encode(), path.encode(), host.encode()))
        
        if data:
            s.write(b"Content-Length: %d\r\n" % len(data))
        
        s.write(b"\r\n")
        
        if data:
            s.write(data)

        while True:
            l = s.readline()
            if not l or l == b"\r\n":
                break
            if l.startswith(b"Transfer-Encoding:") and b"chunked" in l:
                raise ValueError("Unsupported Transfer-Encoding: chunked")
            elif l.startswith(b"Location:"):
                raise NotImplementedError("Redirects not yet supported")
    except OSError:
        s.close()
        raise

    return s
