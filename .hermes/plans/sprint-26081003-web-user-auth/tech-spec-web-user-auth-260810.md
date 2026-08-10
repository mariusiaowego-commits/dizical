# TECH-SPEC — Sprint 26081003 Web 用户体系

> 实现文档 (agent only) — 给下一棒 agent 看的设计细节
> Plan: `.hermes/plans/sprint-26081003-web-user-auth/AI-PLAN-web-user-auth-260810.md`
> PRD: `PRDs/AI-PRD-web-user-auth-260810.md`

## 1. 数据模型

### `web_users` 表
```sql
CREATE TABLE web_users (
  user_id        INTEGER PRIMARY KEY AUTOINCREMENT,
  username       VARCHAR(64) UNIQUE NOT NULL,
  display_name   VARCHAR(64) NOT NULL,
  password_hash  VARCHAR(256) NOT NULL,
  role           VARCHAR(16) NOT NULL,
  avatar_letter  VARCHAR(1),
  must_change_password BOOLEAN DEFAULT 1,
  created_by     INTEGER,
  created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_login_at  DATETIME NULL,
  revoked        BOOLEAN DEFAULT 0
);
```

**双后端兼容 (sprint 09)**:
- SQLite (本地): `CREATE TABLE IF NOT EXISTS`
- Cloud MySQL (生产): 同 SQL, 不引新 type
- 迁移走 `src/migrate_add_web_users.py`, 通过 db_adapter.execute 双写

## 2. 密码哈希 (argon2)

使用 `argon2-cffi` (pyproject 已含):

```python
from argon2 import PasswordHasher
ph = PasswordHasher()  # 默认 m=65536, t=3, p=4 (OWASP 推荐)

# 建账号
hash_str = ph.hash(initial_password)  # 例: '$argon2id$v=19$m=65536,t=3,p=4$<salt>$<hash>'

# 校验
try:
    ph.verify(hash_str, password_input)  # 校验失败抛 VerifyMismatchError
    # 可选: ph.check_needs_rehash(hash_str) 检测参数升级
except argon2.exceptions.VerifyMismatchError:
    return False
```

## 3. Cookie 签名 (itsdangerous)

使用 `itsdangerous` (pyproject 已含), SECRET_KEY 从环境变量取:

```python
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

SESSION_SECRET = os.getenv("DIZICAL_SESSION_SECRET", "dev-secret-change-in-prod")
SESSION_SALT = "dizical-web-session-v1"
COOKIE_NAME = "dizical_session"
COOKIE_MAX_AGE = 30 * 24 * 3600  # 30 天 (Q3=A)

serializer = URLSafeTimedSerializer(SESSION_SECRET, salt=SESSION_SALT)

# 签发
def make_session_cookie(user_id: int, role: str) -> str:
    return serializer.dumps({"user_id": user_id, "role": role})

# 验证 (FastAPI Depends 里)
def load_session(request: Request) -> Optional[dict]:
    sig = request.cookies.get(COOKIE_NAME)
    if not sig: return None
    try:
        return serializer.loads(sig, max_age=COOKIE_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
```

**Cookie 响应**:
```python
response.set_cookie(
    key=COOKIE_NAME,
    value=sig,
    max_age=COOKIE_MAX_AGE,  # 30 天
    httponly=True,
    secure=True,  # prod 必须 True, dev 可放宽 (DIZICAL_INSECURE_COOKIE=1)
    samesite="lax",
    path="/",
)
```

**"踢出所有设备"** (dad 操作): 删 web_users 行 → 触发 `serializer = URLSafeTimedSerializer(new_secret)` → 老 cookie 签名对不上, 自动失效
- 实现: dad 点 "踢出" → 后端把 `web_users.user_id` 写入 settings `kicked_users_at` dict, `get_current_user` 校验时拒绝被踢的 user_id
- 简化做法: 加 `web_users.session_version INTEGER DEFAULT 0`, dad 点踢出 → `session_version += 1`, cookie payload 加 `sv` 字段, 不匹配即失效

## 4. 角色权限矩阵 (route-level guards)

```python
# src/kid_app/auth.py
ROLE_PERMISSIONS = {
    "dad":      {"practice", "prepare", "report", "achievements", "badges",
                 "config", "praise", "config_users", "admin"},
    "student":  {"practice", "prepare", "report", "achievements", "badges"},
    "family":   {"report", "achievements", "badges"},
    "teacher":  {"practice", "prepare", "report", "achievements", "badges"},
}
```

## 5. FastAPI Dependencies

```python
# src/kid_app/auth.py
async def get_current_user(request: Request) -> Optional[dict]:
    """None = 未登录; dict = {user_id, username, role, display_name, ...}"""
    session = load_session(request)
    if not session: return None
    user = db.fetchone(
        "SELECT user_id, username, display_name, role, avatar_letter, must_change_password, revoked "
        "FROM web_users WHERE user_id = %s",  # db_adapter 兼容 SQLite/MySQL
        (session["user_id"],)
    )
    if not user or user["revoked"]: return None
    return user

async def require_login(request: Request) -> dict:
    user = await get_current_user(request)
    if not user: raise HTTPException(302, headers={"Location": "/login"})
    return user

def require_role(*roles):
    async def dep(request: Request) -> dict:
        user = await require_login(request)
        if user["role"] not in roles:
            raise HTTPException(403, "权限不足")
        return user
    return dep
```

## 6. API 端点签名

| Method | Path | Body | Response |
|--------|------|------|----------|
| POST | `/api/auth/login` | `{username, password, remember=true}` | `{ok, user: {...}}` + Set-Cookie |
| POST | `/api/auth/logout` | `{}` | `{ok}` + 清 cookie |
| POST | `/api/auth/change-password` | `{old_password, new_password}` | `{ok}` |
| GET | `/api/auth/me` | - | `{user: {...}}` 或 401 |
| GET | `/config/users` | - | HTML (dad PIN 守门) |
| POST | `/config/api/users/create` | `{username, display_name, role, avatar_letter}` | `{ok, user_id, initial_password}` (明文一次) |
| POST | `/config/api/users/{user_id}/reset-password` | - | `{ok, new_password}` (明文一次) |
| POST | `/config/api/users/{user_id}/role` | `{role}` | `{ok}` |
| POST | `/config/api/users/{user_id}/revoke` | - | `{ok}` |
| POST | `/config/api/users/{user_id}/logout-all` | - | `{ok}` (递增 session_version) |

## 7. 路由守卫应用范围

**所有页面路由必须加** `Depends(require_login)`:
- `@app.get("/prepare")` / `/practice` / `/achievements` / `/badges` / `/report` / `/report/stage-print` / `/praise`
- `/` (index) 重定向到角色对应落地页
- `/gsap-demo` 公开 (dev 工具)

**写操作 API 加 `Depends(require_role("dad", "student"))`**:
- `POST /api/log` → student 可写, family/teacher 403
- `POST /api/items/{}/archive` 等 → 仅 dad
- `DELETE /api/practice-sessions/{id}` → 仅 dad

**dad PIN 守门** (config 内部, 沿用现有模式):
- `/config/users` 跟其他 config 页同 — PIN 输入框 + 后续 ajax 校验
- `/config/api/users/*` 端点 — header 校验 `X-Dad-Pin` = settings.dad_pin

## 8. UI 设计要点

### `/login` (templates/login.html)
- 极简: 居中卡片, 用户名 + 密码 + 登录按钮 + "记住此设备 30 天" checkbox (默认勾)
- 错误提示: 红色字 "用户名或密码错" (不区分, 防撞库)
- 风格: 跟主站一致 (#FF6B6B 主色 + 圆角卡片)

### `/change-password` (templates/change-password.html)
- 旧密码 + 新密码 + 确认新密码
- 校验: 旧密码正确 + 新密码 ≥ 8 位 + 两次一致

### `/config/users` (templates/config-users.html)
- 跟 `/config/blindbox` 等同款主风格 (主色 #FF6B6B)
- 表格: 用户名 / 显示名 / 角色 / 状态 / 最后登录 / 操作
- 新建 modal: 输 username/display_name/role/avatar_letter → 提交 → 弹"初始密码"对话框 (复制按钮)
- dad PIN 守门: 进入页面先输 PIN, 跟现有 /config 一致

### `_sidebar.html` 动态化
- Jinja 模板变量 `{{ user.display_name }}` / `{{ user.role_label }}`
- 角色 label: dad=「管理员」/ student=「学习者」/ family=「家人」/ teacher=「老师」
- 登出按钮 (右下角 footer 新增)

## 9. 文件清单 (11 文件)

| 文件 | 类型 | 备注 |
| |-----|------|
| `src/migrate_add_web_users.py` | 新 | 幂等建表 |
| `src/kid_app/auth.py` | 新 | 核心: cookie 签名 + 守卫 |
| `src/kid_app/routes/auth_web.py` | 新 | login/logout/change-pw/me |
| `src/kid_app/routes/config_users.py` | 新 | dad 后台管理 |
| `src/kid_app/app.py` | 改 | 加 Depends 守卫 |
| `src/kid_app/templates/_sidebar.html` | 改 | 动态化 |
| `src/kid_app/templates/login.html` | 新 | 登录页 |
| `src/kid_app/templates/change-password.html` | 新 | 改密页 |
| `src/kid_app/templates/config-users.html` | 新 | dad 后台 |
| `tests/test_auth_web.py` | 新 | 30+ case |
| `tests/test_config_users.py` | 新 | admin 端点 |

## 10. 兼容性与红线

- **mp 端 0 改动**: minip/whitelist 不动
- **settings 表 0 改动**: dad_pin/dad_whitelist 全保留
- **CloudRun 部署**: DIZICAL_SESSION_SECRET 环境变量必须设置 (强密码, 跨容器一致)
- **dev 环境**: DIZICAL_INSECURE_COOKIE=1 时 secure=False (允许 http://localhost)

## 12. 单测覆盖矩阵 (test_auth_web.py)

| Case | 期望 |
|------|------|
| test_login_success | 返 ok + Set-Cookie |
| test_login_wrong_password | 401, 不泄密 |
| test_login_revoked_user | 401 |
| test_login_must_change_redirect | must_change=1 → 返 flag, 前端跳 /change-password |
| test_login_remember_default | 30 天 max_age |
| test_login_no_remember | session cookie (max_age=None) |
| test_logout_clear_cookie | Set-Cookie Max-Age=0 |
| test_change_password_success | must_change 清零 |
| test_change_password_wrong_old | 401 |
| test_change_password_too_short | 400 |
| test_change_password_mismatch | 400 |
| test_me_logged_in | 返 user |
| test_me_not_logged_in | 401 |
| test_cookie_expired | 401 |
| test_cookie_tampered | 401 |
| test_role_guard_student_block_config | 403 |
| test_role_guard_family_block_practice | 403 |
| test_role_guard_teacher_allow_practice | 200 |
| test_role_guard_dad_allow_all | 200 |
| test_session_version_kick_all | old cookie 401 |
| test_login_after_kick_all | 重新登录 ok |

(test_config_users.py):
| test_create_user_ok | dad PIN ok → 返明文密码 |
| test_create_user_no_pin | 401 |
| test_create_user_duplicate_username | 400 |
| test_reset_password_ok | 明文新密码 + must_change=1 |
| test_change_role_ok | role 更新 |
| test_revoke_user_ok | revoked=1, 下次登录 401 |
| test_logout_all_ok | session_version+1 |