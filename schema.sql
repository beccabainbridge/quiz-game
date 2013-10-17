create table questions (
  id integer primary key autoincrement,
  num text not null,
  question text not null,
  ans1 text not null,
  ans2 text not null,
  ans3 text not null,
  ans4 text not null,
  correct text not null
)