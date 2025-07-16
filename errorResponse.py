def makeErrorResponse(status, reason, connectionHeader, body):
    contentLength = len(body)
    response = (
        f'HTTP/1.1 {status} {reason}\r\n'
        f'Content-Type: text/plain\r\n'
        f'Content-Length: {contentLength}\r\n'
        f'{connectionHeader}\r\n'
        f'\r\n'
        f'{body}'
    )
    return response.encode(), status, contentLength

def invalidPortErrorResponse(connectionHeader):
    return makeErrorResponse(400, 'Bad Request', connectionHeader, 'invalid port')

def noHostErrorResponse(connectionHeader):
    return makeErrorResponse(400, 'Bad Request', connectionHeader, 'no host')

def misdirectedRequestErrorResponse(connectionHeader):
    return makeErrorResponse(421, 'Misdirected Request', connectionHeader, 'proxy address')

def connectionRefusedErrorResponse(connectionHeader):
    return makeErrorResponse(502, 'Bad Gateway', connectionHeader, 'connection refused')

def couldNotResolveErrorResponse(connectionHeader):
    return makeErrorResponse(502, 'Bad Gateway', connectionHeader, 'could not resolve')

def closedUnexpectedlyErrorResponse(connectionHeader):
    return makeErrorResponse(502, 'Bad Gateway', connectionHeader, 'closed unexpectedly')

def timeoutErrorResponse(connectionHeader):
    return makeErrorResponse(504, 'Gateway Timeout', connectionHeader, 'timed out')
