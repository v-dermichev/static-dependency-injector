from time import sleep

from examples.example_services.logger_service import LoggerService


class HttpClientService:
    def __init__(self, logger: LoggerService) -> None:
        self._logger = logger
        self._logger.log("initialized httpclient")

    def get(self, url: str) -> None:
        self._logger.log(f"GET request -> {url}")
        sleep(3)
        self._logger.log('GET response <- {"body": "some data"}')
