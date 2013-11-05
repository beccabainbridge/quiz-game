create table questions (
  id integer primary key autoincrement,
  question text not null,
  ans1 text not null,
  ans2 text not null,
  ans3 text not null,
  ans4 text not null,
  correct text not null
);
create table highscores (
  name text,
  score integer
);
create table usernames (
  id integer primary key autoincrement,
  username text not null
);
create table passwords (
  id integer primary key,
  password text not null
);
create table proposed (
  changeid integer primary key autoincrement,
  id integer,
  question text,
  ans1 text,
  ans2 text,
  ans3 text,
  ans4 text,
  correct text,
  kind text,
  username text
);
  