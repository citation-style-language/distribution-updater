CSL styles-distribution updater
====================

This is a WSGI app to update the [CSL styles distribution repo](https://github.com/citation-style-language/styles-distribution) based on a Travis CI webhook defined in the [main CSL styles repo](https://github.com/citation-style-language/styles).

Example usage:

```
cd scripts
gunicorn -t 3600 -b 127.0.0.1:8080 --env AUTHORIZATION=[webhook-token] --access-logfile - webapp
```

The WSGI server should be run as the user defined in the bin/update_permissions script, which can be used to properly set permissions on the styles submodules.
