from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Organizer(db.Model):
    __tablename__ = 'organizer'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  
    phone = db.Column(db.String(15), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_blocked = db.Column(db.Boolean, default=False)
    block_reason = db.Column(db.Text, nullable=True)

    listings = db.relationship('FoodListing', backref='organizer', lazy=True)


class NGO(db.Model):
    __tablename__ = 'ngo'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_blocked = db.Column(db.Boolean, default=False)
    block_reason = db.Column(db.Text, nullable=True)


class DeliveryPartner(db.Model):
    __tablename__ = 'delivery_partner'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    vehicle_type = db.Column(db.String(50), nullable=False)  # bike, van, truck
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    deliveries = db.relationship('FoodListing', backref='delivery_partner', lazy=True)


class FoodListing(db.Model):
    __tablename__ = 'food_listing'

    id = db.Column(db.Integer, primary_key=True)
    organizer_id = db.Column(db.Integer, db.ForeignKey('organizer.id'), nullable=False)

    food_type = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.String(50), nullable=False)  # e.g. "50 plates", "10 kg"
    pickup_location = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    expiry_time = db.Column(db.DateTime, nullable=False)  # kab tak safe hai

    dietary_category = db.Column(db.String(50), nullable=False)
    dietary_category_other = db.Column(db.String(100), nullable=True)
    allergens = db.Column(db.String(200), nullable=True)

    status = db.Column(db.String(20), default='pending')  # pending / accepted / picked_up / delivered
    accepted_by_ngo_id = db.Column(db.Integer, db.ForeignKey('ngo.id'), nullable=True)
    delivery_method = db.Column(db.String(20), nullable=True)  # self / partner
    delivery_partner_id = db.Column(db.Integer, db.ForeignKey('delivery_partner.id'), nullable=True)

    reported = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Report(db.Model):
    __tablename__ = 'report'

    id = db.Column(db.Integer, primary_key=True)
    reporter_ngo_id = db.Column(db.Integer, db.ForeignKey('ngo.id'), nullable=False)
    reported_organizer_id = db.Column(db.Integer, db.ForeignKey('organizer.id'), nullable=False)
    listing_id = db.Column(db.Integer, db.ForeignKey('food_listing.id'), nullable=True)
    reason = db.Column(db.Text, nullable=False)
    details = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    reviewed_by = db.Column(db.String(50), nullable=True)

    reporter = db.relationship('NGO', backref='reports_made')
    reported = db.relationship('Organizer', backref='reports_received')
    listing = db.relationship('FoodListing', backref='reports')