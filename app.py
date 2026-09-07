import os
import secrets
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# --- الحماية: SECRET_KEY قوي ومخفي ---
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') or secrets.token_hex(32)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "لازم تسجل دخول أول"

# --- الموديلات ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500))
    project_url = db.Column(db.String(500))

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=db.func.now())

class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=False)

class Experience(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(200))
    year = db.Column(db.String(50))
    description = db.Column(db.Text)

class Education(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    degree = db.Column(db.String(200), nullable=False)
    university = db.Column(db.String(200))
    year = db.Column(db.String(50))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("ماعندك صلاحية")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# --- الصفحات الرئيسية ---
@app.route('/')
def home():
    settings = {s.key: s.value for s in Setting.query.all()}
    projects = Project.query.all()
    experiences = Experience.query.order_by(Experience.id.desc()).all()
    educations = Education.query.order_by(Education.id.desc()).all()
    skills = [
        {'name': 'Python', 'level': 90},
        {'name': 'Flask', 'level': 85},
        {'name': 'React', 'level': 75},
        {'name': 'Flutter', 'level': 70},
        {'name': 'SQL', 'level': 80}
    ]
    return render_template('index.html', settings=settings, projects=projects, skills=skills, experiences=experiences, educations=educations)

@app.route('/contact', methods=['POST'])
def contact():
    new_msg = Contact(
        name=request.form['name'],
        email=request.form['email'],
        message=request.form['message']
    )
    db.session.add(new_msg)
    db.session.commit()
    flash("تم ارسال رسالتك")
    return redirect(url_for('home') + '#contact')

# --- تسجيل / دخول ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        if not name or not email or not password:
            flash("املأ كل الحقول")
            return redirect(url_for('register'))
        hashed = generate_password_hash(password)
        is_first = User.query.count() == 0
        new_user = User(name=name, email=email, password=hashed, is_admin=is_first)
        try:
            db.session.add(new_user)
            db.session.commit()
            flash("تم التسجيل - سجل دخول الآن")
            return redirect(url_for('login'))
        except IntegrityError:
            db.session.rollback()
            flash("هذا الايميل مسجل من قبل")
            return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('admin') if user.is_admin else url_for('home'))
        else:
            flash("الايميل او الباسوورد غلط")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

# --- لوحة التحكم ---
@app.route('/admin')
@admin_required
def admin():
    projects = Project.query.all()
    messages = Contact.query.order_by(Contact.date.desc()).all()
    users_count = User.query.count()
    users = User.query.order_by(User.id.desc()).all()
    return render_template('admin.html', projects=projects, messages=messages, users_count=users_count, users=users)

@app.route('/admin/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    if request.method == 'POST':
        for key in ['name', 'title', 'bio', 'about']:
            setting = Setting.query.filter_by(key=key).first()
            if setting:
                setting.value = request.form[key]
        db.session.commit()
        flash('تم حفظ الاعدادات')
        return redirect(url_for('admin_settings'))
    settings = {s.key: s.value for s in Setting.query.all()}
    return render_template('admin_settings.html', settings=settings)

@app.route('/admin/experience', methods=['GET','POST'])
@admin_required
def admin_experience():
    if request.method == 'POST':
        exp = Experience(title=request.form['title'], company=request.form['company'], year=request.form['year'], description=request.form['description'])
        db.session.add(exp)
        db.session.commit()
        return redirect(url_for('admin_experience'))
    experiences = Experience.query.all()
    return render_template('admin_experience.html', experiences=experiences)

@app.route('/delete_exp/<int:id>')
@admin_required
def delete_exp(id):
    db.session.delete(Experience.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('admin_experience'))

@app.route('/admin/education', methods=['GET','POST'])
@admin_required
def admin_education():
    if request.method == 'POST':
        edu = Education(degree=request.form['degree'], university=request.form['university'], year=request.form['year'])
        db.session.add(edu)
        db.session.commit()
        return redirect(url_for('admin_education'))
    educations = Education.query.all()
    return render_template('admin_education.html', educations=educations)

@app.route('/delete_edu/<int:id>')
@admin_required
def delete_edu(id):
    db.session.delete(Education.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('admin_education'))

@app.route('/add_project', methods=['GET','POST'])
@admin_required
def add_project():
    if request.method == 'POST':
        p = Project(title=request.form['title'], description=request.form['description'], image_url=request.form['image_url'], project_url=request.form['project_url'])
        db.session.add(p)
        db.session.commit()
        return redirect(url_for('admin'))
    return render_template('add_project.html')

@app.route('/delete_project/<int:id>')
@admin_required
def delete_project(id):
    db.session.delete(Project.query.get_or_404(id))
    db.session.commit()
    return redirect(url_for('admin'))

# --- انشاء القاعدة اول مرة ---
with app.app_context():
    db.create_all()
    defaults = {
        'name': 'Mahmoud El kowry',
        'title': 'مطور تطبيقات ويب بـ Flask & React',
        'bio': 'أبني حلول تقنية تساعد عملك ينمو',
        'about': 'أنا مطور شغوف ببناء تطبيقات ويب...'
    }
    for k, v in defaults.items():
        if not Setting.query.filter_by(key=k).first():
            db.session.add(Setting(key=k, value=v))
    db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
