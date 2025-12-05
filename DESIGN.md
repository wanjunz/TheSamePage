
We created tables using SQL.

The 'chapters' table holds all the book information. The structure of 'chapters' is (title TEXT NOT NULL, author TEXT NOT NULL, forum_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL).


The 'forums' table holds all the comments in each forum. The structure of 'forums' is (username TEXT NOT NULL, comment TEXT NOT NULL, parent_id INTEGER, time DATETIME, forum_id INTEGER, percent INTEGER, FOREIGN KEY (forum_id) REFERENCES chapters(forum_id)).