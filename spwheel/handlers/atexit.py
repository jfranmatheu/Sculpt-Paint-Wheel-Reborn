import atexit


_exit = False

@atexit.register
def cleanup() -> None:
    global _exit
    if _exit:
        return
    _exit = True
