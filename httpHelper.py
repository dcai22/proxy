# message must be a string literal
def parseHttpMessage(message):
    sections = message.split(b'\r\n\r\n', 1)
    body = sections[1]
    header = sections[0].decode('utf-8')
    headerLines = header.split('\r\n')
    startLine = headerLines[0]
    headers = {}
    for headerLine in headerLines[1:]:
        splitHeader = headerLine.split(':', 1)
        headerName = splitHeader[0].lower()
        values = splitHeader[1].split(',')
        strippedValues = list(map(str.strip, values))

        if headerName in ['connection', 'proxy-connection', 'transfer-encoding']:
            headers[headerName] = list(map(str.lower, strippedValues))
        else:
            headers[headerName] = strippedValues

    return startLine, headers, body

def buildHttpMessage(startLine, headers, body = b''):
    header = startLine + '\r\n'
    for headerName in headers:
        if not headers.get(headerName):
            continue

        headerLine = f'{headerName}: '
        headerLine += ', '.join(headers[headerName])
        headerLine += f'\r\n'
        header += headerLine

    message = header.encode() + b'\r\n' + body
    return message

def getStatusAndBytes(response):
    header, body = response.split(b'\r\n\r\n', 1)
    bytes = len(body)
    header = header.decode('utf-8')
    startLine = header.split('\r\n')[0]
    status = startLine.split(' ')[1]
    return status, bytes

# messageType is 'request' or 'response'
def getContentLength(headers, messageType):
    if headers.get('transfer-encoding') is not None:
        # -1 indicates reading until connection is closed
        return -1
    elif headers.get('content-length') is not None:
        return int(headers['content-length'][0])
    elif messageType == 'request':
        return 0
    else:
        return -1

def parseUrl(url):
    if '://' in url:
        scheme, url = url.split('://', 1)
    else:
        scheme = 'http'

    if '/' in url:
        hostPort, pathQuery = url.split('/', 1)
        pathQuery = '/' + pathQuery
    else:
        hostPort = url
        pathQuery = '/'

    if ':' in hostPort:
        hostname, port = hostPort.split(':', 1)
    else:
        hostname = hostPort
        port = '80'

    if '?' in pathQuery:
        path, query = pathQuery.split('?', 1)
    else:
        path = pathQuery
        query = ''

    return scheme.lower(), hostname.lower(), str(int(port)), path, query
