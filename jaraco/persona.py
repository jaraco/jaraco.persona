import json

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
        return """
            var currentUser = %(username)s;

            function simpleXhrSentinel(xhr) {
                return function() {
                    if (xhr.readyState == 4) {
                        if (xhr.status == 200){
                            // reload page to reflect new login state
                            window.location.reload();
                          }
                        else {
                            navigator.id.logout();
                            alert("XMLHttpRequest error: " + xhr.status);
                          }
                        }
                      }
                    }

            function verifyAssertion(assertion) {
                // Your backend must return HTTP status code 200 to indicate successful
                // verification of user's email address and it must arrange for the binding
                // of currentUser to said address when the page is reloaded
                var xhr = new XMLHttpRequest();
                xhr.open("POST", "%(login_path)s", true);
                // see http://www.openjs.com/articles/ajax_xmlhttp_using_post.php
                var param = "assertion="+assertion;
                xhr.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
                xhr.setRequestHeader("Content-length", param.length);
                xhr.setRequestHeader("Connection", "close");
                xhr.send(param); // for verification by your backend

                xhr.onreadystatechange = simpleXhrSentinel(xhr); }

            function signoutUser() {
                // Your backend must return HTTP status code 200 to indicate successful
                // sign out (usually the resetting of one or more session variables) and
                // it must arrange for the binding of currentUser to 'null' when the page
                // is reloaded
                var xhr = new XMLHttpRequest();
                xhr.open("GET", "%(logout_path)s", true);
                xhr.send(null);
                xhr.onreadystatechange = simpleXhrSentinel(xhr); }

            // Go!
            navigator.id.watch( {
                loggedInUser: currentUser,
                     onlogin: verifyAssertion,
                    onlogout: signoutUser } );
        """ % vars()

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
