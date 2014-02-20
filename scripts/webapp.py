from __future__ import print_function
import os
import sys
import json
import traceback
import styles_distribution as updater
from cgi import parse_qs

def server(environ, start_response):
    if environ.get("HTTP_AUTHORIZATION") == os.getenv("AUTHORIZATION"):
        status = "200 OK"
    else:
        status = "400 Bad Request"

    request_body_size = int(environ.get('CONTENT_LENGTH', 0))
    request_body = environ['wsgi.input'].read(request_body_size)
    if request_body:
        try:
            payload = parse_qs(request_body)["payload"][0]
            environ["commit_hash"] = json.loads(payload)["commit"]
        except ValueError:
            status = "400 Bad Request"
    else:
        environ["commit_hash"] = "HEAD"

    data = "\n"
    environ["response_status"] = status

    start_response(status, [
        ("Content-Type", "text/plain"),
        ("Content-Length", str(len(data)))
    ])
    return iter([data])

def update_styles(environ):
    if environ["response_status"][0:3] != "200":
        return

    try:
        print("Updating styles to {0}".format(environ["commit_hash"]))

        # Styles directories are in ../styles/
        styles_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'styles'))
        updater.ORIGINAL_STYLES_DIRECTORY = os.path.join(styles_dir, 'original')
        updater.DISTRIBUTION_STYLES_DIRECTORY = os.path.join(styles_dir, 'distribution')

        updater.main(False, environ["commit_hash"])

    except:
        traceback.print_exc()

# Run code after request completion
#
# Adapted from http://code.google.com/p/modwsgi/wiki/RegisteringCleanupCode
class Generator:
    def __init__(self, iterable, callback, environ):
        self.__iterable = iterable
        self.__callback = callback
        self.__environ = environ
    def __iter__(self):
        for item in self.__iterable:
            yield item
    def close(self):
        try:
            if hasattr(self.__iterable, 'close'):
                self.__iterable.close()
        finally:
            self.__callback(self.__environ)

class ExecuteOnCompletion:
    def __init__(self, application, callback):
        self.__application = application
        self.__callback = callback
    def __call__(self, environ, start_response):
        result = self.__application(environ, start_response)
        return Generator(result, self.__callback, environ)

sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0) # make stdout unbuffered
application = ExecuteOnCompletion(server, update_styles)
