# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy.exc import IntegrityError
import os
from werkzeug.utils import secure_filename
from dotenv import load_dotenv # 1. جديد للامان



load_dotenv() # 2. جديد للامان

app = Flask(__name__)
app.config['SECRET_KEY'] = 'my_secret_key_123456'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ===== اعدادات الايميل =====
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL-PASSWORD') # 3. اتغيرت عشان الامان
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME') # حط الكود الجديد هنا مباشر

mail = Mail(app)
# ===========================

def allowed_file(filename):
    return '.' in filename and filename.split('.')[-1].lower() in ALLOWED_EXTENSIONS

db = SQLAlchemy(app)



login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ========== الموديلات ==========
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(200))
    project_url = db.Column(db.String(200))

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref='activities')
    action = db.Column(db.String(200))
    ip = db.Column(db.String(50))
    date = db.Column(db.DateTime, default=datetime.utcnow)

class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    value = db.Column(db.String(500), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ========== الصفحات ==========
@app.route('/')
def home():
    settings = {s.key: s.value for s in Setting.query.all()}
    projects = Project.query.all()
    skills = [
        {'name': 'Python', 'level': 90},
        {'name': 'Flask', 'level': 85},
        {'name': 'React', 'level': 75},
        {'name': 'Flutter', 'level': 70},
        {'name': 'SQL', 'level': 80}
    ]
    return render_template('index.html', settings=settings, projects=projects, skills=skills)

@app.route('/contact', methods=['POST'])
def contact():
    name = request.form['name']
    email = request.form['email']
    message = request.form['message']

    # 1. احفظ في الداتا بيز الاول
    new_msg = Contact(name=name, email=email, message=message)
    db.session.add(new_msg)
    db.session.commit()

    # 2. الايميل اللي هيوصلك انت
    msg = Message(
        subject=f'📩 رسالة جديدة من {name}',
        sender=app.config['MAIL_DEFAULT_SENDER'],
        recipients=['mahmoud2040758@gmail.com']
    )
    msg.body = f"""
لديك رسالة جديدة من موقعك الشخصي

**بيانات المرسل:**
الاسم: {name}
البريد: {email}

**الرسالة:**
{message}

---
تم الارسال بتاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""

    # 3. رد تلقائي للعميل
    reply = Message(
        subject='شكرا على تواصلك معي',
        sender=app.config['MAIL_DEFAULT_SENDER'],
        recipients=[email]
    )
    reply.body = f"""مرحبا {name},

شكرا على تواصلك معي عبر موقعي الشخصي.
لقد استلمت رسالتك وسأقوم بالرد عليك في اقرب وقت ممكن.

تحياتي
محمود
"""

    # 4. حط try هنا عشان لو الايميل فشل
    try:
        mail.send(msg)
        mail.send(reply)
        flash('تم ارسال رسالتك بنجاح ✅')
    except Exception as e:
        print("خطأ في الايميل:", e) # هيطبع الخطأ في التيرمنال
        flash('تم حفظ رسالتك بس الايميل فشل ⚠️')

    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        is_first_user = User.query.count() == 0
        new_user = User(name=name, email=email, password=password, is_admin=is_first_user)
        try:
            db.session.add(new_user)
            db.session.commit()
            flash("تم التسجيل بنجاح")
            return redirect(url_for('login'))
        except IntegrityError:
            db.session.rollback()
            flash("هذا الايميل مستخدم من قبل")
            return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            act = Activity(user_id=user.id, action='تسجيل دخول', ip=request.remote_addr)
            db.session.add(act)
            db.session.commit()
            return redirect(url_for('admin'))
        flash('الإيميل أو كلمة السر غلط')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/admin')
@login_required
def admin():
    if not current_user.is_admin:
        flash("ممنوع. لست ادمن")
        return redirect(url_for('home'))

    projects = Project.query.all()
    messages = Contact.query.order_by(Contact.date.desc()).all() # 4. تم التصحيح هنا
    return render_template('admin.html', projects=projects, messages=messages)

@app.route('/admin/settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    if not current_user.is_admin:
        return "403 ممنوع", 403
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

@app.route('/add_project', methods=['GET', 'POST'])
@login_required
def new_project():
    if not current_user.is_admin: return "403 ممنوع", 403
    if request.method == 'POST':
        file = request.files['image']
        filename = ''
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        new_project = Project(
            title=request.form['title'],
            description=request.form['description'],
            image_url='/static/uploads/' + filename,
            project_url=request.form['project_url']
        )
        db.session.add(new_project)
        db.session.commit()
        flash('تمت اضافة المشروع')
        return redirect(url_for('admin'))
    return render_template('add_project.html')

@app.route('/edit_project/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_project(id):
    if not current_user.is_admin: return "403 ممنوع", 403
    project = Project.query.get_or_404(id)
    if request.method == 'POST':
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            project.image_url = '/static/uploads/' + filename
        project.title = request.form['title']
        project.description = request.form['description']
        project.project_url = request.form['project_url']
        db.session.commit()
        return redirect(url_for('admin'))
    return render_template('edit_project.html', project=project)

@app.route('/delete_project/<int:id>')
@login_required
def delete_project(id):
    if not current_user.is_admin: return "403 ممنوع", 403
    project = Project.query.get_or_404(id)
    db.session.delete(project)
    db.session.commit()
    return redirect(url_for('admin'))

with app.app_context():
    db.create_all()   

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if Setting.query.count() == 0:
            db.session.add_all([
                Setting(key='name', value='Mahmoud El kowry'),
                Setting(key='title', value='مطور تطبيقات ويب بـ Flask & React'),
                Setting(key='bio', value='أبني حلول تقنية تساعد عملك ينمو ويتحقق في أقل وقت ممكن'),
                Setting(key='about', value='أنا مطور شغوف ببناء تطبيقات ويب ومواقع تساعد الشركات. عندي خبرة في Flask و React و Flutter'),
            ])
            db.session.commit()
    app.run(debug=True, host='0.0.0.0', port=5000)
