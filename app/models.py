from datetime import datetime,timezone,timedelta
from app import db, login_manager
from flask_login import UserMixin
ist_timezone = timezone(timedelta(hours=5, minutes=30))  # Create IST timezone object


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
    title = db.Column(db.String(255), nullable=False)
    authors = db.Column(db.String(255), nullable=False)
    publisher = db.Column(db.String(255))
    year = db.Column(db.Integer)
    description=db.Column(db.Text)
    pageCount=db.Column(db.Integer)
    imageLink=db.Column(db.String(255))
    language=db.Column(db.String(10))
    categories = db.Column(db.String(255))
    quantity = db.Column(db.Integer, default=1,nullable=False)
    borrowed_copies = db.relationship('BorrowedBook', backref='book', lazy=True)

class BorrowedBook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    borrow_date = db.Column(db.DateTime, nullable=False, default=datetime.now(ist_timezone) )
    return_date = db.Column(db.DateTime)
    is_returned = db.Column(db.Boolean, default=False)


class CheckoutRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now(ist_timezone))
    status = db.Column(db.String(20), nullable=False, default='pending')

    user = db.relationship('User', backref='checkout_requests')
    book = db.relationship('Book', backref='checkout_requests')
class ReturnRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    borrowed_book_id = db.Column(db.Integer, db.ForeignKey('borrowed_book.id'), nullable=False) 
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.now(ist_timezone))
    status = db.Column(db.String(20), nullable=False, default='pending')
    
    # Relationship to BorrowedBook
    borrowed_book = db.relationship('BorrowedBook', backref='return_requests')
