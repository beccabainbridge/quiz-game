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

def add_question(row, filename):
    with closing(connect_db(filename)) as db:
        db.execute('INSERT INTO questions (num, question, ans1, ans2, ans3, ans4, correct) VALUES (?, ?, ?, ?, ?, ?, ?)', row)
        db.commit()

def generate_db_from_csv(filename):
    with codecs.open(csv, encoding="utf-8", mode='rb') as f:
        for row in f:
            row = row.rstrip().split(',')
            add_question(row, filename)
