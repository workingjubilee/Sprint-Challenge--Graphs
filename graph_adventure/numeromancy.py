from enum import Flag, auto

class Now(Flag):
    DONE = auto()
    MORE = auto()
    LOOP = auto()
    CONTINUE = auto()