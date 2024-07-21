from flask import Blueprint, render_template, url_for, flash, redirect, request
from flask_login import login_required, current_user
from app import db
from app.models import Book, BorrowedBook,User
from app.utils import send_email
import requests
from collections import Counter
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from app.books.forms import BookSearchForm, BookCheckoutForm, BookForm
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
    return render_template('books/book_detail.html', title=book.title, book=book, borrowed_by_current_user=borrowed_by_current_user)

@books.route("/book/<int:book_id>/checkout", methods=['GET', 'POST'])
@login_required
def checkout_book(book_id):
    book = Book.query.get_or_404(book_id)
    form = BookCheckoutForm()
    if form.validate_on_submit():
        if book.quantity > 0:
            borrowed_book = BorrowedBook(user_id=current_user.id, book_id=book.id)
            book.quantity -= 1
            db.session.add(borrowed_book)
            db.session.commit()
            flash('Book checked out successfully!', 'success')
            
            # Send email notification
            subject = f"Book Checkout: {book.title}"
            body = f"Dear {current_user.username},\n\nYou have successfully checked out '{book.title}' by {book.author}. Please return it within 14 days.\n\nBest regards,\nLibrary Management System"
            send_email(subject, current_user.email, body)
            
            return redirect(url_for('books.book_detail', book_id=book.id))
        else:
            flash('This book is currently unavailable.', 'danger')
    return render_template('books/checkout.html', title='Checkout Book', form=form, book=book)

@books.route("/book/<int:book_id>/return")
@login_required
def return_book(book_id):
    borrowed_book = BorrowedBook.query.filter_by(user_id=current_user.id, book_id=book_id, is_returned=False).first()
    if borrowed_book:
        borrowed_book.is_returned = True
        borrowed_book.return_date = datetime.utcnow()
        borrowed_book.book.quantity += 1
        db.session.commit()
        flash('Book returned successfully!', 'success')
    else:
        flash('You have not borrowed this book.', 'danger')
    return redirect(url_for('books.book_detail', book_id=book_id))

@books.route("/add_book", methods=['GET', 'POST'])
@login_required
def add_book():
    if current_user.role not in ['admin', 'librarian']:
        flash('You do not have permission to add books.', 'danger')
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        isbn = request.form.get('isbn')
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
                    quantity=1
                )
                db.session.add(new_book)
                db.session.commit()
                flash('Book added successfully!', 'success')
                return redirect(url_for('books.book_detail', book_id=new_book.id))
            else:
                flash('Book not found with the given ISBN.', 'danger')
        else:
            flash('Error fetching book data. Please try again.', 'danger')

    return render_template('books/add_book.html', title='Add Book')

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
