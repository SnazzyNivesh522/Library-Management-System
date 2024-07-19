from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange

class BookForm(FlaskForm):
    isbn = StringField('ISBN', validators=[DataRequired(), Length(min=10, max=13)])
    title = StringField('Title', validators=[DataRequired(), Length(max=100)])
    author = StringField('Author', validators=[DataRequired(), Length(max=100)])
    publisher = StringField('Publisher', validators=[Length(max=100)])
    year = IntegerField('Year', validators=[NumberRange(min=1000, max=9999)])
    genre = StringField('Genre', validators=[Length(max=50)])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Submit')
