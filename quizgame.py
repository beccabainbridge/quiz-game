import os
import sqlite3
from contextlib import closing
from random import shuffle
from flask import Flask, render_template, request, redirect, g, session, flash
from flaskext.bcrypt import Bcrypt
from access_db import * # don't do this :)

#configs
DEBUG = os.environ["QUIZ_DEBUG"]
SECRET_KEY = os.environ["QUIZ_SECRET_KEY"]

database = 'quizgame.db'
schema = 'schema.sql'
csv = 'quiz_questions.csv'

app = Flask(__name__)
bcrypt = Bcrypt(app)
app.config.from_object(__name__)

def get_questions(n, ordered=False):
    question_nums = get_question_nums()
    if not ordered:
        shuffle(question_nums)
    question_nums = question_nums[:n]
    questions = [get_question(num) for num in question_nums]
    return questions

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        if username in get_usernames():
            pw_hash = get_password(username)
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
        elif username in get_usernames():
            error = "Username already in use. Please choose another."
        else:
            add_user(username, password)
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
        n = get_num_questions() + 1

        question_info = [n, q, a1, a2, a3, a4, c]
        names = ['num', 'question', 'ans1', 'ans2', 'ans3', 'ans4', 'correct']
                
        try:
            if not i and (update_type == 'delete' or update_type == 'update'):
                raise Exception('Must enter question number to update or delete')
            
            if update_type == 'delete':
                add_proposed([i] + question_info + ['delete', session['username']])
                flash('Question submitted for deletion')                    
            else:
                for item in question_info:
                    if item == "":
                        if update_type == 'add':
                            raise Exception('Input cannot be left blank')
                    else:
                        if update_type == 'update':
                            pass

                if update_type == 'add':
                    add_proposed([i] + question_info + ['add', session['username']])
                    flash('Question submitted for addition')
                else:
                    add_proposed([i] + question_info + ['update', session['username']])
                    flash('Question submitted for update')

        except (sqlite3.OperationalError, Exception) as e:
            flash('Invalid question entry: ' + str(e))

    questions = get_questions(get_num_questions(), ordered=True)
    return render_template('database.html', questions=questions)

@app.route('/admin', methods=['GET','POST'])
def admin():
    if request.method == 'POST':
        pass

    additions, updates, deletions = get_proposed()
    questions = get_questions(get_num_questions(), ordered=True)
    return render_template('admin.html', add=additions, update=updates, delete=deletions, questions=questions)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        total_questions = get_num_questions()
        options = range(5, total_questions + 1, 5)

        if options[-1] != total_questions:
            options.append(total_questions)

        return render_template('welcome.html', options=options)

    else:
        nquestions = int(request.form['nquestions'])
        app.questions = get_questions(nquestions)
        app.nquestions = nquestions
        app.curquestion = 0
        app.score = 0
        num_to_show = 10
        app.highscores = get_highscores(num_to_show)
        if len(app.highscores) >= num_to_show:
            app.lowest_highscore = app.highscores[-1][1]
        else:
            app.lowest_highscore = None
        
        return redirect('main')

@app.route('/main')
def main():
    if app.curquestion >= app.nquestions:
        return redirect('/end')
    else:
        return redirect('/next')

@app.route('/end', methods=['GET','POST'])
def end():
    score = app.score/app.nquestions * 100
    if request.method == 'GET' and score >= app.lowest_highscore:
        return render_template('end.html', score=score, \
                                   highscores=app.highscores, get_info=True)
    elif request.method == 'POST':
        name = request.form['name']
        add_to_highscores(name, score)
        # update highscores
        app.highscores = get_highscores(10)
        return render_template('end.html', score=score, \
                                   highscores=app.highscores, get_info=False)
        
    else:
        return render_template('end.html', score=score, \
                                   highscores=app.highscores, get_info=False)

@app.route('/next', methods=['GET', 'POST'])
def next():
    if request.method == 'GET':
        app.question_info = app.questions[app.curquestion]
        app.n = app.curquestion + 1
        app.q = app.question_info['question']
        a1, a2, a3, a4 = app.question_info['A'], app.question_info['B'], \
                         app.question_info['C'], app.question_info['D']
        
        return render_template('question.html', num=app.n, question=app.q, \
                                   ans1=a1, ans2=a2, ans3=a3, ans4=a4)
    else:
        # gets response to question and stays on question if not answered
        ans = request.form
        if len(ans) == 0:
            return redirect('main')
        else:
            ans = ans['response']
        
        app.curquestion += 1

        correct = app.question_info['correct']
        if ans == correct:
            app.score += 1.0
            feedback = 'Correct!'
        else:
            feedback = 'Incorrect! The correct answer was "%s"' \
                         %(app.question_info[correct])

        flash(feedback)
        return redirect('main')

if __name__ == '__main__':
    if get_num_questions() == 0:
        create_database(database, schema, csv)
    app.run()
