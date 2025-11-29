from flask import (
    render_template,
    redirect,
    url_for,
    request,
    jsonify,
    session,
)
from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

from .models import db, User, ParkingLot, ParkingSpot, Reservation
from . import cache


def register_routes(app):

    # ---------- disable browser caching of HTML responses ----------
    def no_cache(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    @app.after_request
    def add_cache_headers(response):
        return no_cache(response)

    # ====================== SPA ENTRY ======================
    @app.route("/")
    def home():
        # Vue SPA entry point
        return render_template("index.html")

    # ====================== DEBUG TASK TRIGGERS (ADMIN ONLY) ======================
    @app.route("/debug/run_daily_reminders", methods=["POST"])
    @login_required
    def debug_run_daily_reminders():
        if current_user.role != "admin":
            return jsonify({"error": "Admin access required"}), 403
        from .tasks import send_daily_reminders

        send_daily_reminders.delay()
        return jsonify({"message": "Daily reminder task queued."})

    @app.route("/debug/run_monthly_reports", methods=["POST"])
    @login_required
    def debug_run_monthly_reports():
        if current_user.role != "admin":
            return jsonify({"error": "Admin access required"}), 403
        from .tasks import send_monthly_reports

        send_monthly_reports.delay()
        return jsonify({"message": "Monthly report task queued."})

    # ====================== AUTH JSON APIs ======================
    @app.route("/api/me", methods=["GET"])
    def api_me():
        if not current_user.is_authenticated:
            return jsonify({"user": None})
        return jsonify(
            {
                "user": {
                    "id": current_user.id,
                    "username": current_user.username,
                    "role": current_user.role,
                }
            }
        )

    @app.route("/api/register", methods=["POST"])
    def api_register():
        data = request.get_json() or {}
        username = data.get("username", "").strip()
        password = data.get("password", "")

        if not username or not password:
            return jsonify({"error": "Both username and password are required."}), 400

        if User.query.filter_by(username=username).first():
            return jsonify({"error": "Username already exists."}), 400

        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password=hashed_pw, role="user")
        db.session.add(new_user)
        db.session.commit()

        return jsonify({"message": "Registration successful. Please log in."}), 201

    @app.route("/api/login", methods=["POST"])
    def api_login():
        if current_user.is_authenticated:
            return jsonify(
                {
                    "message": "Already logged in.",
                    "user": {
                        "id": current_user.id,
                        "username": current_user.username,
                        "role": current_user.role,
                    },
                }
            )

        data = request.get_json() or {}
        username = data.get("username", "").strip()
        password = data.get("password", "")

        if not username or not password:
            return jsonify({"error": "Both username and password are required."}), 400

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            session.permanent = False
            session.modified = True
            return jsonify(
                {
                    "message": "Login successful.",
                    "user": {
                        "id": user.id,
                        "username": user.username,
                        "role": user.role,
                    },
                }
            )

        return jsonify({"error": "Invalid credentials."}), 401

    @app.route("/api/logout", methods=["POST"])
    @login_required
    def api_logout():
        logout_user()
        session.clear()
        return jsonify({"message": "Logged out."})

    # ====================== ADMIN JSON DASHBOARD ======================
    @app.route("/api/admin/dashboard", methods=["GET"])
    @login_required
    def api_admin_dashboard():
        if current_user.role != "admin":
            return jsonify({"error": "Admin access required"}), 403

        cache_key = "admin_dashboard"
        cached = cache.get(cache_key)
        if cached:
            return jsonify(cached)

        lots = ParkingLot.query.all()
        users = User.query.filter_by(role="user").all()
        reservations = (
            Reservation.query.order_by(Reservation.start_time.desc()).limit(50).all()
        )

        lots_data = []
        for lot in lots:
            total = len(lot.spots)
            available = sum(1 for s in lot.spots if s.status == "A")
            occupied = total - available
            lots_data.append(
                {
                    "id": lot.id,
                    "name": lot.name,
                    "address": lot.address,
                    "pincode": lot.pincode,
                    "price_per_hour": lot.price_per_hour,
                    "max_spots": lot.max_spots,
                    "total_spots": total,
                    "available_spots": available,
                    "occupied_spots": occupied,
                }
            )

        users_data = [
            {
                "id": u.id,
                "username": u.username,
                "reservation_count": len(u.reservations),
            }
            for u in users
        ]

        reservations_data = []
        for r in reservations:
            reservations_data.append(
                {
                    "id": r.id,
                    "user": r.user.username if r.user else None,
                    "lot": r.spot.lot.name if r.spot and r.spot.lot else None,
                    "spot_id": r.spot_id,
                    "start_time": r.start_time.isoformat() if r.start_time else None,
                    "end_time": r.end_time.isoformat() if r.end_time else None,
                    "cost": r.cost,
                }
            )

        data = {"lots": lots_data, "users": users_data, "reservations": reservations_data}
        cache.set(cache_key, data, timeout=60)
        return jsonify(data)

    # ====================== ADMIN LOT MANAGEMENT JSON APIs ======================
    @app.route("/api/admin/lots", methods=["GET", "POST"])
    @login_required
    def api_admin_lots():
        if current_user.role != "admin":
            return jsonify({"error": "Admin access required"}), 403

        if request.method == "GET":
            lots = ParkingLot.query.all()
            data = []
            for lot in lots:
                total = len(lot.spots)
                available = sum(1 for s in lot.spots if s.status == "A")
                occupied = total - available
                data.append(
                    {
                        "id": lot.id,
                        "name": lot.name,
                        "address": lot.address,
                        "pincode": lot.pincode,
                        "price_per_hour": lot.price_per_hour,
                        "max_spots": lot.max_spots,
                        "total_spots": total,
                        "available_spots": available,
                        "occupied_spots": occupied,
                    }
                )
            return jsonify({"lots": data})

        # POST -> create lot
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        address = data.get("address", "").strip()
        pincode = data.get("pincode", "").strip()
        price_per_hour = data.get("price_per_hour")
        max_spots = data.get("max_spots")

        if not name or not address or not pincode or price_per_hour is None or max_spots is None:
            return jsonify({"error": "All fields are required."}), 400

        try:
            price_per_hour = float(price_per_hour)
            max_spots = int(max_spots)
            if max_spots <= 0 or price_per_hour < 0:
                raise ValueError
        except ValueError:
            return jsonify({"error": "Invalid price or number of spots."}), 400

        lot = ParkingLot(
            name=name,
            address=address,
            pincode=pincode,
            price_per_hour=price_per_hour,
            max_spots=max_spots,
        )
        db.session.add(lot)
        db.session.flush()  # gives lot.id

        for _ in range(max_spots):
            db.session.add(ParkingSpot(lot_id=lot.id))

        db.session.commit()
        cache.delete("admin_dashboard")

        total = len(lot.spots)
        available = sum(1 for s in lot.spots if s.status == "A")
        occupied = total - available
        return (
            jsonify(
                {
                    "id": lot.id,
                    "name": lot.name,
                    "address": lot.address,
                    "pincode": lot.pincode,
                    "price_per_hour": lot.price_per_hour,
                    "max_spots": lot.max_spots,
                    "total_spots": total,
                    "available_spots": available,
                    "occupied_spots": occupied,
                }
            ),
            201,
        )

    @app.route("/api/admin/lots/<int:lot_id>", methods=["PUT", "DELETE"])
    @login_required
    def api_admin_lot_detail(lot_id):
        if current_user.role != "admin":
            return jsonify({"error": "Admin access required"}), 403

        lot = ParkingLot.query.get_or_404(lot_id)

        if request.method == "DELETE":
            if any(s.status == "O" for s in lot.spots):
                return (
                    jsonify(
                        {
                            "error": "Cannot delete lot — some spots are still occupied."
                        }
                    ),
                    400,
                )
            db.session.delete(lot)
            db.session.commit()
            cache.delete("admin_dashboard")
            return jsonify({"message": "Parking lot deleted."})

        # PUT -> update lot
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        address = data.get("address", "").strip()
        pincode = data.get("pincode", "").strip()
        price_per_hour = data.get("price_per_hour")
        new_max = data.get("max_spots")

        if not name or not address or not pincode or price_per_hour is None or new_max is None:
            return jsonify({"error": "All fields are required."}), 400

        try:
            price_per_hour = float(price_per_hour)
            new_max = int(new_max)
            if new_max <= 0 or price_per_hour < 0:
                raise ValueError
        except ValueError:
            return jsonify({"error": "Invalid price or number of spots."}), 400

        # adjust spots
        if new_max > lot.max_spots:
            # add spots
            for _ in range(new_max - lot.max_spots):
                db.session.add(ParkingSpot(lot_id=lot.id))
        elif new_max < lot.max_spots:
            # remove available spots only
            diff = lot.max_spots - new_max
            available_spots = ParkingSpot.query.filter_by(
                lot_id=lot.id, status="A"
            ).limit(diff).all()
            if len(available_spots) < diff:
                return (
                    jsonify(
                        {
                            "error": "Not enough available spots to reduce max_spots. Free some spots first."
                        }
                    ),
                    400,
                )
            for s in available_spots:
                db.session.delete(s)

        lot.name = name
        lot.address = address
        lot.pincode = pincode
        lot.price_per_hour = price_per_hour
        lot.max_spots = new_max

        db.session.commit()
        cache.delete("admin_dashboard")

        total = len(lot.spots)
        available = sum(1 for s in lot.spots if s.status == "A")
        occupied = total - available

        return jsonify(
            {
                "id": lot.id,
                "name": lot.name,
                "address": lot.address,
                "pincode": lot.pincode,
                "price_per_hour": lot.price_per_hour,
                "max_spots": lot.max_spots,
                "total_spots": total,
                "available_spots": available,
                "occupied_spots": occupied,
            }
        )

    # ====================== USER JSON DASHBOARD + ACTIONS ======================
    @app.route("/api/user/dashboard", methods=["GET"])
    @login_required
    def api_user_dashboard():
        if current_user.role != "user":
            return jsonify({"error": "User access required"}), 403

        cache_key = f"user_dashboard_{current_user.id}"
        cached = cache.get(cache_key)
        if cached:
            return jsonify(cached)

        lots = [
            lot
            for lot in ParkingLot.query.all()
            if any(spot.status == "A" for spot in lot.spots)
        ]

        current_res = Reservation.query.filter_by(
            user_id=current_user.id, end_time=None
        ).first()

        history = (
            Reservation.query.filter(
                Reservation.user_id == current_user.id,
                Reservation.end_time != None,  # noqa: E711
            )
            .order_by(Reservation.start_time.desc())
            .all()
        )

        lots_data = []
        for lot in lots:
            available = sum(1 for s in lot.spots if s.status == "A")
            lots_data.append(
                {
                    "id": lot.id,
                    "name": lot.name,
                    "price_per_hour": lot.price_per_hour,
                    "available_spots": available,
                }
            )

        current_data = None
        if current_res:
            current_data = {
                "id": current_res.id,
                "spot_id": current_res.spot_id,
                "lot_name": current_res.spot.lot.name
                if current_res.spot and current_res.spot.lot
                else None,
                "start_time": current_res.start_time.isoformat()
                if current_res.start_time
                else None,
            }

        history_data = []
        for r in history:
            history_data.append(
                {
                    "id": r.id,
                    "spot_id": r.spot_id,
                    "lot_name": r.spot.lot.name if r.spot and r.spot.lot else None,
                    "start_time": r.start_time.isoformat() if r.start_time else None,
                    "end_time": r.end_time.isoformat() if r.end_time else None,
                    "cost": r.cost,
                }
            )

        total_reservations = len(history)
        total_spent = sum((r.cost or 0.0) for r in history)

        lot_counts = {}
        for r in history:
            lot_name = r.spot.lot.name if r.spot and r.spot.lot else "Unknown"
            lot_counts[lot_name] = lot_counts.get(lot_name, 0) + 1

        most_used_lot = max(lot_counts, key=lot_counts.get) if lot_counts else None

        data = {
            "lots": lots_data,
            "current": current_data,
            "history": history_data,
            "summary": {
                "total_reservations": total_reservations,
                "total_spent": total_spent,
                "most_used_lot": most_used_lot,
                "lot_counts": lot_counts,
            },
        }
        cache.set(cache_key, data, timeout=60)
        return jsonify(data)

    @app.route("/api/user/book", methods=["POST"])
    @login_required
    def api_user_book():
        if current_user.role != "user":
            return jsonify({"error": "User access required"}), 403

        data = request.get_json() or {}
        lot_id = data.get("lot_id")
        if not lot_id:
            return jsonify({"error": "lot_id is required"}), 400

        active = Reservation.query.filter_by(
            user_id=current_user.id, end_time=None
        ).first()
        if active:
            return jsonify({"error": "You already have an active reservation."}), 400

        spot = ParkingSpot.query.filter_by(lot_id=lot_id, status="A").first()
        if not spot:
            return jsonify({"error": "No available spots in this lot."}), 400

        spot.status = "O"
        res = Reservation(
            spot_id=spot.id, user_id=current_user.id, start_time=datetime.now()
        )
        db.session.add(res)
        db.session.commit()

        cache.delete("admin_dashboard")
        cache.delete(f"user_dashboard_{current_user.id}")

        return jsonify(
            {
                "message": "Spot booked successfully.",
                "reservation": {
                    "id": res.id,
                    "spot_id": res.spot_id,
                    "lot_name": res.spot.lot.name
                    if res.spot and res.spot.lot
                    else None,
                    "start_time": res.start_time.isoformat()
                    if res.start_time
                    else None,
                },
            }
        )

    @app.route("/api/user/release", methods=["POST"])
    @login_required
    def api_user_release():
        if current_user.role != "user":
            return jsonify({"error": "User access required"}), 403

        data = request.get_json() or {}
        reservation_id = data.get("reservation_id")
        if not reservation_id:
            return jsonify({"error": "reservation_id is required"}), 400

        res = Reservation.query.get(reservation_id)
        if not res or res.user_id != current_user.id:
            return jsonify({"error": "Reservation not found."}), 404

        if res.end_time is not None:
            return jsonify({"error": "Reservation already released."}), 400

        res.end_time = datetime.now()
        duration = (res.end_time - res.start_time).total_seconds() / 3600
        lot = res.spot.lot
        res.cost = round(duration * lot.price_per_hour, 2)
        res.spot.status = "A"
        db.session.commit()

        cache.delete("admin_dashboard")
        cache.delete(f"user_dashboard_{current_user.id}")

        return jsonify(
            {
                "message": "Spot released.",
                "reservation": {
                    "id": res.id,
                    "spot_id": res.spot_id,
                    "lot_name": res.spot.lot.name
                    if res.spot and res.spot.lot
                    else None,
                    "start_time": res.start_time.isoformat()
                    if res.start_time
                    else None,
                    "end_time": res.end_time.isoformat()
                    if res.end_time
                    else None,
                    "cost": res.cost,
                },
            }
        )

    @app.route("/api/user/export_csv", methods=["POST"])
    @login_required
    def api_user_export_csv():
        if current_user.role != "user":
            return jsonify({"error": "User access required"}), 403

        from .tasks import generate_csv_for_user

        generate_csv_for_user.delay(current_user.id)
        return jsonify(
            {"message": "Export started. You will receive an email when it is ready."}
        )

    # ====================== SIMPLE REDIRECT HELPERS (NO JINJA UI) ======================
    @app.route("/login")
    def login():
        # Flask-Login will redirect here when login is required.
        # UI is entirely handled in the Vue SPA at "/".
        return redirect(url_for("home"))

    @app.route("/register")
    def register():
        # Registration UI is handled in Vue SPA at "/".
        return redirect(url_for("home"))

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        session.clear()
        return redirect(url_for("home"))
