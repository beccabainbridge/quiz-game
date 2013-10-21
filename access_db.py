import sqlite3
import codecs
from contextlib import closing

csv = 'quiz_questions.csv'

def create_database(filename, schema):
    init_db(filename, schema)
    generate_db_from_csv(filename)

def connect_db(filename):
    return sqlite3.connect(filename)

def init_db(filename, schema):
    with closing(connect_db(filename)) as db:
        with open(schema, mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def question_in_db(question, filename):
    with closing(connect_db(filename)) as db:
        query = db.execute('SELECT COUNT(*) from questions WHERE question=?', (question,))
        exists = query.fetchone()[0]
        return exists >= 1

def add_question(row, filename):
    with closing(connect_db(filename)) as db:
        if question_in_db(row[1], filename):
            raise Exception('Question already in database.')
        else:
            db.execute('INSERT INTO questions (num, question, ans1, ans2, ans3, ans4, correct) VALUES (?, ?, ?, ?, ?, ?, ?)', row)
            db.commit()

def generate_db_from_csv(filename):
    with codecs.open(csv, encoding="utf-8", mode='rb') as f:
        for row in f:
            row = row.rstrip().split(',')
            add_question(row, filename)
