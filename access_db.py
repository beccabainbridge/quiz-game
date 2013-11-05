import sqlite3
import codecs
from flaskext.bcrypt import Bcrypt
from contextlib import closing

db_file = 'quizgame.db'

def create_database(db_file, schema, csv):
    def init_db():
        with closing(connect_db(db_file)) as db:
            with open(schema, mode='r') as f:
                db.cursor().executescript(f.read())
                db.commit()

    def generate_db_from_csv():
        with codecs.open(csv, encoding="utf-8", mode='rb') as f:
            for row in f:
                row = row.rstrip().split(',') # removes new line chars before splitting
                add_question(row, db_file)

    init_db()
    generate_db_from_csv()

def connect_db(db_file=db_file):
    return sqlite3.connect(db_file)

def select(database, query, items=None):
    with closing(connect_db(database)) as db:
        if items:
            q = db.execute(query, items)
        else:
            q = db.execute(query)
        return q.fetchall()

def insert(database, query, items):
    with closing(connect_db(database)) as db:
        db.execute(query, items)
        db.commit()

def update(database, query, items):
    insert(database, query, items)

def delete(database, query, items):
    with closing(connect_db(database)) as db:
        db.execute(query, items)
        db.commit()

def get_db_size(database, table):
    try:
        query = "SELECT COUNT(*) FROM %s" % table
        sizeinfo = select(database, query)
        size = sizeinfo[0][0]
    except sqlite3.OperationalError:
        size = 0

    return size

def item_in_db(database, table, (name, item)):
    query = "SELECT COUNT(*) from %s WHERE %s=?" %(table, name)
    result = select(database, query, item)
    exists = result[0][0]
    return exists >= 1

def get_num_questions():
    return get_db_size(db_file, 'questions')

def question_in_db(question):
    return item_in_db(db_file, 'questions', ('question', question))

def add_question(row):
    if question_in_db(row[1], db_file):
        raise Exception('Question already in database. If you want to change the question, choose "Update Question"')
    else:
        insert(db_file, 'INSERT INTO questions (num, question, ans1, ans2, ans3, ans4, correct) VALUES (?, ?, ?, ?, ?, ?, ?)', row)

def update_question(question_num, change, remove=False):
    question = select(db_file, "SELECT question from questions WHERE id=?", \
                                  (question_num,))[0][0]
    if not question_in_db(question, db_file):
        raise Exception('Question not in database.')
    else:
        if remove:
            delete(db_file, 'DELETE FROM questions WHERE id=?', (question_num,))
        else:
            update(db_file, 'UPDATE questions SET %s=? where id=?' %change[0], \
                       (change[1], question_num))


def add_to_highscores(name, score):
    insert(db_file, "INSERT INTO highscores (name, score) VALUES (?, ?)", (name, score,))


def get_highscores(num):
    try:
        query = select(db_file, "SELECT name, score FROM highscores order by score desc")
        highscores = [(name, score) for name, score in query]
        if len(highscores) < num:
            return highscores
        else:
            return highscores[:num]
    except sqlite3.OperationalError:
        return []

def get_question(n):
    q = select(db_file, "SELECT id, question, ans1, ans2, ans3, ans4, correct FROM questions WHERE id=?", (n,))
    entry = q[0]
    #consider using zip here
    return dict(id=entry[0], question=entry[1], A=entry[2], B=entry[3], \
                        C=entry[4], D=entry[5], correct=entry[6])

def get_question_nums():
    entries = select(db_file, "SELECT id from questions")
    question_ids = [row[0] for row in entries]
    return question_ids

def add_user(username, pw_hash):
    insert(db_file, 'INSERT INTO usernames (username) VALUES (?)', (username,))
    q = select(db_file, 'SELECT id from usernames WHERE username=?', \
                             (username,))
    id_num = q[0][0]
    insert(db_file, 'INSERT INTO passwords (id, password) VALUES (?,?)', \
                       (id_num, pw_hash))

def get_usernames():
    entries = select(db_file, "SELECT username from usernames")
    usernames = [entry[0] for entry in entries]
    return usernames

def get_password(username):
    id_num = select(db_file, 'SELECT id from usernames WHERE username=?', \
                        (username,))[0][0]
    password = select(db_file, 'SELECT password FROM passwords WHERE id=?', \
                       (id_num,))[0][0]
    return password

def add_proposed(row):
    insert(db_file, "INSERT INTO proposed (id, num, question, ans1, ans2, ans3, ans4, correct, kind, username) VALUES (?,?,?,?,?,?,?,?,?,?)", row)

def get_proposed():
    proposed = {}
    for kind in ['add', 'update', 'delete']:
        proposed[kind] = select(db_file, "SELECT * from proposed WHERE kind=?", kind)
    return proposed['add'], proposed['update'], proposed['delete']
