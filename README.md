# 🚗 Vehicle Parking App – V2

**Modern Application Development II Project**

---

## 📘 Overview

**Vehicle Parking App – V2** is a multi-user web application designed to manage **4-wheeler parking lots and parking spot reservations**.

The application supports **two roles: Admin and User**, provides real-time parking spot allocation, and implements **asynchronous background jobs and scheduled tasks** using **Redis and Celery**, as required for the MAD-II syllabus.

The system uses **Flask for APIs**, **VueJS for UI**, **SQLite for persistence**, and **Bootstrap for styling**.

---

## 🧱 Tech Stack

* **Backend**: Flask (Python)
* **Frontend**: VueJS (via CDN), HTML, CSS
* **Styling**: Bootstrap
* **Templating**: Jinja2 (entry point only)
* **Database**: SQLite (created programmatically)
* **Caching**: Redis
* **Async & Scheduled Jobs**: Celery + Redis
* **Charts**: Chart.js

---

## 👥 User Roles

### 🛠 Admin (Superuser)

* Automatically created when the database is initialized
* No registration required
* Only **one admin** exists in the system

**Admin Capabilities:**

* Create, edit, and delete parking lots
* Define number of parking spots per parking lot (spots auto-generated)
* Set price per hour for each parking lot
* Delete parking lots only if all spots are free
* View occupancy status of parking spots
* View all registered users
* View revenue and usage summaries via dashboard charts

---

### 👤 User

* Register and login
* View available parking lots
* Book a parking spot (automatically allocated)
* Release / vacate a parking spot
* View personal parking history and cost summary

---

## 🧹 Core Entities & Relationships

### User

* `id`
* `username`
* `password`
* `role` (admin / user)

### ParkingLot

* `id`
* `name`
* `address`
* `pincode`
* `price_per_hour`
* `max_spots`

### ParkingSpot

* `id`
* `lot_id` (Foreign Key)
* `status` (`A` = Available, `O` = Occupied)

### Reservation

* `id`
* `spot_id` (Foreign Key)
* `user_id` (Foreign Key)
* `start_time`
* `end_time`
* `cost`

> The database is created programmatically using SQLAlchemy. Manual database creation is not used.

---

## 🌟 Core Functionalities

### 🔐 Authentication & RBAC

* Role-based login system
* Separate dashboards for Admin and Users

---

### 📊 Admin Dashboard

* View total users, parking lots, and revenue
* Create, edit, and delete parking lots
* Automatic generation of parking spots
* View parking spot occupancy
* View registered users
* Visual summary charts for revenue and occupancy

---

### 📌 User Dashboard

* View parking lots with available spots
* Book the first available parking spot
* Release parking spots when leaving
* Time-based parking cost calculation
* Reservation history and usage summary

---

## 🔄 Background Jobs (Redis + Celery)

### ✅ Daily Reminder (Scheduled Job)

* Runs once daily
* Identifies inactive users or newly created parking lots
* Sends reminder notifications via email or messaging service

### ✅ Monthly Activity Report (Scheduled Job)

* Runs on the **first day of every month**
* Generates an HTML report containing:

  * Total reservations
  * Total amount spent
  * Most used parking lot
  * Reservation details
* Sends the report to users via email

### ✅ Export as CSV (User-Triggered Async Job)

* User can trigger export from dashboard
* Celery job generates reservation CSV
* Notification is sent once export is completed

---

## ⚡ Performance & Caching

* Redis caching used for dashboard data
* Cache expiry enabled
* Async processing ensures non-blocking APIs

---

## 📁 Project Structure

```
Vehicle_Parking_App_V2/
├── app/
│   ├── __init__.py
│   ├── models.py
│   ├── routes.py
│   ├── tasks.py
│   └── celery_app.py
├── templates/
│   ├── index.html
│   └── email_monthly_report.html
├── instance/
│   └── (SQLite DB created at runtime)
├── requirements.txt
├── run.py
├── README.md
```

---

## ⚙️ Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/sanaIITM/Vehicle_Parking_App_V2.git
cd Vehicle_Parking_App_V2
```

### 2. Create Virtual Environment

```bash
python -m venv venv
venv\\Scripts\\activate   # Windows
source venv/bin/activate  # Linux / Mac
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Start Redis Server

```bash
redis-server
```

### 5. Start Celery Worker

```bash
celery -A app.celery_app.celery worker --loglevel=info --pool=solo
```

### 6. Start Celery Beat (Scheduler)

```bash
celery -A app.celery_app.celery beat --loglevel=info
```

bash
celery -A app.celery_app.celery worker -B --loglevel=info

````

### 7. Run Flask App
```bash
python run.py
````

---

## ✅ Compliance Checklist (MAD-II)

* Flask API
* VueJS UI
* SQLite database (programmatic creation)
* Redis caching
* Celery async jobs
* Scheduled daily reminders
* Monthly email reports
* CSV export
* Role-based access control

---

## 👨‍🏫 Submitted For

**Course:** Modern Application Development II  
**Institution:** IIT Madras  
**Program:** Diploma  
**Student:** Sana Bint Salim Valiyakath  
**Roll No:** 24f1000823
