import os
import secrets
from functools import wraps
from flask import abort
from flask_login import current_user
from flask import current_app
from flask_mail import Message
import requests
from app import mail

from PIL import Image

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def librarian_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'librarian']:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
def send_email(subject, recipient, body):
    msg = Message(subject,
                  sender=current_app.config['MAIL_USERNAME'],
                  recipients=[recipient],body=body)
    msg.body = body
    mail.send(msg)


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(current_app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn

def fetch_book_details_from_api(isbn):
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if 'items' in data and len(data['items']) > 0:
            volume_info = data['items'][0]['volumeInfo']
            # for key,value in volume_info.items():
            #     print(f"{key}: {value}")
            # print()
            return {
                'isbn': isbn,
                'title': volume_info.get('title', 'Unknown'),
                'authors': ', '.join(volume_info.get('authors', ['Unknown'])),
                'publisher': volume_info.get('publisher', 'Unknown'),
                'year': volume_info.get('publishedDate', 'Unknown')[:4],
                'categories': ', '.join(volume_info.get('categories', ['Unknown'])),
                'description': volume_info.get('description', ''),
                'image_link': volume_info.get('imageLinks', {}).get('thumbnail', ''),
                'pageCount':volume_info.get('pageCount'),
                'language': volume_info.get('language')
            }
    return None