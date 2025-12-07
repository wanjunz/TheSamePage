## SQL Tables
Our project relied heavily on the tables we created in SQL. We created four tables: users, chapters, forums, and homeBooks. Our table structures are as follows:
- CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, username TEXT NOT NULL, hash TEXT NOT NULL);
- CREATE TABLE chapters (title TEXT NOT NULL, author TEXT NOT NULL, forum_id TEXT NOT NULL PRIMARY KEY AUTOINCREMENT NOT NULL, thumbnail TEXT, pageCount INTEGER);
- CREATE TABLE forums (user_id INTEGER, comment TEXT NOT NULL, parent_id INTEGER, time DATETIME, forum_id TEXT NOT NULL, percentage TEXT, comment_id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, FOREIGN KEY (forum_id) REFERENCES chapters(forum_id));
- CREATE TABLE homeBooks (forum_id TEXT NOT NULL, user_id INTEGER, status TEXT, FOREIGN KEY (forum_id) REFERENCES chapters(forum_id));

### users table
The 'users' table is essential for our registration and log in pages. These store the usernames and hashed passwords for each user. In order to ensure no users use the same username and that users log in with the appropriate password, we check the values in this table. The column values are id INTEGER (primary key), username TEXT, and hash TEXT(password). 

### chapters table
The 'chapters' table holds all the information for a book in our database. This will store all the relevant information we need to match a forum to a book. The columns for 'chapters' are title TEXT, author TEXT, thumbnail TEXT, pageCount TEXT (all four for the book), and forum_id (the primary key, this is the unique volume ID of the book retrieved from the API). Every time a new book is interacted with, either by adding to their TBR list or commented on the book's forum, it is added to the table. 

### forums table
The 'forums' table holds all the comments in each forum. The structure of 'forums' is user_id INTEGER, comment TEXT NOT NULL, parent_id INTEGER, time DATETIME, forum_id TEXT NOT NULL, percentage TEXT, comment_id INTEGER (primary key, or identifier for comment). Each row in this table stores a different comment, with the corresponding user id of the user (from the users table) that wrote the comment, time the comment was written, and percentage of the book the user was through when they posted the comment (None if the user didn't put one). Note that the percentage is of a TEXT datatype to allow for it being "None" and otherwise, it will be rounded to the nearest integer percent. 

All replies to a comment will also have the same percentage tracked in our table. Then, each comment has a unique comment_id and replies to a parent comment are tracked through the parent_id column, which holds the comment_id for the comment the current comment is a reply to. The forum_id corresponds to that of the forum/book the comment is under/about. This table is essential for the functionality of our contributions and forum pages. 

### homeBooks table
The 'homeBooks' table stores the books on a user's home page. Its columns are forum_id TEXT NOT NULL, user_id INTEGER, and status TEXT. The forum_id is the tracker for the books, as stated before, and the user_id identifies the corresponding user. Then, the status can be "TBR", "PROG", or "DONE" for whether the user has the book on its TBR list, in progress list, or completed list. This table is then essential to the display of the home page. 


## Implementation
Our project involved a lot of passing data values back and forth between forms from our HTML pages and our python code, as well as storing data in our SQL tables. Several of our pages required data from our tables to render the appropriate books for our pages but when we added buttons/forms for each of these books, we wanted to preserve the book's information and be able to send it back through our forms. We did set this information to hidden in our forms but a major concern was whether the data our forms passed back could be corrupted by users (through page inspections and changing values). As a result, we ensured every time we attempted to add a new book to our database (as in the forum id was not in our table), we double checked this book exists in the Google Books API prior to adding it to our table so we would not have books that the user makes up in our database. This procedure was put in a separate method (checkVolumeID) where the argument was the volumeID (or forum_id, in our tables) and this essentially returns False if the volumeID doesn't exist in the API or if it does, it will insert the book's information into the chapters table and return the row of the chapters table corresponding to this newly inserted book. 

We also decided that for our project, we would not use the cs50 library. We later on realized that this meant we needed additional steps to run SQL commands in Python and so since throughout our project we repeatedly ran SQL commands, we created a separate method for running these, named executeSQL. The first argument for this method is the String that is the SQL command. The next one is a tuple of the ? arguments to prevent SQL injection attacks. Finally, the third argument is True/False depending on whether values in our SQL tables were changed (like when we INSERT/UPDATE) or not (like when we SELECT). 

### search.html
Our search function queries the Google Books API ([documentation here](https://developers.google.com/books/docs/v1/getting_started)). As the user types in the search box, we use JavaScript in search.html to clean up the query and pass it into the API call coded in "app.py" "@app.route("/api/search")". We run a query each time the user types in a character. But the search.html page won't display the search results until the text in the search box matches the query text so we can avoid race conditions. The way we call the API, we ensure that the book results contain the user's query as a substring. A "good murder" query won't pull up "A Good Girl's Guide to Murder"; our page will only display books with "good murder" within the title, such as "Harry Finds a Good Murder". We also only display the first 10 results to prevent cluttering of our page. 

### forum.html
Two ways to access the forum.html page are through the homepage when the user clicks on the 'Access Forum' icon or when they find a book via search.html. The book's volume ID is passed through as a hidden input and then we use the volume ID to call and display the rest of the book's information, including title, authors, and book cover. We chose to use the volume ID because each book has a unique volume ID in the Google Books API. In "app.py", we have conditionals to check if the user tried changing the volume ID through 'inspect'. We only add books to our chapters table after confirming that the book exists in the Google Books API through the volume ID passed in. 

The user can filter through the comments on the forums page to see comments up to the page number that the user has filtered for. We used Javacsript so the filter form submits when the user changes the value in the input box and hits 'enter'. 

### contributions.html
We decided to implement the 'delete' function by updating the comment text to '[deleted comment]' instead of deleting the comment from our database to ensure the integrity of our database and the comment_id increment. The user will still see their deleted comments in their contributions page, but their comment will no longer appear in the corresponding forum page.

### login.html and register.html
We decided that when a user attempts to register with a username that's already taken or logs in with the incorrect information or inputs blank/contradictory information to pass appropriate messages to these html files and set these messages to visible. We thought this would look smoother than sending the user to a separate error page. 

### home.html
We decided to implement a scrollbar feature on the tables displaying the books in a user's TBR, currently reading, and past reads lists in the case there were too many books on a given list to display on the user's screen. We also only display the tables if the lists are not empty and these tables contain values tracked in our homeBooks table, passed by the python code. 