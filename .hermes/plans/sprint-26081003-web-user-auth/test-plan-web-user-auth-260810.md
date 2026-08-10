# TEST-PLAN — Sprint 26081003 Web 用户体系

> agent self-verify 用, dad 看 PR review packet 里的测试结果摘要
> TECH-SPEC: `.hermes/plans/sprint-26081003-web-user-auth/tech-spec-web-user-auth-260810.md`

## 测试矩阵

### test_auth_web.py (21 case)

#### Login 路径
| Case | 期望 | 风险等级 |
|------|------|---------|
| `test_login_success` | 200 + Set-Cookie (30 天) | 主路径 |
| `test_login_wrong_password` | 401, 返通用错 (不区分用户名/密码错) | 安全基线 |
| `test_login_revoked_user` | 401 | 安全基线 |
| `test_login_must_change_redirect_signal` | 200 + 返 must_change=true, 前端跳 /change-password | 安全基线 |
| `test_login_remember_default_30day` | Set-Cookie Max-Age=2592000 | 主路径 |
| `test_login_no_remember_session_cookie` | Set-Cookie Max-Age 不设 (session cookie) | 主路径 |
| `test_login_duplicate_username_constraint` | DB UNIQUE 约束, 注册时 400 | 主路径 |

#### Logout 路径
| Case | 期望 | 风险等级 |
|------|------|---------|
| `test_logout_clears_cookie` | Set-Cookie Max-Age=0 | 主路径 |
| `test_logout_not_logged_in_idempotent` | 200 (幂等) | 边缘 |

#### Change-password 路径
| Case | 期望 | 风险等级 |
|------|------|---------|
| `test_change_password_success` | 200 + must_change 清零 | 主路径 |
| `test_change_password_wrong_old` | 401 | 安全基线 |
| `test_change_password_too_short` | 400 (≥8 位) | 安全基线 |
| `test_change_password_mismatch` | 400 | 边缘 |

#### Me 路径
| Case | 期望 | 风险等级 |
|------|------|---------|
| `test_me_logged_in` | 200 返 user 对象 | 主路径 |
| `test_me_not_logged_in` | 401 | 主路径 |

#### Cookie 完整性
| Case | 期望 | 风险等级 |
|------|------|---------|
| `test_cookie_expired_30day_max_age` | 31 天后 cookie 失效 → 401 | 安全基线 |
| `test_cookie_tampered_signature` | 改 cookie 1 字符 → 401 | 安全基线 |
| `test_cookie_session_version_mismatch` | session_version+1 后老 cookie 失效 | 安全基线 |

#### Role 守卫矩阵 (5 角色 × 4 资源 = 20 组合, 抽 6 关键)
| Case | 期望 | 风险等级 |
|------|------|---------|
| `test_guard_dad_can_access_config` | 200 | 主路径 |
| `test_guard_student_block_config` | 403 | 主路径 |
| `test_guard_family_block_practice` | 403 | 主路径 |
| `test_guard_teacher_can_practice` | 200 | 主路径 |
| `test_guard_guest_not_implemented` | - | 本期砍 |
| `test_guard_visitor_404` | - | 本期砍 |

### test_config_users.py (8 case)

#### Dad 后台端点
| Case | 期望 |
|------|------|
| `test_create_user_ok_with_pin` | 200 + 返明文 initial_password |
| `test_create_user_wrong_pin` | 401 |
| `test_create_user_no_pin` | 401 |
| `test_create_user_duplicate_username` | 400 |
| `test_reset_password_ok_with_pin` | 200 + 明文新密码 |
| `test_change_role_ok_with_pin` | 200 + role 更新 |
| `test_revoke_user_ok_with_pin` | 200 + revoked=1 |
| `test_logout_all_ok_with_pin` | 200 + session_version+1 |

### 兼容性回归 (基线)
| Case | 期望 | 风险等级 |
|------|------|---------|
| `test_verify_pin_still_works_dad_root` | dad_pin 路径 100% 不变 | mp 提审路径 |
| `test_minip_whitelist_d_unchanged` | dad_whitelist settings 表查询路径 100% 不变 | mp 提审路径 |
| `test_existing_pytest_passes` | 全部现有测试 (~270 passed) 不破 | 基线 |

## 验收门槛 (Definition of Done)

- [ ] pytest 全部绿 (含现有基线 + 新 29+ case)
- [ ] lsof 8765 LISTEN
- [ ] curl `/` → 302 → `/login`
- [ ] curl `/api/auth/login` with dad PIN 在另一端点 (verify-pin) → 仍 ok
- [ ] dad 浏览器流程 (建女儿账号 → 女儿 iPad 登录 → 改密 → 进 /practice) 全走通

## 自动化跑法

```bash
cd /Users/mt16/dev/dizical
python3 -m pytest tests/test_auth_web.py tests/test_config_users.py -v 2>&1 | tail -60
python3 -m pytest tests/ -x --tb=short 2>&1 | tail -30  # 全量基线
```

## Dad 手动验证清单

1. 重启 8765 服务: `./scripts/stop-prod.sh && ./scripts/start-p-d.sh`
2. 浏览器开 `http://localhost:8765` → 期待跳 `/login`
3. dad PIN 验证流程: 浏览器开 `/config/users` → 输 PIN=0905 → 进管理页
4. 建女儿账号: 点"新建" → 输 username=yoyo / display_name=女儿 / role=student → 提交 → 弹"初始密码 K7mQ3xLp" → 复制
5. 浏览器隐身模式开 url → `/login` → 输 yoyo/K7mQ3xLp → 强制跳 `/change-password` → 改密 → 进 `/practice`
6. 抽屉显示: 女儿 / 学习者
7. 访问 `/config` → 期待 403
8. 验证 30 天 cookie: 关浏览器 → 重开 → 自动登录 (期待)
9. dad 在 `/config/users` 点 "踢出所有设备" → 女儿下次访问 → 跳 /login
10. mp 端验证: 打开"呦助"小程序 → 输 PIN=0905 → 正常进 (mp 路径 100% 不变)