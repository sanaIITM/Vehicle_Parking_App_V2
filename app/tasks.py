from datetime import datetime, timedelta, date
from io import StringIO
import csv

from flask import render_template
from flask_mail import Message

from .celery_app import celery
from .models import db, User, ParkingLot, Reservation
from . import mail

#check for optimization
#task receive bug to be fixed
@celery.task
def send_daily_reminders():
    """
    Daily reminder:
    - If there is at least one parking lot
    - For every user (role='user') who has never parked or last parked > 7 days ago
    - Send a simple reminder email.
    Assumes username is the email address.
    """
    if ParkingLot.query.first() is None:
        return "No parking lots; skipping reminders."

    cutoff = datetime.utcnow() - timedelta(days=7)

    users = User.query.filter_by(role='user').all()
    for u in users:
        last_res = (
            Reservation.query
            .filter_by(user_id=u.id)
            .order_by(Reservation.start_time.desc())
            .first()
        )
        if last_res is None or (last_res.start_time and last_res.start_time < cutoff):
            if not u.username:
                continue
            msg = Message(
                subject="Parking Reminder",
                recipients=[u.username],  # username as email
                body=(
                    f"Hi {u.username},\n\n"
                    "We have parking lots available. "
                    "Book a parking spot if you need one today.\n\n"
                    "- Vehicle Parking App"
                ),
            )
            mail.send(msg)

    return "Daily reminders sent."


@celery.task
def send_monthly_reports():
    """
    Monthly HTML activity report:
    - For each user (role='user')
    - Collect previous month's reservations
    - Compute total spent, lot usage
    - Send HTML email using email_monthly_report.html
    """
    today = date.today()
    first_this_month = today.replace(day=1)
    last_month_end = first_this_month - timedelta(days=1)
    first_last_month = last_month_end.replace(day=1)

    start_dt = datetime.combine(first_last_month, datetime.min.time())
    end_dt = datetime.combine(last_month_end, datetime.max.time())
    month_label = first_last_month.strftime('%B %Y')

    users = User.query.filter_by(role='user').all()
    for u in users:
        reservations = (
            Reservation.query
            .filter(
                Reservation.user_id == u.id,
                Reservation.start_time >= start_dt,
                Reservation.start_time <= end_dt,
            )
            .order_by(Reservation.start_time.asc())
            .all()
        )
        if not reservations:
            continue

        total_spent = sum((r.cost or 0.0) for r in reservations)

        lot_counts = {}
        for r in reservations:
            lot_name = r.spot.lot.name if r.spot and r.spot.lot else "Unknown"
            lot_counts[lot_name] = lot_counts.get(lot_name, 0) + 1

        most_used_lot = max(lot_counts, key=lot_counts.get) if lot_counts else None

        html = render_template(
            'email_monthly_report.html',
            user=u,
            reservations=reservations,
            total_spent=total_spent,
            lot_counts=lot_counts,
            most_used_lot=most_used_lot,
            month_label=month_label,
        )

        if not u.username:
            continue
        msg = Message(
            subject=f"Your Parking Activity - {month_label}",
            recipients=[u.username],
        )
        msg.html = html
        mail.send(msg)

    return "Monthly reports sent."


@celery.task
def generate_csv_for_user(user_id):
    """
    Async CSV export:
    - All reservations for a user
    - Email as CSV attachment
    """
    user = User.query.get(user_id)
    if not user:
        return "User not found."

    reservations = (
        Reservation.query
        .filter_by(user_id=user.id)
        .order_by(Reservation.start_time.asc())
        .all()
    )

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Reservation ID', 'Lot', 'Spot ID', 'Start Time', 'End Time', 'Cost'])

    for r in reservations:
        lot_name = r.spot.lot.name if r.spot and r.spot.lot else "Unknown"
        writer.writerow([
            r.id,
            lot_name,
            r.spot_id,
            r.start_time.strftime('%Y-%m-%d %H:%M') if r.start_time else '',
            r.end_time.strftime('%Y-%m-%d %H:%M') if r.end_time else '',
            f"{r.cost:.2f}" if r.cost is not None else '',
        ])

    csv_data = output.getvalue()

    if not user.username:
        return "User has no email/username."

    msg = Message(
        subject="Your Parking History (CSV Export)",
        recipients=[user.username],
        body=(
            f"Hi {user.username},\n\n"
            "Attached is your parking history in CSV format.\n\n"
            "- Vehicle Parking App"
        ),
    )
    msg.attach('parking_history.csv', 'text/csv', csv_data)
    mail.send(msg)

    return f"CSV export sent to {user.username}."
