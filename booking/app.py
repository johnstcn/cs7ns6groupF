from flask_bootstrap import Bootstrap
from flask_admin import Admin
from database import create_app
import config
import views

app = create_app(config)
Bootstrap(app)
admin = Admin(app, name='Booking', template_mode='bootstrap3')
app.register_blueprint(views.sv)


if __name__ == '__main__':
    app.run()
