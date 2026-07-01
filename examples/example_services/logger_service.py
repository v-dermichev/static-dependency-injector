class LoggerService:
    def __init__(self):
        self.log("initialized logger")

    def log(self, message: str) -> None:
        print(message)
