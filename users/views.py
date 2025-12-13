import os
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename

from users.forms import RegisterForm, LoginForm, ChangePasswordForm, UpdateEmailForm
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from models import User, Post, TaikoRecord, Favorite

users_blueprint = Blueprint('users', __name__, template_folder='templates/user')

from werkzeug.utils import secure_filename
import os

AVATAR_UPLOAD_FOLDER = 'static/uploads/avatar'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@users_blueprint.route('/register', methods=['GET', 'POST'])
def register():
    from app import create_app

    app = create_app()
    # Create signup form object
    form1 = RegisterForm()

    # If request method is POST or form is valid
    if form1.validate_on_submit():
        with app.app_context():
            u1 = User.query.filter_by(email=form1.email.data).first()
        # If this returns a user, then the email already exists in database

        # If email already exists redirect user back to signup page with error message so user can try again
        if u1:
            flash('Email address already exists')
            return render_template('user/register.html', form=form1)

        # Create a new user with the form data
        new_user = User(
            username=form1.username.data,
            email=form1.email.data,
            # dob=form1.dob.data,
            # first_name=form1.first_name.data,
            # last_name=form1.last_name.data,
            password=form1.password.data,
            role='user'
            )

        # Add the new user to the database
        db.session.add(new_user)
        db.session.commit()

        app.logger.info(f"User registered: {form1.email.data}, IP: {request.remote_addr}")
        # Sends user to login page
        return redirect(url_for('users.login'))
    # If request method is GET or form not valid re-render signup page
    return render_template('user/register.html', form=form1)


@users_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    from app import create_app
    app = create_app()

    print("\n[DEBUG] === 登录请求开始 ===")
    print(f"[DEBUG] 请求方法: {request.method}")
    print(f"[DEBUG] 当前用户是否已登录: {current_user.is_authenticated}")

    # Create login form object
    form = LoginForm(request.form)

    print(f"[DEBUG] 表单数据: login={form.login.data}, password={'*' * len(form.password.data) if form.password.data else None}")
    print(f"[DEBUG] 表单验证结果: {form.validate_on_submit()}")
    if form.errors:
        print(f"[DEBUG] 表单错误: {form.errors}")

    if request.method == 'POST' and form.validate_on_submit():
        print("[DEBUG] 表单验证通过，开始查询用户...")

        # 支持用户名或邮箱登录
        user = User.query.filter(
            (User.username == form.login.data) | (User.email == form.login.data)
        ).first()

        if user:
            print(f"[DEBUG] 找到用户: {user.username} (id={user.id}, email={user.email}, is_admin={user.is_admin})")
            password_correct = user.verify_password(form.password.data)
            print(f"[DEBUG] 密码验证结果: {password_correct}")
        else:
            print("[DEBUG] 未找到匹配的用户（用户名或邮箱都不存在）")
            password_correct = False

        if user and password_correct:
            print("[DEBUG] 登录验证成功，开始登录用户")
            login_user(user)

            # Update user login details
            print("[DEBUG] 更新登录信息...")
            user.last_login = user.current_login
            user.current_login = datetime.utcnow()
            user.last_login_ip = user.current_login_ip or request.remote_addr
            user.current_login_ip = request.remote_addr
            user.total_logins += 1
            # user.update_security_fields_on_login(ip_addr=request.remote_addr)

            try:
                db.session.commit()
                print("[DEBUG] 数据库提交成功")
            except Exception as e:
                db.session.rollback()
                print(f"[DEBUG] 数据库提交失败: {e}")

            # Set session variables
            session['logged_in'] = True
            session['user_id'] = user.id
            app.logger.info(f"User logged in: {user.email} (username: {user.username}), IP: {request.remote_addr}")
            flash('You have been logged in.', 'success')
            print("[DEBUG] Flash 消息已发送")

            # 跳转判断
            if user.is_admin_user():
                print("[DEBUG] 用户是管理员，准备跳转到 admin.dashboard")
                return redirect(url_for('admin.dashboard'))
            else:
                print("[DEBUG] 普通用户，准备跳转到 index")
                return redirect(url_for('index'))

        else:
            print("[DEBUG] 登录失败（用户不存在或密码错误）")
            flash('Invalid username/email or password.', 'danger')

    else:
        print("[DEBUG] 未提交 POST 或表单验证失败，渲染登录页面")

    print("[DEBUG] === 登录请求结束，渲染登录模板 ===\n")
    return render_template('user/login.html', form=form)


@users_blueprint.route('/my_account')
def information():
    # Render the account information page for the current user
    return render_template('user/my_account.html', user=current_user)


@users_blueprint.route('/update_password', methods=['GET', 'POST'])
@login_required
def update_password():
    # Create change password form object
    form = ChangePasswordForm()

    # If form is valid
    if form.validate_on_submit():
        user = current_user

        # Verify the current password
        if user.verify_password(form.current_password.data):
            if form.new_password.data != form.current_password.data:

                # Set the new password
                user.set_password(form.new_password.data)
                db.session.commit()
                flash('Your password has been updated.', 'success')
                return redirect(url_for('users.login'))
            else:
                flash('New password cannot be the same as the current password.', 'error')
        else:
            flash('Current password is incorrect.', 'error')
    return render_template('user/update_password.html', form=form)


# users/views.py —— 修改邮箱功能
@users_blueprint.route('/update_email', methods=['GET', 'POST'])
@login_required
def update_email():
    form = UpdateEmailForm()

    if form.validate_on_submit():
        # 检查新邮箱是否已被占用（不能是别人的）
        if User.query.filter_by(email=form.email.data).first():
            flash('This email is already taken', 'danger')
            return render_template('user/update_email.html', form=form)

        # 更新邮箱
        current_user.email = form.email.data
        db.session.commit()

        flash('update succeed, Please login again', 'success')
        logout_user()  # 强制重新登录（推荐做法）
        return redirect(url_for('users.login'))

    # 预填充当前邮箱
    form.email.data = current_user.email
    form.confirm_email.data = current_user.email

    return render_template('user/update_email.html', form=form)
@users_blueprint.route('/logout')
@login_required
def logout():
    from app import create_app
    app = create_app()

    # Log out the user and update the session
    user_info = f"User logged out: {current_user.email}, IP: {request.remote_addr}"
    logout_user()
    session['logged_in'] = False
    app.logger.info(user_info)

    # Redirect to the home page
    return redirect(url_for('index'))

@users_blueprint.route('/favorite/<type>/<int:item_id>')
@login_required
def toggle_favorite(type, item_id):
    if type == 'post':
        item = Post.query.get_or_404(item_id)
    elif type == 'taiko':
        item = TaikoRecord.query.get_or_404(item_id)
    else:
        flash('无效类型', 'danger')
        return redirect(request.referrer or url_for('index'))

    favorite = Favorite.query.filter_by(
        user_id=current_user.id,
        post_id=item_id if type == 'post' else None,
        taiko_id=item_id if type == 'taiko' else None
    ).first()

    if favorite:
        db.session.delete(favorite)
        db.session.commit()
        flash('已取消收藏', 'info')
    else:
        favorite = Favorite(
            user_id=current_user.id,
            post_id=item_id if type == 'post' else None,
            taiko_id=item_id if type == 'taiko' else None
        )
        db.session.add(favorite)
        db.session.commit()
        flash('收藏成功', 'success')

    return redirect(request.referrer or url_for('index'))

# users/views.py —— 添加我的收藏路由
@users_blueprint.route('/my_favorites')
@login_required
def my_favorites():
    # 正确写法：从 Favorite 模型查询，过滤当前用户，按时间倒序
    favorites = Favorite.query.filter_by(user_id=current_user.id)\
                              .order_by(Favorite.created_at.desc())\
                              .all()
    return render_template('user/my_favorites.html', favorites=favorites)

@users_blueprint.route('/my_account', methods=['GET', 'POST'])
@login_required
def my_account():
    if request.method == 'POST':
        # 头像上传（所有用户）
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"{current_user.id}_{int(datetime.utcnow().timestamp())}_{file.filename}")
                file_path = os.path.join(AVATAR_UPLOAD_FOLDER, filename)
                os.makedirs(AVATAR_UPLOAD_FOLDER, exist_ok=True)
                file.save(file_path)
                current_user.avatar = filename
                flash('头像更新成功！', 'success')
            else:
                flash('文件类型不支持或未选择文件', 'danger')

        # 只有管理员能修改 bio、GitHub、Twitter
        if current_user.is_admin_user():
            current_user.bio = request.form.get('bio', current_user.bio)
            current_user.github = request.form.get('github', '').strip()
            current_user.twitter = request.form.get('twitter', '').strip()
            flash('个人资料已更新', 'success')

        db.session.commit()
        return redirect(url_for('users.my_account'))

    # GET 请求：显示页面
    return render_template('user/my_account.html')


# # 头像
#
# @users_blueprint.route('/upload_avatar', methods=['POST'])
# @login_required
# def upload_avatar():
#     if 'avatar' not in request.files:
#         flash('没有选择文件', 'danger')
#         return redirect(url_for('users.my_account'))
#
#     file = request.files['avatar']
#     if file.filename == '':
#         flash('没有选择文件', 'danger')
#         return redirect(url_for('users.my_account'))
#
#     if file and allowed_file(file.filename):
#         # 安全文件名
#         filename = secure_filename(f"{current_user.id}_{file.filename}")
#         file_path = os.path.join(AVATAR_UPLOAD_FOLDER, filename)
#         os.makedirs(AVATAR_UPLOAD_FOLDER, exist_ok=True)
#         file.save(file_path)
#
#         current_user.avatar = filename
#         db.session.commit()
#         flash('头像上传成功！', 'success')
#     else:
#         flash('文件类型不支持', 'danger')
#
#     return redirect(url_for('users.my_account'))