from website import create_app
from flask import Flask, render_template, request, session
from flask_migrate import Migrate
import sys



application = create_app()



if __name__ == '__main__':
    application.run(debug=True)

