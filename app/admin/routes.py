from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import User, Book, BorrowedBook
from app.utils import admin_required, librarian_required
from sqlalchemy import func
from datetime import datetime, timedelta
from app.admin.forms import BookForm

admin = Blueprint('admin', __name__)

@admin.route("/admin/dashboard")
@login_required
@librarian_required
def admin_dashboard():
    total_users = User.query.count()
    total_books = Book.query.count()
    total_borrowed = BorrowedBook.query.filter_by(is_returned=False).count()
    
    # Books borrowed in the last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_borrows = BorrowedBook.query.filter(BorrowedBook.borrow_date >= thirty_days_ago).count()
    
    # Most borrowed books
    most_borrowed = db.session.query(
        Book.title, func.count(BorrowedBook.id).label('borrow_count')
    ).join(BorrowedBook).group_by(Book.id).order_by(func.count(BorrowedBook.id).desc()).limit(5).all()
    
    # Users with most borrows
    top_users = db.session.query(
        User.username, func.count(BorrowedBook.id).label('borrow_count')
    ).join(BorrowedBook).group_by(User.id).order_by(func.count(BorrowedBook.id).desc()).limit(5).all()
    
    return render_template('admin/dashboard.html', title='Admin Dashboard',
                           total_users=total_users, total_books=total_books,
                           total_borrowed=total_borrowed, recent_borrows=recent_borrows,
                           most_borrowed=most_borrowed, top_users=top_users)

@admin.route("/admin/users")
@login_required
@admin_required
def manage_users():
    users = User.query.all()
    return render_template('admin/manage_users.html', title='Manage Users', users=users)

@admin.route("/admin/books")
@login_required
@librarian_required
def manage_books():
    books = Book.query.all()
    return render_template('admin/manage_books.html', title='Manage Books', books=books)

@admin.route("/admin/borrowed")
@login_required
@librarian_required
def manage_borrowed():
    borrowed_books = BorrowedBook.query.filter_by(is_returned=False).all()
    return render_template('admin/manage_borrowed.html', title='Manage Borrowed Books', borrowed_books=borrowed_books)

@admin.route("/admin/reports")
@login_required
@admin_required
def reports():
    # Generate various reports here
    return render_template('admin/reports.html', title='Reports')

@admin.route("/admin/book/new", methods=['GET', 'POST'])
@login_required
@librarian_required
def new_book():
    form = BookForm()
    if form.validate_on_submit():
        book = Book(
            isbn=form.isbn.data,
            title=form.title.data,
            author=form.author.data,
            publisher=form.publisher.data,
            year=form.year.data,
            genre=form.genre.data,
            quantity=form.quantity.data
        )
        db.session.add(book)
        db.session.commit()
        flash('Book has been added!', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    return render_template('admin/create_book.html', form=form)

@admin.route("/admin/book/<int:book_id>/update", methods=['GET', 'POST'])
@login_required
@librarian_required
def update_book(book_id):
    book = Book.query.get_or_404(book_id)
    form = BookForm()
    if form.validate_on_submit():
        book.isbn = form.isbn.data
        book.title = form.title.data
        book.author = form.author.data
        book.publisher = form.publisher.data
        book.year = form.year.data
        book.genre = form.genre.data
        book.quantity = form.quantity.data
        db.session.commit()
        flash('Book has been updated!', 'success')
        return redirect(url_for('admin.admin_dashboard'))
    elif request.method == 'GET':
        form.isbn.data = book.isbn
        form.title.data = book.title
        form.author.data = book.author
        form.publisher.data = book.publisher
        form.year.data = book.year
        form.genre.data = book.genre
        form.quantity.data = book.quantity
    return render_template('admin/update_book.html', form=form, book=book)

@admin.route("/admin/book/<int:book_id>/delete", methods=['POST'])
@login_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    db.session.delete(book)
    db.session.commit()
    flash('Book has been deleted!', 'success')
    return redirect(url_for('admin.admin_dashboard'))