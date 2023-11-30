import requests

NUMBER_TO_RANK_IMG = [
    ['UNRANKED', '<img width="100" height="100" src="https://media.valorant-api.com/competitivetiers/564d8e28-c226-3180-6285-e48a390db8b1/0/largeicon.png">'],
    ['UNRANKED', '<img width="100" height="100" src="https://media.valorant-api.com/competitivetiers/564d8e28-c226-3180-6285-e48a390db8b1/0/largeicon.png">'],
    ['UNRANKED', '<img width="100" height="100" src="https://media.valorant-api.com/competitivetiers/564d8e28-c226-3180-6285-e48a390db8b1/0/largeicon.png">'],
    ['IRON 1', '<img width="100" height="100" src="https://media.valorant-api.com/competitivetiers/564d8e28-c226-3180-6285-e48a390db8b1/3/largeicon.png">'],
    ['IRON 2', '<img width="100" height="100" src="https://media.valorant-api.com/competitivetiers/564d8e28-c226-3180-6285-e48a390db8b1/4/largeicon.png">'],
    ['IRON 3', '<img width="100" height="100" src="https://media.valorant-api.com/competitivetiers/564d8e28-c226-3180-6285-e48a390db8b1/5/largeicon.png">'],
    ['BRONZE 1', '<img width="100" height="100" src="https://media.valorant-api.com/competitivetiers/564d8e28-c226-3180-6285-e48a390db8b1/6/largeicon.png">'],
    ['BRONZE 2', '<img width="100" height="100" src="https://media.valorant-api.com/competitivetiers/564d8e28-c226-3180-6285-e48a390db8b1/7/largeicon.png">'],
    ['BRONZE 3', '<img width="100" height="100" src="https://media.valorant-api.com/competitivetiers/564d8e28-c226-3180-6285-e48a390db8b1/8/largeicon.png">'],
    ['SILVER 1', '<img width="100" height="100" src="https://media.valorant-api.com/competitivetiers/564d8e28-c226-3180-6285-e48a390db8b1/9/largeicon.png">'],
    ['SILVER 2', '<img width="100" height="100" src="https://media.valorant-api.com/competitivetiers/564d8e28-c226-3180-6285-e48a390db8b1/10/largeicon.png">'],
    ['SILVER 3', '<img width="100" height="100" src="https://media.valorant-api.com/competitivetiers/564d8e28-c226-3180-6285-e48a390db8b1/11/largeicon.png">'],
    ['GOLD 1', '<img width="100" height="100" src="https://media.valorant-api.com/competitivetiers/564d8e28-c226-3180-6285-e48a390db8b1/12/largeicon.png">'],
    ['GOLD 2', '<img width="100" height="100" src="https://media.valorant-api.com/competitivetiers/564d8e28-c226-3180-6285-e48a390db8b1/13/largeicon.png">'],
    ['GOLD 3', '<img width="100" height="100" src="https://media.valorant-api.com/competitivetiers/564d8e28-c226-3180-6285-e48a390db8b1/14/largeicon.png">'],
    ['PLATINUM 1', '<img width="100" height="100" src="https://media.valorant-api.com/competitivetiers/564d8e28-c226-3180-6285-e48a390db8b1/15/largeicon.png">'],
    ['PLATINUM 2', '<img width="100" height="100" src="https://media.valorant-api.com/competitivetiers/564d8e28-c226-3180-6285-e48a390db8b1/16/largeicon.png">'],
    ['PLATINUM 3', '<img width="100" height="100" src="https://media.valorant-api.com/competitivetiers/564d8e28-c226-3180-6285-e48a390db8b1/17/largeicon.png">'],
    ['DIAMOND 1', '<img width="100" height="100" src="https://media.valorant-api.com/competitivetiers/564d8e28-c226-3180-6285-e48a390db8b1/18/largeicon.png">'],
    ['DIAMOND 2', '<img width="100" height="100" src="https://media.valorant-api.com/competitivetiers/564d8e28-c226-3180-6285-e48a390db8b1/19/largeicon.png">'],
    ['DIAMOND 3', '<img width="100" height="100" src="https://media.valorant-api.com/competitivetiers/564d8e28-c226-3180-6285-e48a390db8b1/20/largeicon.png">'],
    ['IMMORTAL 1', '<img width="100" height="100" src="https://media.valorant-api.com/competitivetiers/564d8e28-c226-3180-6285-e48a390db8b1/21/largeicon.png">'],
    ['IMMORTAL 2', '<img width="100" height="100" src="https://media.valorant-api.com/competitivetiers/564d8e28-c226-3180-6285-e48a390db8b1/22/largeicon.png">'],
    ['IMMORTAL 3', '<img width="100" height="100" src="https://media.valorant-api.com/competitivetiers/564d8e28-c226-3180-6285-e48a390db8b1/23/largeicon.png">'],
    ['RADIANT', '<img width="100" height="100" src="https://media.valorant-api.com/competitivetiers/564d8e28-c226-3180-6285-e48a390db8b1/24/largeicon.png">']
        ]

FORCED_CIPHERS = [
    'ECDHE-ECDSA-AES128-GCM-SHA256',
    'ECDHE-ECDSA-CHACHA20-POLY1305',
    'ECDHE-RSA-AES128-GCM-SHA256',
    'ECDHE-RSA-CHACHA20-POLY1305',
    'ECDHE+AES128',
    'RSA+AES128',
    'ECDHE+AES256',
    'RSA+AES256',
    'ECDHE+3DES',
    'RSA+3DES']

version = requests.get("https://valorant-api.com/v1/version").json()["data"]

headers = {
            "Accept-Encoding": "deflate, gzip, zstd",
            "user-agent": f"RiotClient/{version['riotClientBuild']} rso-auth (Windows;10;;Professional, x64)",
            "Cache-Control": "no-cache",
            "Accept": "application/json",
            'Accept-Language': 'en-US,en;q=0.9'
        }

auth_headers = {
    'X-Riot-ClientPlatform': "ew0KCSJwbGF0Zm9ybVR5cGUiOiAiUEMiLA0KCSJwbGF0Zm9ybU9TIjogIldpbmRvd3MiLA0KCSJwbGF0Zm9ybU9TVmVyc2lvbiI6ICIxMC4wLjE5MDQyLjEuMjU2LjY0Yml0IiwNCgkicGxhdGZvcm1DaGlwc2V0IjogIlVua25vd24iDQp9",
    'X-Riot-ClientVersion': version["riotClientVersion"],
    "User-Agent": "ShooterGame/13 Windows/10.0.19043.REPLACE_STRING.256.64bit"
}