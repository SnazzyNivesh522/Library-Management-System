from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Length, ValidationError
from app.models import Book

class BookSearchForm(FlaskForm):
    query = StringField('Search', validators=[DataRequired()])
    submit = SubmitField('Search')

class BookCheckoutForm(FlaskForm):
    submit = SubmitField('Checkout')
class BookReturnForm(FlaskForm):
    submit = SubmitField('Request Return')

class BookForm(FlaskForm):
    isbn = StringField('ISBN', validators=[DataRequired(), Length(min=10, max=13)])
    title = StringField('Title', validators=[DataRequired()])
    author = StringField('Author', validators=[DataRequired()])
    publisher = StringField('Publisher')
    year = IntegerField('Year')
    genre = StringField('Genre')
    quantity = IntegerField('Quantity', validators=[DataRequired()])
    submit = SubmitField('Submit')

    def validate_isbn(self, isbn):
        existing_book = Book.query.filter_by(isbn=isbn.data).first()
        if existing_book:
            raise ValidationError('A book with this ISBN already exists.')
class ISBNSearchForm(FlaskForm):
    isbn = StringField('ISBN', validators=[DataRequired(), Length(min=10, max=13)])
    submit = SubmitField('Search')
        

