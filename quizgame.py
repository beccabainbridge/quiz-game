import os
import sqlite3
from copy import copy
from contextlib import closing
from random import shuffle
from flask import Flask, render_template, request, redirect, session, flash
from flaskext.bcrypt import Bcrypt
import access_db

#configs
DEBUG = os.environ["QUIZ_DEBUG"]
SECRET_KEY = os.environ["QUIZ_SECRET_KEY"]
DATABASE = os.environ["QUIZ_DATABASE"]
SCHEMA = os.environ["QUIZ_SCHEMA"]
CSV = os.environ["QUIZ_CSV"]

app = Flask(__name__)
bcrypt = Bcrypt(app)
app.config.from_object(__name__)

class QuestionValidationError(Exception):
    pass

def get_questions(n, ordered=False):
    question_nums = access_db.get_question_nums()
    if not ordered:
        shuffle(question_nums)
    question_nums = question_nums[:n]
    questions = [access_db.get_question(num) for num in question_nums]
    return questions

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        if username in access_db.get_usernames():
            pw_hash = access_db.get_password(username)
            if bcrypt.check_password_hash(pw_hash, request.form['password']):
                session['username'] = username
                session['logged_in'] = True
                flash('You were logged in')
                return redirect('database')
            else:
                error = 'Incorrect password'
        else:
            error = 'Invalid username'

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect('/')

@app.route('/create_account', methods=['GET', 'POST'])
def create_user():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_confirm = request.form['password_confirm']
        if password != password_confirm:
            error = "Passwords don't match"
        elif username in access_db.get_usernames():
            error = "Username already in use. Please choose another."
        else:
            pw_hash = bcrypt.generate_password_hash(password)
            access_db.add_user(username, pw_hash)
            flash('Account created')
            return redirect('login')

    return render_template('create_account.html', error=error)

@app.route('/database', methods=['GET', 'POST'])
def database_access():
    if request.method == 'POST':
        update_type = request.form['change']
        i = request.form['id']
        q = request.form['question']
        a1, a2, a3, a4 = request.form['ans1'], request.form['ans2'], request.form['ans3'], request.form['ans4']
        c = request.form['correct']

        question_info = [q, a1, a2, a3, a4, c]
        names = ['question', 'ans1', 'ans2', 'ans3', 'ans4', 'correct']

        try:
            if not i and (update_type == 'delete' or update_type == 'update'):
                raise QuestionValidationError('Must enter question number to update or delete')

            if update_type == 'delete':
                access_db.add_proposed([i] + question_info + ['delete', session['username']])
                flash('Question submitted for deletion')
            else:
                for item in question_info:
                    if item == "" and update_type == 'add':
                        raise QuestionValidationError('Input cannot be left blank')

                access_db.add_proposed([i] + question_info + [update_type, session['username']])
                flash('Question submitted for %s' % update_type)

        except (sqlite3.OperationalError, QuestionValidationError) as e:
            flash('Invalid question entry: ' + str(e))

    questions = get_questions(access_db.get_num_questions(), ordered=True)
    return render_template('database.html', questions=questions)

@app.route('/admin', methods=['GET','POST'])
def admin():
    if request.method == 'POST':
        if request.form['button'] == "Reset High Scores":
            access_db.reset_highscores()
        changes = request.form.getlist("change")
        action = request.form['button']
        for change in changes:
            if action == 'Reject':
                access_db.remove_proposed(change)
            elif action == 'Accept':
                access_db.make_db_change(change)
    additions, updates, deletions = access_db.get_proposed()
    questions = get_questions(access_db.get_num_questions(), ordered=True)
    highscores = access_db.get_highscores()
    return render_template('admin.html', add=additions, update=updates, delete=deletions, questions=questions, highscores=highscores)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        total_questions = access_db.get_num_questions()
        options = range(5, total_questions + 1, 5)

        if options[-1] != total_questions:
            options.append(total_questions)

        return render_template('welcome.html', options=options)

    else:
        nquestions = int(request.form['nquestions'])
        session['questions'] = get_questions(nquestions)
        session['nquestions'] = nquestions
        session['curquestion'] = 0
        session['score'] = 0
        num_to_show = 10
        app.highscores = access_db.get_highscores(num_to_show)
        if len(app.highscores) >= num_to_show:
            app.lowest_highscore = app.highscores[-1][1]
        else:
            app.lowest_highscore = None

        return redirect('main')

@app.route('/main')
def main():
    if session['curquestion'] >= session['nquestions']:
        return redirect('/end')
    else:
        return redirect('/next')

@app.route('/end', methods=['GET','POST'])
def end():
    score = session['score']/session['nquestions'] * 100
    get_info = False
    if request.method == 'GET' and score >= app.lowest_highscore:
        get_info = True
    elif request.method == 'POST':
        name = request.form['name']
        access_db.add_to_highscores(name, score)
        # update highscores
        app.highscores = access_db.get_highscores(10)

    return render_template('end.html', score=score, \
                               highscores=app.highscores, get_info=get_info)

@app.route('/next', methods=['GET', 'POST'])
def next():
    if request.method == 'GET':
        num = session['curquestion'] + 1
        session['question_info'] = session['questions'][num-1]
        return render_template('question.html', num=num, \
                               question_info=session['question_info'])
    else:
        # gets response to question and stays on question if not answered
        ans = request.form
        if len(ans) == 0:
            return redirect('main')
        else:
            ans = ans['response']

        session['curquestion'] += 1

        correct = session['question_info']['correct']
        if ans == correct:
            session['score'] += 1.0
            feedback = 'Correct!'
        else:
            feedback = 'Incorrect! The correct answer was "%s"' \
                       %(session['question_info'][correct])

        flash(feedback)
        return redirect('main')

if __name__ == '__main__':
    if access_db.get_num_questions() == 0:
        access_db.create_database(DATABASE, SCHEMA, CSV)
    app.run()
