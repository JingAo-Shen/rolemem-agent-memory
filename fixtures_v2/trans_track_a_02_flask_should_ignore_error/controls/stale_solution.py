from flask import Flask

class CustomApp(Flask):
    def should_ignore_error(self, error):
        return isinstance(error, KeyError)
