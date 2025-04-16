import datetime

class Logger:
    def __init__(self, path: str):
        self.path = path

        with open(self.path, "a") as file:
            file.write(f"===== Logging Started at {datetime.datetime.now()} =====\n")

    def log(self, message: str = "", component: str = ""):
        with open(self.path, "a") as file:
            file.write(f"[{datetime.datetime.now().time()}] ({component}) -> {message}\n")


if __name__ == "__main__":
    logger = Logger("log.txt")

    logger.log("Hello World", "Logging Test")