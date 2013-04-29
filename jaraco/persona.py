import json

import pkg_resources
import browserid
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
        """
        When initialized, the tool installs itself into the 'before_handler'
        hook at the default priority.

        As a result, for every request for which the tool is enabled,
        self.authenticate will be invoked.
        """
        super(Persona, self).__init__('before_handler', self.authenticate)

    @property
    def username(self):
        """
        The tool supplies a username property which stores the authenticated
        user's name in the session. A subclass could override this property
        to customize the server-side storage of the username.
        """
        return cherrypy.session.get('username', None)

    @username.setter
    def username(self, username):
        cherrypy.session['username'] = username

    def persona_script(self, login_path, logout_path):
        username = json.dumps(self.username)
        username
        template = pkg_resources.resource_string(__name__, 'XHR persona.js')
        return template % vars()

    def authenticate(self, audience, login_path='/login',
            logout_path='/logout'):
        """
        Entry point for this tool.

        Audience is the host name and port on which this server is hosting.
        It may be set to 'HOST' to use the HOST header, but this setting
        SHOULD ONLY BE USED when the HOST header has been verified by a
        trusted party (such as a reverse-proxy).
        """
        if audience == 'HOST':
            audience = cherrypy.request.headers['HOST']
        self.audience = audience

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
            # the user is not logged in, but the tool is enabled, so instead
            #  of allowing the default handler to run, respond instead with
            #  the authentication page.
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
        # Verify the assertion using browserid.
        validation = browserid.verify(assertion, self.audience)

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
        'tools.persona.audience': 'localhost:8080',
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
