from flask import Blueprint, render_template, url_for, flash, redirect, request,abort
from flask_login import login_required, current_user
from app import db
from app.models import Book, BorrowedBook,User,CheckoutRequest,ReturnRequest
from app.utils import send_email
import requests
from collections import Counter
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from app.books.forms import BookSearchForm, BookCheckoutForm, BookForm,BookReturnForm,ISBNSearchForm
from app.utils import fetch_book_details_from_api
from app.utils import send_email, admin_required, librarian_required
from datetime import datetime, timedelta

books = Blueprint('books', __name__)

@books.route("/search", methods=['GET', 'POST'])
def search():
    form = BookSearchForm()
    if form.validate_on_submit():
        query = form.query.data
        books = Book.query.filter(
            (Book.title.like(f'%{query}%')) |
            (Book.author.like(f'%{query}%')) |
            (Book.isbn.like(f'%{query}%'))
        ).all()
        return render_template('books/search_results.html', books=books, query=query)
    return render_template('books/search.html', title='Search Books', form=form)

@books.route("/book/<int:book_id>")
def book_detail(book_id):
    book = Book.query.get_or_404(book_id)
    borrowed_by_current_user = BorrowedBook.query.filter_by(book_id=book_id, user_id=current_user.id, is_returned=False).first()
    checkout_form = BookCheckoutForm()
    return_form = BookReturnForm()  # Make sure this is defined
    return render_template(
        "books/book_detail.html",
        title=book.title,
        book=book,
        borrowed_by_current_user=borrowed_by_current_user,
        checkout_form=checkout_form,
        return_form=return_form,
    )

@books.route("/book/<int:book_id>/checkout", methods=['POST'])
@login_required
def checkout_book(book_id):
    book = Book.query.get_or_404(book_id)

    # Check if the user already has an outstanding checkout request for this book
    existing_request = CheckoutRequest.query.filter_by(
        user_id=current_user.id, book_id=book_id, status='pending'
    ).first()
    if existing_request:
        flash('You already have a pending checkout request for this book.', 'warning')
        return redirect(url_for('books.book_detail', book_id=book.id))

    # Create a new checkout request
    checkout_request = CheckoutRequest(user_id=current_user.id, book_id=book.id)
    db.session.add(checkout_request)
    db.session.commit()
    flash('Checkout request submitted. Please wait for librarian approval.', 'info')
    return redirect(url_for('books.book_detail', book_id=book.id))


@books.route("/book/<int:book_id>/return", methods=['POST'])
@login_required
def return_book(book_id):
    # Check if the user has borrowed the book and hasn't already requested a return
    borrowed_book = BorrowedBook.query.filter_by(
        user_id=current_user.id, book_id=book_id, is_returned=False
    ).first()

    if not borrowed_book:
        flash('You have not borrowed this book or already returned it.', 'danger')
        return redirect(url_for('books.book_detail', book_id=book_id))

    existing_request = ReturnRequest.query.filter_by(
        borrowed_book_id=borrowed_book.id, status='pending'
    ).first()
    if existing_request:
        flash('You already have a pending return request for this book.', 'warning')
        return redirect(url_for('books.book_detail', book_id=borrowed_book.book_id))
    
    # Create a new return request
    return_request = ReturnRequest(borrowed_book_id=borrowed_book.id)
    db.session.add(return_request)
    db.session.commit()

    flash('Return request submitted. Please wait for librarian approval.', 'info')
    return redirect(url_for('books.book_detail', book_id=book_id))


@books.route("/add_book", methods=['GET', 'POST'])
@login_required
@librarian_required
def add_book():
    isbn_form = ISBNSearchForm()
    book_form = BookForm()
    
    if isbn_form.validate_on_submit():
        isbn = isbn_form.isbn.data
        book_details = fetch_book_details_from_api(isbn)
        if book_details:
            book_form = BookForm(data=book_details)
            return render_template('books/confirm_book.html', form=book_form, book_details=book_details)
        else:
            flash('Book not found with the given ISBN.', 'danger')
    
    if book_form.validate_on_submit():
        new_book = Book(
            isbn=book_form.isbn.data,
            title=book_form.title.data,
            author=book_form.author.data,
            publisher=book_form.publisher.data,
            year=book_form.year.data,
            categoriesgenre=book_form.categories.data,
            quantity=book_form.quantity.data
        )
        db.session.add(new_book)
        db.session.commit()
        flash('Book added successfully!', 'success')
        return redirect(url_for('books.book_detail', book_id=new_book.id))
    
    return render_template('books/add_book.html', isbn_form=isbn_form, book_form=book_form)


@books.route("/confirm_book", methods=['POST'])
@login_required
@librarian_required
def confirm_book():
    form = BookForm()
    if form.validate_on_submit():
        new_book = Book(
            isbn=form.isbn.data,
            title=form.title.data,
            author=form.author.data,
            publisher=form.publisher.data,
            year=form.year.data,
            categories=form.categories.data,
            quantity=form.quantity.data
        )
        db.session.add(new_book)
        db.session.commit()
        flash('Book added successfully!', 'success')
        return redirect(url_for('books.book_detail', book_id=new_book.id))
    return render_template('books/edit_book.html', form=form)
@books.route("/recommendations")
@login_required
def recommendations():
    user_borrows = BorrowedBook.query.filter_by(user_id=current_user.id).all()
    borrowed_book_ids = [borrow.book_id for borrow in user_borrows]
    
    # Genre-based recommendations
    borrowed_genres = db.session.query(Book.genre).filter(Book.id.in_(borrowed_book_ids)).distinct().all()
    genres = [genre for (genre,) in borrowed_genres]
    genre_recommendations = Book.query.filter(Book.genre.in_(genres), ~Book.id.in_(borrowed_book_ids)).limit(5).all()
    
    # Collaborative filtering recommendations
    all_users = User.query.all()
    all_books = Book.query.all()
    
    # Create a user-item matrix
    user_item_matrix = np.zeros((len(all_users), len(all_books)))
    for user in all_users:
        user_borrows = BorrowedBook.query.filter_by(user_id=user.id).all()
        for borrow in user_borrows:
            user_item_matrix[user.id - 1][borrow.book_id - 1] = 1
    
    # Calculate user similarity
    user_similarity = cosine_similarity(user_item_matrix)
    
    # Find similar users
    similar_users = user_similarity[current_user.id - 1].argsort()[::-1][1:6]  # Top 5 similar users
    
    # Get book recommendations from similar users
    collaborative_recommendations = []
    for user_id in similar_users:
        user_borrows = BorrowedBook.query.filter_by(user_id=user_id + 1).all()
        collaborative_recommendations.extend([borrow.book for borrow in user_borrows if borrow.book_id not in borrowed_book_ids])
    
    # Combine and rank recommendations
    all_recommendations = genre_recommendations + collaborative_recommendations
    recommendation_counts = Counter(all_recommendations)
    final_recommendations = [book for book, _ in recommendation_counts.most_common(5)]
    
    return render_template('books/recommendations.html', title='Book Recommendations', recommended_books=final_recommendations)



# ... (previous routes: search, book_detail, checkout_book, return_book) ...

@books.route("/book/new", methods=['GET', 'POST'])
@login_required
@librarian_required
def new_book():
    form = BookForm()
    if form.validate_on_submit():
        isbn = form.isbn.data
        response = requests.get(f'https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}')
        if response.status_code == 200:
            book_data = response.json()
            if 'items' in book_data and len(book_data['items']) > 0:
                volume_info = book_data['items'][0]['volumeInfo']
                new_book = Book(
                    isbn=isbn,
                    title=volume_info.get('title', 'Unknown'),
                    author=', '.join(volume_info.get('authors', ['Unknown'])),
                    publisher=volume_info.get('publisher', 'Unknown'),
                    year=volume_info.get('publishedDate', 'Unknown')[:4],
                    genre=', '.join(volume_info.get('categories', ['Unknown'])),
                    quantity=form.quantity.data  # Use quantity from the form
                )
                db.session.add(new_book)
                db.session.commit()
                flash('Book added successfully!', 'success')
                return redirect(url_for('books.book_detail', book_id=new_book.id))
            else:
                flash('Book not found with the given ISBN.', 'danger')
        else:
            flash('Error fetching book data. Please try again.', 'danger')
    return render_template('books/new_book.html', title='New Book', form=form, legend='New Book')

@books.route("/book/<int:book_id>/update", methods=['GET', 'POST'])
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
        flash('Your book has been updated!', 'success')
        return redirect(url_for('books.book_detail', book_id=book.id))
    elif request.method == 'GET':
        form.isbn.data = book.isbn
        form.title.data = book.title
        form.author.data = book.author
        form.publisher.data = book.publisher
        form.year.data = book.year
        form.genre.data = book.genre
        form.quantity.data = book.quantity
    return render_template('books/new_book.html', title='Update Book',
                           form=form, legend='Update Book')

@books.route("/book/<int:book_id>/delete", methods=['POST'])
@login_required
@librarian_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    db.session.delete(book)
    db.session.commit()
    flash('Your book has been deleted!', 'success')
    return redirect(url_for('books.search'))

@books.route("/book/<int:book_id>/return_by_librarian", methods=['POST'])
@login_required
@librarian_required
def return_book_by_librarian(book_id):
    borrowed_book = BorrowedBook.query.filter_by(book_id=book_id, is_returned=False).first()
    if borrowed_book:
        borrowed_book.is_returned = True
        borrowed_book.return_date = datetime.utcnow()
        borrowed_book.book.quantity += 1
        db.session.commit()
        flash('Book returned successfully!', 'success')
    else:
        flash('This book is not currently borrowed.', 'danger')
    return redirect(url_for('admin.manage_borrowed'))  # Redirect back to manage borrowed page
# ... (rest of the routes: recommendations) ...
