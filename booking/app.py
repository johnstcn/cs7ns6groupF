from flask import render_template, session, redirect, url_for, request
from flask_bootstrap import Bootstrap
from flask_admin import Admin
from api.login import LoginForm
from api.search import SearchForm
from database import create_app
from models import *
import config

app = create_app(config)
Bootstrap(app)
admin = Admin(app, name='Booking', template_mode='bootstrap3')


@app.route('/user/<name>')
def user(name):
    return render_template('user.html', name=name)


@app.route('/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        if request.method == 'GET':
            username = request.args.get('username')
        else:
            username = request.form.get('username')
        return redirect(url_for('search'))
    return render_template('login.html', form=form)


@app.route('/search', methods=['GET', 'POST'])
def search():
    # room1 = Room(RoomID="101", RoomState='unoccupied')
    # room2 = Room(RoomID="102", RoomState='unoccupied')
    # room3 = Room(RoomID="103", RoomState='unoccupied')
    # room4 = Room(RoomID="104", RoomState='unoccupied')
    # room5 = Room(RoomID="105", RoomState='unoccupied')
    # room6 = Room(RoomID="106", RoomState='unoccupied')
    # room7 = Room(RoomID="201", RoomState='unoccupied')
    # room8 = Room(RoomID="202", RoomState='unoccupied')
    # room9 = Room(RoomID="203", RoomState='unoccupied')
    # room10 = Room(RoomID="204", RoomState='unoccupied')
    # room11 = Room(RoomID="205", RoomState='unoccupied')
    #
    # db.session.add_all([room1, room2, room3, room4, room5, room6, room7, room8, room9, room10, room11])
    # db.session.commit()
    #
    # print("Add successfully")
    # form = SearchForm()
    u = Room.query.filter(Room.RoomState == 'unoccupied').all()
    labels = ['RoomID']
    content = [i.RoomID for i in u]
    return render_template('search.html', labels=labels, content=content)


if __name__ == '__main__':

    app.run()
