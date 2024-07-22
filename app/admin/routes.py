from flask import Blueprint, render_template, redirect, url_for, flash, request,abort
from flask_login import login_required, current_user
from app import db
from app.models import User, Book, BorrowedBook,CheckoutRequest,ReturnRequest
from app.utils import admin_required, librarian_required
from sqlalchemy import func
from datetime import datetime, timedelta
from app.admin.forms import BookForm,ApproveRequestForm

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
    return render_template('admin/manage_borrowed.html', title='Manage Borrowed Books', borrowed_books=borrowed_books,timedelta=timedelta)

@admin.route("/admin/reports")
@login_required
@admin_required
def reports():
    # Generate various reports here
    return render_template('admin/reports.html', title='Reports')
@admin.route("/admin/requests/<request_type>")  
@login_required
@librarian_required
def manage_requests(request_type):
    if request_type == 'checkout':
        requests = CheckoutRequest.query.options(
            db.joinedload(CheckoutRequest.user),
            db.joinedload(CheckoutRequest.book)  # Eager load Book as well
        ).filter_by(status='pending').all()
    elif request_type == 'return':
        requests = (
            ReturnRequest.query
            .join(BorrowedBook)
            .join(User)
            .filter(ReturnRequest.status == "pending")
            .all()
        )
    else:
        abort(404)
    form = ApproveRequestForm()
    return render_template('admin/pending_requests.html', requests=requests, form=form, request_type=request_type)



@admin.route('/requests/<request_type>/<int:request_id>/<action>', methods=['POST'])
@login_required
@librarian_required  
def approve_request(request_type, request_id, action):
    if request_type == 'checkout':
        request_to_update = CheckoutRequest.query.get_or_404(request_id)
        book = Book.query.get_or_404(request_to_update.book_id)
        if action == 'approve':
            if book.quantity > 0:
                book.quantity -= 1
                borrowed_book = BorrowedBook(user_id=request_to_update.user_id, book_id=request_to_update.book_id)
                db.session.add(borrowed_book)
            else:
                flash(f'Cannot approve checkout for {book.title}. Book is out of stock.', 'danger')
                return redirect(url_for('admin.manage_requests', request_type=request_type))
        elif action == 'reject':
            # No specific action needed for rejection in this case
            pass
        else:
            abort(400)  # Bad request
    elif request_type == 'return':
        request_to_update = ReturnRequest.query.get_or_404(request_id)
        # Update BorrowedBook and increment book quantity only if approved
        if action == 'approve':
            borrowed_book = request_to_update.borrowed_book
            borrowed_book.is_returned = True
            borrowed_book.return_date = datetime.utcnow()
            borrowed_book.book.quantity += 1
    else:
        abort(404)  # Invalid request type
    
    request_to_update.status = action
    db.session.commit()
    flash(f'{request_type.capitalize()} request {action}d!', 'success')
    return redirect(url_for('admin.manage_requests', request_type=request_type))


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
