## SQL Tables
Our project relied heavily on the tables we created in SQL. We created four tables: users, chapters, forums, and homeBooks. 

### users
The 'users' table is essential for our registration and log in pages. These store the usernames and hashed passwords for each user. In order to ensure no users use the same username and that users log in with the appropriate password, we check the values in this table. The column values are id INTEGER (primary key), username TEXT, and hash TEXT(password). 

### chapters
The 'chapters' table holds all the information for a book in our database. This will store all the relevant information we need to match a forum to a book. The columns for 'chapters' are title TEXT, author TEXT, thumbnail TEXT, pageCount TEXT (all four for the book), and forum_id (the primary key, or identifier for a forum). 

### forums
The 'forums' table holds all the comments in each forum. The structure of 'forums' is user_id INTEGER, comment TEXT NOT NULL, parent_id INTEGER, time DATETIME, forum_id INTEGER, percentage TEXT, comment_id INTEGER (primary key, or identifier for comment). Each row in this table stores a different comment, with the corresponding user id of the user (from the users table) that wrote the comment, time the comment was written, and percentage of the book the user was through when they posted the comment (None if the user didn't put one). Note that the percentage is of a TEXT datatype to allow for it being "None" and otherwise, it will be rounded to the nearest integer percent. 

All replies to a comment will also have the same percentage tracked in our table. Then, each comment has a unique comment_id and replies to a parent comment are tracked through the parent_id column, which holds the comment_id for the comment the current comment is a reply to. The forum_id corresponds to that of the forum/book the comment is under/about. This table is essential for the functionality of our contributions and forum pages. 

### homeBooks
The 'homeBooks' table stores the books on a user's home page. Its columns are forum_id INTEGER, user_id INTEGER, and status TEXT. The forum_id is the tracker for the books, as stated before, and the user_id identifies the corresponding user. Then, the status can be "TBR", "PROG", or "DONE" for whether the user has the book on its TBR list, in progress list, or completed list. This table is then essential to the display of the home page. 