import socket
from enums import CacheStatus
from httpHelper import parseUrl

def normalise(target: str) -> str:
    scheme, hostname, port, path, query = parseUrl(target)
    normalisedTarget = f'{scheme}://{hostname}:{port}{path}'
    if query:
        normalisedTarget += f'?{query}'
    return normalisedTarget

def safeClose(socket: socket.socket) -> None:
    try:
        socket.close()
    except Exception:
        pass

def resBodyIsExpected(method: str, status: str) -> bool:
    return not (method == 'HEAD' or status in ['204', '304'])

def log(addr: tuple[str, int], cache: CacheStatus, date: str, request: str, status: str, numBytes: int) -> None:
    host, port = addr
    print(f'{host} {port} {cache.value} [{date}] "{request}" {status} {numBytes}')
