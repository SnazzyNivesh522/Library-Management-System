from flask import Blueprint, render_template
from app.models import Book

main = Blueprint('main', __name__)

@main.route("/")
@main.route("/home")
def home():
    recent_books = Book.query.order_by(Book.id.desc()).limit(5).all()
    return render_template('home.html', title='Home', recent_books=recent_books)

@main.route("/about")
def about():
    return render_template('about.html', title='About')