from app import scheduler, db
from app.models import BorrowedBook
from app.utils import send_email
from datetime import datetime, timedelta

@scheduler.task('cron', id='send_due_reminders', hour=9)
def send_due_reminders():
    tomorrow = datetime.utcnow().date() + timedelta(days=1)
    due_borrows = BorrowedBook.query.filter(
        BorrowedBook.borrow_date <= tomorrow - timedelta(days=13),
        BorrowedBook.is_returned == False
    ).all()

    for borrow in due_borrows:
        subject = "Book Due Reminder"
        body = f"Dear {borrow.borrower.username},\n\nThis is a reminder that the book '{borrow.book.title}' is due tomorrow. Please return it to the library as soon as possible.\n\nBest regards,\nLibrary Management System"
        send_email(subject, borrow.borrower.email, body)

    print(f"Sent {len(due_borrows)} due reminders.")