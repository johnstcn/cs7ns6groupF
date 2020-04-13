from flask_bootstrap import Bootstrap
from flask_admin import Admin
from flask import Flask
import config
import views

app = Flask(__name__)
app.config.from_object(config)

Bootstrap(app)
# admin = Admin(app, name='Booking', template_mode='bootstrap3')
app.register_blueprint(views.sv)


if __name__ == '__main__':
    app.run()
