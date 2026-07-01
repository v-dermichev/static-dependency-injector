from examples.example_services.http_client_service import HttpClientService
from examples.example_services.logger_service import LoggerService


class UserProviderService:
    def __init__(self, logger: LoggerService, http_client: HttpClientService):
        self._logger = logger
        self._http_client = http_client
        self._user_pool = {
            "John",
            "Jane",
            "Bob",
        }
        self._taken_users: set[str] = set()
        self._logger.log("initialized user provider")

    def get_user(self) -> str:
        user = next((u for u in self._user_pool if u not in self._taken_users), None)
        if not user:
            raise ValueError("No more users available")
        self._http_client.get(f"https://example.com/users/{user}")
        self._taken_users.add(user)
        self._logger.log(f"User {user} is taken")
        return user
