from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(100), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('vintage_item.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    item = db.relationship('VintageItem', backref='cart_items')

class VintageItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    selling_price = db.Column(db.Float, nullable=True)  # Made optional
    description = db.Column(db.Text, nullable=True)
    condition = db.Column(db.String(50), default='Good')  # Added default
    status = db.Column(db.String(20), default='Available')
    image_url = db.Column(db.String(255), nullable=True)

    def __init__(self, *args, **kwargs):
        super(VintageItem, self).__init__(*args, **kwargs)
        if self.selling_price is None:
            self.selling_price = self.price  # Default selling price to price if not specified

    def __repr__(self):
        return f"<Item {self.name}>"
