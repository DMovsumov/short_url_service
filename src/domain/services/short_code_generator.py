import secrets
import string


class ShortCodeGenerator:
    def __init__(self, length: int = 6):
        self.length = length
        self.chars = string.ascii_letters + string.digits

    def generate(self) -> str:
        return "".join(secrets.choice(self.chars) for _ in range(self.length))
