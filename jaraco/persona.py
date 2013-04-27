import json

import pkg_resources
import requests
import cherrypy


class Persona(cherrypy.Tool):
    """
    The base CherryPy Tool for redirecting unauthenticated requests to Mozilla
    Persona for authentication. Extend this class
    and override :property:`username` if you
    would like to customize credential storage.

    Make sure you have the following in your _cp_config::

        'tools.persona.on': True,

    as well as initializing the tool at the module level or in your cherrypy
    initializer::

        cherrypy.tools.persona = Persona()
    """

    def __init__(self):
        super(Persona, self).__init__('before_handler', self.authenticate)

    @property
    def username(self):
        return cherrypy.session.get('username', None)

    @username.setter
    def username(self, username):
        cherrypy.session['username'] = username

    def persona_script(self, login_path, logout_path):
        username = json.dumps(self.username)
        username
        template = pkg_resources.resource_string(__name__, 'XHR persona.js')
        return template % vars()

    def authenticate(self, login_path='/login', logout_path='/logout'):
        """
        """
        if cherrypy.request.path_info == login_path:
            cherrypy.request.handler = self.login
            return
        elif cherrypy.request.path_info == logout_path:
            cherrypy.request.handler = self.logout
            return

        # add the script to the request so the various handlers can inject
        # it into their content.
        cherrypy.request.persona_script = self.persona_script(login_path, logout_path)

        if not self.username:
            cherrypy.request.handler = self.force_login

    def force_login(self):
        """
        This handler replaces the default handler when the user is not yet
        authenticated.
        Return a response that will:
         - trigger persona to authenticate the user
         - on success, try to load the page again
        """
        return """
        <html><head>
        <script src="https://login.persona.org/include.js"></script>
        <script>
            %(persona_script)s
            navigator.id.request();
        </script>
        </head>
        <body>
        Please log in...
        </body>
        </html>
        """ % dict(persona_script=cherrypy.request.persona_script)

    def login(self):
        assertion = cherrypy.request.params['assertion']
        # Send the assertion to Mozilla's verifier service.
        data = {'assertion': assertion, 'audience': 'http://localhost:8080'}
        resp = requests.post('https://verifier.login.persona.org/verify',
            data=data, verify=True)

        # Did the verifier respond?
        resp.raise_for_status()

        validation = resp.json()
        # Check if the assertion was valid
        if validation['status'] != 'okay':
            raise cherrypy.HTTPError(400, "invalid")
        # Log the user in by setting the username
        self.username = validation['email']
        return 'You are logged in'

    def logout(self):
        self.username = None
        return 'Logged out.'


class HelloWorld:
    """
    A fully-contained example CherryPy app utilizing persona
    """
    _cp_config = {
        'tools.persona.on': True,
        'tools.sessions.on': True,
    }

    @cherrypy.expose
    def index(self):
        return "Hello %(username)s" % cherrypy.session

    @classmethod
    def run(cls):
        config = {
            'global': {
                'server.socket_host': '::0',
            }
        }
        cherrypy.tools.persona = Persona()
        cherrypy.quickstart(cls(), "/", config)

if __name__ == '__main__':
    HelloWorld.run()
