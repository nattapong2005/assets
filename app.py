from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # เปลี่ยนเป็น secret key ที่ปลอดภัย
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'  # ฐานข้อมูลหลัก (สำหรับผู้ใช้งาน)
app.config['SQLALCHEMY_BINDS'] = {
    'assets': 'sqlite:///assets.db'  # กำหนดการเชื่อมต่อสำหรับฐานข้อมูล assets
}
db = SQLAlchemy(app)

# Model สำหรับผู้ใช้งาน (ใน users.db - ฐานข้อมูลหลัก)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    department = db.Column(db.String(80), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

# Model สำหรับทรัพย์สิน (ใน assets.db - ฐานข้อมูล 'assets')
class Asset(db.Model):
    __bind_key__ = 'assets'  # ระบุว่า Model นี้ใช้การเชื่อมต่อ 'assets'
    id = db.Column(db.Integer, primary_key=True)
    asset_id = db.Column(db.String(80), unique=True, nullable=False)
    asset_type = db.Column(db.String(80), nullable=False)
    user_id = db.Column(db.Integer, nullable=False)  # Foreign key to User (optional)
    username = db.Column(db.String(80), nullable=False)
    details = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(80), nullable=False)
    department = db.Column(db.String(80), nullable=False)

    def __repr__(self):
        return f'<Asset {self.asset_id}>'

with app.app_context():
    db.create_all()

# กำหนด Route หลักให้ redirect ไปที่หน้า Login
@app.route('/')
def index():
    return redirect(url_for('login'))

# หน้า Register (เหมือนเดิม)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        department = request.form['department']

        if User.query.filter_by(username=username).first():
            flash('ชื่อผู้ใช้งานนี้มีอยู่ในระบบแล้ว', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)  # *** ส่วนสำคัญ: เข้ารหัสรหัสผ่าน ***
        new_user = User(username=username, password=hashed_password, department=department)
        db.session.add(new_user)
        db.session.commit()
        flash('ลงทะเบียนสำเร็จ! กรุณาเข้าสู่ระบบ', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# หน้า Login (เหมือนเดิม)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['department'] = user.department
            flash('เข้าสู่ระบบสำเร็จ!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('ชื่อผู้ใช้งานหรือรหัสผ่านไม่ถูกต้อง', 'danger')
    return render_template('login.html')

# หน้า Dashboard (ปรับปรุง)
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    return render_template('dashboard.html', user=user)

# หน้าจัดการทรัพย์สิน
@app.route('/assets')
def assets_list():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    department = session['department']
    is_admin = department == 'IT'

    query = Asset.query

    if not is_admin:
        query = query.filter_by(department=department)

    search_term = request.args.get('search')
    if search_term:
        query = query.filter(
            (Asset.asset_id.contains(search_term)) |
            (Asset.asset_type.contains(search_term)) |
            (Asset.username.contains(search_term)) |
            (Asset.details.contains(search_term))
        )

    if is_admin:
        department_filter = request.args.get('department_filter')
        if department_filter and department_filter != 'all':
            query = query.filter_by(department=department_filter)

        status_filter = request.args.get('status_filter')
        if status_filter and status_filter != 'all':
            query = query.filter_by(status=status_filter)

    assets = query.all()
    return render_template('assets_list.html', assets=assets, user=user, is_admin=is_admin)

# หน้าเพิ่มทรัพย์สิน
@app.route('/assets/add', methods=['GET', 'POST'])
def add_asset():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        asset_id = request.form['asset_id']
        asset_type = request.form['asset_type']
        details = request.form['details']
        price = request.form['price']
        status = request.form['status']
        department = session['department']
        username = user.username

        if Asset.query.filter_by(asset_id=asset_id).first():
            flash('ID ทรัพย์สินนี้มีอยู่ในระบบแล้ว', 'danger')
            return redirect(url_for('add_asset'))

        new_asset = Asset(asset_id=asset_id, asset_type=asset_type, user_id=user.id, username=username, details=details, price=price, status=status, department=department)
        db.session.add(new_asset)  # ใช้ db.session แทน assets_db.session
        db.session.commit()
        flash('เพิ่มทรัพย์สินสำเร็จ!', 'success')
        return redirect(url_for('assets_list'))

    return render_template('add_asset.html', user=user)

# หน้าแก้ไขทรัพย์สิน
@app.route('/assets/edit/<int:id>', methods=['GET', 'POST'])
def edit_asset(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    asset = Asset.query.get_or_404(id)
    is_admin = session['department'] == 'IT'

    if not is_admin and asset.department != session['department']:
        flash('คุณไม่มีสิทธิ์แก้ไขทรัพย์สินนี้', 'danger')
        return redirect(url_for('assets_list'))

    if request.method == 'POST':
        asset.asset_id = request.form['asset_id']
        asset.asset_type = request.form['asset_type']
        asset.details = request.form['details']
        asset.price = request.form['price']
        asset.status = request.form['status']
        db.session.commit()  # ใช้ db.session แทน assets_db.session
        flash('แก้ไขทรัพย์สินสำเร็จ!', 'success')
        return redirect(url_for('assets_list'))

    return render_template('edit_asset.html', asset=asset, user=user)

# หน้าลบทรัพย์สิน
@app.route('/assets/delete/<int:id>')
def delete_asset(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    is_admin = session['department'] == 'IT'
    if not is_admin:
        flash('คุณไม่มีสิทธิ์ลบทรัพย์สิน', 'danger')
        return redirect(url_for('assets_list'))

    asset = Asset.query.get_or_404(id)
    db.session.delete(asset)  # ใช้ db.session แทน assets_db.session
    db.session.commit()  # ใช้ db.session แทน assets_db.session
    flash('ลบทรัพย์สินสำเร็จ!', 'success')
    return redirect(url_for('assets_list'))

# หน้า Reset Password (เหมือนเดิม)
@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    # ... (โค้ดเดิม) ...
    return render_template('reset_password.html')

# หน้า Logout (เหมือนเดิม)
@app.route('/logout')
def logout():
    # ... (โค้ดเดิม) ...
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)