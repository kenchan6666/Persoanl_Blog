# app.py
import datetime
from datetime import datetime
import os
from logging.handlers import RotatingFileHandler
import logging
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, current_user, login_required
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from markupsafe import Markup
import markdown as md
from forms import CommentForm  # 新建 forms.py 加 CommentForm

from extensions import db  # Import db from extensions.py

# from models import db, User, Post, TaikoRecord
# from users.views import auth_bp  # 你的登录蓝图
# from blog.views import blog_bp  # 你的博客蓝图
# from blueprints.taiko import taiko_bp  # 以后加


# db = SQLAlchemy()
login_manager = LoginManager()

# today = datetime.date.today()

def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')


    # --------login_manager--------
    login_manager.init_app(app)
    login_manager.login_view = 'users.login'  # 你的登录路由\
    # -----------------------------


    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///blog.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


    # ----------logger------------
    handler = RotatingFileHandler('app.log', maxBytes=500000, backupCount=10)
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    # ----------------------------

    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
    app.config['ENCRYPTION_KEY'] = os.getenv('ENCRYPTION_KEY')
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['RECAPTCHA_PUBLIC_KEY'] = os.getenv('RECAPTCHA_PUBLIC_KEY')
    app.config['RECAPTCHA_PRIVATE_KEY'] = os.getenv('RECAPTCHA_PRIVATE_KEY')
    app.config['SQLALCHEMY_ECHO'] = True
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


    # Initialize database
    # db = SQLAlchemy(app)
    db.init_app(app)

    with app.app_context():
        db.create_all()

    @login_manager.user_loader
    def load_user(user_id):
        # -------------------------------
        from models import User
        # -------------------------------
        return User.query.get(int(user_id))

    # --------------------------
    from users.views import users_blueprint
    # from blog.views import blog_blueprint
    from admin.views import admin_blueprint
    from archive.views import archive_blueprint
    # --------------------------

    # -----------注册蓝图---------
    app.register_blueprint(users_blueprint, url_prefix='/users')
    # app.register_blueprint(blog_blueprint, url_prefix='/blog')
    app.register_blueprint(admin_blueprint, url_prefix='/admin')
    app.register_blueprint(archive_blueprint, url_prefix='/archive')
    # app.register_blueprint(taiko_bp, url_prefix='/taiko')

    # 注册 markdown 过滤器
    @app.template_filter('markdown')
    def markdown_filter(text):
        if not text:
            return ''
        # 安全渲染 Markdown
        html = md.markdown(text, extensions=['fenced_code', 'tables', 'nl2br', 'codehilite','toc','extra'])
        return Markup(html)

    # ==================== 全局上下文处理器（base.html 核心）===================
    # app.py 全局上下文（保持不变或简化）
    @app.context_processor
    def inject_global_vars():
        from models import Post, TaikoRecord, SiteSettings
        settings = SiteSettings.query.first() or SiteSettings()
        return {
            'site_title': settings.site_title,
            'site_subtitle': settings.site_subtitle,
            'site_description': settings.site_description,
            'site_motto': settings.site_motto,
            'footer_text': settings.footer_text,
            'current_year': datetime.now().year,
            'latest_posts': Post.query.order_by(Post.created_at.desc()).limit(6).all(),
            'recent_taiko': TaikoRecord.query.order_by(TaikoRecord.played_at.desc()).limit(10).all(),
        }

    # ==================== 主页路由（个人介绍 + 太鼓成绩）===================
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            user = current_user
        else:
            # 未登录也显示公开信息（以后可以加个默认介绍）
            user = None
        return render_template('index.html', user=user)

    # @app.route('/index')
    # def index():
    #     if current_user.is_authenticated:
    #         user = current_user
    #     else:
    #         # 未登录也显示公开信息（以后可以加个默认介绍）
    #         user = None
    #     return render_template('index.html', user=user)

    # ==================== 其他基础页面路由 ====================
    @app.route('/about')
    def about():
        return render_template('about.html')
    # app.py —— 太鼓专页
    @app.route('/taiko')
    def taiko_page():

        from models import TaikoRecord
        # 筛选参数
        main_cat = request.args.get('main_category')
        sub_cat = request.args.get('sub_category')
        difficulty = request.args.get('difficulty')
        crown = request.args.get('crown')

        records = TaikoRecord.query.order_by(TaikoRecord.played_at.desc())

        if main_cat:
            records = records.filter_by(main_category=main_cat)
        if sub_cat:
            records = records.filter_by(sub_category=sub_cat)
        if difficulty:
            records = records.filter_by(difficulty=difficulty)
        if crown:
            records = records.filter_by(crown=crown)

        return render_template('taiko.html', records=records.all())


    # app.py —— 太鼓战绩详情页
    @app.route('/taiko/<int:record_id>')
    def taiko_detail(record_id):

        from models import TaikoRecord

        record = TaikoRecord.query.get_or_404(record_id)
        return render_template('taiko_detail.html', record=record)

    # app.py —— 文章详情页（简单版）
    # @app.route('/post/<int:post_id>')
    # def post_detail(post_id):
    #
    #     from models import Post
    #
    #     post = Post.query.get_or_404(post_id)
    #     # 可选：浏览量 +1
    #     post.view_count += 1
    #     db.session.commit()
    #     return render_template('archive/post_detail.html', post=post)

    @app.route('/search')
    def search():

        from models import Comment, Post

        query = request.args.get('q', '')
        category = request.args.get('category')

        posts = Post.query
        if query:
            posts = posts.filter(Post.title.contains(query) | Post.content.contains(query))
        if category:
            posts = posts.filter_by(category=category)
        posts = posts.order_by(Post.created_at.desc()).all()

        return render_template('archive/archive.html', posts=posts, records=[], query=query, current_category=category)

    @app.route('/post/<int:post_id>', methods=['GET', 'POST'])
    def post_detail(post_id):

        from models import Comment, Post

        post = Post.query.get_or_404(post_id)
        post.view_count += 1
        db.session.commit()

        form = CommentForm()
        if form.validate_on_submit() and current_user.is_authenticated:
            comment = Comment(
                content=form.content.data,
                author=current_user,
                post=post
            )
            db.session.add(comment)
            db.session.commit()
            flash('评论发表成功！', 'success')
            return redirect(url_for('post_detail', post_id=post_id))

        # 在这里排序评论
        comments = post.comments.order_by(Comment.created_at.desc()).all()

        return render_template('archive/post_detail.html', post=post, comment_form=form, comments=comments)



    # 管理员后台快捷入口
    # @app.route('/dashboard')
    # @login_required
    # def base():
    #     if not current_user.is_admin_user():
    #         return redirect(url_for('index'))
    #     return render_template('admin/base.html')
    #
    # with app.app_context():
    #     db.create_all()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)