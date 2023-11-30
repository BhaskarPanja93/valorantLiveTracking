from gevent import monkey
monkey.patch_all()
from gevent.pywsgi import WSGIServer

import urllib3
from cryptography.fernet import Fernet
from flask import Flask, request, redirect, make_response, render_template_string
from flask_sock import Sock
from json import loads
from ping3 import ping

from internals.exceptions import *
from internals.flask_templates import *
from internals.mysql_pool import *
from internals.viewer import *
from internals.account import *

acc_identifier = 0
flaskPurposes = allPurposes()
turboMethods = turboMethods()
divNames = TurboFlaskDivNames()
randomGenerator = randomGenerator()
flaskTemplates = FlaskTemplates(divNames)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
mysqlPool = mysqlPool(dbName="val_tracker_db", user="root", password="SageHasBestBoobs@69", host="192.168.1.2")
added_accounts:dict[str,AccountAuth] = {}
active_viewers:list[Viewer_class] = []
wait_list_viewers = []
rate_limit_queue = []
rate_limit_wait_duration = 2
rate_limited_at = 0
last_request_sent = 0
all_accounts_fetched  = False



def rate_limit_checker(response:requests.api.request):
    global rate_limited_at, rate_limit_wait_duration
    print()
    print(response.status_code, response.json())
    if response.status_code == 429:
        print("limit detected")
        rate_limited_at = time()
        rate_limit_wait_duration += 0.1
        return False
    return True


def rate_limiter(bypass=False):
    global last_request_sent

    if not bypass:
        _id = randomGenerator.AlphaNumeric(5, 10)
        rate_limit_queue.append(_id)
        while time() - last_request_sent < rate_limit_wait_duration or not all_accounts_fetched or rate_limit_queue[0]!=_id or time()-rate_limited_at < 60:
            sleep(0.1)
        last_request_sent = time()
        rate_limit_queue.pop(0)

    while True:
        try:
            if type(ping("google.com", unit="ms")) == float:
                break
        except:
            sleep(0.1)


def generate_account_table(viewerObj:Viewer_class): ## remove argument by making a dummy button to activate the form
    authenticated_admin_table = authenticated_non_admin_table = "<table><tr><th>Rank<th>Name<th>Level<th>BattlePass<th>Season<th>NextUpdate<th>Credentials<th>Extras</tr>"
    for acc in added_accounts.values():
        line = (f"<tr>"
                f"<td><div id='{acc.identifier}{divNames.rank}'>{acc.rank}</div></td>"
                f"<td><div id='{acc.identifier}{divNames.game_name}'>{acc.name}</div></td>"
                f"<td><div id='{acc.identifier}{divNames.level}'>{acc.level}</div></td>"
                f"<td><div id='{acc.identifier}{divNames.bp_level}'>{acc.bp_level}</div></td>"
                f"<td><div id='{acc.identifier}{divNames.season}'>{acc.season}</div></td>"
                f"<td><div id='{acc.identifier}{divNames.next_update}'></div></td>"
                )
        if not acc.auth_failed:
            private_line = f"<td><div id='{acc.identifier}{divNames.credentials}'>{acc.email}<br><br>{acc.username}<br>{acc.password}</div></td>"
        else:
            private_line = f"<td><div id='{acc.identifier}{divNames.credentials}'>{acc.email}<br><br>{acc.username}<br>{viewerObj.generate_pass_update_form(acc.email, acc.username, acc.identifier, False)}</div></td>"
        public_line = f"<td><div id='{acc.identifier}{divNames.credentials}'>- hidden -</div></td>"
        extra_line = f"<td><div id='{acc.identifier}{divNames.extras}'>{acc.extras}</div></td></tr>"
        authenticated_admin_table += line + private_line + extra_line
        authenticated_non_admin_table += line + public_line+ extra_line

    authenticated_admin_table += "</table>"
    authenticated_non_admin_table += "</table>"
    return authenticated_admin_table, authenticated_non_admin_table


def auto_add_accounts():
    global acc_identifier, all_accounts_fetched
    registered_accounts = mysqlPool.execute("SELECT * from account_details", False)
    for acc_tup in registered_accounts:
        playerID, username, password, email, extras = acc_tup
        acc_identifier+=1
        acc = AccountAuth(str(acc_identifier), playerID, print, username, password, rate_limiter, rate_limit_checker, divNames, turboMethods, active_viewers, email, extras)
        added_accounts[acc.identifier] = acc
    all_accounts_fetched = True

    for viewer in active_viewers:
        admin_table, non_admin_table = generate_account_table(viewer)
        if viewer.admin:
            Thread(target=viewer.send_flask_data, args=(admin_table, viewer.divNames.authenticated_table, viewer.turboMethods.update,)).start()
        else:
            Thread(target=viewer.send_flask_data, args=(non_admin_table, viewer.divNames.authenticated_table, viewer.turboMethods.update,)).start()

    for acc in added_accounts.values():
        Thread(target=acc.auth_account, kwargs={"fetch_details":True}).start()

def cookieObj_to_dict(cookieObj:Cookie) -> dict:
    cookie_dict:dict = {"HOST_URL": cookieObj.host_url, "REMOTE_ADDRESS": cookieObj.remote_addr, "USER_AGENT": cookieObj.user_agent, "VIEWER_ID": cookieObj.viewer_id, "DELIM":cookieObj.delim}
    return cookie_dict


def dict_to_cookieObj(cookie_dict:dict) -> Cookie:
    cookieObj = Cookie(cookie_dict["DELIM"])
    cookieObj.remote_addr = cookie_dict["REMOTE_ADDRESS"]
    cookieObj.user_agent = cookie_dict["USER_AGENT"]
    cookieObj.viewer_id = cookie_dict["VIEWER_ID"]
    cookieObj.host_url = cookie_dict["HOST_URL"]
    return cookieObj


def request_to_cookieObj(request:request) -> Cookie:
    cookieObj = Cookie(randomGenerator.AlphaNumeric(5,10))
    cookieObj.remote_addr = request.remote_addr
    cookieObj.user_agent = request.user_agent.string
    cookieObj.host_url = request.host
    return cookieObj


def decrypt_session_data(cookie:str)-> tuple[Cookie,str]:
    try:
        cookie_decrypted_bytes = Fernet(cookie_encryptor_key).decrypt(cookie.encode())
        if cookie_decrypted_bytes[0] == 123 and cookie_decrypted_bytes[-1] == 125:
            cookie_decrypted = eval(cookie_decrypted_bytes)
            cookie_obj = dict_to_cookieObj(cookie_decrypted)
            return cookie_obj, "SUCCESS"
        else:
            raise InvalidOrModifiedCookieError
    except:
        return Cookie(""), "INVALID COOKIE"


def request_cookie_matches_device(request:request) -> tuple[Cookie, bool, str]:
    cookie = request.cookies
    dummy_cookie = Cookie("")
    try:
        if cookie.get("DEVICE_INFO") is None:
            return dummy_cookie, False, "NO_DEVICE_INFO"
        device_info = cookie["DEVICE_INFO"]
        decrypted_cookie_device_info, comment = decrypt_session_data(device_info)
        if decrypted_cookie_device_info.user_agent != request.user_agent.string and len(request.user_agent.string):
            return decrypted_cookie_device_info, False, "INVALID DEVICE"
        if decrypted_cookie_device_info.remote_addr != request.remote_addr and len(request.remote_addr):
            return decrypted_cookie_device_info, False, "INVALID IP"
        return decrypted_cookie_device_info, True, "SUCCESS"
    except:
        return dummy_cookie, False, "INVALID COOKIE"

class ModifiedTurbo(Turbo):
    def __init__(self, app=None):
        super().__init__(app)

    def init_app(self, app):
        ws_route = app.config.setdefault('TURBO_WEBSOCKET_ROUTE', '/ws')
        if ws_route:
            self.sock = Sock()
            self.sock.init_app(app)
        app.context_processor(self.context_processor)

def viewer_id_wait_list_manager(viewer_id):
    if viewer_id not in wait_list_viewers:
        wait_list_viewers.append(viewer_id)
    sleep(30)
    if viewer_id in wait_list_viewers:
        wait_list_viewers.remove(viewer_id)



def process_form(formSender:Viewer_class, form:dict):
    global acc_identifier
    if not formSender or not formSender.am_i_online():
        print(f"PLAYER OFFLINE")
        return
    
    if "PURPOSE" not in form or "CSRF" not in form:
        print("PURPOSE CSRF not in form")
        return

    _purpose:str = form["PURPOSE"]
    generalPurpose, realPurpose, token = _purpose.split(".")
    expectedCSRF = formSender.check_and_invalidate_csrf(generalPurpose, realPurpose, token)
    if form["CSRF"] != expectedCSRF or not expectedCSRF:
        print("invalid PURPOSE or CSRF")
        return
    if generalPurpose == flaskPurposes.updatePassword().general:
        if realPurpose == flaskPurposes.updatePassword().submitButton:
            new_password = form.get("NEW_PASSWORD").strip()
            identifier = form.get("_ID").strip()
            acc = added_accounts[identifier]
            acc.password = new_password
            for viewer in active_viewers:
                if viewer.admin:
                    Thread(target=viewer.send_flask_data, args=(f"{acc.email}<br><br>{acc.username}<br> TRYING NEW PASSWORD", f"{acc.identifier}{divNames.credentials}", turboMethods.update,)).start()
            if acc.auth_account(fetch_details=True) is not None:
                mysqlPool.execute(f"UPDATE account_details set password=\"{acc.password}\" where puuid=\"{acc.playerID}\"", True)
                for viewer in active_viewers:
                    if viewer.admin:
                        Thread(target=viewer.send_flask_data, args=(f"{acc.email}<br><br>{acc.username}<br> PASSWORD ACCEPTED", f"{acc.identifier}{divNames.credentials}", turboMethods.update,)).start()
            else:
                for viewer in active_viewers:
                    if viewer.admin:
                        Thread(target=viewer.send_flask_data, args=(f"{acc.email}<br><br>{acc.username}<br> PASSWORD WRONG", f"{acc.identifier}{divNames.credentials}", turboMethods.update,)).start()
            sleep(3)
            for viewer in active_viewers:
                if viewer.admin:
                    if not acc.auth_failed:
                        Thread(target=viewer.send_flask_data, args=(f"{acc.email}<br><br>{acc.username}<br>{acc.password}", f"{acc.identifier}{divNames.credentials}", turboMethods.update,)).start()
                    else:
                        viewer.generate_pass_update_form(acc.email, acc.username, acc.identifier)


    elif generalPurpose == flaskPurposes.newAccount().general:
        if realPurpose == flaskPurposes.newAccount().submitButton:
            username = form.get("USERNAME").strip()
            password = form.get("PASSWORD").strip()
            email = form.get("EMAIL").strip()
            extras = form.get("EXTRAS").strip()
            acc_identifier += 1
            formSender.send_flask_data("CHECKING", divNames.new_account_form, turboMethods.update)
            acc = AccountAuth(str(acc_identifier), "", print, username, password, rate_limiter, rate_limit_checker, divNames, turboMethods, active_viewers, email, extras)
            if acc.auth_account(fetch_details=True) is not None:
                old = mysqlPool.execute(f"SELECT puuid from account_details where puuid=\"{acc.playerID}\"", False)
                if not old:
                    added_accounts[acc.identifier] = acc
                    formSender.send_flask_data("ACCOUNT ACCEPTED", divNames.new_account_form, turboMethods.update)
                    mysqlPool.execute(f"INSERT INTO account_details values (\"{acc.playerID}\", \"{acc.username}\", \"{acc.password}\", \"{acc.email}\", \"{acc.extras}\")", True)
                    for viewer in active_viewers:
                        admin_table, non_admin_table = generate_account_table(viewer)
                        if viewer.admin:
                            Thread(target=viewer.send_flask_data, args=(admin_table, viewer.divNames.authenticated_table, viewer.turboMethods.update,)).start()
                        else:
                            Thread(target=viewer.send_flask_data, args=(non_admin_table, viewer.divNames.authenticated_table, viewer.turboMethods.update,)).start()
                else:
                    formSender.send_flask_data("ACCOUNT ALREADY PRESENT", divNames.new_account_form, turboMethods.update)
            else:
                formSender.send_flask_data("ACCOUNT REJECTED", divNames.new_account_form, turboMethods.update)
            sleep(2)
            formSender.render_add_account_form()


app = Flask("Valorant Tracker")
app.secret_key = randomGenerator.AlphaNumeric(100, 200).encode()
cookie_encryptor_key = Fernet.generate_key()
turbo_app = ModifiedTurbo(app)
@app.before_request
def pre_request_processing():
    if 'HTTP_X_FORWARDED_FOR' in request.environ: ## ngrok
        ip = request.environ['HTTP_X_FORWARDED_FOR']
        request.remote_addr = ip


@app.route('/favicon.ico', methods=['GET'])
def _favicon():
    return redirect("https://avatars.githubusercontent.com/u/101955196")


@app.route('/', methods=['GET'])
def _root_url():
    response = make_response(render_template_string(flaskTemplates.home_base()))
    cookie_object, valid_cookie, cookie_rejection_comment = request_cookie_matches_device(request)
    viewer_id = cookie_object.viewer_id
    if not valid_cookie or not viewer_id:
        while True:  # while needed
            viewer_id = randomGenerator.AlphaNumeric(30, 50)
            if viewer_id not in turbo_app.clients and viewer_id not in wait_list_viewers:
                break
        cookie_object = request_to_cookieObj(request)
        cookie_object.viewer_id = viewer_id
    Thread(target=viewer_id_wait_list_manager, args=(cookie_object.viewer_id,)).start()
    cookie_object.delim = randomGenerator.AlphaNumeric(5, 10)
    real_cookie = Fernet(cookie_encryptor_key).encrypt(str(cookieObj_to_dict(cookie_object)).encode()).decode()
    response.set_cookie('DEVICE_INFO', real_cookie, expires=time() + 12 * 30 * 24 * 60 * 60, httponly=True)  # 1year
    response.set_cookie('DEVICE_INFO_COOKIE_CREATED_AT', str(time()), expires=time() + 12 * 30 * 24 * 60 * 60, httponly=True)
    return response



@turbo_app.sock.route("/ws")
def turbo_stream(ws_obj):
    cookie_object, valid_cookie, cookie_rejection_comment = request_cookie_matches_device(request)
    viewer_id = cookie_object.viewer_id
    delim = cookie_object.delim
    if not valid_cookie or not viewer_id or not delim or viewer_id not in wait_list_viewers:
        return

    viewerObj = Viewer_class(turbo_app, randomGenerator, flaskTemplates, divNames, turboMethods, flaskPurposes, flaskTemplates)
    viewerObj.cookieObj = cookie_object
    viewerObj.viewer_id = cookie_object.viewer_id
    viewerObj.web_socket_list = [ws_obj]
    turbo_app.clients[viewer_id] = [ws_obj]
    active_viewers.append(viewerObj)
    admin_table, non_admin_table = generate_account_table(viewerObj)
    viewerObj.send_flask_data(admin_table if viewerObj.admin else non_admin_table, divNames.authenticated_table, turboMethods.update)
    if viewerObj.admin:
        Thread(target=viewerObj.render_add_account_form).start()
    while viewerObj.am_i_online(): # while needed
        try:
            received_data = ws_obj.receive(timeout=10)
            if received_data is not None:
                Thread(target=process_form, args=(viewerObj, loads(received_data))).start()
        except:
            break
    active_viewers.remove(viewerObj)



if __name__ == "__main__":
    print("Starting server...")
    print("http://127.0.0.1:5000")
    Thread(target=auto_add_accounts).start()
    WSGIServer(('0.0.0.0', 5000,), app, log=None).serve_forever()