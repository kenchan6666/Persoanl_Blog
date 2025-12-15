# admin/views.py —— 完全复刻你原来的风格
from datetime import datetime, timedelta

from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app import db
from models import User, Post, TaikoRecord, SiteSettings, Comment
import os

import re
import uuid
from flask import current_app

admin_blueprint = Blueprint('admin', __name__, template_folder='templates')

UPLOAD_FOLDER = 'static/uploads/taiko'
POST_UPLOAD_FOLDER = 'static/uploads/post'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp','bmp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_dt_local(s: str):
    # <input type="datetime-local"> 格式: 2025-12-15T13:45
    return datetime.fromisoformat(s) if s else None

def url_to_abs_path(url: str) -> str:
    # url: /static/uploads/post/xxx.png -> 绝对路径
    return os.path.join(current_app.root_path, url.lstrip("/"))

def save_image_file(file, folder_rel: str, url_prefix: str):
    """
    folder_rel: 'static/uploads/post' 这种相对项目根目录的路径
    url_prefix: '/static/uploads/post'
    """
    if not file or file.filename == "":
        return None

    if not allowed_file(file.filename):
        return None

    os.makedirs(os.path.join(current_app.root_path, folder_rel), exist_ok=True)

    filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{uuid.uuid4().hex}_{file.filename}")
    abs_path = os.path.join(current_app.root_path, folder_rel, filename)
    file.save(abs_path)

    return f"{url_prefix}/{filename}"

def remove_image_markdown(content: str, image_url: str) -> str:
    # 删除形如 ![xxx](/static/uploads/post/xxx.png)
    pattern = rf'!\[[^\]]*\]\({re.escape(image_url)}\)'
    content = re.sub(pattern, '', content)
    content = re.sub(r'\n{3,}', '\n\n', content).strip()
    return content

def extract_post_image_urls(content: str):
    return re.findall(r'!\[.*?\]\((/static/uploads/post/[^\)]+)\)', content)

@admin_blueprint.before_request
@login_required
def require_admin():
    if not current_user.is_admin_user():
        flash('需要管理员权限', 'danger')
        return redirect(url_for('index'))
    return None


# admin/views.py —— dashboard 函数
@admin_blueprint.route('/dashboard')
def dashboard():
    stats = {
        'user_count': User.query.count(),
        'post_count': Post.query.count(),
        'taiko_count': TaikoRecord.query.count(),
    }
    # 把置顶文章查询移到这里
    pinned_posts = Post.query.filter_by(is_pinned=True).order_by(Post.updated_at.desc()).limit(5).all()
    return render_template('admin/admin.html', **stats, pinned_posts=pinned_posts)

@admin_blueprint.route('/users')
def view_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

# admin/views.py —— 添加删除用户路由
@admin_blueprint.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if not current_user.is_admin_user():
        flash('权限不足', 'danger')
        return redirect(url_for('admin.view_users'))

    user_to_delete = User.query.get_or_404(user_id)
    if user_to_delete.id == current_user.id:
        flash('不能删除自己', 'danger')
        return redirect(url_for('admin.view_users'))

    db.session.delete(user_to_delete)
    db.session.commit()
    flash(f'用户 {user_to_delete.username} 已删除', 'success')
    return redirect(url_for('admin.view_users'))

@admin_blueprint.route('/logs')
def view_logs():
    log_path = os.path.join(os.getcwd(), 'app.log')
    logs = ["日志文件不存在或无法读取"]
    if os.path.exists(log_path):
        try:
            # 先尝试 utf-8
            with open(log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            logs = lines[-50:][::-1]
        except UnicodeDecodeError:
            try:
                # 如果 utf-8 失败，尝试 gbk（Windows 中文常见）
                with open(log_path, 'r', encoding='gbk') as f:
                    lines = f.readlines()
                logs = lines[-50:][::-1]
            except:
                logs = ["日志文件编码错误，无法显示"]
        except Exception as e:
            logs = [f"读取错误: {str(e)}"]
    return render_template('admin/logs.html', logs=logs)

@admin_blueprint.route('/settings', methods=['GET', 'POST'])
def site_settings():
    settings = SiteSettings.query.first()
    if request.method == 'POST':
        for key, value in request.form.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        db.session.commit()
        flash('网站设置已更新', 'success')
        return redirect(url_for('admin.site_settings'))
    return render_template('admin/settings.html', settings=settings)

# 写post
@admin_blueprint.route('/write_post', methods=['GET', 'POST'])
def write_post():
    if request.method == 'POST':
        title = request.form['title'].strip()
        content = request.form['content']
        category = request.form.get('category', 'TECH')  # 你原来默认是 '技术'，容易不匹配Enum :contentReference[oaicite:7]{index=7}

        created_at = parse_dt_local(request.form.get('created_at'))  # 新增：可自定义日期

        if not title:
            flash('标题不能为空', 'danger')
            return render_template('admin/write_post.html')

        # 多张图片上传（你原逻辑保留）
        uploaded_images = []
        if 'images' in request.files:
            files = request.files.getlist('images')
            for file in files:
                url = save_image_file(file, folder_rel=POST_UPLOAD_FOLDER, url_prefix="/static/uploads/post")
                if url:
                    uploaded_images.append(url)

        if uploaded_images:
            image_md = '\n\n' + '\n'.join(f"![上传图片]({url})" for url in uploaded_images)
            content += image_md

        post = Post(
            title=title,
            content=content,
            category=category,
            author=current_user
        )

        if created_at:
            post.created_at = created_at  # Post 本身就有 created_at 字段 :contentReference[oaicite:8]{index=8}

        db.session.add(post)
        db.session.commit()

        flash('文章发布成功！图片已嵌入', 'success')
        return redirect(url_for('admin.dashboard'))

    return render_template('admin/write_post.html')


# 修改
# @admin_blueprint.route('/edit_article/<int:post_id>', methods=['GET', 'POST'])
# def edit_article(post_id):
#     post = Post.query.get_or_404(post_id)
#     if request.method == 'POST':
#         post.title = request.form['title'].strip()
#         post.content = request.form['content']
#         post.category = request.form['category']
#
#         # 新上传图片追加到内容
#         uploaded_images = []
#         if 'images' in request.files:
#             files = request.files.getlist('images')
#             os.makedirs(POST_UPLOAD_FOLDER, exist_ok=True)
#             for file in files:
#                 if file and file.filename != '' and allowed_file(file.filename):
#                     filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{file.filename}")
#                     file_path = os.path.join(POST_UPLOAD_FOLDER, filename)
#                     file.save(file_path)
#                     uploaded_images.append(f"/static/uploads/post/{filename}")
#
#         if uploaded_images:
#             image_md = '\n\n' + '\n'.join(f"![新上传图片]({url})" for url in uploaded_images)
#             post.content += image_md
#
#         db.session.commit()
#         flash('文章更新成功', 'success')
#         return redirect(url_for('admin.manage_articles'))
#
#     # 提取已上传图片 URL 用于预览
#     import re
#     image_urls = re.findall(r'!\[.*?\]\((/static/uploads/post/[^\)]+)\)', post.content)
#
#     return render_template('admin/edit_article.html', post=post, image_urls=image_urls)

@admin_blueprint.route('/edit_article/<int:post_id>', methods=['GET', 'POST'])
def edit_article(post_id):
    post = Post.query.get_or_404(post_id)

    if request.method == 'POST':
        post.title = request.form['title'].strip()
        post.category = request.form['category']

        # 先拿到用户编辑后的正文
        content = request.form['content']

        # 日期可改（不填就不改）
        created_at = parse_dt_local(request.form.get('created_at'))
        if created_at:
            post.created_at = created_at

        # 旧图列表（由模板 hidden input 传回来）
        existing_urls = request.form.getlist("existing_image_urls")
        delete_indexes = {int(x) for x in request.form.getlist("delete_image_indexes")}

        # 1) 删除 / 2) 替换
        for idx, old_url in enumerate(existing_urls):
            # 删除
            if idx in delete_indexes:
                content = remove_image_markdown(content, old_url)
                abs_path = url_to_abs_path(old_url)
                if os.path.exists(abs_path):
                    os.remove(abs_path)
                continue

            # 替换（replace_0, replace_1...）
            f = request.files.get(f"replace_{idx}")
            if f and f.filename:
                new_url = save_image_file(f, folder_rel=POST_UPLOAD_FOLDER, url_prefix="/static/uploads/post")
                if new_url:
                    # 替换内容里的 URL（只替换一次）
                    content = content.replace(old_url, new_url, 1)
                    # 删除旧文件
                    abs_path = url_to_abs_path(old_url)
                    if os.path.exists(abs_path):
                        os.remove(abs_path)

        # 3) 追加新图（new_images）
        new_urls = []
        for f in request.files.getlist("new_images"):
            url = save_image_file(f, folder_rel=POST_UPLOAD_FOLDER, url_prefix="/static/uploads/post")
            if url:
                new_urls.append(url)

        if new_urls:
            content = content.rstrip() + "\n\n" + "\n".join(f"![新上传图片]({u})" for u in new_urls)

        post.content = content
        post.content_html = None  # 关键：清空缓存HTML :contentReference[oaicite:10]{index=10}

        db.session.commit()
        flash('文章更新成功', 'success')
        return redirect(url_for('admin.manage_articles'))

    image_urls = extract_post_image_urls(post.content)  # 你原来用 regex 提取 :contentReference[oaicite:11]{index=11}
    return render_template('admin/edit_article.html', post=post, image_urls=image_urls)


# admin/views.py —— 编辑文章支持删除图片
# @admin_blueprint.route('/delete_image', methods=['POST'])
# def delete_image():
#     image_url = request.form['image_url']
#     if not image_url.startswith('/static/uploads/post/'):
#         flash('无效的图片路径', 'danger')
#         return redirect(request.referrer)
#
#     # 从数据库文章内容中移除图片 Markdown
#     posts = Post.query.all()
#     updated = False
#     for post in posts:
#         if image_url in post.content:
#             # 移除整行 ![...](url)
#             import re
#             post.content = re.sub(rf'!\\[.*?\\]\\({re.escape(image_url)}\\)', '', post.content)
#             post.content = re.sub(r'\n\n+', '\n\n', post.content).strip()  # 清理空行
#             updated = True
#
#     if updated:
#         db.session.commit()
#         flash('图片已删除', 'success')
#
#     # 删除物理文件
#     file_path = os.path.join('static', image_url.lstrip('/'))
#     if os.path.exists(file_path):
#         os.remove(file_path)
#
#     return redirect(request.referrer or url_for('admin.manage_articles'))


# admin/views.py —— 太鼓战绩上传（支持段位和歌曲）
@admin_blueprint.route('/add_taiko', methods=['GET', 'POST'])
def add_taiko():
    if request.method == 'POST':
        main_category = request.form['main_category']  # DAN / SONG :contentReference[oaicite:15]{index=15}
        name = request.form['name']
        note = request.form.get('note', '')

        played_at = parse_dt_local(request.form.get('played_at')) or datetime.utcnow()

        # 多张截图上传
        screenshot_urls = []
        for f in request.files.getlist('screenshots'):  # 模板要改字段名
            url = save_image_file(f, folder_rel='static/uploads/taiko', url_prefix="/static/uploads/taiko")
            if url:
                screenshot_urls.append(url)

        # 兼容旧字段：screenshot 放第一张（你的 TaikoRecord 只有一个 screenshot 字段） :contentReference[oaicite:16]{index=16}
        screenshot_path = screenshot_urls[0] if screenshot_urls else None

        # 把多图也写进 note 末尾（后续展示页面可用 regex 提取）
        if screenshot_urls:
            note = (note or "").rstrip() + "\n\n" + "\n".join(f"![截图]({u})" for u in screenshot_urls)

        record = TaikoRecord(
            main_category=main_category,
            name=name,
            note=note,
            screenshot=screenshot_path,
            played_at=played_at,
            player=current_user
        )

        if main_category == 'SONG':  # 修正这里
            record.sub_category = request.form['sub_category']
            record.difficulty = request.form['difficulty']
            record.score = int(request.form['score'])
            record.good = int(request.form.get('good', 0))
            record.ok = int(request.form.get('ok', 0))
            record.bad = int(request.form.get('bad', 0))
            record.crown = request.form['crown']

        db.session.add(record)
        db.session.commit()
        flash('太鼓战绩上传成功！', 'success')
        return redirect(url_for('admin.dashboard'))

    return render_template('admin/add_taiko.html')


# admin/views.py —— 置顶管理 + 切换置顶状态
@admin_blueprint.route('/pin_post/<int:post_id>')
def pin_post(post_id):
    post = Post.query.get_or_404(post_id)
    post.is_pinned = not post.is_pinned
    db.session.commit()
    flash(f"文章《{post.title}》已{'置顶' if post.is_pinned else '取消置顶'}", 'success')
    return redirect(url_for('admin.dashboard'))

@admin_blueprint.route('/pinned')
def pinned_posts():
    posts = Post.query.filter_by(is_pinned=True).order_by(Post.updated_at.desc()).all()
    return render_template('admin/pinned.html', posts=posts)

## ==================== 文章管理 + 筛选 ====================
@admin_blueprint.route('/articles')
def manage_articles():
    # 筛选参数
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    category = request.args.get('category')
    search_query = request.args.get('q')

    # 查询基础
    query = Post.query.order_by(Post.created_at.desc())

    # 日期筛选
    if start_date:
        query = query.filter(Post.created_at >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(Post.created_at <= datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))

    # 分类筛选
    if category and category != 'all':
        query = query.filter_by(category=category)

    # 搜索
    if search_query:
        query = query.filter(Post.title.contains(search_query) | Post.content.contains(search_query))

    posts = query.all()
    return render_template('admin/articles.html', posts=posts)


import re
from flask import current_app

import re
from flask import current_app

@admin_blueprint.route('/delete_image', methods=['POST'])
def delete_image():
    post_id = request.form.get('post_id', type=int)
    image_url = (request.form.get('image_url') or '').strip()

    if not post_id:
        flash('缺少 post_id', 'danger')
        return redirect(request.referrer or url_for('admin.manage_articles'))

    if not image_url.startswith('/static/uploads/post/'):
        flash('无效的图片路径', 'danger')
        return redirect(url_for('admin.edit_article', post_id=post_id))

    post = Post.query.get_or_404(post_id)

    # 1) 从 Markdown 内容里移除 ![...](url)
    pattern = rf'!\[[^\]]*\]\({re.escape(image_url)}\)'
    post.content = re.sub(pattern, '', post.content)
    post.content = re.sub(r'\n{3,}', '\n\n', post.content).strip()

    # 2) 清空缓存 HTML（否则前台可能继续显示旧内容）
    post.content_html = None

    db.session.commit()

    # 3) 删除物理文件（用项目根路径拼绝对路径）
    abs_path = os.path.normpath(os.path.join(current_app.root_path, image_url.lstrip('/')))
    uploads_root = os.path.normpath(os.path.join(current_app.root_path, 'static', 'uploads', 'post')) + os.sep
    if abs_path.startswith(uploads_root) and os.path.exists(abs_path):
        os.remove(abs_path)

    flash('图片已删除', 'success')
    return redirect(url_for('admin.edit_article', post_id=post_id))



@admin_blueprint.route('/pin_article/<int:post_id>')
def pin_article(post_id):
    post = Post.query.get_or_404(post_id)
    post.is_pinned = not post.is_pinned
    db.session.commit()
    flash(f"文章已{'置顶' if post.is_pinned else '取消置顶'}", 'success')
    return redirect(url_for('admin.manage_articles'))

@admin_blueprint.route('/delete_article/<int:post_id>', methods=['POST'])
def delete_article(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash('文章已删除', 'success')
    return redirect(url_for('admin.manage_articles'))


# ==================== 文章评论管理 ====================
@admin_blueprint.route('/article_comments/<int:post_id>')
def article_comments(post_id):
    post = Post.query.get_or_404(post_id)
    comments = post.comments.order_by(Comment.created_at.desc()).all()
    return render_template('admin/comments.html', post=post, comments=comments)

@admin_blueprint.route('/delete_comment/<int:comment_id>', methods=['POST'])
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    post_id = comment.post_id
    db.session.delete(comment)
    db.session.commit()
    flash('评论已删除', 'success')
    return redirect(url_for('admin.article_comments', post_id=post_id))

# 注释掉 approve_comment（按你要求保留）
# @admin_blueprint.route('/approve_comment/<int:comment_id>')
# def approve_comment(comment_id):
#     comment = Comment.query.get_or_404(comment_id)
#     comment.is_approved = not comment.is_approved
#     db.session.commit()
#     flash(f"评论已{'批准' if comment.is_approved else '驳回'}", 'success')
#     return redirect(request.referrer or url_for('admin.manage_articles'))
# admin/views.py —— 内容管理（文章 + 太鼓战绩）

@admin_blueprint.route('/contents')
def manage_contents():
    # 获取所有内容，按时间倒序
    posts = Post.query.order_by(Post.created_at.desc()).all()
    records = TaikoRecord.query.order_by(TaikoRecord.played_at.desc()).all()

    # 合并并排序（置顶优先）
    contents = []
    for item in posts + records:
        item_type = 'post' if isinstance(item, Post) else 'record'
        contents.append({
            'id': item.id,
            'type': item_type,
            'title': item.title if item_type == 'post' else item.name,
            'category': item.category.value if item_type == 'post' else item.main_category.value,
            'date': item.created_at if item_type == 'post' else item.played_at,
            'is_pinned': getattr(item, 'is_pinned', False),
            'item': item
        })

    # 按置顶 + 时间排序
    contents.sort(key=lambda x: (not x['is_pinned'], x['date']), reverse=True)

    return render_template('admin/contents.html', contents=contents)


@admin_blueprint.route('/pin_content/<content_type>/<int:content_id>')
def pin_content(content_type, content_id):
    if content_type == 'post':
        item = Post.query.get_or_404(content_id)
    elif content_type == 'record':
        item = TaikoRecord.query.get_or_404(content_id)
    else:
        flash('类型错误', 'danger')
        return redirect(url_for('admin.manage_contents'))

    item.is_pinned = not item.is_pinned
    db.session.commit()
    flash('操作成功', 'success')
    return redirect(url_for('admin.manage_contents'))

@admin_blueprint.route('/delete_content/<content_type>/<int:content_id>', methods=['POST'])
def delete_content(content_type, content_id):
    if content_type == 'post':
        item = Post.query.get_or_404(content_id)
    elif content_type == 'record':
        item = TaikoRecord.query.get_or_404(content_id)
    else:
        flash('类型错误', 'danger')
        return redirect(url_for('admin.manage_contents'))

    db.session.delete(item)
    db.session.commit()
    flash('内容已删除', 'success')
    return redirect(url_for('admin.manage_contents'))

# admin/views.py —— 管理员回复评论
@admin_blueprint.route('/reply_comment/<int:comment_id>', methods=['POST'])
def reply_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    reply_text = request.form['reply'].strip()
    if reply_text:
        comment.reply = reply_text
        comment.replied_at = datetime.utcnow()
        db.session.commit()
        flash('回复成功', 'success')
    else:
        flash('回复内容不能为空', 'danger')
    return redirect(url_for('admin.manage_contents'))