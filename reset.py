from app import app, db
from models import FoodListing

with app.app_context():
    listings = FoodListing.query.all()
    for l in listings:
        l.status = 'pending'
        l.accepted_by_ngo_id = None
    db.session.commit()
    print("Reset done! Total listings updated:", len(listings))