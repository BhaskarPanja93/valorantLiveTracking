from gevent import monkey
monkey.patch_all()

from gevent.pywsgi import WSGIServer
from dynamicWebsite import *
from internals.Enums import *



def sendBasePage(viewerObj:BaseViewer):
    pass


def newViewer(viewerObj:BaseViewer):
    pass


def formSubmit(viewerObj:BaseViewer, form:dict):
    pass


baseApp, turboApp = createApps(formSubmit,
                               newViewer,
                               "Valorant Live Tracker",
                               Routes.home.value,
                               Routes.websocket.value,
                               Secrets.fernetSecret.value,
                               "",
                               "Stats",
                               True)


WSGIServer(('0.0.0.0', Constants.sitePort.value,), baseApp, log=None).serve_forever()

