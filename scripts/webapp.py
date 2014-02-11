from __future__ import print_function
import os
import sys
import traceback
import styles_distribution as updater

def server(environ, start_response):
    data = "\n"
    start_response("200 OK", [
        ("Content-Type", "text/plain"),
        ("Content-Length", str(len(data)))
    ])
    return iter([data])

def update_styles(environ):
    try:
        print("Updating styles")

        # Styles directories are in ../styles/
        styles_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'styles'))
        updater.ORIGINAL_STYLES_DIRECTORY = os.path.join(styles_dir, 'original')
        updater.DISTRIBUTION_STYLES_DIRECTORY = os.path.join(styles_dir, 'distribution')

        updater.main(False, 'HEAD')

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
        try:
            result = self.__application(environ, start_response)
        except:
            self.__callback(environ)
            raise
        return Generator(result, self.__callback, environ)

sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0) # make stdout unbuffered
application = ExecuteOnCompletion(server, update_styles)