from httpHelper import parseUrl

def normalise(target):
    scheme, hostname, port, path, query = parseUrl(target)
    normalisedTarget = f'{scheme}://{hostname}:{port}{path}'
    if query:
        normalisedTarget += f'?{query}'
    return normalisedTarget

def safeClose(socket):
    try:
        socket.close()
    except Exception:
        pass

def resBodyIsExpected(method, status):
    return not (method == 'HEAD' or status in ['204', '304'])

def log(addr, cache, date, request, status, bytes):
    host, port = addr
    print(f'{host} {port} {cache} [{date}] "{request}" {status} {bytes}')
