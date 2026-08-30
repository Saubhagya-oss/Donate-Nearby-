from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from models import db, Organizer, NGO, FoodListing, DeliveryPartner, Report
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import math
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SECRET_KEY'] = 'your-secret-key-here'

db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*")


def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    return round(distance, 2)


@app.route('/')
def home():
    return render_template('home.html')


with app.app_context():
    db.create_all()


# ---------- ORGANIZER SIGNUP ----------
@app.route('/organizer/signup', methods=['GET', 'POST'])
def organizer_signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phone')

        existing = Organizer.query.filter_by(email=email).first()
        if existing:
            return "Email already registered", 400

        hashed_pw = generate_password_hash(password)
        new_organizer = Organizer(name=name, email=email, password=hashed_pw, phone=phone)
        db.session.add(new_organizer)
        db.session.commit()

        return redirect(url_for('organizer_login'))

    return render_template('organizer_signup.html')


# ---------- ORGANIZER LOGIN ----------
@app.route('/organizer/login', methods=['GET', 'POST'])
def organizer_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        organizer = Organizer.query.filter_by(email=email).first()
        if organizer and check_password_hash(organizer.password, password):
            if organizer.is_blocked:
                return f"Your account has been blocked. Reason: {organizer.block_reason}", 403
            session['organizer_id'] = organizer.id
            return redirect(url_for('organizer_dashboard'))

        return "Invalid credentials", 401

    return render_template('organizer_login.html')


# ---------- NGO SIGNUP ----------
@app.route('/ngo/signup', methods=['GET', 'POST'])
def ngo_signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phone')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')

        existing = NGO.query.filter_by(email=email).first()
        if existing:
            return "Email already registered", 400

        hashed_pw = generate_password_hash(password)
        new_ngo = NGO(name=name, email=email, password=hashed_pw, phone=phone,
                       latitude=latitude, longitude=longitude)
        db.session.add(new_ngo)
        db.session.commit()

        return redirect(url_for('ngo_login'))

    return render_template('ngo_signup.html')


# ---------- NGO LOGIN ----------
@app.route('/ngo/login', methods=['GET', 'POST'])
def ngo_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        ngo = NGO.query.filter_by(email=email).first()
        if ngo and check_password_hash(ngo.password, password):
            if ngo.is_blocked:
                return f"Your account has been blocked. Reason: {ngo.block_reason}", 403
            session['ngo_id'] = ngo.id
            return redirect(url_for('ngo_dashboard'))

        return "Invalid credentials", 401

    return render_template('ngo_login.html')


# ---------- Dashboard ----------
@app.route('/organizer/dashboard')
def organizer_dashboard():
    if 'organizer_id' not in session:
        return redirect(url_for('organizer_login'))
    
    organizer = Organizer.query.get(session['organizer_id'])
    if organizer.is_blocked:
        session.clear()
        return redirect(url_for('organizer_login'))
    
    from datetime import datetime
    now = datetime.utcnow()
    listings = FoodListing.query.filter_by(organizer_id=session['organizer_id']).all()
    # Add expired flag to each listing
    for listing in listings:
        listing.is_expired = listing.expiry_time < now and listing.status == 'pending'
    return render_template('organizer_dashboard.html', listings=listings)


@app.route('/ngo/dashboard')
def ngo_dashboard():
    if 'ngo_id' not in session:
        return redirect(url_for('ngo_login'))

    ngo = NGO.query.get(session['ngo_id'])
    if ngo.is_blocked:
        session.clear()
        return redirect(url_for('ngo_login'))

    all_listings = FoodListing.query.filter_by(status='pending').all()

    nearby_listings = []
    for listing in all_listings:
        if listing.organizer.is_blocked:
            continue
        distance = haversine(ngo.latitude, ngo.longitude, listing.latitude, listing.longitude)
        if distance <= 15:
            nearby_listings.append({
                'listing': listing,
                'distance': distance
            })

    nearby_listings.sort(key=lambda x: x['distance'])

    # Fetch accepted listings for this NGO (My Pickups)
    my_pickups = FoodListing.query.filter_by(
        status='accepted',
        accepted_by_ngo_id=session['ngo_id']
    ).all()

    return render_template('ngo_dashboard.html', nearby_listings=nearby_listings, my_pickups=my_pickups)


# ---------- POST SURPLUS FOOD (Organizer) ----------
@app.route('/food/post', methods=['GET', 'POST'])
def food_post():
    if 'organizer_id' not in session:
        return redirect(url_for('organizer_login'))

    if request.method == 'POST':
        food_type = request.form.get('food_type')
        quantity = request.form.get('quantity')
        pickup_location = request.form.get('pickup_location')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        expiry_time_str = request.form.get('expiry_time')
        dietary_category = request.form.get('dietary_category')
        dietary_category_other = request.form.get('dietary_category_other')
        allergens = request.form.get('allergens')

        expiry_time = datetime.strptime(expiry_time_str, '%Y-%m-%dT%H:%M')

        new_listing = FoodListing(
            organizer_id=session['organizer_id'],
            food_type=food_type,
            quantity=quantity,
            pickup_location=pickup_location,
            latitude=float(latitude),
            longitude=float(longitude),
            expiry_time=expiry_time,
            dietary_category=dietary_category,
            dietary_category_other=dietary_category_other if dietary_category == 'Custom / Other' else None,
            allergens=allergens if allergens else None,
            status='pending'
        )
        db.session.add(new_listing)
        db.session.commit()

        return redirect(url_for('organizer_dashboard'))

    return render_template('food_post.html')


@app.route('/food/accept/<int:listing_id>')
def accept_food(listing_id):
    if 'ngo_id' not in session:
        return redirect(url_for('ngo_login'))

    listing = FoodListing.query.get(listing_id)
    if listing and listing.status == 'pending':
        listing.status = 'accepted'
        listing.accepted_by_ngo_id = session['ngo_id']
        db.session.commit()

    return redirect(url_for('ngo_dashboard'))


@app.route('/food/report/<int:listing_id>', methods=['POST'])
def report_food(listing_id):
    if 'ngo_id' not in session:
        return redirect(url_for('ngo_login'))

    listing = FoodListing.query.get(listing_id)
    if listing:
        listing.reported = True
        db.session.commit()

    return redirect(url_for('ngo_dashboard'))


# ---------- API ENDPOINTS FOR AJAX ----------
@app.route('/api/listings/nearby')
def api_nearby_listings():
    if 'ngo_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    ngo = NGO.query.get(session['ngo_id'])
    now = datetime.utcnow()
    all_listings = FoodListing.query.filter(
        FoodListing.status == 'pending',
        FoodListing.expiry_time > now
    ).all()

    nearby_listings = []
    for listing in all_listings:
        if listing.organizer.is_blocked:
            continue
        distance = haversine(ngo.latitude, ngo.longitude, listing.latitude, listing.longitude)
        if distance <= 15:
            dietary_display = listing.dietary_category
            if listing.dietary_category == 'Custom / Other' and listing.dietary_category_other:
                dietary_display = listing.dietary_category_other
            nearby_listings.append({
                'id': listing.id,
                'food_type': listing.food_type,
                'quantity': listing.quantity,
                'pickup_location': listing.pickup_location,
                'expiry_time': listing.expiry_time.strftime('%Y-%m-%d %H:%M'),
                'distance': distance,
                'organizer_name': listing.organizer.name,
                'organizer_id': listing.organizer.id,
                'dietary_category': dietary_display,
                'allergens': listing.allergens
            })

    nearby_listings.sort(key=lambda x: x['distance'])
    return jsonify({'listings': nearby_listings})


@app.route('/api/listings/my-accepted')
def api_my_accepted_listings():
    if 'ngo_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    listings = FoodListing.query.filter_by(
        accepted_by_ngo_id=session['ngo_id'],
        status='accepted'
    ).all()
    
    result = []
    for l in listings:
        result.append({
            'id': l.id,
            'food_type': l.food_type,
            'quantity': l.quantity,
            'pickup_location': l.pickup_location,
            'expiry_time': l.expiry_time.strftime('%Y-%m-%d %H:%M'),
            'organizer_name': l.organizer.name if l.organizer else 'Unknown',
            'dietary_category': l.dietary_category_other if l.dietary_category == 'Custom / Other' and l.dietary_category_other else l.dietary_category,
            'allergens': l.allergens or ''
        })
    
    return jsonify({'listings': result})


@app.route('/api/listings/my')
def api_my_listings():
    if 'organizer_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    from datetime import datetime
    now = datetime.utcnow()
    listings = FoodListing.query.filter_by(organizer_id=session['organizer_id']).all()
    return jsonify({'listings': [
        {
            'id': l.id,
            'food_type': l.food_type,
            'quantity': l.quantity,
            'pickup_location': l.pickup_location,
            'expiry_time': l.expiry_time.strftime('%Y-%m-%d %H:%M'),
            'status': l.status,
            'is_expired': l.expiry_time < now and l.status == 'pending',
            'delivery_method': l.delivery_method,
            'dietary_category': l.dietary_category_other if l.dietary_category == 'Custom / Other' and l.dietary_category_other else l.dietary_category,
            'allergens': l.allergens
        } for l in listings
    ]})


@app.route('/api/food/accept/<int:listing_id>', methods=['POST'])
def api_accept_food(listing_id):
    if 'ngo_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    listing = FoodListing.query.get(listing_id)
    if not listing or listing.status != 'pending':
        return jsonify({'error': 'Listing not available'}), 400

    listing.status = 'accepted'
    listing.accepted_by_ngo_id = session['ngo_id']
    db.session.commit()

    socketio.emit('listing_accepted', {
        'listing_id': listing_id,
        'ngo_name': NGO.query.get(session['ngo_id']).name
    }, room=f'organizer_{listing.organizer_id}')

    socketio.emit('listing_updated', {'listing_id': listing_id, 'status': 'accepted'})

    return jsonify({'success': True, 'message': 'Food pickup accepted!'})


@app.route('/api/food/complete/<int:listing_id>', methods=['POST'])
def api_complete_food(listing_id):
    if 'ngo_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    listing = FoodListing.query.get(listing_id)
    if not listing or listing.status != 'accepted':
        return jsonify({'error': 'Listing not available for completion'}), 400

    if listing.accepted_by_ngo_id != session['ngo_id']:
        return jsonify({'error': 'You can only complete your own accepted pickups'}), 403

    listing.status = 'picked_up'
    db.session.commit()

    socketio.emit('listing_completed', {
        'listing_id': listing_id,
        'ngo_name': NGO.query.get(session['ngo_id']).name
    }, room=f'organizer_{listing.organizer_id}')

    socketio.emit('listing_updated', {'listing_id': listing_id, 'status': 'picked_up'})

    return jsonify({'success': True, 'message': 'Pickup marked as completed!'})


@app.route('/api/food/post', methods=['POST'])
def api_post_food():
    if 'organizer_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    organizer = Organizer.query.get(session['organizer_id'])
    if organizer.is_blocked:
        return jsonify({'error': 'Your account has been blocked. You cannot post new listings.', 'blocked': True, 'reason': organizer.block_reason}), 403

    food_type = request.form.get('food_type')
    quantity = request.form.get('quantity')
    pickup_location = request.form.get('pickup_location')
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')
    expiry_time_str = request.form.get('expiry_time')
    dietary_category = request.form.get('dietary_category')
    dietary_category_other = request.form.get('dietary_category_other')
    allergens = request.form.get('allergens')

    if not all([food_type, quantity, pickup_location, latitude, longitude, expiry_time_str, dietary_category]):
        return jsonify({'error': 'All fields required including dietary category'}), 400

    if dietary_category == 'Custom / Other' and not dietary_category_other:
        return jsonify({'error': 'Custom dietary category description required'}), 400

    expiry_time = datetime.strptime(expiry_time_str, '%Y-%m-%dT%H:%M')

    new_listing = FoodListing(
        organizer_id=session['organizer_id'],
        food_type=food_type,
        quantity=quantity,
        pickup_location=pickup_location,
        latitude=float(latitude),
        longitude=float(longitude),
        expiry_time=expiry_time,
        dietary_category=dietary_category,
        dietary_category_other=dietary_category_other if dietary_category == 'Custom / Other' else None,
        allergens=allergens if allergens else None,
        status='pending'
    )
    db.session.add(new_listing)
    db.session.commit()

    socketio.emit('new_listing', {
        'id': new_listing.id,
        'food_type': new_listing.food_type,
        'quantity': new_listing.quantity,
        'pickup_location': new_listing.pickup_location,
        'expiry_time': new_listing.expiry_time.strftime('%Y-%m-%d %H:%M'),
        'organizer_name': Organizer.query.get(session['organizer_id']).name
    })

    return jsonify({'success': True, 'listing_id': new_listing.id})


@app.route('/api/food/delete/<int:listing_id>', methods=['POST'])
def api_delete_food(listing_id):
    if 'organizer_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    listing = FoodListing.query.get(listing_id)
    if not listing or listing.organizer_id != session['organizer_id']:
        return jsonify({'error': 'Listing not found'}), 404

    db.session.delete(listing)
    db.session.commit()

    socketio.emit('listing_deleted', {'listing_id': listing_id}, room=f'organizer_{session["organizer_id"]}')

    return jsonify({'success': True, 'message': 'Listing deleted'})


# ---------- DELIVERY ENDPOINTS ----------
@app.route('/api/delivery/partners/<int:listing_id>')
def api_delivery_partners(listing_id):
    if 'organizer_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    listing = FoodListing.query.get(listing_id)
    if not listing or listing.organizer_id != session['organizer_id']:
        return jsonify({'error': 'Listing not found'}), 404

    if listing.status != 'accepted':
        return jsonify({'error': 'Listing must be accepted before arranging delivery'}), 400

    partners = DeliveryPartner.query.filter_by(is_available=True, verified=True).all()
    nearby_partners = []
    for partner in partners:
        distance = haversine(listing.latitude, listing.longitude, partner.latitude, partner.longitude)
        if distance <= 20:  # 20km radius
            nearby_partners.append({
                'id': partner.id,
                'name': partner.name,
                'phone': partner.phone,
                'vehicle_type': partner.vehicle_type,
                'distance': distance
            })

    nearby_partners.sort(key=lambda x: x['distance'])
    return jsonify({'partners': nearby_partners})


@app.route('/api/delivery/assign', methods=['POST'])
def api_assign_delivery():
    if 'organizer_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    listing_id = data.get('listing_id')
    partner_id = data.get('partner_id')
    delivery_method = data.get('delivery_method')  # 'self' or 'partner'

    listing = FoodListing.query.get(listing_id)
    if not listing or listing.organizer_id != session['organizer_id']:
        return jsonify({'error': 'Listing not found'}), 404

    if listing.status != 'accepted':
        return jsonify({'error': 'Listing must be accepted before arranging delivery'}), 400

    if delivery_method == 'self':
        listing.delivery_method = 'self'
        listing.status = 'delivered'
        db.session.commit()
        return jsonify({'success': True, 'message': 'Marked as self-delivery'})

    elif delivery_method == 'partner' and partner_id:
        partner = DeliveryPartner.query.get(partner_id)
        if not partner or not partner.is_available:
            return jsonify({'error': 'Delivery partner not available'}), 400

        listing.delivery_method = 'partner'
        listing.delivery_partner_id = partner_id
        partner.is_available = False
        listing.status = 'delivered'
        db.session.commit()

        return jsonify({'success': True, 'message': f'Delivery assigned to {partner.name}'})

    return jsonify({'error': 'Invalid delivery method'}), 400


# ---------- REPORT & BLOCK ENDPOINTS ----------
@app.route('/api/report/organizer', methods=['POST'])
def api_report_organizer():
    if 'ngo_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    organizer_id = data.get('organizer_id')
    listing_id = data.get('listing_id')
    reason = data.get('reason')
    details = data.get('details', '')

    if not organizer_id or not reason:
        return jsonify({'error': 'Organizer ID and reason are required'}), 400

    organizer = Organizer.query.get(organizer_id)
    if not organizer:
        return jsonify({'error': 'Organizer not found'}), 404

    if organizer.is_blocked:
        return jsonify({'error': 'This organizer is already blocked'}), 400

    existing_report = Report.query.filter_by(
        reporter_ngo_id=session['ngo_id'],
        reported_organizer_id=organizer_id,
        listing_id=listing_id
    ).first()
    if existing_report:
        return jsonify({'error': 'You have already reported this organizer for this listing'}), 400

    report = Report(
        reporter_ngo_id=session['ngo_id'],
        reported_organizer_id=organizer_id,
        listing_id=listing_id,
        reason=reason,
        details=details
    )
    db.session.add(report)
    db.session.commit()

    unique_reporters = db.session.query(Report.reporter_ngo_id).filter_by(
        reported_organizer_id=organizer_id
    ).distinct().count()

    if unique_reporters >= 3:
        organizer.is_blocked = True
        organizer.block_reason = f'Auto-blocked after {unique_reporters} reports from different NGOs'
        db.session.commit()
        
        FoodListing.query.filter_by(organizer_id=organizer_id, status='pending').update({'status': 'rejected'})
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Report submitted. Organizer has been auto-blocked due to multiple reports.',
            'report_id': report.id,
            'auto_blocked': True
        })

    return jsonify({'success': True, 'message': 'Report submitted successfully', 'report_id': report.id})


@app.route('/api/report/list')
def api_list_reports():
    if 'ngo_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    reports = Report.query.filter_by(reporter_ngo_id=session['ngo_id']).all()
    return jsonify({'reports': [
        {
            'id': r.id,
            'organizer_name': r.reported.name,
            'organizer_email': r.reported.email,
            'reason': r.reason,
            'details': r.details,
            'status': r.status,
            'created_at': r.created_at.strftime('%Y-%m-%d %H:%M'),
            'listing_id': r.listing_id
        } for r in reports
    ]})


@app.route('/api/admin/block/organizer/<int:organizer_id>', methods=['POST'])
def api_block_organizer(organizer_id):
    if 'ngo_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    organizer = Organizer.query.get(organizer_id)
    if not organizer:
        return jsonify({'error': 'Organizer not found'}), 404

    data = request.get_json()
    reason = data.get('reason', 'Blocked by admin/moderation')

    organizer.is_blocked = True
    organizer.block_reason = reason
    db.session.commit()

    FoodListing.query.filter_by(organizer_id=organizer_id, status='pending').update({'status': 'rejected'})
    db.session.commit()

    return jsonify({'success': True, 'message': f'Organizer {organizer.name} has been blocked'})


@app.route('/api/admin/unblock/organizer/<int:organizer_id>', methods=['POST'])
def api_unblock_organizer(organizer_id):
    if 'ngo_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    organizer = Organizer.query.get(organizer_id)
    if not organizer:
        return jsonify({'error': 'Organizer not found'}), 404

    organizer.is_blocked = False
    organizer.block_reason = None
    db.session.commit()

    return jsonify({'success': True, 'message': f'Organizer {organizer.name} has been unblocked'})


@app.route('/api/check/blocked/<int:organizer_id>')
def api_check_blocked(organizer_id):
    organizer = Organizer.query.get(organizer_id)
    if not organizer:
        return jsonify({'error': 'Organizer not found'}), 404

    return jsonify({
        'is_blocked': organizer.is_blocked,
        'block_reason': organizer.block_reason
    })


# Socket.IO Events
@socketio.on('connect')
def handle_connect():
    print('Client connected')


@socketio.on('join_organizer')
def handle_join_organizer(data):
    if 'organizer_id' in session:
        join_room(f'organizer_{session["organizer_id"]}')


@socketio.on('join_ngo')
def handle_join_ngo(data):
    if 'ngo_id' in session:
        join_room(f'ngo_{session["ngo_id"]}')


if __name__ == '__main__':
    socketio.run(app, debug=True)