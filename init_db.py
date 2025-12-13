# init_db.py —— 超级完整初始化脚本（管理员 + 普通用户 + 网站设置 + 大量文章 + 太鼓战绩）

from app import create_app, db
from models import (
    User, SiteSettings, Post, TaikoRecord,
    Category, TaikoMainCategory, TaikoSubCategory, CrownType
)
from datetime import datetime, timedelta
import random

app = create_app()

with app.app_context():
    print("\n[INIT] 开始重建数据库...")
    db.drop_all()
    db.create_all()
    print("[INIT] 所有表创建成功！\n")

    # ====================== 1. 创建管理员和普通用户 ======================
    print("[INIT] 创建用户...")
    users = []

    # 管理员（你）
    admin = User(
        username='yatnam',
        email='ynchanhk@gmail.com',
        password='12345',
        is_admin=True
    )
    admin.bio = 'Code by day, Taiko by night.\n当前目标：全曲虹满连'
    admin.github = 'https://github.com/yourname'  # 替换成你的真实链接
    admin.twitter = 'https://twitter.com/yourname'
    db.session.add(admin)
    users.append(admin)

    # 普通用户（示例）
    normal_users = [
        ("alice", "alice@example.com", "alice123"),
        ("bob", "bob@example.com", "bob123"),
        ("charlie", "charlie@example.com", "charlie123"),
        ("diana", "diana@example.com", "diana123"),
        ("eve", "eve@example.com", "eve123"),
    ]

    for username, email, pwd in normal_users:
        user = User(
            username=username,
            email=email,
            password=pwd
        )
        user.bio = random.choice([
            f"{username} 喜欢编程和太鼓达人",
            f"Flask 爱好者，{username} 在路上",
            f"正在挑战虹满连，{username} 加油！",
            f"{username} 的博客之旅开始啦"
        ])
        db.session.add(user)
        users.append(user)

    db.session.commit()
    print(f"[INIT] 创建 1 名管理员 + {len(normal_users)} 名普通用户，共 {len(users)} 人")

    # ====================== 2. 初始化网站全局设置 ======================
    print("\n[INIT] 初始化网站设置...")
    if not SiteSettings.query.first():
        settings = SiteSettings(
            site_title='YAT NAM',
            site_subtitle='Code by day, Taiko by night',
            site_description='一个用 Python 写后端的开发者，同时也是太鼓达人段位挑战者。<br>当前目标：全曲虹满连',
            site_motto='Code × Taiko',
            footer_text='Powered by Flask • Built with passion and full combos'
        )
        db.session.add(settings)
        db.session.commit()
        print("[INIT] 网站全局设置初始化成功")
    else:
        print("[INIT] 网站设置已存在，跳过")

    # ====================== 3. 添加大量示例文章 ======================
    print("\n[INIT] 添加示例文章...")
    if Post.query.count() == 0:
        articles = [
            ("欢迎来到我的博客", "生活", "这是我的个人博客，这里会记录编程心得和太鼓达人挑战历程。"),
            ("Flask 蓝图最佳实践", "技术", "分享如何组织大型 Flask 项目，使用蓝图、工厂模式和扩展。"),
            ("太鼓达人虹满连技巧分享", "太鼓达人", "2000 裏鬼虹满连心得：手元、节奏感、心态调整全解析。"),
            ("2025 年 Python 后端趋势", "技术", "FastAPI、异步、AI 集成，后端开发的未来方向。"),
            ("生活中的节奏感", "生活", "打太鼓让我学会在生活中把握节奏，分享一些小感悟。"),
            ("我的太鼓装备进化史", "太鼓达人", "从入门鼓棒到专业鼓面，聊聊我的装备升级之路。"),
            ("用 Python 写一个太鼓成绩爬虫", "技术", "用 Selenium 抓取太鼓官网成绩，自动统计 FC 数量。"),
            ("周末的完美放松方式", "生活", "打太鼓 + 写代码 + 看书，这就是我的周末。"),

        ]

        admin_user = User.query.filter_by(username='yatnam').first()
        for i, (title, cat_str, preview) in enumerate(articles, 1):
            category = Category.TECH if "技术" in cat_str else Category.TAIKO if "太鼓" in cat_str else Category.LIFE
            post = Post(
                title=title,
                content=f"# {title}\n\n{preview}\n\n这是一篇示例文章，内容丰富，支持 Markdown 语法、代码高亮、表格等功能。",
                author=admin_user,
                category=category,
                is_pinned=(i <= 2)  # 前两篇置顶
            )
            db.session.add(post)

        db.session.commit()
        print(f"[INIT] 添加 {len(articles)} 篇示例文章（含置顶）")
    else:
        print(f"[INIT] 已存在 {Post.query.count()} 篇文章，跳过添加")

    # ====================== 4. 添加大量示例太鼓战绩 ======================
    print("\n[INIT] 添加示例太鼓战绩...")
    if TaikoRecord.query.count() == 0:
        player = User.query.filter_by(username='yatnam').first()

        # 歌曲战绩
        songs = [
            ("2000", "裏鬼", 1000000, TaikoSubCategory.FULL_COMBO, CrownType.RAINBOW_FC, "人生第一虹！"),
            ("Saitama2000", "鬼", 998500, TaikoSubCategory.FULL_COMBO, CrownType.GOLD_FC, "稳定金满连"),
            ("Namco Original", "鬼", 995000, TaikoSubCategory.GOOD_OK, CrownType.GOLD_FC, "全良达成！"),
            ("Touhou Medley", "裏鬼", 982000, TaikoSubCategory.BRUSH_SCORE, CrownType.SILVER_FC, "刷分练习曲"),
            ("Tenjiku2000", "裏鬼", 990000, TaikoSubCategory.FULL_COMBO, CrownType.GOLD_FC, "又一个金满连"),
        ]

        for name, diff, score, sub_cat, crown, note in songs:
            record = TaikoRecord(
                main_category=TaikoMainCategory.SONG,
                sub_category=sub_cat,
                name=name,
                difficulty=diff,
                score=score,
                good=random.randint(800, 950),
                ok=random.randint(50, 150),
                bad=random.randint(0, 10),
                crown=crown,
                note=note,
                player=player
            )
            db.session.add(record)

        # 段位战绩
        dans = ["十段", "名人", "玄人", "達人"]
        for name in dans:
            record = TaikoRecord(
                main_category=TaikoMainCategory.DAN,
                name=name,
                note=f"终于达到{name}段位了！",
                player=player
            )
            db.session.add(record)

        db.session.commit()
        print(f"[INIT] 添加 {len(songs)} 首歌曲战绩 + {len(dans)} 个段位战绩")
    else:
        print(f"[INIT] 已存在 {TaikoRecord.query.count()} 条战绩，跳过添加")

    print("\n[INIT] 数据库初始化全部完成！网站内容超级丰富！")
    print("现在运行：python app.py 启动网站")
    print("\n登录账号示例：")
    print("    管理员: yatnam / 12345")
    print("    普通用户: alice / alice123 等")
    print("\n后台地址：/admin/dashboard")
    print("[INIT] 初始化脚本结束\n")