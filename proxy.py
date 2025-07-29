# coding: utf-8
from errorResponse import *
from cache import *
from httpHelper import *
from util import *
from enums import *

from datetime import datetime, timezone
import sys
import threading
import socket

ZID = 'z5420380'
BUFFER_LEN = 8192

### Command Line Args
if len(sys.argv) != 5:
    print(f'Usage: python3 {sys.argv[0]} <port> <timeout> <maxObjectSize> <maxCacheSize>')
    sys.exit(1)
PROXY_PORT = int(sys.argv[1])
TIMEOUT = int(sys.argv[2])
MAX_OBJECT_SIZE = int(sys.argv[3])
MAX_CACHE_SIZE = int(sys.argv[4])

def handleClient(clientSocket: socket.socket, addr: tuple[str, int]) -> None:
    while True:
        cacheStatus = CacheStatus.NONE

        ### 2. Client Request
        try:
            clientRequest = clientSocket.recv(BUFFER_LEN)
            date = datetime.now(timezone.utc).astimezone().strftime('%d/%b/%Y:%H:%M:%S %z')
        except Exception:
            break
        if clientRequest == b'':
            break

        # Parse request
        reqStartLine, reqHeaders, reqBody = parseHttpMessage(clientRequest)
        method, target, reqProtocol = reqStartLine.split(' ')

        # Read body
        reqContentLength = getContentLength(reqHeaders, MessageType.REQUEST)
        connectionClosed, _, reqBody = readBody(reqBody, clientSocket, reqContentLength)
        if connectionClosed:
            break

        # Connection header
        # Proxy-Connection header is moved to Connection if necessary, and deleted
        if reqHeaders.get('connection') is None:
            reqHeaders['connection'] = reqHeaders.get('proxy-connection', [])
        if reqHeaders.get('proxy-connection') is not None:
            del reqHeaders['proxy-connection']
        connectionHeader = reqHeaders.get('connection')
        persistent = 'close' not in connectionHeader

        if method in ['GET', 'HEAD', 'POST']:
            _, hostname, port, path, query = parseUrl(target)
            if hostname == '':
                try:
                    response, status, numBytes = noHostErrorResponse(connectionHeader)
                    clientSocket.sendall(response)
                    log(addr, cacheStatus, date, reqStartLine, status, numBytes)
                except Exception:
                    break
                if persistent: continue
                else: break
            if hostname in ['127.0.0.1', 'localhost'] and int(port) == PROXY_PORT:
                try:
                    response, status, numBytes = misdirectedRequestErrorResponse(connectionHeader)
                    clientSocket.sendall(response)
                    log(addr, cacheStatus, date, reqStartLine, status, numBytes)
                except Exception:
                    break
                if persistent: continue
                else: break

            # Check cache
            if method == 'GET':
                cachedResponse = cache.lookup(normalise(target))
                if cachedResponse is not None:
                    cacheStatus = CacheStatus.HIT
                    try:
                        status, numBytes = getStatusAndBytes(cachedResponse)
                        clientSocket.sendall(cachedResponse)
                        log(addr, cacheStatus, date, reqStartLine, status, numBytes)
                    except Exception:
                        break
                else:
                    cacheStatus = CacheStatus.MISS

            transformedRequest = transformRequest(method, path, query, reqHeaders, reqProtocol, reqBody)

            ### 3. Proxy-Server Connection
            serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                serverSocket.connect((hostname, int(port)))
            except ConnectionRefusedError:
                safeClose(serverSocket)
                try:
                    response, status, numBytes = connectionRefusedErrorResponse(connectionHeader)
                    clientSocket.sendall(response)
                    log(addr, cacheStatus, date, reqStartLine, status, numBytes)
                except Exception:
                    break
                if persistent: continue
                else: break
            except socket.gaierror:
                safeClose(serverSocket)
                try:
                    response, status, numBytes = couldNotResolveErrorResponse(connectionHeader)
                    clientSocket.sendall(response)
                    log(addr, cacheStatus, date, reqStartLine, status, numBytes)
                except Exception:
                    break
                if persistent: continue
                else: break
            except Exception:
                safeClose(serverSocket)
                if persistent: continue
                else: break
            serverSocket.settimeout(TIMEOUT)

            ### 4. Client Request Forwarding
            try:
                serverSocket.sendall(transformedRequest)
            except Exception:
                safeClose(serverSocket)
                try:
                    response, status, numBytes = closedUnexpectedlyErrorResponse(connectionHeader)
                    clientSocket.sendall(response)
                    log(addr, cacheStatus, date, reqStartLine, status, numBytes)
                except Exception:
                    break
                if persistent: continue
                else: break

            ### 5. Server Response
            try:
                serverResponse = serverSocket.recv(BUFFER_LEN)
            except socket.timeout:
                safeClose(serverSocket)
                try:
                    response, status, numBytes = timeoutErrorResponse(connectionHeader)
                    clientSocket.sendall(response)
                    log(addr, cacheStatus, date, reqStartLine, status, numBytes)
                except Exception:
                    break
                if persistent: continue
                else: break
            except Exception:
                safeClose(serverSocket)
                try:
                    response, status, numBytes = closedUnexpectedlyErrorResponse(connectionHeader)
                    clientSocket.sendall(response)
                    log(addr, cacheStatus, date, reqStartLine, status, numBytes)
                except Exception:
                    break
                if persistent: continue
                else: break
            if serverResponse == b'':
                safeClose(serverSocket)
                try:
                    response, status, numBytes = closedUnexpectedlyErrorResponse(connectionHeader)
                    clientSocket.sendall(response)
                    log(addr, cacheStatus, date, reqStartLine, status, numBytes)
                except Exception:
                    break
                if persistent: continue
                else: break
            # Parse response
            resStartLine, resHeaders, resBody = parseHttpMessage(serverResponse)
            resStartLineComponents = resStartLine.split(' ', 2)
            if len(resStartLineComponents) == 2:
                resStartLineComponents.append('')
            resProtocol, status, reason = resStartLineComponents

            # Read body
            if resBodyIsExpected(method, status):
                resContentLength = getContentLength(resHeaders, MessageType.RESPONSE)
            else:
                resContentLength = 0
            connectionClosed, timedOut, resBody = readBody(resBody, serverSocket, resContentLength)
            if connectionClosed or timedOut:
                safeClose(serverSocket)
                try:
                    response, status, numBytes = closedUnexpectedlyErrorResponse(connectionHeader) if connectionClosed else timeoutErrorResponse(connectionHeader)
                    clientSocket.sendall(response)
                    log(addr, cacheStatus, date, reqStartLine, status, numBytes)
                except Exception:
                    break
                if persistent: continue
                else: break

            ### 6. Proxy-Server Connection Termination
            safeClose(serverSocket)

            ### 7. Server Response Forwarding
            resHeaders['connection'] = connectionHeader

            # Insert or Append 'Via'
            viaHeader = resHeaders.get('via', [])
            viaHeader.append(f'1.1 {ZID}')
            resHeaders['via'] = viaHeader

            resStartLine = f'{resProtocol} {status}'
            if reason:
                resStartLine += f' {reason}'
            transformedResponse = buildHttpMessage(resStartLine, resHeaders, resBody)

            try:
                clientSocket.sendall(transformedResponse)
                log(addr, cacheStatus, date, reqStartLine, status, len(resBody))
            except Exception:
                break

            # Cache response
            if method == 'GET' and status == '200':
                cache.cache(normalise(target), transformedResponse)

            ### 8. Client-Proxy Connection Termination
            if not persistent:
                break
        elif method == 'CONNECT':
            hostname, _, port = target.partition(':')
            if port != '443':
                try:
                    response, status, numBytes = invalidPortErrorResponse(connectionHeader)
                    clientSocket.sendall(response)
                    log(addr, cacheStatus, date, reqStartLine, status, numBytes)
                except Exception:
                    break
                if persistent: continue
                else: break
            if hostname == '':
                try:
                    response, status, numBytes = noHostErrorResponse(connectionHeader)
                    clientSocket.sendall(response)
                    log(addr, cacheStatus, date, reqStartLine, status, numBytes)
                except Exception:
                    break
                if persistent: continue
                else: break

            ### 3. Proxy-Server Connection
            serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                serverSocket.connect((hostname, 443))
            except ConnectionRefusedError:
                safeClose(serverSocket)
                try:
                    response, status, numBytes = connectionRefusedErrorResponse(connectionHeader)
                    clientSocket.sendall(response)
                    log(addr, cacheStatus, date, reqStartLine, status, numBytes)
                except Exception:
                    break
                if persistent: continue
                else: break
            except socket.gaierror:
                safeClose(serverSocket)
                try:
                    response, status, numBytes = couldNotResolveErrorResponse(connectionHeader)
                    clientSocket.sendall(response)
                    log(addr, cacheStatus, date, reqStartLine, status, numBytes)
                except Exception:
                    break
                if persistent: continue
                else: break
            except Exception:
                safeClose(serverSocket)
                if persistent: continue
                else: break
            serverSocket.settimeout(TIMEOUT)

            ### 4. Proxy Response
            response = b'HTTP/1.1 200 Connection Established\r\n\r\n'
            try:
                clientSocket.sendall(response)
                log(addr, cacheStatus, date, reqStartLine, 200, 0)
            except Exception:
                safeClose(serverSocket)
                break

            ### 5. Raw Data Relay
            clientToServerThread = threading.Thread(target=blindForward, args=(clientSocket, serverSocket))
            serverToClientThread = threading.Thread(target=blindForward, args=(serverSocket, clientSocket))
            clientToServerThread.start()
            serverToClientThread.start()
            clientToServerThread.join()
            serverToClientThread.join()

            ### 6. Connection Termination
            safeClose(serverSocket)
            break
    safeClose(clientSocket)

def readBody(body: bytes, socket: socket.socket, contentLength: int) -> tuple[bool, bool, bytes]:
    connectionClosed = False
    timedOut = False
    try:
        while contentLength < 0 or len(body) < contentLength:
            if contentLength < 0:
                numBytes = BUFFER_LEN
            else:
                numBytes = min(BUFFER_LEN, contentLength - len(body))
            buffer = socket.recv(numBytes)
            if buffer == b'':
                if contentLength >= 0 and len(body) != contentLength:
                    connectionClosed = True
                break
            body += buffer
    except socket.timeout:
        timedOut = True
    except Exception:
        connectionClosed = True
    return connectionClosed, timedOut, body

def transformRequest(method: str, path: str, query: str, headers: dict[str, list[str]], protocol: str, body: bytes) -> bytes:
    headers['connection'] = ['close']

    # Insert or Append 'Via'
    viaHeader = headers.get('via', [])
    viaHeader.append(f'1.1 {ZID}')
    headers['via'] = viaHeader

    # Origin-Form Target
    target = path
    if query != '':
        target += '?' + query

    # Transform headers map into string for forwarding
    startLine = f'{method} {target} {protocol}'
    request = buildHttpMessage(startLine, headers, body)

    return request

def blindForward(fromSocket: socket.socket, toSocket: socket.socket) -> None:
    try:
        while True:
            data = fromSocket.recv(BUFFER_LEN)
            if data == b'':
                try: toSocket.shutdown(socket.SHUT_WR)
                except Exception: pass
                try: fromSocket.shutdown(socket.SHUT_RD)
                except Exception: pass
                return
            toSocket.sendall(data)
    except Exception:
        pass

proxySocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
proxySocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
proxySocket.bind(('localhost', PROXY_PORT))

proxySocket.listen(1)

cache = Cache(MAX_OBJECT_SIZE, MAX_CACHE_SIZE)

while True:
    ### 1. Client-Proxy Connection
    clientSocket, addr = proxySocket.accept()
    clientSocket.settimeout(TIMEOUT)
    clientThread = threading.Thread(target=handleClient, args=(clientSocket, addr))
    clientThread.start()
