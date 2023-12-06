import string
import random


def get_random_string(length=6):
    """Generate random string with arbitrary number"""
    # choose from all lowercase letter + digits
    letters = string.ascii_lowercase + string.digits
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str
