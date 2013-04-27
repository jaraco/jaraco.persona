jaraco.persona
==============

``jaraco.persona`` is a `CherryPy <http://cherrypy.org>`_ tool implementation
of the `Mozilla Persona <http://www.mozilla.org/en-US/persona/>`_ protocol.

Usage
=====

To use the library, simply install it (using easy_install or pip) alongside
your site code, then enable both sessions and the persona tool in your site.

Here is the complete example, which is also available in the library and may
be launched by invoking ``python -m jaraco.persona``::

    class HelloWorld:
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

Configuration
=============

The tool requires an 'audience' parameter, which specifies the ``host:port``
string on which the service runs. This parameter must be configured to match
the server so that requests can be properly authenticated. The 'audience'
may be set to the string 'HOST' in which case the HTTP Host header will be
used, but this setting should only be used in an environment where the Host
header can be trusted, such as when a reverse proxy is used that validates
the header.

Partial Auth
============

If you have a section of your site which should be secured and another which
should not, you may apply the tool selectively to certain paths in your
CherryPy config. For example::

    config = {
        # by default, require all resources to be secure
        '/': {
            'tools.sessions.on': True,
            'tools.persona.on': True,
        },
        # allow access to static resources without auth
        '/static': {
            'tools.static.on': True,
            'tools.static.dir': './static',
            'tools.persona.on': False,
        }
        # don't require auth for favicon.ico
        'favicon.ico': {
            'tools.persona.on': False,
        }
    }

More details can be found in the `Configuration
<http://docs.cherrypy.org/stable/concepts/config.html>`_ section of the
CherryPy docs.
