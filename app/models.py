from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    image_file = db.Column(db.String(200), nullable=True)
    borrowed_books = db.relationship('BorrowedBook', backref='borrower', lazy=True)


class Book(db.Model):
    __tablename__ = 'book'
    id = db.Column(db.Integer, primary_key=True)
    isbn = db.Column(db.String(13), unique=True, nullable=False)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    publisher = db.Column(db.String(100))
    year = db.Column(db.Integer)
    genre = db.Column(db.String(50))
    quantity = db.Column(db.Integer, default=1,nullable=False)
    borrowed_copies = db.relationship('BorrowedBook', backref='book', lazy=True)

class BorrowedBook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    borrow_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    return_date = db.Column(db.DateTime)
    is_returned = db.Column(db.Boolean, default=False)