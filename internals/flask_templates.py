from internals.div_names import TurboFlaskDivNames


class FlaskTemplates:
    def __init__(self, div_names:TurboFlaskDivNames):
        self.div_names  = div_names
        
    def home_base(self):
        return f"""
<!DOCTYPE html>
<head>

<script src="https://cdnjs.cloudflare.com/ajax/libs/jquery/3.3.1/jquery.min.js"></script>

<script>
function submit_ws(form) 
{{
    let form_data = JSON.stringify(Object.fromEntries(new FormData(form)));
    web_sock.send(form_data);
    return false;
}}
</script>

<style>
    th, td {{border: 1px solid black; margin-left: auto; margin-right: auto;}}
</style>

<script type="module">
import * as Turbo from "https://cdn.skypack.dev/pin/@hotwired/turbo@v7.1.0-RBjb2wnkmosSQVoP27jT/min/@hotwired/turbo.js";
Turbo.disconnectStreamSource(window.web_sock)
window.web_sock = new WebSocket(`ws${{location.protocol.substring(4)}}//${{location.host}}/ws`);
window.web_sock.addEventListener('close', function() {{document.getElementById("{self.div_names.new_account_form}").innerHTML = "DISCONNECTED, REFRESH TO CONTINUE";}});
Turbo.connectStreamSource(window.web_sock);
</script>


</head>


<body>
<div id="{self.div_names.script}_create"></div><br>
<div id="{self.div_names.authenticated_table}"></div><br>
<div id="{self.div_names.failed_table}"></div><br>
<div id="{self.div_names.new_account_form}"></div><br>
<div id="{self.div_names.public}"></div><br>
<div id="{self.div_names.private}"></div><br>
<div id="{self.div_names.debug}"></div><br>
</body>
"""


    @staticmethod
    def update_pass_form(secret_generator):
        purpose, csrf_token, extra = secret_generator()
        return f"""
<form id='PASSWORD_UPDATE_FORM' onsubmit="return submit_ws(this)" autocomplete="on">
<input type="hidden" id="CSRF" name="CSRF" value="{csrf_token}">
<input type="hidden" id="PURPOSE" name="PURPOSE" value="{purpose}">
<input type="hidden" id="_ID" name="_ID" value="{extra[0]}">
<input type="text" id="NEW_PASSWORD" name="NEW_PASSWORD" value="" placeholder="PASSWORD"><br>
<input type=submit value="UPDATE">
</form>"""


    @staticmethod
    def add_account(secret_generator):
        purpose, csrf_token, extra = secret_generator()
        return f"""
<form id='NEW_ACCOUNT_FORM' onsubmit="return submit_ws(this)" autocomplete="on">
<input type="hidden" id="CSRF" name="CSRF" value="{csrf_token}">
<input type="hidden" id="PURPOSE" name="PURPOSE" value="{purpose}">
<input type="text" id="USERNAME" name="USERNAME" value="" placeholder="USERNAME"><br>
<input type="text" id="PASSWORD" name="PASSWORD" value="" placeholder="PASSWORD"><br>
<input type="text" id="EMAIL" name="EMAIL" value="" placeholder="EMAIL"><br>
<textarea rows="10" cols="30" id="EXTRAS" name="EXTRAS" value="" placeholder="EXTRAS"></textarea><br>
<input type=submit value="ADD">
</form>"""


