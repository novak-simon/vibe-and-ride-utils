
from user.model import User

def get_current_user() -> User:
    return User(id=0, name="Tester", genre_preferences=["pop", "rock"])