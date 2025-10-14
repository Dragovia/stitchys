import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, VintageItem, CartItem
from functools import wraps

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vintage_vault.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Change this to a secure secret key
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Admin credentials - In production, these should be stored securely
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = generate_password_hash('admin123')  # Change this password

db.init_app(app)
with app.app_context():
    db.drop_all()  # Drop all tables
    db.create_all()  # Create new tables with updated schema

# Allowed file extensions for images
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Login required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Customer routes
@app.route('/')
def index():
    items = VintageItem.query.filter_by(status='Available').all()
    return render_template('index.html', items=items)

@app.route('/hats')
def hats():
    items = VintageItem.query.filter_by(category='Hats', status='Available').all()
    return render_template('hats.html', items=items)

@app.route('/clothing')
def clothing():
    items = VintageItem.query.filter_by(category='Clothing', status='Available').all()
    return render_template('clothing.html', items=items)

# Admin routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD, password):
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials', 'error')
    
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    items = VintageItem.query.all()
    return render_template('admin/dashboard.html', items=items)

@app.route('/admin/add', methods=['GET', 'POST'])
@admin_required
def admin_add_item():
    if request.method == 'POST':
        name = request.form['name']
        category = request.form['category']
        price = float(request.form['price'])
        selling_price = float(request.form.get('selling_price', price))  # Default to price if not specified
        description = request.form['description']
        condition = request.form.get('condition', 'Good')
        
        # Handle image upload
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                image_url = 'uploads/' + filename  # Use forward slashes for URLs
            else:
                image_url = None
        else:
            image_url = None

        new_item = VintageItem(
            name=name,
            category=category,
            price=price,
            selling_price=selling_price,
            description=description,
            condition=condition,
            image_url=image_url,
            status='Available'
        )
        
        db.session.add(new_item)
        db.session.commit()
        flash('Item added successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/add_item.html')

@app.route('/admin/edit/<int:item_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_item(item_id):
    item = VintageItem.query.get_or_404(item_id)
    
    if request.method == 'POST':
        item.name = request.form['name']
        item.category = request.form['category']
        item.price = float(request.form['price'])
        item.description = request.form['description']
        
        # Handle image upload
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                # Delete old image if it exists
                if item.image_url:
                    old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(item.image_url))
                    if os.path.exists(old_image_path):
                        os.remove(old_image_path)
                
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                item.image_url = os.path.join('uploads', filename)
        
        db.session.commit()
        flash('Item updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    return render_template('admin/edit_item.html', item=item)

@app.route('/admin/delete/<int:item_id>')
@admin_required
def admin_delete_item(item_id):
    item = VintageItem.query.get_or_404(item_id)
    
    # Delete image file if it exists
    if item.image_url:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(item.image_url))
        if os.path.exists(image_path):
            os.remove(image_path)
    
    db.session.delete(item)
    db.session.commit()
    flash('Item deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

def get_cart_session_id():
    if 'cart_id' not in session:
        session['cart_id'] = os.urandom(16).hex()
    return session['cart_id']

@app.route('/cart')
def view_cart():
    session_id = get_cart_session_id()
    cart_items = CartItem.query.filter_by(session_id=session_id).all()
    total = sum(item.item.price * item.quantity for item in cart_items)
    total_items = sum(item.quantity for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total, total_items=total_items)

@app.route('/cart/add/<int:item_id>', methods=['POST'])
def add_to_cart(item_id):
    session_id = get_cart_session_id()
    cart_item = CartItem.query.filter_by(session_id=session_id, item_id=item_id).first()
    
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = CartItem(session_id=session_id, item_id=item_id, quantity=1)
        db.session.add(cart_item)
    
    db.session.commit()
    flash('Item added to cart!', 'success')
    return redirect(request.referrer or url_for('index'))

@app.route('/cart/update/<int:item_id>', methods=['POST'])
def update_cart_item(item_id):
    session_id = get_cart_session_id()
    cart_item = CartItem.query.filter_by(session_id=session_id, item_id=item_id).first_or_404()
    
    quantity = int(request.form.get('quantity', 1))
    if quantity > 0 and quantity <= 10:
        cart_item.quantity = quantity
        db.session.commit()
        flash('Cart updated!', 'success')
    
    return redirect(url_for('view_cart'))

@app.route('/cart/remove/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):
    session_id = get_cart_session_id()
    cart_item = CartItem.query.filter_by(session_id=session_id, item_id=item_id).first_or_404()
    
    db.session.delete(cart_item)
    db.session.commit()
    flash('Item removed from cart!', 'success')
    return redirect(url_for('view_cart'))

if __name__ == '__main__':
    app.run(debug=True)
