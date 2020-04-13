from flask import Blueprint, render_template, redirect, url_for, request, flash
from forms.login import LoginForm
import operation


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
    conn = operation.connect('test.db')
    table_name = 'room'
    unoccupied = operation.select(conn, table_name)
    occupied = operation.select(conn, table_name, 'occupied')
    labels = ['RoomID']
    occupied_room_id = [i[1] for i in occupied]
    unoccupied_room_id = [i[1] for i in unoccupied]
    if request.method == 'POST':
        result = dict()
        for idx in unoccupied_room_id:
            if request.values.get(str(idx)) == 'Y':
                result[idx] = operation.update(conn, table_name, idx)

        if len(result):
            for idx, flag in result.items():
                if flag:
                    flash('Room {} successfully booked'.format(idx))
                else:
                    flash('Room {} not available'.format(idx))

    return render_template('search.html', labels=labels, content=unoccupied_room_id, content1=occupied_room_id)


