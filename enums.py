from enum import Enum

class MessageType(Enum):
    REQUEST = 'request'
    RESPONSE = 'response'

class CacheStatus(Enum):
    NONE = '-'
    HIT = 'H'
    MISS = 'M'
