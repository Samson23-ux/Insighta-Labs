import string
from secrets import choice


async def is_number(val: str) -> bool:
    """checks if strings are integers or float"""
    try:
        float(val)
        return True
    except ValueError:
        return False

async def is_integer(val: str) -> int | bool:
    """converts to integer for query parameters"""
    try:
        val: int = int(val)
        return val
    except ValueError:
        return False
    
async def is_float(val: str) -> float | bool:
    """converts to integer for query parameters"""
    try:
        val: float = float(val)
        return val
    except ValueError:
        return False
    

async def get_random_string() -> str:
    state: str = ""
    seq = string.ascii_letters + string.digits + string.punctuation
    state: str = "".join(choice(seq) for _ in range(43))
    return state
