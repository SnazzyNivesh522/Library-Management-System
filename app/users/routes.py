from flask import Blueprint, render_template, url_for, flash, redirect, request
from flask_login import login_required, current_user
from app import db
from app.models import User, BorrowedBook
from app.users.forms import UpdateAccountForm
from app.utils import save_picture

users = Blueprint('users', __name__)

@users.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('users.account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file) if current_user.image_file else None
    has_profile_picture = bool(current_user.image_file)  # New line: Determine if user has picture
    return render_template('users/account.html', title='Account',
                           image_file=image_file, form=form, has_profile_picture=has_profile_picture)  # Pass the flag to the template

@users.route("/user/<string:username>")
def user_books(username):
    user = User.query.filter_by(username=username).first_or_404()
    borrowed_books = BorrowedBook.query.filter_by(user_id=user.id).order_by(BorrowedBook.borrow_date.desc()).all()
    return render_template('users/user_books.html', user=user, borrowed_books=borrowed_books)