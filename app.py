#!/usr/bin/env python
# -*- coding: utf-8 -*-#

import os
import logging
import connexion

from dotenv import load_dotenv


class Server:
    application = None
    app = None

    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.connexion_app = connexion.FlaskApp(__name__, specification_dir="./swagger")
        load_dotenv()

        self.connexion_app.app.secret_key = os.getenv('SECRET_KEY')
        self.connexion_app.add_api(os.getenv('SWAGGER_FILE'), options={'swagger_ui': True})

        self.port = int(os.getenv('PORT', 8080))
        self.debug = bool(os.getenv('DEBUG', False))

        # orm_handler.db_init()

        @self.connexion_app.app.after_request
        def apply_cors(response):
            response.headers["Content-Type"] = "application/json"
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "x-api-key, Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token"
            response.headers["Access-Control-Request-Headers"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, PUT, POST, OPTIONS, DELETE"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            return response

        # @self.connexion_app.app.teardown_appcontext
        # def shutdown_session(exception=None):
        #     orm_handler.db_session.remove()

    def run(self):
        if self.debug:
            print("Running in Debug Mode")
            self.connexion_app.run(port=self.port, debug=True, threaded=True)
        else:
            self.connexion_app.run(port=self.port, debug=self.debug, server="gevent")


s = None

if __name__ == "__main__":
    s = Server()
    s.run()
