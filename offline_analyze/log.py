LOG_LEVEL = 1

class colors:
    RED       = '\033[31;1m'
    GREEN     = '\033[32;1m'
    YELLOW    = '\033[33;1m'
    BLUE      = '\033[34;1m'
    MAGENTA   = '\033[35;1m'
    CYAN      = '\033[36;1m'
    BOLD      = '\033[1m'
    UNDERLINE = '\033[4m'
    ENDC      = '\033[0m'

def e(msg: str):
    if (LOG_LEVEL <= 4):
        print(f"{colors.RED}ERROR:======>>{msg}<<======{colors.ENDC}")


def d(msg: str):
    if (LOG_LEVEL <= 3):
        print(f"{colors.YELLOW}DEBUG:  {msg}{colors.ENDC}")


def v(msg: str):
    if (LOG_LEVEL <= 2):
        print(f"{colors.GREEN}VERBOSE:  {msg}{colors.ENDC}")


def i(msg: str):
    if (LOG_LEVEL <= 1):
        print(f"{colors.BLUE}INFO:  {msg}{colors.ENDC}")
