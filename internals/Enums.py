from time import sleep
from pooledMySQL import Manager as MySQLPool
from customisedLogs import Manager as LogManager
from ping3 import ping
from randomisedString import Generator as StrGen
from SecretEnum import Secrets, Enum
from requests import get


class RequiredFiles(Enum):
    common = [
        r"internal\AutoReRun.py",
        r"internal\CustomResponse.py",
        r"internal\Enum.py",
        r"internal\Logger.py",
        r"internal\MysqlPool.py",
        r"internal\SecretEnum.py",
        r"internal\StringGenerator.py",
    ]
    coreFile = r"core.py"
    userGatewayFile = r"gateway.py"
    adminGatewayFile = r"admin_gateway.py"
    purchaseImageFolder = r"savedImages"
    thumbnailFolder = r"thumbnails"


class Constants(Enum):
    logCount = 1000
    sitePort = 60100


class Routes(Enum):
    home = "/vt"
    websocket = "/vtws"

print(get('https://valorant-api.com/v1/version').json()['data']['riotClientBuild'])
print(get('https://valorant-api.com/v1/version').json()['data']['riotClientVersion'])
class RequestHeaders(Enum):
    regularHeaders = {
        "Accept-Encoding": "deflate, gzip, zstd",
        "user-agent": f"RiotClient/{get('https://valorant-api.com/v1/version').json()['data']['riotClientBuild']} rso-auth (Windows;10;;Professional, x64)",
        "Cache-Control": "no-cache",
        "Accept": "application/json",
        'Accept-Language': 'en-US,en;q=0.9'
    }

    authHeaders = {
        'X-Riot-ClientPlatform': "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9",
        'X-Riot-ClientVersion': get("https://valorant-api.com/v1/version").json()["data"]["riotClientVersion"],
        "User-Agent": f"ShooterGame/13 Windows/10.0.19043.{StrGen().OnlyNumeric(5,5)}.256.64bit"
    }


class commonMethods:
    @staticmethod
    def waitForNetwork(logger:LogManager):
        """
        Blocking function to check for internet connection.
        :param logger: LogManager object to log to if no internet found
        :return:
        """
        paused = False
        while True:
            try:
                if type(ping("3.6.0.0")) == float:
                    return
            except:
                if not paused:
                    logger.fatal("INTERNET", "No network found...")
                    paused = True
            sleep(1)

    @staticmethod
    def checkRelatedIP(addressA: str, addressB: str):
        """
        Check if 2 IPv4 belong to same */24 subnet
        :param addressA: IPv4 as string
        :param addressB: IPv4 as string
        :return:
        """
        if addressA.count(".") == 3 and addressB.count(".") == 3:
            a = addressA.split(".")[:-1]
            b = addressB.split(".")[:-1]
            return a == b
        return addressA == addressB

    @staticmethod
    def sqlISafe(parameter):
        """
        Sanitise SQL syntax before passing it to main Database
        :param parameter: String containing the syntax to execute
        :return:
        """
        if type(parameter) == str:
            return parameter.replace("'", "").replace('"', "").strip()
        return parameter

    @staticmethod
    def connectDB(logger:LogManager) -> MySQLPool:
        """
        Blocking function to connect to DB
        :return: None
        """
        for host in Secrets.DBHosts.value:
            try:
                mysqlPool = MySQLPool(user="root", password=Secrets.DBPassword.value, dbName=Secrets.DBName.value, host=host)
                mysqlPool.execute(f"SELECT DATABASE();")
                logger.success("DB", f"connected to: {host}")
                return mysqlPool
            except:
                logger.failed("DB", f"failed: {host}")
        else:
            logger.fatal("DB", "Unable to connect to DataBase")
            input("EXIT...")
            exit(0)
