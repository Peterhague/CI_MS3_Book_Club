import os
from flask import (
    Flask, flash, render_template, redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
if os.path.exists("env.py"):
    import env


app = Flask(__name__)

app.config["MONGO_DBNAME"] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo = PyMongo(app)

@app.route("/")
@app.route("/see_books")
def see_books():
    books = list(mongo.db.books.find())
    return render_template("books.html", books=books)


@app.route("/search", methods=["GET", "POST"])
def search():
    query = request.form.get("query")
    books = list(mongo.db.books.find({"$text": {"$search": query}}))
    return render_template("books.html", books=books)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
            flash("Username already exists")
            return redirect(url_for("register"))

        register = {
            "username": request.form.get("username").lower(),
            "password": generate_password_hash(request.form.get("password")),
            "first_name": request.form.get("first_name").lower(),
            "last_name": request.form.get("last_name").lower(),
            "location": request.form.get("location").lower(),
            "clubs_joined": []
        }
        mongo.db.users.insert_one(register)

        session["user"] = request.form.get("username").lower()
        flash("Registration successful")
        return redirect(url_for("profile", username=session["user"]))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # check if username exists in db
        existing_user = mongo.db.users.find_one(
            {"username": request.form.get("username").lower()})

        if existing_user:
        # ensure hashed password matches user input
            if check_password_hash(
                existing_user["password"], request.form.get("password")):
                    session["user"] = request.form.get("username").lower() 
                    flash("Welcome, {}".format(request.form.get("username")))                  
                    return redirect(url_for(
                        "profile", username=session["user"])) 
            else:
                # invalid password match
                flash("Incorrect Username and/or Password")
                return redirect(url_for("login"))

        else:
            # username doesn't exist
            flash("Incorrect Username and/or Password")
            return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/edit_details/<this_user_id>", methods=["GET", "POST"])
def edit_details(this_user_id):
    if request.method == "POST":
        edit_user = {
            "first_name": request.form.get("first_name"),
            "last_name": request.form.get("last_name"),
            "location": request.form.get("location"),
            "username": request.form.get("username")
        }
        mongo.db.users.update({"_id": ObjectId(this_user_id)}, edit_user)
        flash("Account Successfully Updated")

    return render_template("edit_details.html", this_user_id=this_user_id)


@app.route("/profile/<username>", methods=["GET", "POST"])
def profile(username):
    # grab the session user's username from the db
    this_user = mongo.db.users.find_one(
        {"username": session["user"]})
    books = list(mongo.db.books.find())

    if session["user"]:
        return render_template("profile.html", username=username, books=books, this_user=this_user)

    return redirect(url_for("login"))


@app.route("/profiles_other/<username>", methods=["GET", "POST"])
def profiles_other(username):
    books = list(mongo.db.books.find())
    this_user = mongo.db.users.find_one({"username": username})
    return render_template("profiles_other.html", username=username, books=books, this_user=this_user)


@app.route("/logout")
def logout():
    flash("You have been logged out")
    session.pop("user")
    return redirect(url_for("login"))


@app.route("/add_book", methods=["GET", "POST"])
def add_book():
    if request.method == "POST":
        clubs_joined = { "$addToSet": {"clubs_joined": request.form.get("book_title")}}  
        clubs_created = { "$addToSet": {"clubs_created": request.form.get("book_title")}}    
        user_id = mongo.db.users.find_one({"username": session["user"]})["_id"]
        book = {
            "genre_name": request.form.get("genre_name"),
            "book_title": request.form.get("book_title"),
            "author_first": request.form.get("author_first"),            
            "author_last": request.form.get("author_last"),
            "date": request.form.get("date"),
            "book_description": request.form.get("book_description"),
            "start_date": request.form.get("start_date"),
            "created_by": session["user"],
            "members": [session["user"]]
        }
        mongo.db.books.insert_one(book)
        mongo.db.users.update({"_id": ObjectId(user_id)}, clubs_created)
        mongo.db.users.update({"_id": ObjectId(user_id)}, clubs_joined)
        flash("Book Successfully Added")
        return redirect(url_for("see_books")) 

    genres = mongo.db.genres.find().sort("genre_name", 1)
    return render_template("add_book.html", genres=genres)


@app.route("/edit_book/<book_id>", methods=["GET", "POST"])
def edit_book(book_id):
    if request.method == "POST":
        submit = {
            "genre_name": request.form.get("genre_name"),
            "book_title": request.form.get("book_title"),
            "author_first": request.form.get("author_first"),
            "author_last": request.form.get("author_last"),
            "date": request.form.get("date"),
            "book_description": request.form.get("book_description"),
            "start_date": request.form.get("start_date"),
            "created_by": session["user"]
        }
        mongo.db.books.update({"_id": ObjectId(book_id)}, submit)
        flash("Book Successfully Updated")

    book = mongo.db.books.find_one({"_id": ObjectId(book_id)})
    genres = mongo.db.genres.find().sort("genre_name", 1)
    return render_template("edit_book.html", book=book, genres=genres)


@app.route("/delete_book/<book_id>")
def delete_book(book_id):
    mongo.db.books.remove({"_id": ObjectId(book_id)})
    flash("Book Deleted")
    return redirect(url_for("see_books"))


@app.route("/join_club/<book_id>", methods=["GET", "POST"])
def join_club(book_id):
    member = { "$addToSet": {"members": session["user"]}}
    book = mongo.db.books.find_one({"_id": ObjectId(book_id)})
    club = { "$addToSet": {"clubs_joined": book["book_title"]}}    
    user_id = mongo.db.users.find_one({"username": session["user"]})["_id"]
    mongo.db.books.update({"_id": ObjectId(book_id)}, member)
    mongo.db.users.update({"_id": ObjectId(user_id)}, club)
    flash("You have joined this book club")

    book = mongo.db.books.find_one({"_id": ObjectId(book_id)})
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    genres = mongo.db.genres.find().sort("genre_name", 1)
    return redirect(url_for("see_books"))


@app.route("/leave_club/<book_id>", methods=["GET", "POST"])
def leave_club(book_id):
    remove_member = { "$pull": {"members": session["user"]}}
    book = mongo.db.books.find_one({"_id": ObjectId(book_id)})
    remove_club = { "$pull": {"clubs_joined": book["book_title"]}}    
    user_id = mongo.db.users.find_one({"username": session["user"]})["_id"]
    mongo.db.books.update({"_id": ObjectId(book_id)}, remove_member)
    mongo.db.users.update({"_id": ObjectId(user_id)}, remove_club)
    flash("You have left this book club")

    book = mongo.db.books.find_one({"_id": ObjectId(book_id)})
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    genres = mongo.db.genres.find().sort("genre_name", 1)
    return redirect(url_for("see_books"))


@app.route("/go_to_club/<book_id>", methods=["GET", "POST"])
def go_to_club(book_id):
    book = mongo.db.books.find_one({"_id": ObjectId(book_id)})
    return render_template("club_home.html", book_id=book_id, book=book)


@app.route("/add_comment/<book_id>", methods=["GET", "POST"])
def add_comment(book_id):
    if request.method == "POST":
        book = mongo.db.books.find_one({"_id": ObjectId(book_id)})
        comment = { "$push": {"comments": request.form.get("comment")}}
        comments_by = { "$push": {"comments_by" : session["user"]}}
        commented_on = { "$push": {"commented_on" : book["book_title"]}}
        user_id = mongo.db.users.find_one({"username": session["user"]})["_id"]
        mongo.db.books.update({"_id": ObjectId(book_id)}, comment)
        mongo.db.books.update({"_id": ObjectId(book_id)}, comments_by)
        mongo.db.users.update({"_id": ObjectId(user_id)}, comment)
        mongo.db.users.update({"_id": ObjectId(user_id)}, commented_on)
    
    book = mongo.db.books.find_one({"_id": ObjectId(book_id)})
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    return render_template("club_home.html", book_id=book_id, book=book)


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
            port=int(os.environ.get("PORT")),
            debug=True)
