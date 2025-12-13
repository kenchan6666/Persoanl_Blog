# views.py —— archive_blueprint 更新
from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from app import db
from models import User, Post, TaikoRecord, SiteSettings
from sqlalchemy import case

archive_blueprint = Blueprint('archive', __name__, template_folder='templates/archive')


@archive_blueprint.route('/archive')
def archive():
    category = request.args.get('category')  # ?category=技术

    # 使用 case 语句实现置顶优先排序
    posts = Post.query.order_by(
        case(
            (Post.is_pinned == True, 0),  # 置顶优先级 0
            else_=1  # 非置顶优先级 1
        ),
        Post.updated_at.desc(),  # 置顶按更新时间排序
        Post.created_at.desc()  # 非置顶按创建时间排序
    )

    records = TaikoRecord.query.order_by(TaikoRecord.played_at.desc())

    if category:
        posts = posts.filter_by(category=category)

    return render_template('archive/archive.html', posts=posts.all(), records=records.all(), current_category=category)

# # 在查询时用 case 排序
# from sqlalchemy import case
#
# posts = Post.query.order_by(
#     case(
#         (Post.is_pinned == True, 0),
#         else_=1
#     ),
#     Post.updated_at.desc(),
#     Post.created_at.desc()
# ).all()