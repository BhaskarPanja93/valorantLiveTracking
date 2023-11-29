from threading import Thread
from time import sleep

from turbo_flask import Turbo

from internals.cookie import Cookie
from internals.div_names import TurboFlaskDivNames as divNames
from internals.flask_purposes import allPurposes
from internals.flask_templates import FlaskTemplates as htmlTemplates, FlaskTemplates
from internals.random_gen import randomGenerator
from internals.turbo_methods import TurboFlaskMethods as turboMethods


class Viewer_class:
    def __init__(self, turbo_app:Turbo, randomGenerator:randomGenerator, htmlTemplates:htmlTemplates, divNames:divNames, turboMethods:turboMethods, flaskPurposes:allPurposes, flaskTemplates:FlaskTemplates):
        self.admin = True
        self.randomGenerator = randomGenerator
        self.htmlTemplates = htmlTemplates
        self.divNames = divNames
        self.turboMethods = turboMethods
        self.flaskPurposes = flaskPurposes
        self.flaskTemplates = flaskTemplates

        self.active_functions = []
        self.turbo_app = turbo_app
        self.viewer_id = ""
        self.web_socket_list = []
        self.cookieObj:Cookie|None = None

        self.purpose_to_csrf:dict[str,dict[str,str]] = {}
        self.can_receive_turbo_flask_data = True
        self.div_name_to_html_data = {}


    @staticmethod
    def add_style(style_text, real_text):
        return f"<p style='{style_text}'>{real_text}</p>"


    def am_i_online(self):
        return self.turbo_app.clients.get(self.viewer_id) == self.web_socket_list


    def generate_pass_update_form(self, email, username, account_identifier, render=True):
        purpose = self.flaskPurposes.updatePassword()
        string = f"{self.flaskTemplates.update_pass_form(self.generate_purpose_and_csrf(purpose.general, purpose.submitButton, [account_identifier]))}"
        if render:
            Thread(target=self.send_flask_data, args=(f"{email}<br><br>{username}<br>{string}", f"{account_identifier}{self.divNames.credentials}", self.turboMethods.update,)).start()
        else:
            return string


    def render_add_account_form(self):
        purpose = self.flaskPurposes.newAccount()
        string = f"{self.flaskTemplates.add_account(self.generate_purpose_and_csrf(purpose.general, purpose.submitButton, []))}"
        Thread(target=self.send_flask_data, args=(f"{string}", self.divNames.new_account_form, self.turboMethods.update,)).start()



    def generate_purpose_and_csrf(self, general_purpose:str, real_purpose:str, extras:list):

        function_name = "generate_purpose"
        self.active_functions.append(function_name)
        def wrapper() -> tuple[str, str, list]:
            while True: # while needed
                token = self.randomGenerator.AlphaNumeric(_min=5, _max=10)
                csrf = self.randomGenerator.AlphaNumeric(_min=10, _max=20)
                purpose_tag = f"{general_purpose}.{real_purpose}.{token}"
                if general_purpose not in self.purpose_to_csrf:
                    self.purpose_to_csrf[general_purpose] = {}
                if purpose_tag not in self.purpose_to_csrf[general_purpose] or not self.purpose_to_csrf[general_purpose][purpose_tag]:
                    self.purpose_to_csrf[general_purpose][purpose_tag] = csrf
                    break
            return purpose_tag, csrf, extras
        self.active_functions.remove(function_name)
        return wrapper


    def check_and_invalidate_csrf(self, general_purpose:str, real_purpose:str, token:str):
        purpose_tag = f"{general_purpose}.{real_purpose}.{token}"
        if general_purpose in self.purpose_to_csrf and purpose_tag in self.purpose_to_csrf[general_purpose]:
            return self.purpose_to_csrf[general_purpose].pop(purpose_tag)
        return None


    def invalidate_general_csrf(self, general_purpose:str):
        self.purpose_to_csrf[general_purpose] = {}


    def send_flask_data(self, new_data: str, expected_div_name: str, method: str, action_delay: float = 0, remove_after: float = 0, _internal_delay: float = 0, _override: bool = False):
        function_name = "send_flask_data"
        if type(new_data) != str:
            new_data = str(new_data)

        self.active_functions.append(function_name)
        if action_delay:
            _internal_delay = action_delay
            Thread(target=self.send_flask_data, args=(new_data, expected_div_name, method, 0, remove_after, _internal_delay)).start()
            self.active_functions.remove(function_name)
            return

        if _internal_delay:
            sleep(_internal_delay)
            self.send_flask_data(new_data, expected_div_name, method, 0, remove_after)
            self.active_functions.remove(function_name)
            return

        new_div_name = None
        if not _override:
            for _ in range(1200):
                if not self.can_receive_turbo_flask_data:
                    sleep(0.01)
            self.can_receive_turbo_flask_data = False
        for _ in range(50):
            try:
                if not self.am_i_online():
                    break
                if method == self.turboMethods.new_div:
                    while True: # while needed
                        delimiter = self.randomGenerator.AlphaNumeric(_min=5, _max=30)
                        new_div_name = f"{expected_div_name}_{delimiter}"
                        if new_div_name not in self.div_name_to_html_data:
                            self.div_name_to_html_data[new_div_name] = ""
                            self.send_flask_data(f"""<div id='{new_div_name}'></div><div id='{expected_div_name}_create'></div>""", f'{expected_div_name}_create', self.turboMethods.replace, 0, 0, _override=True)
                            break
                        elif not self.div_name_to_html_data[new_div_name]:
                            break
                    self.send_flask_data(new_data, new_div_name, self.turboMethods.update, action_delay, remove_after, _override=True)
                    break
                elif method == self.turboMethods.replace:
                    self.turbo_app.push(self.turbo_app.replace(new_data, expected_div_name), to=self.viewer_id)
                    self.div_name_to_html_data[expected_div_name] = new_data
                    break
                elif method == self.turboMethods.remove:
                    self.turbo_app.push(self.turbo_app.remove(expected_div_name), to=self.viewer_id)
                    self.div_name_to_html_data[expected_div_name] = ""
                    break
                elif method == self.turboMethods.update:
                    if expected_div_name not in self.div_name_to_html_data or self.div_name_to_html_data[expected_div_name] != new_data:
                        self.turbo_app.push(self.turbo_app.update(new_data, expected_div_name), to=self.viewer_id)
                        self.div_name_to_html_data[expected_div_name] = new_data
                    if remove_after:
                        action_delay = remove_after
                        Thread(target=self.send_flask_data, args=('', expected_div_name, self.turboMethods.remove, 0, 0, remove_after)).start()
                    break
            except:
                pass
            sleep(1/1000)
        if not _override:
            self.can_receive_turbo_flask_data = True

        self.active_functions.remove(function_name)
        return new_div_name

