import pytz
import ssl
from time import time
from json import loads, dumps
from urllib.parse import urlparse
from requests import Session, Response
from rateLimitedQueues import Manager as RateLimiter
from pooledMySQL import Manager as MySQLManager
from threading import Thread
from dynamicWebsite import ModifiedTurbo
from requests.adapters import HTTPAdapter
from datetime import datetime
from bs4 import BeautifulSoup
from Enums import *


class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs) -> None:
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ctx.set_ciphers(':'.join([
        'ECDHE-ECDSA-AES128-GCM-SHA256',
        'ECDHE-ECDSA-CHACHA20-POLY1305',
        'ECDHE-RSA-AES128-GCM-SHA256',
        'ECDHE-RSA-CHACHA20-POLY1305',
        'ECDHE+AES128',
        'RSA+AES128',
        'ECDHE+AES256',
        'RSA+AES256',
        'ECDHE+3DES',
        'RSA+3DES']))
        kwargs['ssl_context'] = ctx
        return super(TLSAdapter, self).init_poolmanager(*args, **kwargs)


class AccountData:
    def __init__(self):
        self.PUUID = ""
        self.region = ""
        self.currentActID = ""
        self.currentEpisodeID = ""
        self.currentBPID = ""
        self.level = 0
        self.BPLevel = 0
        self.currentAct = 0
        self.currentEpisode = 0
        self.gameName = ""
        self.warnings = []
        self.penalties = []
        self.username = "flickmytittie"
        self.password = "ItsAlwaysSage@69"
        self.matches = {}
        self.fetchedRecentData = False
        self.lastUpdate = 0
        self.isInGame = False


class persistentLoginData:
    def __init__(self):
        self.accessToken = ""
        self.scope = ""
        self.iss = ""
        self.idToken = ""
        self.tokenType = ""
        self.sessionState = ""
        self.expiresIn = 0
        self.cookies = {}
        self.authHeader = RequestHeaders.authHeaders.value
        self.entitlementToken = ""


    def readDict(self, values:dict):
        self.accessToken = values.get("access_token")
        self.scope = values.get("scope")
        self.iss = values.get("iss")
        self.idToken = values.get("id_token")
        self.tokenType = values.get("token_type")
        self.sessionState = values.get("session_state")
        self.expiresIn = int(values.get("expires_in"))


class AccMan:
    def __init__(self, turboApp: ModifiedTurbo, riotRateLimit:RateLimiter, pooledMYSQL: MySQLManager):
        self.accountData = AccountData()
        self.persistentData = persistentLoginData()
        self.timeZone = pytz.timezone("Asia/Calcutta")
        self.turboApp = turboApp
        self.HTTPSession = Session()
        self.HTTPSession.mount("https://", TLSAdapter())
        self.riotRateLimit = riotRateLimit
        self.mysqlPool = pooledMYSQL
        self.status = []

    def generatePenaltyHTML(self):
        HTML = ""
        for penalty in self.accountData.warnings:
            if HTML != "":
                HTML += "<br><br>"
            HTML += f"{datetime.fromisoformat(penalty['Expiry']).astimezone(self.timeZone).ctime()}<br>[Warning] {penalty['WarningEffect']['WarningType']}:{penalty['WarningEffect']['WarningTier']}"
        for penalty in self.accountData.penalties:
            if HTML != "":
                HTML += "<br><br>"
            HTML += f"{datetime.fromisoformat(penalty['Expiry']).astimezone(self.timeZone).ctime()}<br>[Penalty] {penalty['QueueRestrictionEffect']['QueueIDs'][0]}"
        return HTML


    def modifyStatus(self, status: str, add: bool = True, duration: float = 0):
        if add:
            print(status)
            if len(self.status) >= 5: self.status.pop(0)
            self.status.append(status)
            Thread(target=self.modifyStatus, args=(status, False, duration)).start()
        else:
            if duration!=0:
                sleep(duration)
                if status in self.status: self.status.remove(status)
        for viewerObj in self.turboApp.activeViewers:
            pass
            # TODO:

    def initiateLogin(self, processGameData: bool = False):
        self.__prepareConnection(processGameData=processGameData)


    def __prepareConnection(self, count: int = 1, functionResponse: Response = None, processGameData: bool = False):
        processed = False

        if functionResponse is not None:
            try:
                response = functionResponse.json()
                if self.accountData.username and self.accountData.password and response.get("response") is None:
                    processed = True
            except:
                return print(BeautifulSoup(functionResponse.content).prettify())

        if processed: return self.__sendLoginCredentials(processGameData=processGameData)
        else:
            self.HTTPSession.cookies.clear()
            data = {
                "acr_values": "",
                "claims": "",
                "client_id": "riot-client",
                "code_challenge": "",
                "code_challenge_method": "",
                "nonce": StrGen().AlphaNumeric(16, 16),
                "redirect_uri": "http://localhost/redirect",
                'response_type': 'token id_token',
                "scope": "openid link ban lol_region account",
            }
            self.riotRateLimit.queueAction(self.HTTPSession.post, postFunction=self.__prepareConnection, postKwArgs={"processGameData": processGameData, "count": count + 1},
                                           url='https://auth.riotgames.com/api/v1/authorization',
                                           headers=RequestHeaders.regularHeaders.value,
                                           json=data,
                                           executePriority=0, executeThreaded=False)
            self.modifyStatus(f"[{count}] Prepare Connection")


    def __sendLoginCredentials(self, count: int = 1, functionResponse: Response = None, processGameData: bool = False):
        processed = False

        if functionResponse is not None:
            try:
                response = functionResponse.json()
                print(response)
                if response.get("type") == "multifactor": # TODO
                    self.modifyStatus(f"MFA required")
                    body = {
                        "type": "multifactor",
                        "code": input(f"MFA Enabled {response['multifactor']['methods']}: "),
                        "remember": True
                    }
                    self.riotRateLimit.queueAction(self.HTTPSession.put, postFunction=self.__sendLoginCredentials, postKwArgs={"processGameData": processGameData, "count": count + 1},
                                                   url='https://auth.riotgames.com/api/v1/authorization',
                                                   json=body,
                                                   headers=RequestHeaders.regularHeaders.value,
                                                   executePriority=2, executeThreaded=False)
                elif response.get("type") == "auth" and response.get("error") == "auth_failure":
                    self.modifyStatus(f"Auth Failed") # TODO
                    self.accountData.password = input("Password: ")
                elif response.get("type") == "response":
                    loginMemory = {}
                    for pair in urlparse(response['response']['parameters']['uri']).fragment.split("&"):
                        key, value = pair.split("=")
                        loginMemory[key] = value
                        self.persistentData.readDict(loginMemory)
                    processed = True
            except:
                return print(BeautifulSoup(functionResponse.content).prettify())

        if processed: return self.__fetchEntitlement(processGameData=processGameData)
        else:
            if self.accountData.username and self.accountData.password:
                body = {
                    "language": "en_US",
                    "username": self.accountData.username,
                    "password": self.accountData.password,
                    "region": None,
                    "remember": True,
                    "type": "auth",
                }
                self.riotRateLimit.queueAction(self.HTTPSession.put, postFunction=self.__sendLoginCredentials, postKwArgs={"processGameData":processGameData, "count": count + 1},
                                               url='https://auth.riotgames.com/api/v1/authorization',
                                               json=body,
                                               headers=RequestHeaders.regularHeaders.value,
                                               executePriority=1, executeThreaded=False)
                self.modifyStatus(f"[{count}] Login Initiated")


    def __fetchEntitlement(self, count: int = 1, functionResponse: Response = None, processGameData=True):
        processed = False

        if functionResponse is not None:
            try:
                response = functionResponse.json()
                self.persistentData.entitlementToken = response['entitlements_token']
                self.persistentData.authHeader.update({
                    'Authorization': f"Bearer {self.persistentData.accessToken}",
                    'X-Riot-Entitlements-JWT': self.persistentData.entitlementToken})
                self.persistentData.cookies = self.HTTPSession.cookies # TODO
                self.accountData.PUUID = self.persistentData.cookies["sub"]
                processed = True
            except:
                return print(BeautifulSoup(functionResponse.content).prettify())

        if processed: return self.__fetchRegion(processGameData=processGameData)
        else:
            self.riotRateLimit.queueAction(self.HTTPSession.post, postFunction=self.__fetchEntitlement, postKwArgs={"processGameData":processGameData, "count": count + 1},
                                           url='https://entitlements.auth.riotgames.com/api/token/v1',
                                           headers=RequestHeaders.regularHeaders.value|{'Authorization': f"Bearer {self.persistentData.accessToken}"},
                                           json={},
                                           executePriority=3, executeThreaded=False)
            self.modifyStatus(f"[{count}] Entitlement Initiated")


    def __fetchRegion(self, count: int = 1, functionResponse: Response = None, processGameData=True):

        processed = False

        if functionResponse is not None:
            try:
                response = functionResponse.json()
                self.accountData.region = response["affinities"]["live"]
                currentAct, nextAct, currentEpisode = get("https://valorant-api.com/v1/seasons").json()["data"][-3:]
                self.accountData.currentActID = currentAct["uuid"]
                self.accountData.currentEpisodeID = currentEpisode["uuid"]
                self.accountData.currentAct = int(currentAct["displayName"][-1])
                self.accountData.currentEpisode = int(currentEpisode["displayName"][-1])
                self.accountData.currentBPID = [event for event in get("https://valorant-api.com/v1/contracts").json()["data"] if event["content"]["relationType"] == "Season"][-1]["uuid"]
                processed = True
                if self.accountData.matches.get("initialFetched") != 1:
                    self.modifyStatus("Fetching Matches from cache")
                    listOfDict = self.mysqlPool.execute(f"select puuid, matchHistory from registered_accounts where puuid=\"{self.accountData.PUUID}\" limit 1")
                    self.accountData.matches = loads(listOfDict[0]["matchHistory"]) if (listOfDict and listOfDict[0] and listOfDict[0]["matchHistory"]) else {"initialFetched": 0, "history": []}
                self.modifyStatus(f"Matches cached: {len(self.accountData.matches['history'])}")
            except:
                return print(BeautifulSoup(functionResponse.content).prettify())

        if processed and processGameData: return self.waitForMatchEnd()
        else:
            self.riotRateLimit.queueAction(self.HTTPSession.put, postFunction=self.__fetchRegion, postKwArgs={"processGameData": processGameData, "count": count+1},
                                           url="https://riot-geo.pas.si.riotgames.com/pas/v1/product/valorant",
                                           headers={'Authorization': 'Bearer ' + self.persistentData.accessToken},
                                           json={"id_token": self.persistentData.idToken},
                                           executePriority=4, executeThreaded=False,)
            self.modifyStatus(f"[{count}] Region Initiated")






    def waitForMatchEnd(self):
        self.riotRateLimit.queueAction(self.HTTPSession.get, postFunction=self.fetchRecords, executePriority=6, executeThreaded=False,
                                       url=f"https://glz-{self.accountData.region}-1.{self.accountData.region}.a.pvp.net/core-game/v1/players/{self.accountData.PUUID}",
                                       headers=self.persistentData.authHeader)
        self.modifyStatus(f"Checking match {self.accountData.PUUID}")


    def fetchRecords(self, functionResponse:Response):
        if not self.accountData.fetchedRecentData or (functionResponse.status_code == 404):
            if self.accountData.isInGame:
                self.modifyStatus("Status: IDLE")
                self.accountData.isInGame = False
                self.accountData.fetchedRecentData = True
                self.riotRateLimit.queueAction(self.HTTPSession.put, postFunction=self.saveGameName, executePriority=7, executeThreaded=False,
                                               url=f"https://pd.{self.accountData.region}.a.pvp.net/name-service/v2/players",
                                               headers=self.persistentData.authHeader,
                                               json=[self.accountData.PUUID])
                self.riotRateLimit.queueAction(self.HTTPSession.get, postFunction=self.saveLevel, executePriority=8, executeThreaded=False,
                                               url=f"https://pd.{self.accountData.region}.a.pvp.net/account-xp/v1/players/{self.accountData.PUUID}",
                                               headers=self.persistentData.authHeader)
                self.riotRateLimit.queueAction(self.HTTPSession.get, postFunction=self.savePenalties, executePriority=9, executeThreaded=False,
                                               url=f"https://pd.{self.accountData.region}.a.pvp.net/restrictions/v3/penalties",
                                               headers=self.persistentData.authHeader)
                # self.riotRateLimit.queueAction(self.HTTPSession.get, postFunction=self.saveBPLevel, executePriority=10, executeThreaded=False,
                #                                url=f"https://pd.{self.accountData.region}.a.pvp.net/contracts/v1/contracts/{self.accountData.PUUID}",
                #                                headers=self.persistentData.authHeader)
                self.fetchMatches()
            for remainingTime in range(300 - int(time() - self.accountData.lastUpdate), 0, -1):
                    self.modifyStatus(f"Waiting: {remainingTime}", True, 1)
                    sleep(1)
        elif functionResponse.status_code == 200:
            self.accountData.isInGame = True
            for remainingTime in range(140 - int(time() - self.accountData.lastUpdate), 0, -1):
                self.modifyStatus(f"InGame: {remainingTime}", True, 1)
                sleep(1)
        else:
            print(functionResponse.status_code)
            print(functionResponse.json())
        self.accountData.lastUpdate = time()
        self.waitForMatchEnd()


    def fetchMatches(self, functionResponse: Response=None, low=0, high=10):
        if functionResponse is not None:
            if functionResponse.status_code != 200 or "History" not in functionResponse.json():
                self.accountData.matches["initialFetched"] = 1
                self.mysqlPool.execute(f"UPDATE registered_accounts set matchHistory='{dumps(self.accountData.matches)}' where puuid=\"{self.accountData.PUUID}\"")
                print(f"returning {low} {high} {functionResponse.json()}")
                return
            response = functionResponse.json()
            for matchDict in response["History"]:
                matchId = matchDict['MatchID']
                if self.mysqlPool.execute(f"SELECT _id from known_matches where _id=\"{matchId}\" limit 1"):
                    self.addSingleMatch(matchId=matchId)
                    if self.accountData.matches["initialFetched"] == 1:
                        self.modifyStatus("No new game")
                    else:
                        self.modifyStatus("Same match but not initial fetched")
                        continue
                else:
                    self.modifyStatus("Adding match")
                    if not self.mysqlPool.execute(f"SELECT _id from known_matches where _id=\"{matchId}\""):
                        self.riotRateLimit.queueAction(self.HTTPSession.get, postFunction=self.addSingleMatch, postKwArgs={"matchId":matchId}, executePriority=11, executeThreaded=False,
                                                       url=f"https://pd.{self.accountData.region}.a.pvp.net/match-details/v1/matches/{matchId}",
                                                       headers=self.persistentData.authHeader)
            else:
                self.accountData.matches["initialFetched"] = 1
                self.mysqlPool.execute(f"UPDATE registered_accounts set matchHistory='{dumps(self.accountData.matches)}' where puuid=\"{self.accountData.PUUID}\"")

        self.modifyStatus(f"Checking history {low}, {high}")
        self.riotRateLimit.queueAction(self.HTTPSession.get, postFunction=self.fetchMatches, postKwArgs={"low":low+10, "high":high+10}, executePriority=12, executeThreaded=False,
                                       url=f"https://pd.{self.accountData.region}.a.pvp.net/match-history/v1/history/{self.accountData.PUUID}?startIndex={low}&endIndex={high}",
                                       headers=self.persistentData.authHeader)


    def addSingleMatch(self, matchId:str, functionResponse:Response=None):
        if functionResponse is not None:
            response = functionResponse.json()
            playerSide = {}
            for playerDict in response['players']:
                playerSide[playerDict['subject']] = playerDict['teamId']
            self.mysqlPool.execute(f"INSERT into known_matches values ("
                                   f"\"{matchId}\","
                                   f"\"{response['matchInfo']['mapId']}\","
                                   f"\"{response['matchInfo']['gameStartMillis']}\","
                                   f"\"{response['matchInfo']['gameLengthMillis']}\","
                                   f"\"{response['matchInfo']['queueID'] if response['matchInfo']['queueID'] != '' else response['matchInfo']['provisioningFlowID']}\","
                                   f"\"{response['matchInfo']['seasonId']}\","
                                   f"\"{response['teams'][0]['teamId'] if response['teams'][0]['won'] else response['teams'][1]['teamId']}\","
                                   f"'{dumps(playerSide)}',"
                                   f"'{dumps(response)}'"
                                   f")", catchErrors=True)
        print(self.accountData.gameName, matchId)
        if matchId not in self.accountData.matches["history"]:
            self.accountData.matches["history"].append(matchId)
            self.mysqlPool.execute(f"UPDATE registered_accounts set matchHistory='{dumps(self.accountData.matches)}' where puuid=\"{self.accountData.PUUID}\"")



    def savePenalties(self, functionResponse:Response):
        response = functionResponse.json()
        self.accountData.warnings = []
        self.accountData.penalties = []
        for penalty in response["Penalties"]:
            if penalty["QueueRestrictionEffect"] is not None:
                self.accountData.penalties.append(penalty)

            elif penalty["WarningEffect"] is not None:
                self.accountData.warnings.append(penalty)


    def saveGameName(self, functionResponse:Response):
        response = functionResponse.json()
        name = response[0]["GameName"] + "#" + response[0]["TagLine"]
        self.modifyStatus(f"Name: {name}")
        if name != self.accountData.gameName:
            self.accountData.gameName = name
            self.mysqlPool.execute(f"UPDATE registered_accounts set game_name=\"{self.accountData.gameName}\" where puuid=\"{self.accountData.PUUID}\"")


    def saveLevel(self, functionResponse:Response):
        response = functionResponse.json()
        if "Progress" in response:
            level = response["Progress"]["Level"]
            self.modifyStatus(f"Level: {level}")
            if self.accountData.level != level:
                self.accountData.level = level
        else:
            errorID = StrGen().AlphaNumeric(5,5)
            open(errorID, "w").write(dumps(response))
            print(f"Error saveLevel: {errorID}")


    def saveBPLevel(self, functionResponse:Response):
        response = functionResponse.json()
        if "Contracts" in response:
            for contract in response["Contracts"]:
                if contract["ContractDefinitionID"] == self.accountData.BPLevel:
                    BPLevel: int = contract["ProgressionLevelReached"]
                    self.modifyStatus(f"BPLevel: {BPLevel}")
                    if self.accountData.BPLevel != BPLevel:
                        self.accountData.BPLevel = BPLevel
        else:
            errorID = StrGen().AlphaNumeric(5,5)
            open(errorID, "w").write(dumps(response))
            print(f"Error saveBPLevel: {errorID}")


