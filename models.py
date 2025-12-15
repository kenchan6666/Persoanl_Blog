# models.py —— 完全按照你原来的顶级代码风格重写（2025 终极版）
from app import db
from flask_login import UserMixin
from datetime import datetime
import enum
from werkzeug.security import generate_password_hash, check_password_hash
import markdown
from typing import List, Optional


# ====================== 1. 用户系统（完整版）======================
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # “个人设置”
    avatar = db.Column(db.String(200), default='/static/images/avatar/default.png')
    bio = db.Column(db.Text, default='这个家伙很懒，什么都没写。')
    github = db.Column(db.String(200))
    twitter = db.Column(db.String(200))

    # 权限与日志
    is_admin = db.Column(db.Boolean, default=False)

    last_login = db.Column(db.DateTime)  # 上次登录时间
    current_login = db.Column(db.DateTime)  # 本次登录时间
    last_login_ip = db.Column(db.String(45))  # 上次登录 IP
    current_login_ip = db.Column(db.String(45))  # 本次登录 IP
    total_logins = db.Column(db.Integer, default=0)  # 总登录次数

    # 关系
    posts = db.relationship('Post', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    taiko_records = db.relationship('TaikoRecord', backref='player', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')

    def __init__(self, username: str, email: str, password: str, **kwargs):
        self.username = username.strip()
        self.email = email.lower().strip()
        self.set_password(password)
        self.is_admin = kwargs.get('is_admin', False)
        self.github = kwargs.get('github', '')
        self.twitter = kwargs.get('twitter', '')

    # ------------------- 密码相关 -------------------
    def set_password(self, password: str) -> None:
        """加密存储密码"""
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password: str) -> bool:
        """验证密码"""
        return check_password_hash(self.password_hash, password)

    # ------------------- 权限相关 -------------------
    def make_admin(self) -> None:
        """将用户设为管理员"""
        self.is_admin = True
        db.session.commit()

    def is_admin_user(self) -> bool:
        """是否为管理员"""
        return self.is_admin

    # ------------------- 文章相关 -------------------
    def get_published_posts(self, category: str = None) -> List['Post']:
        """获取用户已发布的文章（可按分类过滤）"""
        query = self.posts.filter_by(is_published=True).order_by(Post.created_at.desc())
        if category:
            query = query.filter_by(category=category)
        return query.all()

    def get_post_count(self) -> int:
        """统计用户文章总数"""
        return self.posts.count()

    # ------------------- 太鼓相关 -------------------
    def get_best_records(self, limit: int = 5) -> List['TaikoRecord']:
        """获取用户最高分的几首曲目"""
        return self.taiko_records.order_by(TaikoRecord.score.desc()).limit(limit).all()

    def get_full_combo_count(self) -> int:
        """统计 FC/AP 次数"""
        return self.taiko_records.filter(TaikoRecord.crown.in_(['金满连', '虹满连'])).count()

    def __repr__(self):
        return f'<User {self.username}>'

    def __str__(self):
        return self.username


class Favorite(db.Model):
    __tablename__ = 'favorite'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=True)
    taiko_id = db.Column(db.Integer, db.ForeignKey('taiko_record.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='favorites')
    post = db.relationship('Post')
    taiko = db.relationship('TaikoRecord')



# ====================== 2. 文章分类枚举 ======================
class Category(enum.Enum):
    TECH = "TECH"
    TAIKO = "TAIKO"
    LIFE = "LIFE"
    # TAIKO_ABOUT = "TAIKO_ABOUT"

    @property
    def display_name(self):
        """用于模板显示中文"""
        return {
            "TECH": "技术",
            "TAIKO": "太鼓达人",
            "LIFE": "生活"
            # "TAIKO_ABOUT": "太鼓相关"
        }[self.value]

    @classmethod
    def choices(cls):
        return [(choice.name, choice.value) for choice in cls]

    # def __str__(self):
    #     return self.value
    #
    # @property
    # def display_name(self):
    #     """模板里显示中文"""
    #     return {
    #         'TECH': '技术',
    #         'TAIKO': '太鼓达人',
    #         'LIFE': '生活'
    #     }[self.value]


# ====================== 3. 文章系统（完整版）======================
class Post(db.Model):
    __tablename__ = 'post'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)           # Markdown 原文
    content_html = db.Column(db.Text)                      # 渲染后 HTML（缓存）
    summary = db.Column(db.Text)                           # 摘要（可选）
    category = db.Column(db.Enum(Category), default=Category.TECH)
    tags = db.Column(db.String(200))                       # 逗号分隔
    cover_image = db.Column(db.String(200))
    is_published = db.Column(db.Boolean, default=True)
    view_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    is_pinned = db.Column(db.Boolean, default=False, index=True)  # 置顶

    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # 关系
    comments = db.relationship('Comment', backref='post', lazy='dynamic', cascade='all, delete-orphan')

    # models.py —— Post 类 __init__ 方法更新
    def __init__(self, title: str, content: str, author: User, **kwargs):
        self.title = title.strip()
        self.content = content
        self.author = author
        self.slug = kwargs.get('slug') or self.generate_slug(title)
        self.category = kwargs.get('category', Category.TECH)
        self.tags = kwargs.get('tags', '')
        self.summary = kwargs.get('summary')
        self.cover_image = kwargs.get('cover_image')
        self.is_published = kwargs.get('is_published', True)
        self.is_pinned = kwargs.get('is_pinned', False)  # 新增置顶字段，默认 False

    def generate_slug(self, title: str) -> str:
        """简单生成 slug（实际可用 flask-slugify 增强）"""
        import re
        slug = re.sub(r'[^\w\s-]', '', title.lower())
        slug = re.sub(r'[-\s]+', '-', slug).strip('-_')
        return f"{slug}-{int(datetime.utcnow().timestamp())}"

    def render_content(self) -> str:
        """将 Markdown 渲染为 HTML（带代码高亮）"""
        if not self.content_html:
            self.content_html = markdown.markdown(
                self.content,
                extensions=['fenced_code', 'tables', 'toc', 'codehilite', 'nl2br']
            )
            db.session.commit()
        return self.content_html

    def add_view(self) -> None:
        """增加浏览量"""
        self.view_count += 1
        db.session.commit()

    def get_comment_count(self) -> int:
        """评论数"""
        return self.comments.count()

    def get_tags_list(self) -> List[str]:
        """返回标签列表"""
        return [tag.strip() for tag in self.tags.split(',') if tag.strip()] if self.tags else []

    def __repr__(self):
        return f'<Post {self.title}>'

    def __str__(self):
        return self.title

    images = db.relationship(
        "PostImage",
        backref="post",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )


class PostImage(db.Model):
    __tablename__ = "post_image"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False, index=True)
    url = db.Column(db.String(300), nullable=False)  # /static/uploads/...
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ====================== 4. 太鼓达人成绩（完整版）======================
from enum import Enum
from datetime import datetime

class TaikoMainCategory(enum.Enum):
    DAN = "DAN"
    SONG = "SONG"

class TaikoSubCategory(enum.Enum):
    BRUSH_SCORE = "BRUSH_SCORE"
    FULL_COMBO = "FULL_COMBO"
    GOOD_OK = "GOOD_OK"

class CrownType(enum.Enum):
    CLEAR = "CLEAR"
    SILVER_FC = "SILVER_FC"
    GOLD_FC = "GOLD_FC"
    RAINBOW_FC = "RAINBOW_FC"


class TaikoRecordImage(db.Model):
    __tablename__ = "taiko_record_image"
    id = db.Column(db.Integer, primary_key=True)
    taiko_record_id = db.Column(db.Integer, db.ForeignKey("taiko_record.id"), nullable=False, index=True)
    url = db.Column(db.String(300), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TaikoRecord(db.Model):
    __tablename__ = 'taiko_record'

    id = db.Column(db.Integer, primary_key=True)

    # 主类别（必填）
    main_category = db.Column(db.Enum(TaikoMainCategory), nullable=False)

    # 子类别（只有歌曲需要）
    sub_category = db.Column(db.Enum(TaikoSubCategory), nullable=True)

    # 通用字段（段位和歌曲都需要）
    name = db.Column(db.String(150), nullable=False)          # 段位名 或 歌曲名
    screenshot = db.Column(db.String(200))                    # 截图路径（可选）
    note = db.Column(db.Text)                                 # 说明（可选）
    played_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 歌曲专属字段（段位时为 NULL）
    difficulty = db.Column(db.String(20))                     # 鬼 / 裏鬼
    score = db.Column(db.Integer)                             # 分数
    good = db.Column(db.Integer, default=0)
    ok = db.Column(db.Integer, default=0)
    bad = db.Column(db.Integer, default=0)
    crown = db.Column(db.Enum(CrownType), default=CrownType.CLEAR)

    player_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # player = db.relationship('User', backref='taiko_records')

    # ==================== __init__ 方法（已恢复并优化） ====================
    def __init__(self, main_category: str, name: str, player: User, **kwargs):
        self.main_category = TaikoMainCategory(main_category)
        self.name = name.strip()
        self.player = player

        # 通用字段
        self.screenshot = kwargs.get('screenshot')
        self.note = kwargs.get('note', '')
        self.played_at = kwargs.get('played_at', datetime.utcnow())

        # 只有歌曲才有这些字段
        if self.main_category == TaikoMainCategory.SONG:
            sub_cat_str = kwargs.get('sub_category')
            if sub_cat_str:
                self.sub_category = TaikoSubCategory(sub_cat_str)
            else:
                self.sub_category = TaikoSubCategory.BRUSH_SCORE  # 默认刷分（用中文）

            self.difficulty = kwargs.get('difficulty')
            self.score = kwargs.get('score')
            self.good = kwargs.get('good', 0)
            self.ok = kwargs.get('ok', 0)
            self.bad = kwargs.get('bad', 0)
            crown_str = kwargs.get('crown')
            if crown_str:
                self.crown = CrownType(crown_str)
            else:
                self.crown = CrownType.CLEAR
        else:
            # 段位不需要这些字段
            self.sub_category = None
            self.difficulty = None
            self.score = None
            self.good = 0
            self.ok = 0
            self.bad = 0
            self.crown = CrownType.CLEAR

    # ==================== 辅助方法 ====================
    def is_full_combo(self) -> bool:
        if self.main_category != TaikoMainCategory.SONG:
            return False
        total_notes = self.good + self.ok + self.bad
        return self.bad == 0 and total_notes > 0

    def get_accuracy(self) -> float:
        if self.main_category != TaikoMainCategory.SONG or self.score is None:
            return 0.0
        total = self.good + self.ok + self.bad
        if total == 0:
            return 0.0
        return round((self.good + self.ok * 0.5) / total * 100, 2)

    def __repr__(self):
        return f'<Taiko {self.main_category.value} - {self.name}>'

    def __str__(self):
        if self.main_category == TaikoMainCategory.DAN:
            return f"段位：{self.name}"
        else:
            crown_str = self.crown.value if self.crown else "未知"
            return f"{self.name} [{self.difficulty}] - {self.score:,} ({crown_str})"

    images = db.relationship(
        "TaikoRecordImage",
        backref="taiko_record",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )


# ====================== 5. 评论系统（完整版）======================
class Comment(db.Model):
    __tablename__ = 'comment'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_approved = db.Column(db.Boolean, default=True)

    # 新增：管理员回复
    reply = db.Column(db.Text)  # 管理员回复内容
    replied_at = db.Column(db.DateTime)  # 回复时间

    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

    def __init__(self, content: str, author: User, post: Post):
        self.content = content.strip()
        self.author = author
        self.post = post

    def __repr__(self):
        return f'<Comment by {self.author.username} on Post {self.post_id}>'

# ====================== 6. 网站全局设置（新加，管理员可修改）======================
class SiteSettings(db.Model):
    __tablename__ = 'site_settings'

    id = db.Column(db.Integer, primary_key=True)
    site_title = db.Column(db.String(100), default='Yat Nam')
    site_subtitle = db.Column(db.String(200), default='Taiko and coding')
    site_description = db.Column(db.Text, default='一个后端开发者，同时也是太鼓达人段位挑战者。当前目标：八段')
    site_motto = db.Column(db.Text, default='Code × Taiko')
    footer_text = db.Column(db.String(200), default='Powered by Flask & pure passion')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, **kwargs):
        self.site_title = kwargs.get('site_title', 'Yat Nam')
        self.site_subtitle = kwargs.get('site_subtitle', 'Taiko and coding')
        self.site_description = kwargs.get('site_description', '一个后端开发者，同时也是太鼓达人段位挑战者。当前目标：八段')
        self.site_motto = kwargs.get('site_motto', 'Code × Taiko')
        self.footer_text = kwargs.get('footer_text', 'Powered by Flask & pure passion')

    def __repr__(self):
        return f'<SiteSettings {self.site_title}>'

# ====================== init_db 函数放最下面 ======================
# init_db.py —— 完整初始化脚本（推荐独立文件）

# def init_db():
#     from app import create_app, db
#
#     app = create_app()
#
#     with app.app_context():
#         print("正在重建数据库...")
#         db.drop_all()
#         db.create_all()
#         print("所有表创建成功！")
#
#         # 1. 创建管理员账号
#         if not User.query.first():
#             admin = User(
#                 username='yatnam',
#                 email='ynchanhk@gmail.com',
#                 password='12345',  # 会自动哈希
#                 is_admin=True
#             )
#             admin.bio = 'Code by day, Taiko by night.\n当前目标：全曲虹满连'
#             admin.github = 'https://github.com/yourname'  # 可替换成你的真实链接
#             admin.twitter = 'https://twitter.com/yourname'
#             db.session.add(admin)
#             db.session.commit()
#             print(f"管理员创建成功！用户名: {admin.username} 邮箱: {admin.email}")
#
#         # 2. 初始化网站设置
#         if not SiteSettings.query.first():
#             settings = SiteSettings(
#                 site_title='YAT NAM',
#                 site_subtitle='Code by day, Taiko by night',
#                 site_description='一个用 Python 写后端的开发者，同时也是太鼓达人段位挑战者。<br>当前目标：全曲虹满连',
#                 site_motto='Code × Taiko',
#                 footer_text='Powered by Flask • Built with passion and full combos'
#             )
#             db.session.add(settings)
#             db.session.commit()
#             print("网站全局设置已初始化")
#
#         # 3. 初始化示例文章（只有没有文章时才添加）
#         if Post.query.count() == 0:
#             example_post = Post(
#                 title='欢迎来到我的博客',
#                 content='# 欢迎！\n\n这是我的第一篇博客文章。\n\n这里会记录我的编程心得、Flask 项目经验，以及太鼓达人的挑战历程。\n\n希望你也能在这里找到共鸣～',
#                 author=User.query.first(),
#                 category=Category.LIFE
#             )
#             db.session.add(example_post)
#             db.session.commit()
#             print("添加示例文章：《欢迎来到我的博客》")
#
#         # 4. 初始化示例太鼓战绩（只有没有战绩时才添加）
#         # 4. 初始化示例太鼓战绩
#         if TaikoRecord.query.count() == 0:
#             from models import CrownType, SubCategory  # 导入 SubCategory
#             example_record = TaikoRecord(
#                 song_name='2000',
#                 difficulty='裏鬼',
#                 score=1000000,
#                 max_combo=1000,
#                 good=900,
#                 ok=100,
#                 bad=0,
#                 crown=CrownType.RAINBOW_FC,
#                 sub_category=SubCategory.FULL_COMBO,  # ← 必须加上！选一个子类别
#                 note='人生第一虹！激动到手抖',
#                 player=User.query.first()
#             )
#             db.session.add(example_record)
#             db.session.commit()
#             print("添加示例太鼓战绩：2000 裏鬼 虹满连")
#
#         print("\n数据库初始化完成！")
#         print("现在运行命令启动网站：")
#         print("    python app.py")
#         print("\n登录账号：")
#         print("    用户名: yatnam")
#         print("    邮箱: ynchanhk@gmail.com")
#         print("    密码: 12345")
#         print("\n后台地址：/admin/dashboard")