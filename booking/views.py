from flask import Blueprint, render_template, redirect, url_for, request, flash
from forms.login import LoginForm
from models import *
import db_operation

sv = Blueprint("sv", __name__)  # initialise a Blueprint instance


@sv.route('/user/<name>')
def user(name):
    return render_template('user.html', name=name)


@sv.route('/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        if request.method == 'GET':
            username = request.args.get('username')
        else:
            username = request.form.get('username')
        return redirect('/search')
    return render_template('login.html', form=form)


@sv.route('/search', methods=['GET', 'POST'])
def search():
    u = Room.query.filter(Room.RoomState == 'unoccupied').all()
    labels = ['RoomID']
    room_id = [i.RoomID for i in u]
    if request.method == 'POST':
        result = dict()
        for idx in room_id:
            if request.values.get(idx) == 'Y':
                result[idx] = db_operation.update(idx)

        if len(result):
            for idx, flag in result.items():
                if flag:
                    print(1)
                    flash('Room {} successfully booked'.format(idx))
                else:
                    print(0)
                    flash('Room {} not available'.format(idx))

    return render_template('search.html', labels=labels, content=room_id)
