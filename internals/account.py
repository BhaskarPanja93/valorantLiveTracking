import re
import ssl
from secrets import token_urlsafe
from threading import Thread
from time import sleep, time
import requests
from InquirerPy import prompt

from internals.constants import FORCED_CIPHERS, auth_headers, headers, NUMBER_TO_RANK_IMG
from internals.div_names import TurboFlaskDivNames as divNames
from internals.turbo_methods import TurboFlaskMethods as turboMethods
from internals.viewer import Viewer_class


class TLSAdapter(requests.adapters.HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs) -> None:
        ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        ctx.set_ciphers(':'.join(FORCED_CIPHERS))
        kwargs['ssl_context'] = ctx
        return super(TLSAdapter, self).init_poolmanager(*args, **kwargs)


class AccountAuth:
    def __init__(self, _id, puuid, log, username, password, rate_limiter, rate_limit_checker, divNames:divNames, turboMethods:turboMethods, viewer_list:list[Viewer_class], email, extras):
        self.identifier = _id
        self.last_update = 0
        self.viewer_list = viewer_list
        self.divNames = divNames
        self.turboMethods = turboMethods
        self.rate_limiter = rate_limiter
        self.rate_limit_checker = rate_limit_checker
        self.email = email
        self.extras = extras

        self.rank = ""
        self.name = ""
        self.level = 0
        self.bp_level = 0
        self.episode = ""
        self.act = ""
        self.season = ""

        self.auth_failed = False
        self.log = log
        self.session = requests.Session()
        self.session.mount("https://", TLSAdapter())
        self.auth_headers = auth_headers.copy()
        self.auth_headers["User-Agent"] = self.auth_headers["User-Agent"].replace("REPLACE_STRING", self.identifier)
        self.playerID = puuid
        self.region = None
        self.seasonID = ""

        self.username = username
        self.password = password
        #Thread(target=self.auth_account, kwargs={"fetch_details":True}).start()

    def get_latest_season_id(self, threaded=False):
        while True:
            if threaded:
                sleep(60 * 60)
            while True:
                self.rate_limiter()
                content = requests.get(f"https://shared.{self.region}.a.pvp.net/content-service/v3/content", headers=self.auth_headers)
                if self.rate_limit_checker(content):
                    content = content.json()
                    break
            for season in content["Seasons"]:
                if season["IsActive"]:
                    if season["Type"] == "act":
                        name = season["Name"].split()
                        self.seasonID = season["ID"]
                        self.act = name[0][0]+name[1]
                    elif season["Type"] == "episode":
                        name = season["Name"].split()
                        self.episode = name[0][0]+name[1]
            if self.season != self.episode+self.act:
                self.season = self.episode+self.act
                for viewer in self.viewer_list:
                    Thread(target=viewer.send_flask_data, args=(self.season, f"{self.identifier}{self.divNames.season}", self.turboMethods.update,)).start()

            if not threaded:
                break

    def auth_account(self, cookies=None, fetch_details=False):
        self.session.cookies.clear()
        if cookies is not None:
            for cookie in cookies:
                self.session.cookies.set(cookie, cookies[cookie])
        data = {
            "acr_values": "",
            "claims": "",
            "client_id": "riot-client",
            "code_challenge": "",
            "code_challenge_method": "",
            "nonce": token_urlsafe(16),
            "redirect_uri": "http://localhost/redirect",
            'response_type': 'token id_token',
            "scope": "openid link ban lol_region account",
        }
        while True:
            self.rate_limiter()
            r = self.session.post('https://auth.riotgames.com/api/v1/authorization', json=data, headers=headers)
            if self.rate_limit_checker(r):
                r = r.json()
                break
        if not self.username and not self.password:
            if r.get("response") is None:
                return None
        if self.username and self.password:
            body = {
                "language": "en_US",
                "password": self.password,
                "region": None,
                "remember": True,
                "type": "auth",
                "username": self.username,
            }

            while True:
                self.rate_limiter()
                r = self.session.put("https://auth.riotgames.com/api/v1/authorization", json=body, headers=headers)
                if self.rate_limit_checker(r):
                    r = r.json()
                    break
            if r.get("type") == "multifactor":
                self.log("2fa detected")
                body = {
                    "type": "multifactor",
                    "code": self.ask_for_mfa(),
                    "remember": True
                }
                while True:
                    self.rate_limiter()
                    r = self.session.put("https://auth.riotgames.com/api/v1/authorization", json=body, headers=headers)
                    if self.rate_limit_checker(r):
                        break

            if r.get("error") == "auth_failure":
                for viewer in self.viewer_list:
                    if viewer.admin:
                        viewer.generate_pass_update_form(self.email, self.username, self.identifier)
                return None
        pattern = re.compile('access_token=((?:[a-zA-Z]|\d|\.|-|_)*).*id_token=((?:[a-zA-Z]|\d|\.|-|_)*).*expires_in=(\d*)')
        try:
            data = pattern.findall(r['response']['parameters']['uri'])[0]
        except Exception as e:
            self.log(f"[AUTH FAIL] {e} {repr(e)} {r}")
            input("WAITING FOR RESOLUTION !")

        access_token = data[0]
        id_token = data[1]
        expires_in = data[2]
        expire_in_epoch = int(time()) + int(expires_in)
        while True:
            self.rate_limiter()
            r = self.session.post('https://entitlements.auth.riotgames.com/api/token/v1', headers={'Authorization': 'Bearer ' + access_token} | headers, json={})
            if self.rate_limit_checker(r):
                r = r.json()
                break
        self.auth_headers.update({
            'Authorization': f"Bearer {access_token}",
            'X-Riot-Entitlements-JWT': r['entitlements_token']})
        self.playerID = self.session.cookies.get_dict()["sub"]
        while True:
            self.rate_limiter()
            r = self.session.put("https://riot-geo.pas.si.riotgames.com/pas/v1/product/valorant", headers={'Authorization': 'Bearer ' + access_token}, json={"id_token": id_token})
            if self.rate_limit_checker(r):
                r = r.json()
                break
        self.region = r["affinities"]["live"]
        self.get_latest_season_id()
        if fetch_details:
            Thread(target=self.get_latest_season_id, args=(True,)).start()
            Thread(target=self.get_account_data, args=(True,)).start()
        return {
            "cookies": self.session.cookies.get_dict(),
            "expire_in": expire_in_epoch,
            "lol_region": self.region
        }

    def get_account_data(self, threaded=False):
        while True:
            if self.auth_failed:
                if self.auth_account() is None:
                    return
            try:
                while True:
                    self.rate_limiter()
                    r = self.session.get(f"https://pd.{self.region}.a.pvp.net/mmr/v1/players/{self.playerID}", headers=self.auth_headers)
                    if self.rate_limit_checker(r):
                        r = r.json()
                        break
                if r["QueueSkills"]["competitive"].get("SeasonalInfoBySeasonID") is not None:
                    season_info = r["QueueSkills"]["competitive"]["SeasonalInfoBySeasonID"].get(self.seasonID)
                    if season_info is not None:
                        rank = season_info["CompetitiveTier"]
                        rr = season_info["RankedRating"]
                    else:
                        rank = 0
                        rr = 0
                else:
                    rank = 0
                    rr = 0
                rank = NUMBER_TO_RANK_IMG[rank][1]+"<br>RR: "+str(rr)+"/100"
                if rank != self.rank:
                    self.rank = rank
                    for viewer in self.viewer_list:
                        Thread(target=viewer.send_flask_data, args=(str(self.rank), f"{self.identifier}{self.divNames.rank}", self.turboMethods.update,)).start()
                while True:
                    self.rate_limiter()
                    r = self.session.put(f"https://pd.{self.region}.a.pvp.net/name-service/v2/players", headers=self.auth_headers, json=[self.playerID])
                    if self.rate_limit_checker(r):
                        r = r.json()
                        break
                name = r[0]["GameName"] + "#" + r[0]["TagLine"]
                if name != self.name:
                    self.name = name
                    for viewer in self.viewer_list:
                        Thread(target=viewer.send_flask_data, args=(str(self.name), f"{self.identifier}{self.divNames.game_name}", self.turboMethods.update,)).start()

                while True:
                    self.rate_limiter()
                    r = self.session.get(f"https://pd.{self.region}.a.pvp.net/account-xp/v1/players/{self.playerID}", headers=self.auth_headers)
                    if self.rate_limit_checker(r):
                        r = r.json()
                        break
                try:
                    level = r["Progress"]["Level"]
                    if level != self.level:
                        self.level = level
                        for viewer in self.viewer_list:
                            Thread(target=viewer.send_flask_data, args=(str(self.level), f"{self.identifier}{self.divNames.level}", self.turboMethods.update,)).start()

                except Exception as e:
                    self.log(f"[LEVEL FAIL] {e} {repr(e)} {r} {self.playerID} {self.name} {self.auth_headers["User-Agent"]}")
                while True:
                    self.rate_limiter(bypass=True)
                    r = self.session.get("https://valorant-api.com/v1/contracts")
                    if self.rate_limit_checker(r):
                        r = r.json()
                        break
                contracts = [a for a in r["data"] if a["content"]["relationType"] == "Season"]
                bp = contracts[-1]["uuid"]
                while True:
                    self.rate_limiter()
                    r = self.session.get(f"https://pd.{self.region}.a.pvp.net/contracts/v1/contracts/{self.playerID}", headers=self.auth_headers, verify=False)
                    if self.rate_limit_checker(r):
                        r = r.json()
                        break
                try:
                    for contract in r["Contracts"]:
                        if contract["ContractDefinitionID"] == bp:
                            bp_level: int = contract["ProgressionLevelReached"]
                            if bp_level != self.bp_level:
                                self.bp_level = bp_level
                                for viewer in self.viewer_list:
                                    Thread(target=viewer.send_flask_data, args=(str(self.bp_level), f"{self.identifier}{self.divNames.bp_level}", self.turboMethods.update,)).start()
                except Exception as e:
                    self.log(f"[CONTRACTS FAIL] {e} {repr(e)} {r}")
                    continue
                self.last_update = time()
                if not threaded:
                    break
                time_to_wait = 60
                for viewer in self.viewer_list:
                    for _ in range(time_to_wait - int(time() - self.last_update) // 1):
                        Thread(target=viewer.send_flask_data, args=(f"in {time_to_wait-int(time()-self.last_update)} secs", f"{self.identifier}{self.divNames.next_update}", self.turboMethods.update,)).start()
                        sleep(1)
                    Thread(target=viewer.send_flask_data, args=(f"updating", f"{self.identifier}{self.divNames.next_update}", self.turboMethods.update,)).start()

            except Exception as e:
                self.log(f"[FETCH FAIL] [{e}] [{repr(e)}]")
                self.auth_failed = True

    def ask_for_mfa(self):
        self.log("asking for mfa")
        return prompt({"type": "input", "message": "Please enter your MFA/2FA code:", "name": "mfa"})["mfa"]