# Owner Rolü + Kademeli Rol Yönetimi + Gerçek E-posta Gönderimi Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an `owner` role (env-bootstrapped, never DB-assignable) that grants unlimited (Enterprise-equivalent) access without touching the `tier` column; make role management graduated (nobody can touch an equal/higher role); and replace the silently-broken production email path (`RESEND_API_KEY` empty → mail vanishes into logs) with a working `SmtpEmailAdapter` plus a selection matrix that can't fail silently again.

**Architecture:** Domain stays framework-free — a pure `effective_tier(tier, is_owner)` function in `domain/models/user.py`, wrapped by `user_effective_tier(user)` in `auth_utils.py` (the only place allowed to read `settings.owner_emails`, mirroring the existing `has_admin_role`/`ADMIN_EMAILS` pattern). Every tier-gated call site swaps `user.tier` for `user_effective_tier(user)`; DB `tier` column is never written for owners. Email adapters gain a shared `_HtmlEmailAdapter` base (DRY refactor of the existing five-method duplication) and a third concrete adapter, `SmtpEmailAdapter`, selected by a new `EMAIL_PROVIDER` setting with an `auto` fallback chain.

**Tech Stack:** FastAPI, Pydantic Settings, SQLAlchemy, `smtplib` (stdlib, STARTTLS), pytest + `unittest.mock`, Next.js 14 / TypeScript (frontend, verified via `tsc --noEmit`, no JS test framework in this repo).

## Global Constraints

- Role hierarchy becomes `user (0) < moderator (1) < admin (2) < owner (3)` — exact rank values, see `src/domain/models/user.py::_ROLE_RANK`.
- Owner role is **never** assignable through any API — the only sources are `OWNER_EMAILS` env var or a hand-written `role='owner'` DB row.
- DB `tier` column is **never** written to `enterprise` for an owner — `effective_tier()` is a read-time projection only.
- Public `/news/search` (`src/adapters/api/routers/news_router.py::search_news`) must **not** change — it stays hardcoded to the Free cap regardless of any identity.
- Domain layer (`src/domain/`) must never import `src.infrastructure.config.settings` — owner-email lookups live only in `src/adapters/api/auth_utils.py`.
- No hardcoded TR/EN branching (`if language == "TR" else ...`) — new user-facing strings go through the existing dictionary pattern (`_STRINGS` in `email_adapter.py` backend-side, `UI[lang]` in `frontend/lib/i18n.ts` frontend-side).
- Every existing test must keep passing; where a test's mocked behavior no longer matches the new code path (e.g. `MagicMock().smtp_user` being truthy), the test itself must be updated in the same task, not left broken.
- Frontend has no unit test runner in this repo — its verification step is `npx tsc --noEmit`, run only when the frontend dev container is **not** running `npm run build` on host (see CLAUDE.md `.next` collision warning). Do not run `npm run build` against a live container.

---

### Task 1: Domain — `owner` role rank + pure `effective_tier()`

**Files:**
- Modify: `src/domain/models/user.py`
- Test: `tests/adapters/test_tier_gating.py` (new domain-level tests added at top; there is no `tests/domain/test_user.py` in this repo — tier/role tests already live in `tests/adapters/`, follow that convention)

**Interfaces:**
- Produces: `UserRole.OWNER` enum member, `effective_tier(tier: UserTier, is_owner: bool) -> UserTier` (pure function, no settings import)

- [ ] **Step 1: Write the failing tests**

Add to the top of `tests/adapters/test_tier_gating.py` (after the existing imports, before the `tier_at_least helper` section):

```python
from src.domain.models.user import UserRole, role_at_least, effective_tier


def test_owner_role_ranks_above_admin():
    assert role_at_least(UserRole.OWNER, UserRole.ADMIN)
    assert not role_at_least(UserRole.ADMIN, UserRole.OWNER)


def test_effective_tier_owner_is_always_enterprise():
    assert effective_tier(UserTier.FREE, is_owner=True) == UserTier.ENTERPRISE


def test_effective_tier_non_owner_keeps_own_tier():
    assert effective_tier(UserTier.PRO, is_owner=False) == UserTier.PRO
    assert effective_tier(UserTier.FREE, is_owner=False) == UserTier.FREE
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_tier_gating.py -k "owner or effective_tier" -v`
Expected: FAIL — `ImportError: cannot import name 'effective_tier'` (and `UserRole.OWNER` doesn't exist yet).

- [ ] **Step 3: Implement in `src/domain/models/user.py`**

In the `UserRole` enum (around line 54-56), add the fourth member and update the docstring:

```python
class UserRole(str, Enum):
    """Yetki hiyerarşisi — user < moderator < admin < owner (v2.1'de owner eklendi).

    moderator: admin panelini GÖREBİLİR (kullanım/kullanıcı/sponsor listeleri)
        ama rol değiştiremez, sponsor CRUD yapamaz — destek/gözlem amaçlı.
    admin: rol değiştirebilir (kademeli — kendinden düşük roldekilere), sponsor CRUD.
    owner: sınırsız erişim (effective_tier ile Enterprise muamelesi), kimse
        rolünü değiştiremez. API'den ASLA atanamaz — tek kaynak OWNER_EMAILS
        env değişkeni (veya DB'ye elle yazılan role='owner').
    ADMIN_EMAILS bootstrap listesi DB'ye dokunmadan "admin" muamelesi görür
    (bkz. auth_utils.has_admin_role) — role kolonu bundan bağımsızdır.
    """

    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"
    OWNER = "owner"


_ROLE_RANK = {UserRole.USER: 0, UserRole.MODERATOR: 1, UserRole.ADMIN: 2, UserRole.OWNER: 3}
```

Then, right after `tier_at_least()` (after line 41), add the pure projection function:

```python
def effective_tier(tier: "UserTier", is_owner: bool) -> "UserTier":
    """Owner için her zaman Enterprise döner, aksi halde `tier` aynen geçer.

    Saf domain fonksiyonu — owner tespiti (OWNER_EMAILS env) burada YAPILMAZ,
    çağıran katman (auth_utils.user_effective_tier) zaten çözüp bool geçirir.
    DB'deki `tier` kolonu asla `enterprise` olarak YAZILMAZ — bu sadece
    okuma-zamanı bir projeksiyon (admin panelindeki `is_paying` ayrımının
    kirlenmemesi için, bkz. CLAUDE.md v2.1 notu).
    """
    return UserTier.ENTERPRISE if is_owner else UserTier(tier)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_tier_gating.py -k "owner or effective_tier" -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Run the full domain-adjacent suite to check for regressions**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_tier_gating.py tests/adapters/test_tier_limits.py tests/adapters/test_admin_role.py -v`
Expected: all PASS (existing behavior untouched — `_ROLE_RANK` gained a key, didn't change existing ones)

- [ ] **Step 6: Commit**

```bash
git add src/domain/models/user.py tests/adapters/test_tier_gating.py
git commit -m "feat: add owner role rank and pure effective_tier() projection"
```

---

### Task 2: Settings — `OWNER_EMAILS` + SMTP/`EMAIL_PROVIDER` config

**Files:**
- Modify: `src/infrastructure/config/settings.py`
- Test: `tests/infrastructure/test_settings.py`

**Interfaces:**
- Produces: `settings.owner_emails: str`, `settings.owner_email_set: set[str]`, `settings.email_provider: str`, `settings.smtp_host/port/user/password/from/starttls`

- [ ] **Step 1: Check the existing settings test file's pattern**

Run: `venv\Scripts\python.exe -m pytest tests/infrastructure/test_settings.py -v` (just to see current baseline pass before editing)

- [ ] **Step 2: Write the failing tests**

Add to `tests/infrastructure/test_settings.py`:

```python
def test_owner_email_set_normalizes_case_and_whitespace():
    from src.infrastructure.config.settings import Settings
    s = Settings(owner_emails=" Boss@Company.com ,other@x.com")
    assert s.owner_email_set == {"boss@company.com", "other@x.com"}


def test_owner_email_set_empty_by_default():
    from src.infrastructure.config.settings import Settings
    s = Settings(owner_emails="")
    assert s.owner_email_set == set()


def test_email_provider_defaults_to_auto():
    from src.infrastructure.config.settings import Settings
    assert Settings().email_provider == "auto"


def test_smtp_defaults():
    from src.infrastructure.config.settings import Settings
    s = Settings()
    assert s.smtp_host == "smtp.gmail.com"
    assert s.smtp_port == 587
    assert s.smtp_user == ""
    assert s.smtp_password == ""
    assert s.smtp_from == ""
    assert s.smtp_starttls is True
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `venv\Scripts\python.exe -m pytest tests/infrastructure/test_settings.py -k "owner_email or email_provider or smtp" -v`
Expected: FAIL — `AttributeError`/`ValidationError` for unknown fields.

- [ ] **Step 4: Implement in `src/infrastructure/config/settings.py`**

Right after the `admin_emails` field (line 71), add:

```python
    # Virgülle ayrılmış e-posta listesi; eşleşen kullanıcılar owner sayılır
    # (DB'ye dokunmadan). Owner rolü API'den ASLA atanamaz — tek kaynak bu env
    # (veya DB'ye elle yazılan role='owner'). Bkz. auth_utils.has_owner_role.
    owner_emails: str = ""
```

Replace the `── Email (newsletter / keyword alert) ──` block (lines 80-83) with:

```python
    # ── Email (newsletter / keyword alert / doğrulama) ─────────────────────
    # email_provider: auto (varsayılan) SMTP kimlikleri doluysa SMTP → RESEND_API_KEY
    # doluysa Resend → Console. Açık değerler (smtp/resend/console) test/hata
    # ayıklama için zorlama sağlar. Resend'in aksine SMTP domain doğrulaması
    # istemez ve TÜM alıcılara ulaşır (Resend sandbox'ı sadece hesap sahibine izin verir).
    email_provider: str = "auto"
    resend_api_key: str = ""            # boşsa (auto modda) SMTP'ye, o da boşsa console'a düşer
    email_from: str = "NexStream <no-reply@nexstream.news>"
    newsletter_hour_utc: int = 6        # günlük digest saati (06:00 UTC = 09:00 TR)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""                 # boşsa email_from kullanılır
    smtp_starttls: bool = True
```

Add the `owner_email_set` property right after `admin_email_set` (after line 142):

```python
    @property
    def owner_email_set(self) -> set[str]:
        """OWNER_EMAILS değerini normalize edilmiş (küçük harf) set'e çevirir."""
        return {e.strip().lower() for e in self.owner_emails.split(",") if e.strip()}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `venv\Scripts\python.exe -m pytest tests/infrastructure/test_settings.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/infrastructure/config/settings.py tests/infrastructure/test_settings.py
git commit -m "feat: add OWNER_EMAILS and SMTP/EMAIL_PROVIDER settings"
```

---

### Task 3: `auth_utils` — `has_owner_role`, `effective_role`, `user_effective_tier`, `require_owner`

**Files:**
- Modify: `src/adapters/api/auth_utils.py`
- Test: `tests/adapters/test_admin_role.py`

**Interfaces:**
- Consumes: `UserRole.OWNER`, `effective_tier()` (Task 1), `settings.owner_email_set` (Task 2)
- Produces: `has_owner_role(user) -> bool`, `user_effective_tier(user) -> UserTier`, `require_owner` FastAPI dependency, updated `has_admin_role`/`effective_role`

- [ ] **Step 1: Write the failing tests**

Add to `tests/adapters/test_admin_role.py` (after the existing `has_admin_role`/`has_moderator_role` sections, before `require_admin (unit)`):

```python
from src.adapters.api.auth_utils import has_owner_role, effective_role, user_effective_tier, require_owner
from src.domain.models.user import UserTier


# ── has_owner_role / effective_role (owner) ─────────────────────────────────

def test_owner_role_flag_grants_owner():
    assert has_owner_role(_make_user(role=UserRole.OWNER)) is True


def test_owner_emails_env_bootstraps_owner_without_db_role():
    user = _make_user(email="Boss@Company.com")  # role stays USER in DB
    with patch.object(settings, "owner_emails", "boss@company.com"):
        assert has_owner_role(user) is True


def test_regular_admin_is_not_owner():
    assert has_owner_role(_make_user(is_admin=True)) is False


def test_has_admin_role_covers_owner():
    """owner ⊃ admin — owner'ın admin endpoint'lerine erişimi kesilmemeli."""
    assert has_admin_role(_make_user(role=UserRole.OWNER)) is True


def test_effective_role_reports_owner():
    assert effective_role(_make_user(role=UserRole.OWNER)) == "owner"


def test_effective_role_owner_emails_bootstrap_reports_owner_not_admin():
    user = _make_user(email="boss@company.com")
    with patch.object(settings, "owner_emails", "boss@company.com"):
        assert effective_role(user) == "owner"


# ── user_effective_tier ──────────────────────────────────────────────────────

def test_user_effective_tier_owner_is_enterprise_regardless_of_db_tier():
    owner = User(id=1, email="o@test.com", password_hash="h", tier=UserTier.FREE, role=UserRole.OWNER)
    assert user_effective_tier(owner) == UserTier.ENTERPRISE


def test_user_effective_tier_non_owner_keeps_db_tier():
    user = User(id=2, email="u@test.com", password_hash="h", tier=UserTier.PRO, role=UserRole.USER)
    assert user_effective_tier(user) == UserTier.PRO


# ── require_owner ────────────────────────────────────────────────────────────

def test_require_owner_accepts_valid_api_key():
    require_owner(x_api_key=settings.api_key, user=None)


def test_require_owner_accepts_owner_session():
    require_owner(x_api_key=None, user=_make_user(role=UserRole.OWNER))


def test_require_owner_rejects_admin_with_403():
    with pytest.raises(HTTPException) as exc:
        require_owner(x_api_key=None, user=_make_user(is_admin=True))
    assert exc.value.status_code == 403


def test_require_owner_rejects_anonymous_with_401():
    with pytest.raises(HTTPException) as exc:
        require_owner(x_api_key=None, user=None)
    assert exc.value.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_admin_role.py -v`
Expected: FAIL — `ImportError: cannot import name 'has_owner_role'`

- [ ] **Step 3: Implement in `src/adapters/api/auth_utils.py`**

Update the import line (line 33) to pull in `effective_tier`:

```python
from src.domain.models.user import User, UserRole, UserTier, role_at_least, effective_tier, TIER_DAILY_LIMITS
```

Replace `has_admin_role` and add `has_owner_role` right before it (around line 57):

```python
def has_owner_role(user: User) -> bool:
    """Etkin owner kontrolü: DB'deki role="owner" VEYA OWNER_EMAILS bootstrap listesi.

    Owner rolü API'den asla atanamaz — tek kaynak bu env değişkeni ya da elle
    yazılan bir DB satırı. `tier` alanına dokunmaz, bkz. user_effective_tier.
    """
    return user.role == UserRole.OWNER or (user.email or "").lower() in settings.owner_email_set


def has_admin_role(user: User) -> bool:
    """Etkin admin kontrolü: role>=admin (owner dahil) VEYA ADMIN_EMAILS bootstrap.

    owner ⊃ admin ⊃ moderator — owner hiçbir admin endpoint'inden dışlanmaz.
    """
    return role_at_least(user.role, UserRole.ADMIN) or (user.email or "").lower() in settings.admin_email_set or has_owner_role(user)
```

Update `effective_role` (currently around line 74-76):

```python
def effective_role(user: User) -> str:
    """Frontend'e dönülen etkin rol — ADMIN_EMAILS/OWNER_EMAILS bootstrap'lerini yansıtır."""
    if has_owner_role(user):
        return UserRole.OWNER.value
    return UserRole.ADMIN.value if has_admin_role(user) else UserRole(user.role).value
```

Add `user_effective_tier` right after `effective_role`:

```python
def user_effective_tier(user: User) -> UserTier:
    """Owner tespitini (OWNER_EMAILS) çözüp saf domain fonksiyonuna devreden sarmalayıcı.

    Domain katmanı settings import edemediği için bu ayrım burada yaşar — tüm
    tier-gating çağrı noktaları `user.tier` yerine bunu okumalı.
    """
    return effective_tier(user.tier, has_owner_role(user))
```

Add `require_owner` right after `require_admin` (after line 123):

```python
def require_owner(
    x_api_key: Optional[str] = Header(None),
    user: Optional[User] = Depends(get_optional_user),
) -> None:
    """Owner-only endpoint koruması — geçerli X-API-Key VEYA owner kullanıcı oturumu."""
    if api_key_matches(x_api_key):
        return
    if user and has_owner_role(user):
        return
    if user:
        raise HTTPException(status_code=403, detail="Owner privileges required")
    raise HTTPException(status_code=401, detail="Admin authentication required")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_admin_role.py -v`
Expected: all PASS

- [ ] **Step 5: Run the wider auth-adjacent suite for regressions**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_admin_role.py tests/adapters/test_admin_router.py tests/adapters/test_auth_router.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/adapters/api/auth_utils.py tests/adapters/test_admin_role.py
git commit -m "feat: add has_owner_role, user_effective_tier, require_owner to auth_utils"
```

---

### Task 4: `/auth/me` — expose `is_owner` + `effective_tier`

**Files:**
- Modify: `src/adapters/api/routers/auth_router.py`
- Test: `tests/adapters/test_auth_router.py`

**Interfaces:**
- Consumes: `has_owner_role`, `user_effective_tier` (Task 3)
- Produces: `_user_payload(user)` dict gains `is_owner: bool`, `effective_tier: str`

- [ ] **Step 1: Check current `_user_payload` test coverage**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_auth_router.py -k "payload or me" -v` (baseline)

- [ ] **Step 2: Write the failing test**

Add to `tests/adapters/test_auth_router.py` (find the existing import block and add `UserRole` if not already imported, then add near the `/auth/me` tests):

```python
def test_me_reports_is_owner_and_effective_tier_for_owner(app_client):
    from src.domain.models.user import User, UserTier, UserRole
    owner = User(id=1, email="o@test.com", password_hash="h", tier=UserTier.FREE,
                 role=UserRole.OWNER, email_verified=False)
    app_client.app.dependency_overrides[get_optional_user] = lambda: owner
    try:
        resp = app_client.get("/auth/me")
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_owner"] is True
    assert data["effective_tier"] == "enterprise"
    assert data["tier"] == "free"  # DB tier'ına dokunulmadı


def test_me_reports_is_owner_false_for_regular_user(app_client):
    from src.domain.models.user import User, UserTier
    user = User(id=2, email="u@test.com", password_hash="h", tier=UserTier.PRO)
    app_client.app.dependency_overrides[get_optional_user] = lambda: user
    try:
        resp = app_client.get("/auth/me")
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
    data = resp.json()
    assert data["is_owner"] is False
    assert data["effective_tier"] == "pro"
```

Check the top of `tests/adapters/test_auth_router.py` for a `get_optional_user` import; if it imports `get_current_user` only, add `get_optional_user` to that import line (`get_current_user` alone can't be overridden for a GET that depends on it transitively — but FastAPI resolves overrides by the actual dependency callable used in the chain, which is `get_optional_user` under `get_current_user`, so override `get_optional_user`, matching the pattern already used in `test_admin_role.py`).

- [ ] **Step 3: Run tests to verify they fail**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_auth_router.py -k "is_owner" -v`
Expected: FAIL — `KeyError: 'is_owner'`

- [ ] **Step 4: Implement in `src/adapters/api/routers/auth_router.py`**

Update the import line (line 27) to add `has_owner_role, user_effective_tier`:

```python
from src.adapters.api.auth_utils import has_admin_role, has_moderator_role, has_owner_role, effective_role, user_effective_tier, get_current_user, SESSION_COOKIE_NAME
```

Update `_user_payload` (around line 143-161):

```python
def _user_payload(user: User) -> dict:
    """API yanıtlarındaki kullanıcı gösterimi — parola hash'i asla sızmaz.

    `role`: etkin yetki (user/moderator/admin/owner, bootstrap'ler dahil).
    `is_admin`: geriye dönük uyumluluk için korunan türetilmiş alan (role == admin).
    `is_owner`: owner muafiyetleri için (doğrulama banner'ı, yükseltme kartı, checkout gate).
    `effective_tier`: owner için her zaman "enterprise", diğerlerinde `tier` ile aynı —
        DB'deki `tier` kolonu owner için asla değiştirilmez (bkz. user_effective_tier).
    `email_verified`: v1.15 — Free tier'da erişimi kısıtlamaz, sadece ücretli
        kademeye yükseltmede (billing checkout) şart koşulur; owner muaftır.
    """
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "tier": user.tier,
        "effective_tier": user_effective_tier(user).value,
        "role": effective_role(user),
        "is_admin": has_admin_role(user),
        "is_moderator": has_moderator_role(user),
        "is_owner": has_owner_role(user),
        "email_verified": user.email_verified,
    }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_auth_router.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/adapters/api/routers/auth_router.py tests/adapters/test_auth_router.py
git commit -m "feat: expose is_owner and effective_tier on /auth/me"
```

---

### Task 5: `check_tier_limit` — unlimited quota for owner

**Files:**
- Modify: `src/adapters/api/auth_utils.py`
- Test: `tests/adapters/test_tier_limits.py`

**Interfaces:**
- Consumes: `user_effective_tier` (Task 3)

- [ ] **Step 1: Write the failing test**

Add to `tests/adapters/test_tier_limits.py`:

```python
def test_check_tier_limit_owner_never_blocked_despite_free_db_tier():
    from unittest.mock import MagicMock, patch
    from src.domain.models.user import UserRole
    owner = User(id=9, email="o@test.com", password_hash="h", tier=UserTier.FREE, role=UserRole.OWNER)
    with patch("src.adapters.api.auth_utils.UserRepository") as MockRepo:
        repo = MagicMock()
        repo.get_daily_usage_count.return_value = 99999
        MockRepo.return_value = repo
        db = MagicMock()
        result = check_tier_limit(user=owner, db=db)
    assert result is owner
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_tier_limits.py -k owner -v`
Expected: FAIL — a Free-tier user with 99999 usage gets a 429 `HTTPException` raised instead of returning.

- [ ] **Step 3: Implement in `src/adapters/api/auth_utils.py`**

Update `check_tier_limit` (around lines 144-165):

```python
def check_tier_limit(
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Kullanıcının günlük /api/v1 kotasını kontrol eder; aşımda 429.

    Anonim istekler kota dışıdır (None döner); Enterprise ve owner sınırsızdır.
    """
    if user is None:
        return None
    tier = user_effective_tier(user)
    limit = TIER_DAILY_LIMITS.get(tier)
    if limit is None:
        return user
    repo = UserRepository(db)
    count = repo.get_daily_usage_count(user.id)
    if count >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily API limit reached ({limit} req/day). Upgrade your plan for higher limits.",
            headers={"X-Tier": tier, "X-Daily-Limit": str(limit)},
        )
    return user
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_tier_limits.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/adapters/api/auth_utils.py tests/adapters/test_tier_limits.py
git commit -m "feat: exempt owner from daily API quota via user_effective_tier"
```

---

### Task 6: `account_router` usage panel — owner shows unlimited

**Files:**
- Modify: `src/adapters/api/routers/account_router.py`
- Test: new `tests/adapters/test_account_router.py` section (check if the file exists first; if not, this task creates it minimally around the one endpoint touched)

**Interfaces:**
- Consumes: `user_effective_tier` (Task 3)

- [ ] **Step 1: Check whether `tests/adapters/test_account_router.py` exists**

Run: `ls tests/adapters/ | grep account` (Bash) or `Glob: tests/adapters/test_account_router.py`. If it exists, add the test there following its existing fixture pattern (mirror how it overrides `get_current_user`/`get_db`); if not, create it with the minimal scaffold below.

- [ ] **Step 2: Write the failing test**

If the file must be created, use this full content (adjust imports if an existing file already has a different mock-DB helper — reuse it instead of duplicating):

```python
from unittest.mock import MagicMock, patch
from src.adapters.api.auth_utils import get_current_user
from src.domain.models.user import User, UserTier, UserRole
from src.infrastructure.config.database import get_db


def _make_owner():
    return User(id=1, email="o@test.com", password_hash="h", tier=UserTier.FREE, role=UserRole.OWNER)


def test_my_usage_shows_unlimited_for_owner_despite_free_db_tier(app_client):
    owner = _make_owner()
    db = MagicMock()
    app_client.app.dependency_overrides[get_current_user] = lambda: owner
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.account_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_daily_usage_count.return_value = 500
            repo.get_usage_stats.return_value = []
            MockRepo.return_value = repo
            resp = app_client.get("/account/usage")
    finally:
        app_client.app.dependency_overrides.pop(get_current_user, None)
        app_client.app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["daily_limit"] is None
    assert data["remaining_today"] is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_account_router.py -k owner -v`
Expected: FAIL — `data["daily_limit"] == 100` (Free limit), not `None`.

- [ ] **Step 4: Implement in `src/adapters/api/routers/account_router.py`**

Update the import (line 20) to add `user_effective_tier`:

```python
from src.adapters.api.auth_utils import get_current_user, user_effective_tier
```

Update `my_usage` (around lines 33-53), only the limit lookup line changes:

```python
@router.get("/usage")
def my_usage(
    days: int = Query(7, ge=1, le=90, description="İstatistik penceresi (gün)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Kullanıcının kendi kota ve kullanım özeti (hesap sayfası paneli)."""
    repo = UserRepository(db)
    limit = TIER_DAILY_LIMITS.get(user_effective_tier(current_user))    # None = sınırsız (owner dahil)
    used_today = repo.get_daily_usage_count(current_user.id)
    rows = repo.get_usage_stats(user_id=current_user.id, days=days)
    return {
        "tier": current_user.tier,
        "daily_limit": limit,
        "used_today": used_today,
        "remaining_today": None if limit is None else max(limit - used_today, 0),
        "days": days,
        "total_requests": sum(r["count"] for r in rows),
        "by_endpoint": rows,
        "has_api_key": bool(current_user.api_key),
    }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_account_router.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/adapters/api/routers/account_router.py tests/adapters/test_account_router.py
git commit -m "feat: account usage panel shows unlimited quota for owner"
```

---

### Task 7: `v1/news_router_v1` — search cap, export gate, related gate use effective tier

**Files:**
- Modify: `src/adapters/api/routers/v1/news_router_v1.py`
- Modify: `tests/adapters/test_tier_gating.py` (`_make_user` helper gains a `role` param)
- Test: `tests/adapters/test_tier_gating.py`

**Interfaces:**
- Consumes: `user_effective_tier` (Task 3)

- [ ] **Step 1: Update the shared `_make_user` helper**

In `tests/adapters/test_tier_gating.py`, replace the helper (currently lines 18-19):

```python
from src.domain.models.user import UserRole


def _make_user(tier=UserTier.FREE, uid=1, role=UserRole.USER):
    return User(id=uid, email="u@test.com", password_hash="h", tier=tier, role=role)
```

(Add the `UserRole` import next to the existing `from src.domain.models.user import ...` line rather than as a separate statement if there's already one — merge into the existing import.)

- [ ] **Step 2: Write the failing tests**

Add to `tests/adapters/test_tier_gating.py`, in the relevant sections:

```python
def test_v1_search_allows_owner_up_to_200_despite_free_db_tier(app_client):
    mock_service = MagicMock()
    mock_service.hybrid_search.return_value = []
    app_client.app.dependency_overrides[get_news_service] = lambda: mock_service
    app_client.app.dependency_overrides[check_tier_limit] = lambda: _make_user(UserTier.FREE, role=UserRole.OWNER)
    try:
        app_client.post("/api/v1/news/search", json={"query": "test", "n_results": 200})
    finally:
        app_client.app.dependency_overrides.pop(get_news_service, None)
        app_client.app.dependency_overrides.pop(check_tier_limit, None)
    assert mock_service.hybrid_search.call_args[0][1] == 200


def test_v1_related_allowed_for_owner_despite_free_db_tier(app_client):
    mock_service = MagicMock()
    mock_service.get_related.return_value = {"article_id": 1, "related": []}
    app_client.app.dependency_overrides[get_news_service] = lambda: mock_service
    app_client.app.dependency_overrides[check_tier_limit] = lambda: _make_user(UserTier.FREE, role=UserRole.OWNER)
    try:
        resp = app_client.get("/api/v1/news/1/related")
    finally:
        app_client.app.dependency_overrides.pop(get_news_service, None)
        app_client.app.dependency_overrides.pop(check_tier_limit, None)
    assert resp.status_code == 200


def test_v1_export_allowed_for_owner_despite_free_db_tier(app_client):
    mock_service = MagicMock()
    mock_service.export_articles.return_value = []
    app_client.app.dependency_overrides[get_news_service] = lambda: mock_service
    app_client.app.dependency_overrides[check_tier_limit] = lambda: _make_user(UserTier.FREE, role=UserRole.OWNER)
    try:
        resp = app_client.get("/api/v1/news/export")
    finally:
        app_client.app.dependency_overrides.pop(get_news_service, None)
        app_client.app.dependency_overrides.pop(check_tier_limit, None)
    assert resp.status_code == 200
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_tier_gating.py -k owner -v`
Expected: FAIL — search clamps to 10 (Free cap), related/export return 403.

- [ ] **Step 4: Implement in `src/adapters/api/routers/v1/news_router_v1.py`**

Update the import line (line 28) to add `user_effective_tier`:

```python
from src.adapters.api.auth_utils import check_tier_limit, user_effective_tier
```

In `search_news_v1` (around line 92), change:

```python
    cap = TIER_SEARCH_RESULT_CAP[user_effective_tier(user) if user else UserTier.FREE]
```

In `export_news_v1` (around line 139), change:

```python
    if not user or user_effective_tier(user) != UserTier.ENTERPRISE:
```

In `get_related_v1` (around line 180), change:

```python
    if not user or not tier_at_least(user_effective_tier(user), UserTier.PRO):
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_tier_gating.py -v`
Expected: all PASS (existing Free/Pro/Enterprise tests unaffected — `user_effective_tier` returns `user.tier` unchanged for non-owners)

- [ ] **Step 6: Commit**

```bash
git add src/adapters/api/routers/v1/news_router_v1.py tests/adapters/test_tier_gating.py
git commit -m "feat: v1 search/export/related gates use effective tier (owner unlock)"
```

---

### Task 8: Legacy `news_router.py` related gate

**Files:**
- Modify: `src/adapters/api/routers/news_router.py`
- Test: `tests/adapters/test_tier_gating.py`

**Interfaces:**
- Consumes: `user_effective_tier` (Task 3)

- [ ] **Step 1: Write the failing test**

Add to `tests/adapters/test_tier_gating.py`:

```python
def test_legacy_related_allowed_for_owner_despite_free_db_tier(app_client):
    mock_service = MagicMock()
    mock_service.get_related.return_value = {"article_id": 1, "related": []}
    app_client.app.dependency_overrides[get_news_service] = lambda: mock_service
    app_client.app.dependency_overrides[check_tier_limit] = lambda: _make_user(UserTier.FREE, role=UserRole.OWNER)
    try:
        resp = app_client.get("/news/1/related")
    finally:
        app_client.app.dependency_overrides.pop(get_news_service, None)
        app_client.app.dependency_overrides.pop(check_tier_limit, None)
    assert resp.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_tier_gating.py -k legacy_related -v`
Expected: FAIL — 403.

- [ ] **Step 3: Implement in `src/adapters/api/routers/news_router.py`**

Update the auth_utils import (currently `from src.adapters.api.auth_utils import check_tier_limit`):

```python
from src.adapters.api.auth_utils import check_tier_limit, user_effective_tier
```

In `get_related` (around line 98), change:

```python
    if not user or not tier_at_least(user_effective_tier(user), UserTier.PRO):
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_tier_gating.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/adapters/api/routers/news_router.py tests/adapters/test_tier_gating.py
git commit -m "feat: legacy related-articles route honors effective tier"
```

---

### Task 9: `websocket_router.py` — Pro+ gate uses effective tier

**Files:**
- Modify: `src/adapters/api/routers/websocket_router.py`
- Test: `tests/adapters/test_tier_gating.py`

**Interfaces:**
- Consumes: `user_effective_tier` (Task 3)

- [ ] **Step 1: Write the failing test**

Add to `tests/adapters/test_tier_gating.py`:

```python
def test_ws_feed_accepts_owner_despite_free_db_tier(app_client):
    from src.adapters.notifications.websocket_notifier import WebSocketNotifier
    notifier = WebSocketNotifier()
    app_client.app.dependency_overrides[get_optional_user] = lambda: _make_user(UserTier.FREE, role=UserRole.OWNER)
    app_client.app.dependency_overrides[get_notifier] = lambda: notifier
    try:
        with app_client.websocket_connect("/ws/feed") as ws:
            assert notifier.connection_count == 1
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_notifier, None)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_tier_gating.py -k ws_feed_accepts_owner -v`
Expected: FAIL — connection closed with code 1008.

- [ ] **Step 3: Implement in `src/adapters/api/routers/websocket_router.py`**

Update the import (line 12):

```python
from src.adapters.api.auth_utils import get_optional_user, user_effective_tier
```

In `websocket_feed` (around line 30), change:

```python
    if not user or not tier_at_least(user_effective_tier(user), UserTier.PRO):
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_tier_gating.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/adapters/api/routers/websocket_router.py tests/adapters/test_tier_gating.py
git commit -m "feat: /ws/feed live tier gate honors effective tier (owner unlock)"
```

---

### Task 10: `subscription_router.py` — instant-alert gate uses effective tier

**Files:**
- Modify: `src/adapters/api/routers/subscription_router.py`
- Test: `tests/adapters/test_tier_gating.py`

**Interfaces:**
- Consumes: `user_effective_tier` (Task 3)

- [ ] **Step 1: Write the failing test**

Add to `tests/adapters/test_tier_gating.py`:

```python
def test_subscribe_instant_allowed_for_owner_email(app_client):
    mock_repo = _mock_sub_repo()
    mock_users = MagicMock()
    mock_users.get_by_email.return_value = _make_user(UserTier.FREE, role=UserRole.OWNER)
    app_client.app.dependency_overrides[_get_repo] = lambda: mock_repo
    app_client.app.dependency_overrides[_get_user_repo] = lambda: mock_users
    try:
        from unittest.mock import patch
        with patch("src.adapters.api.routers.subscription_router.get_email_adapter") as mock_email:
            mock_email.return_value.send_welcome.return_value = True
            r = app_client.post("/subscriptions/", json={"email": "owner@example.com", "frequency": "instant"})
    finally:
        app_client.app.dependency_overrides.pop(_get_repo, None)
        app_client.app.dependency_overrides.pop(_get_user_repo, None)
    assert r.status_code == 201
```

- [ ] **Step 2: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_tier_gating.py -k subscribe_instant_allowed_for_owner -v`
Expected: FAIL — 403.

- [ ] **Step 3: Implement in `src/adapters/api/routers/subscription_router.py`**

Add a new import line (there is currently no `auth_utils` import in this file):

```python
from src.adapters.api.auth_utils import user_effective_tier
```

In `_assert_instant_allowed` (around line 84), change:

```python
    if not user or not tier_at_least(user_effective_tier(user), UserTier.PRO):
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_tier_gating.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add src/adapters/api/routers/subscription_router.py tests/adapters/test_tier_gating.py
git commit -m "feat: instant keyword-alert gate honors effective tier (owner unlock)"
```

---

### Task 11: `billing_router` — owner gets 400 on checkout, not blocked by unverified email

**Files:**
- Modify: `src/adapters/api/routers/billing_router.py`
- Test: `tests/adapters/test_billing_dev_mode.py`

**Interfaces:**
- Consumes: `has_owner_role` (Task 3)

- [ ] **Step 1: Update the `_make_user` helper to accept a `role`**

In `tests/adapters/test_billing_dev_mode.py`, replace (currently lines 15-16):

```python
from src.domain.models.user import UserRole


def _make_user(tier=UserTier.FREE, email_verified=True, role=UserRole.USER):
    return User(id=1, email="dev@test.com", password_hash="h", tier=tier, email_verified=email_verified, role=role)
```

- [ ] **Step 2: Write the failing test**

Add to `tests/adapters/test_billing_dev_mode.py`:

```python
def test_checkout_rejects_owner_with_400_even_when_unverified(app_client):
    """Owner'ın satın alacağı bir şey yok; email_verified=False olsa da 403
    yerine anlamlı bir 400 alır (unrelated doğrulama gate'ine hiç girmemeli)."""
    owner = _make_user(role=UserRole.OWNER, email_verified=False)
    _override(app_client, owner)
    try:
        with patch("src.adapters.api.routers.billing_router.settings") as ms:
            ms.billing_dev_mode = True
            resp = app_client.post("/billing/checkout", json={
                "tier": "pro", "success_url": "http://x", "cancel_url": "http://x",
            })
    finally:
        app_client.app.dependency_overrides.clear()
    assert resp.status_code == 400
```

(Match whatever teardown pattern `_override`'s sibling tests already use in this file — if they pop specific keys instead of `.clear()`, follow that exact pattern instead.)

- [ ] **Step 3: Run test to verify it fails**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_billing_dev_mode.py -k owner -v`
Expected: FAIL — 403 (blocked by the `email_verified` gate before reaching any owner-specific check).

- [ ] **Step 4: Implement in `src/adapters/api/routers/billing_router.py`**

Update the import (line 24):

```python
from src.adapters.api.auth_utils import get_current_user, has_owner_role
```

In `create_checkout` (around line 82-92), insert the owner check between the tier-validity check and the email-verified check:

```python
    if req.tier not in _PURCHASABLE_TIERS:
        raise HTTPException(status_code=400, detail="Invalid tier. Use 'pro' or 'enterprise'")

    if has_owner_role(current_user):
        raise HTTPException(
            status_code=400,
            detail="Owner hesabı zaten sınırsız erişime sahip, satın alma gerekmez. / Owner accounts already have unlimited access.",
        )

    # v1.15: DNS/MX kontrolü (v1.14) sahte kullanıcı adı + gerçek domain kombinasyonunu
    # yakalayamıyordu — ücretli kademeye yükseltme artık e-posta doğrulaması ister.
    # Free tier'da erişim etkilenmez (bkz. auth_router.py::_send_verification_email).
    # Owner bu şarttan muaftır (yukarıda zaten reddedildi, buraya hiç ulaşmaz).
    if not current_user.email_verified:
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_billing_dev_mode.py tests/adapters/test_billing_router.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/adapters/api/routers/billing_router.py tests/adapters/test_billing_dev_mode.py
git commit -m "feat: billing checkout rejects owner accounts with 400, skips email-verified gate for them"
```

---

### Task 12: `admin_router` — graduated role management

**Files:**
- Modify: `src/adapters/api/routers/admin_router.py`
- Test: `tests/adapters/test_admin_router.py`

**Interfaces:**
- Consumes: `effective_role`, `role_at_least` (domain), `has_owner_role`
- Produces: rewritten `update_user_role` with rank-based authorization

- [ ] **Step 1: Update existing tests that will break under the new logic**

The current handler only calls `repo.update_role`; the new one first calls `repo.get_by_id(user_id)` to compare ranks. Update these three existing tests in `tests/adapters/test_admin_router.py`:

Replace `test_update_user_role_success` (currently lines 166-183):

```python
def test_update_user_role_success(app_client):
    admin = _make_user(id=1, role=UserRole.ADMIN)
    target = _make_user(id=2, role=UserRole.USER)
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_optional_user] = lambda: admin
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_by_id.return_value = target
            repo.update_role.return_value = True
            MockRepo.return_value = repo
            resp = app_client.patch("/admin/users/2/role", json={"role": "moderator"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    assert resp.json() == {"id": 2, "role": "moderator"}
    repo.update_role.assert_called_once_with(2, "moderator")
```

Replace `test_update_user_role_rejects_self_demotion` (currently lines 197-206) — the rule is now "nobody changes their own role", regardless of target role:

```python
def test_update_user_role_rejects_self_change(app_client):
    """Kimse kendi rolünü kendisi değiştiremez (kilitlenmeyi önler)."""
    admin = _make_user(id=1, role=UserRole.ADMIN)
    app_client.app.dependency_overrides[get_optional_user] = lambda: admin
    try:
        resp = app_client.patch("/admin/users/1/role", json={"role": "moderator"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)

    assert resp.status_code == 400
```

Replace `test_update_user_role_404_for_missing_user` (currently lines 209-224) — 404 now comes from the target lookup, not from `update_role`'s return value:

```python
def test_update_user_role_404_for_missing_user(app_client):
    admin = _make_user(id=1, role=UserRole.ADMIN)
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_optional_user] = lambda: admin
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_by_id.return_value = None
            MockRepo.return_value = repo
            resp = app_client.patch("/admin/users/999/role", json={"role": "admin"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 404
```

- [ ] **Step 2: Write the new graduated-matrix tests**

Add to `tests/adapters/test_admin_router.py`:

```python
def _target(id, role):
    return _make_user(id=id, role=role)


def test_moderator_can_promote_plain_user_to_moderator(app_client):
    moderator = _make_user(id=1, role=UserRole.MODERATOR)
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_optional_user] = lambda: moderator
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_by_id.return_value = _target(2, UserRole.USER)
            repo.update_role.return_value = True
            MockRepo.return_value = repo
            resp = app_client.patch("/admin/users/2/role", json={"role": "moderator"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_db, None)
    assert resp.status_code == 200


def test_moderator_cannot_touch_another_moderator(app_client):
    moderator = _make_user(id=1, role=UserRole.MODERATOR)
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_optional_user] = lambda: moderator
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_by_id.return_value = _target(2, UserRole.MODERATOR)
            MockRepo.return_value = repo
            resp = app_client.patch("/admin/users/2/role", json={"role": "user"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_db, None)
    assert resp.status_code == 403


def test_admin_can_promote_moderator_to_admin(app_client):
    admin = _make_user(id=1, role=UserRole.ADMIN)
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_optional_user] = lambda: admin
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_by_id.return_value = _target(2, UserRole.MODERATOR)
            repo.update_role.return_value = True
            MockRepo.return_value = repo
            resp = app_client.patch("/admin/users/2/role", json={"role": "admin"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_db, None)
    assert resp.status_code == 200


def test_admin_cannot_touch_another_admin(app_client):
    admin = _make_user(id=1, role=UserRole.ADMIN)
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_optional_user] = lambda: admin
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_by_id.return_value = _target(2, UserRole.ADMIN)
            MockRepo.return_value = repo
            resp = app_client.patch("/admin/users/2/role", json={"role": "user"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_db, None)
    assert resp.status_code == 403


def test_owner_can_demote_an_admin(app_client):
    owner = _make_user(id=1, role=UserRole.OWNER)
    db = _make_mock_db()
    app_client.app.dependency_overrides[get_optional_user] = lambda: owner
    app_client.app.dependency_overrides[get_db] = lambda: db
    try:
        with patch("src.adapters.api.routers.admin_router.UserRepository") as MockRepo:
            repo = MagicMock()
            repo.get_by_id.return_value = _target(2, UserRole.ADMIN)
            repo.update_role.return_value = True
            MockRepo.return_value = repo
            resp = app_client.patch("/admin/users/2/role", json={"role": "user"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
        app_client.app.dependency_overrides.pop(get_db, None)
    assert resp.status_code == 200


def test_owner_role_can_never_be_assigned(app_client):
    admin = _make_user(id=1, role=UserRole.ADMIN)
    app_client.app.dependency_overrides[get_optional_user] = lambda: admin
    try:
        resp = app_client.patch("/admin/users/2/role", json={"role": "owner"})
    finally:
        app_client.app.dependency_overrides.pop(get_optional_user, None)
    assert resp.status_code == 400
```

- [ ] **Step 3: Run tests to verify the new/updated ones fail**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_admin_router.py -k "role" -v`
Expected: FAIL — old handler has no rank comparison, `repo.get_by_id` never called, "owner" string currently rejected only because it's not yet a valid enum value on the request side (that part might already 400, but the matrix tests fail).

- [ ] **Step 4: Implement in `src/adapters/api/routers/admin_router.py`**

Update the import (line 22 and 26):

```python
from src.adapters.api.auth_utils import require_admin, require_moderator, get_current_user, effective_role
from src.domain.models.sponsor import Sponsor
from src.domain.models.user import User, UserRole, role_at_least
```

Replace `update_user_role` (currently lines 86-105):

```python
_ASSIGNABLE_ROLES = (UserRole.USER.value, UserRole.MODERATOR.value, UserRole.ADMIN.value)


@router.patch("/users/{user_id}/role", dependencies=[Depends(require_admin)])
def update_user_role(
    user_id: int,
    req: RoleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Başka bir kullanıcının rolünü değiştirir — kademeli yetki (v2.1).

    Kurallar: (1) owner rolü asla atanamaz — tek kaynak OWNER_EMAILS env;
    (2) kimse kendi rolünü kendisi değiştiremez; (3) hedefin mevcut rolü
    istek sahibinden KESİNLİKLE düşük olmalı (eşit/üst roldekine dokunulamaz);
    (4) atanacak yeni rol istek sahibinin rolünü AŞAMAZ. Owner herkesi
    yönetir, kendisine kimse dokunamaz (rank'i herkesten yüksek olduğu için
    kural 3 otomatik sağlanır).
    """
    if req.role not in _ASSIGNABLE_ROLES:
        raise HTTPException(status_code=400, detail="role must be user, moderator or admin")
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Kendi rolünüzü kendiniz değiştiremezsiniz.")

    repo = UserRepository(db)
    target = repo.get_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    actor_role = effective_role(current_user)
    target_role = effective_role(target)
    # Hedefin rolü actor'dan KESİNLİKLE düşük olmalı — role_at_least(target, actor)
    # true ise hedef actor'a eşit/üst demektir, izin verilmez.
    if role_at_least(target_role, actor_role):
        raise HTTPException(status_code=403, detail="Bu kullanıcının rolünü değiştirme yetkiniz yok")
    # Atanacak rol actor'un rolünü aşamaz — role_at_least(actor, new_role) false ise reddedilir.
    if not role_at_least(actor_role, req.role):
        raise HTTPException(status_code=403, detail="Bu kullanıcının rolünü değiştirme yetkiniz yok")

    if not repo.update_role(user_id, req.role):
        raise HTTPException(status_code=404, detail="User not found")
    logger.info("Rol değişti: user_id=%s → %s (işlemi yapan: %s)", user_id, req.role, current_user.email)
    return {"id": user_id, "role": req.role}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_admin_router.py -v`
Expected: all PASS

- [ ] **Step 6: Run the full backend suite for regressions before moving on (this task touches shared authz logic)**

Run: `venv\Scripts\python.exe -m pytest tests/ -v --timeout=120`
Expected: all PASS (~570+ tests)

- [ ] **Step 7: Commit**

```bash
git add src/adapters/api/routers/admin_router.py tests/adapters/test_admin_router.py
git commit -m "feat: graduated role management — rank-based authorization, owner unassignable"
```

---

### Task 13: `email_adapter.py` — extract `_HtmlEmailAdapter` base (DRY refactor)

**Files:**
- Modify: `src/adapters/notifications/email_adapter.py`
- Test: `tests/adapters/test_email_adapter.py` (no new tests — this task is a behavior-preserving refactor; existing tests are the safety net)

**Interfaces:**
- Produces: `_HtmlEmailAdapter(EmailPort)` abstract base with `_deliver(to, subject, html) -> bool` as the only method concrete subclasses implement

- [ ] **Step 1: Run the existing email adapter tests to establish a green baseline**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_email_adapter.py -v`
Expected: all PASS (this is the pre-refactor baseline — no code changes yet)

- [ ] **Step 2: Implement the refactor in `src/adapters/notifications/email_adapter.py`**

Insert the new base class right before `class ResendEmailAdapter(EmailPort):` (currently line 218):

```python
class _HtmlEmailAdapter(EmailPort):
    """ResendEmailAdapter ve SmtpEmailAdapter'ın paylaştığı gövde.

    Beş send_* metodunu bir kez tanımlar, somut sınıflar sadece _deliver()'ı
    implemente eder — v2.1 refactor, önceden her adapter kendi beş metodunu
    ayrı ayrı tanımlıyordu (Resend'de _post'a yönlendiren tekrar eden kod).
    """

    def _deliver(self, to: str, subject: str, html: str) -> bool:
        raise NotImplementedError

    def send_digest(self, to: str, articles: List[Article], language: str, sponsor=None) -> bool:
        return self._deliver(to, _t(language, "digest_subject"), _digest_html(to, articles, language, sponsor))

    def send_alert(self, to: str, article: Article, matched_keyword: str, language: str) -> bool:
        subject = f"{_t(language, 'alert_subject_prefix')}: {matched_keyword}"
        return self._deliver(to, subject, _alert_html(article, matched_keyword, language))

    def send_welcome(self, to: str, language: str) -> bool:
        return self._deliver(to, _t(language, "welcome_subject"), _welcome_html(language))

    def send_password_reset(self, to: str, reset_url: str, language: str) -> bool:
        return self._deliver(to, _t(language, "reset_subject"), _password_reset_html(reset_url, language))

    def send_verification(self, to: str, verify_url: str, language: str) -> bool:
        return self._deliver(to, _t(language, "verify_subject"), _verification_html(verify_url, language))
```

Replace `class ResendEmailAdapter(EmailPort):` in full (currently lines 218-257) with:

```python
class ResendEmailAdapter(_HtmlEmailAdapter):
    """Production adapter using Resend (https://resend.com)."""

    _API_URL = "https://api.resend.com/emails"

    def __init__(self):
        self._api_key = settings.resend_api_key
        self._from = settings.email_from

    def _deliver(self, to: str, subject: str, html: str) -> bool:
        try:
            r = requests.post(
                self._API_URL,
                headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                json={"from": self._from, "to": [to], "subject": subject, "html": html},
                timeout=10,
            )
            if r.status_code in (200, 201):
                return True
            logger.error("Resend API hatası %s: %s", r.status_code, r.text[:200])
            return False
        except Exception as e:
            logger.error("Email gönderilemedi (%s): %s", to, e)
            return False
```

- [ ] **Step 3: Run tests to verify nothing broke**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_email_adapter.py -v`
Expected: all PASS unchanged — `send_digest`/`send_alert`/etc. now resolve through `_HtmlEmailAdapter`, calling `self._deliver` which is `ResendEmailAdapter`'s renamed `_post`; external behavior identical.

- [ ] **Step 4: Commit**

```bash
git add src/adapters/notifications/email_adapter.py
git commit -m "refactor: extract _HtmlEmailAdapter base class (DRY, behavior-preserving)"
```

---

### Task 14: `SmtpEmailAdapter` + `get_email_adapter()` selection matrix

**Files:**
- Modify: `src/adapters/notifications/email_adapter.py`
- Test: `tests/adapters/test_email_adapter.py`

**Interfaces:**
- Consumes: `_HtmlEmailAdapter` (Task 13), `settings.email_provider/smtp_*` (Task 2)
- Produces: `SmtpEmailAdapter`, updated `get_email_adapter()`

- [ ] **Step 1: Update the two existing selection tests (they'll break under the new auto-detection logic)**

Replace in `tests/adapters/test_email_adapter.py`:

```python
def test_get_email_adapter_returns_console_without_api_key():
    with patch("src.adapters.notifications.email_adapter.settings") as mock_settings:
        mock_settings.email_provider = "auto"
        mock_settings.resend_api_key = ""
        mock_settings.smtp_user = ""
        mock_settings.smtp_password = ""
        adapter = get_email_adapter()
    assert isinstance(adapter, ConsoleEmailAdapter)


def test_get_email_adapter_returns_resend_with_api_key():
    with patch("src.adapters.notifications.email_adapter.settings") as mock_settings:
        mock_settings.email_provider = "auto"
        mock_settings.resend_api_key = "re_prod_key"
        mock_settings.email_from = "NexStream <x@y.com>"
        mock_settings.smtp_user = ""
        mock_settings.smtp_password = ""
        adapter = get_email_adapter()
    assert isinstance(adapter, ResendEmailAdapter)
```

- [ ] **Step 2: Write the new failing tests**

Add to `tests/adapters/test_email_adapter.py`:

```python
from src.adapters.notifications.email_adapter import SmtpEmailAdapter


def test_smtp_adapter_sends_via_starttls_and_login():
    with patch("src.adapters.notifications.email_adapter.settings") as mock_settings:
        mock_settings.smtp_host = "smtp.gmail.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_user = "me@gmail.com"
        mock_settings.smtp_password = "app-password"
        mock_settings.smtp_from = ""
        mock_settings.email_from = "NexStream <no-reply@test.com>"
        mock_settings.smtp_starttls = True
        adapter = SmtpEmailAdapter()

        mock_server = MagicMock()
        mock_smtp_cm = MagicMock()
        mock_smtp_cm.__enter__.return_value = mock_server
        with patch("smtplib.SMTP", return_value=mock_smtp_cm) as mock_smtp:
            result = adapter.send_welcome("user@test.com", "TR")

    assert result is True
    mock_smtp.assert_called_once_with("smtp.gmail.com", 587, timeout=10)
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("me@gmail.com", "app-password")
    mock_server.sendmail.assert_called_once()
    call_args = mock_server.sendmail.call_args[0]
    assert call_args[0] == "me@gmail.com"
    assert call_args[1] == ["user@test.com"]


def test_smtp_adapter_skips_starttls_when_disabled():
    with patch("src.adapters.notifications.email_adapter.settings") as mock_settings:
        mock_settings.smtp_host = "localhost"
        mock_settings.smtp_port = 25
        mock_settings.smtp_user = "me@test.com"
        mock_settings.smtp_password = "x"
        mock_settings.smtp_from = ""
        mock_settings.email_from = "NexStream <no-reply@test.com>"
        mock_settings.smtp_starttls = False
        adapter = SmtpEmailAdapter()
        mock_server = MagicMock()
        mock_smtp_cm = MagicMock()
        mock_smtp_cm.__enter__.return_value = mock_server
        with patch("smtplib.SMTP", return_value=mock_smtp_cm):
            adapter.send_welcome("user@test.com", "TR")
    mock_server.starttls.assert_not_called()


def test_smtp_adapter_returns_false_on_exception_not_raises():
    with patch("src.adapters.notifications.email_adapter.settings") as mock_settings:
        mock_settings.smtp_host = "smtp.gmail.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_user = "me@gmail.com"
        mock_settings.smtp_password = "bad"
        mock_settings.smtp_from = ""
        mock_settings.email_from = "NexStream <no-reply@test.com>"
        mock_settings.smtp_starttls = True
        adapter = SmtpEmailAdapter()
        with patch("smtplib.SMTP", side_effect=Exception("auth failed")):
            result = adapter.send_welcome("user@test.com", "TR")
    assert result is False


def test_get_email_adapter_auto_prefers_smtp_over_resend_when_both_configured():
    with patch("src.adapters.notifications.email_adapter.settings") as mock_settings:
        mock_settings.email_provider = "auto"
        mock_settings.smtp_user = "me@gmail.com"
        mock_settings.smtp_password = "app-password"
        mock_settings.resend_api_key = "re_also_set"
        adapter = get_email_adapter()
    assert isinstance(adapter, SmtpEmailAdapter)


def test_get_email_adapter_explicit_provider_forces_console():
    with patch("src.adapters.notifications.email_adapter.settings") as mock_settings:
        mock_settings.email_provider = "console"
        mock_settings.smtp_user = "me@gmail.com"
        mock_settings.smtp_password = "app-password"
        mock_settings.resend_api_key = "re_set"
        adapter = get_email_adapter()
    assert isinstance(adapter, ConsoleEmailAdapter)


def test_get_email_adapter_explicit_provider_forces_smtp():
    with patch("src.adapters.notifications.email_adapter.settings") as mock_settings:
        mock_settings.email_provider = "smtp"
        mock_settings.smtp_user = ""
        mock_settings.smtp_password = ""
        adapter = get_email_adapter()
    assert isinstance(adapter, SmtpEmailAdapter)
```

- [ ] **Step 3: Run tests to verify the new/updated ones fail**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_email_adapter.py -v`
Expected: FAIL — `ImportError: cannot import name 'SmtpEmailAdapter'`.

- [ ] **Step 4: Implement in `src/adapters/notifications/email_adapter.py`**

Add to the top imports (after `import requests`, line 17):

```python
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
```

Add `SmtpEmailAdapter` right after `ResendEmailAdapter` (after the class from Task 13), before `get_email_adapter()`:

```python
class SmtpEmailAdapter(_HtmlEmailAdapter):
    """Gmail (veya herhangi bir STARTTLS destekleyen SMTP sağlayıcısı) ile gerçek gönderim.

    Resend'in aksine domain doğrulaması istemez, TÜM alıcılara ulaşır — günlük
    limit Gmail'in kendi kotasından gelir (app password ile ~500 mail/gün).
    """

    def __init__(self):
        self._host = settings.smtp_host
        self._port = settings.smtp_port
        self._user = settings.smtp_user
        self._password = settings.smtp_password
        self._from = settings.smtp_from or settings.email_from
        self._starttls = settings.smtp_starttls

    def _deliver(self, to: str, subject: str, html: str) -> bool:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._from
        msg["To"] = to
        msg.attach(MIMEText(html, "html", "utf-8"))

        try:
            with smtplib.SMTP(self._host, self._port, timeout=10) as server:
                if self._starttls:
                    server.starttls()
                server.login(self._user, self._password)
                server.sendmail(self._user, [to], msg.as_string())
            return True
        except Exception as e:
            logger.error("SMTP e-posta gönderilemedi (%s): %s", to, e)
            return False
```

Replace `get_email_adapter()` (currently lines 260-263):

```python
def get_email_adapter() -> EmailPort:
    """Hangi adapter'ın kullanılacağını seçer — EMAIL_PROVIDER ile yönlendirilebilir.

    auto (varsayılan): SMTP kimlikleri doluysa SMTP → RESEND_API_KEY doluysa
    Resend → Console. Açık değerler (smtp/resend/console) test/hata ayıklama
    için zorlama sağlar.
    """
    provider = (settings.email_provider or "auto").lower()
    if provider == "console":
        return ConsoleEmailAdapter()
    if provider == "smtp":
        return SmtpEmailAdapter()
    if provider == "resend":
        return ResendEmailAdapter()
    if settings.smtp_user and settings.smtp_password:
        return SmtpEmailAdapter()
    if settings.resend_api_key:
        return ResendEmailAdapter()
    return ConsoleEmailAdapter()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_email_adapter.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/adapters/notifications/email_adapter.py tests/adapters/test_email_adapter.py
git commit -m "feat: add SmtpEmailAdapter and EMAIL_PROVIDER auto-selection matrix"
```

---

### Task 15: `main.py` — production console-fallback warning

**Files:**
- Modify: `src/main.py`
- Test: new `tests/adapters/test_main_email_warning.py`

**Interfaces:**
- Produces: `warn_if_email_disabled(environment: str, adapter: EmailPort) -> None`

- [ ] **Step 1: Write the failing tests**

Create `tests/adapters/test_main_email_warning.py`:

```python
import logging
from src.adapters.notifications.email_adapter import ConsoleEmailAdapter, ResendEmailAdapter


def test_warn_if_email_disabled_logs_error_in_production(app_client, caplog):
    """`app_client` reloads src.main with all I/O mocked (see conftest.py) — reuse
    that already-imported, safely-patched module instead of a bare `import src.main`."""
    import src.main
    with caplog.at_level(logging.ERROR, logger="src.main"):
        src.main.warn_if_email_disabled("production", ConsoleEmailAdapter())
    assert any("mail" in r.message.lower() or "console" in r.message.lower() for r in caplog.records)


def test_warn_if_email_disabled_silent_in_development(app_client, caplog):
    import src.main
    with caplog.at_level(logging.ERROR, logger="src.main"):
        src.main.warn_if_email_disabled("development", ConsoleEmailAdapter())
    assert caplog.records == []


def test_warn_if_email_disabled_silent_when_adapter_is_not_console(app_client, caplog):
    import src.main
    with caplog.at_level(logging.ERROR, logger="src.main"):
        src.main.warn_if_email_disabled("production", ResendEmailAdapter())
    assert caplog.records == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_main_email_warning.py -v`
Expected: FAIL — `AttributeError: module 'src.main' has no attribute 'warn_if_email_disabled'`.

- [ ] **Step 3: Implement in `src/main.py`**

Add the import (near the other adapter imports, after line 41):

```python
from src.adapters.notifications.email_adapter import get_email_adapter, ConsoleEmailAdapter
```

Add the function and its call right after the `kafka_adapter = ...` line (line 50):

```python
def warn_if_email_disabled(environment: str, adapter) -> None:
    """Prod'da e-posta adapter'ı Console'a düşerse artık sessiz kalmaz.

    Kök nedeni bulunan sorun: RESEND_API_KEY boş bırakılınca get_email_adapter()
    sessizce ConsoleEmailAdapter'a düşüyordu ve hiçbir yerde iz kalmıyordu —
    doğrulama, şifre sıfırlama, digest, keyword alert'lerin TAMAMI etkileniyordu.
    Uygulama durdurulmaz (mail altyapısı çökünce site de çökmemeli, mevcut
    fail-open felsefesiyle tutarlı) — sadece net bir hata logu bırakılır.
    """
    if environment != "production":
        return
    if isinstance(adapter, ConsoleEmailAdapter):
        log.error(
            "E-posta adapter'ı Console'a düştü — production'da HİÇBİR mail gönderilmiyor "
            "(SMTP_USER/SMTP_PASSWORD veya RESEND_API_KEY eksik/hatalı)."
        )


warn_if_email_disabled(settings.environment, get_email_adapter())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_main_email_warning.py -v`
Expected: all PASS

- [ ] **Step 5: Run the full app-boot-adjacent suite for regressions**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/ -v --timeout=120`
Expected: all PASS (this task adds a module-level call executed on every `app_client` reload — must not slow down or break other tests; if it does, check that `get_email_adapter()` is cheap and side-effect-free at construction time, which it is — no network I/O happens until `_deliver` is called)

- [ ] **Step 6: Commit**

```bash
git add src/main.py tests/adapters/test_main_email_warning.py
git commit -m "feat: log an explicit error when production silently falls back to console email"
```

---

### Task 16: `/health` — expose `email` field

**Files:**
- Modify: `src/adapters/api/routers/health_router.py`
- Test: `tests/adapters/test_health_router.py`

**Interfaces:**
- Produces: `_check_email() -> str`, `/health` response gains `"email"` key

- [ ] **Step 1: Update the existing "all required fields" test**

Replace `test_health_response_has_all_required_fields` (currently lines 63-67):

```python
def test_health_response_has_all_required_fields():
    result = _call_health(chromadb=("ok", 100))
    assert set(result.keys()) == {
        "status", "db", "kafka", "chromadb", "embedder", "email", "indexed_articles"
    }
```

- [ ] **Step 2: Write the new failing tests**

Add to `tests/adapters/test_health_router.py`:

```python
def test_check_email_reports_smtp():
    from src.adapters.api.routers.health_router import _check_email
    from src.adapters.notifications.email_adapter import SmtpEmailAdapter
    with patch("src.adapters.api.routers.health_router.get_email_adapter", return_value=SmtpEmailAdapter()):
        assert _check_email() == "smtp"


def test_check_email_reports_resend():
    from src.adapters.api.routers.health_router import _check_email
    from src.adapters.notifications.email_adapter import ResendEmailAdapter
    with patch("src.adapters.api.routers.health_router.get_email_adapter", return_value=ResendEmailAdapter()):
        assert _check_email() == "resend"


def test_check_email_reports_console_with_warning_suffix():
    from src.adapters.api.routers.health_router import _check_email
    from src.adapters.notifications.email_adapter import ConsoleEmailAdapter
    with patch("src.adapters.api.routers.health_router.get_email_adapter", return_value=ConsoleEmailAdapter()):
        assert _check_email() == "console (mail gönderilmiyor)"


def test_health_includes_email_field_without_affecting_status():
    """email alanı bilgilendirici — dev'de console olması status'u degrade etmemeli."""
    result = _call_health(chromadb=("ok", 1))
    assert "email" in result
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_health_router.py -v`
Expected: FAIL — `_check_email` doesn't exist yet, `"email"` missing from response.

- [ ] **Step 4: Implement in `src/adapters/api/routers/health_router.py`**

Add the import (after `import chromadb`, line 17):

```python
from src.adapters.notifications.email_adapter import get_email_adapter, SmtpEmailAdapter, ResendEmailAdapter
```

Add `_check_email` right after `_check_embedder` (after line 66):

```python
def _check_email() -> str:
    """Hangi e-posta adapter'ının aktif olduğunu raporlar — sessiz Console
    düşüşünün artık /health'te tek bakışta görünür olması için (v2.1)."""
    adapter = get_email_adapter()
    if isinstance(adapter, SmtpEmailAdapter):
        return "smtp"
    if isinstance(adapter, ResendEmailAdapter):
        return "resend"
    return "console (mail gönderilmiyor)"
```

Update `health_check` (around lines 87-103) — add the call and the response key, but keep it **out** of `all_ok` (informational, not a failure signal):

```python
def health_check(request: Request):
    db_status              = _check_db()
    kafka_status           = _check_kafka()
    chroma_status, indexed = _check_chromadb()

    embedder_status        = _check_embedder()
    email_status            = _check_email()

    all_ok = all(s == "ok" for s in [db_status, kafka_status, chroma_status, embedder_status])

    return {
        "status":           "ok" if all_ok else "degraded",
        "db":               db_status,
        "kafka":            kafka_status,
        "chromadb":         chroma_status,
        "embedder":         embedder_status,
        "email":            email_status,
        "indexed_articles": indexed,
    }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `venv\Scripts\python.exe -m pytest tests/adapters/test_health_router.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add src/adapters/api/routers/health_router.py tests/adapters/test_health_router.py
git commit -m "feat: /health reports which email adapter is active"
```

---

### Task 17: Run the full backend suite once, end to end

**Files:** none (verification-only checkpoint before moving to frontend)

- [ ] **Step 1: Run everything**

Run: `venv\Scripts\python.exe -m pytest tests/ -v --timeout=120`
Expected: all tests PASS (backend count should be roughly 553 + ~45 new/modified from Tasks 1-16)

- [ ] **Step 2: If anything fails, stop and fix before continuing to the frontend tasks — do not proceed with a red backend.**

---

### Task 18: Frontend — `types.ts` gains `owner` role + `is_owner`/`effective_tier`

**Files:**
- Modify: `frontend/lib/types.ts`

**Interfaces:**
- Produces: `Role` includes `"owner"`, `User` gains `is_owner?: boolean` and `effective_tier?: Tier`

- [ ] **Step 1: Edit `frontend/lib/types.ts`**

Update the `Role` type (line 5):

```typescript
export type Role = "user" | "moderator" | "admin" | "owner";
```

Update the `User` interface (lines 7-17) — add two fields after `is_moderator`:

```typescript
export interface User {
  id: number;
  email: string;
  name: string;
  tier: Tier;
  role?: Role;                 // v1.13: yetki hiyerarşisi (backend hesaplar, ADMIN_EMAILS dahil)
  is_admin?: boolean;          // geriye dönük uyumluluk — role === "admin" ile aynı
  is_moderator?: boolean;      // role moderator VEYA admin VEYA owner
  is_owner?: boolean;          // v2.1: OWNER_EMAILS bootstrap veya role="owner"
  effective_tier?: Tier;       // v2.1: owner için her zaman "enterprise", diğerlerinde tier ile aynı
  email_verified?: boolean;    // v1.15: Free tier erişimini kısıtlamaz, sadece ücretli yükseltme ister
  created_at?: string;
}
```

- [ ] **Step 2: Verify with the TypeScript compiler**

Run: `cd frontend; npx tsc --noEmit` (only if the frontend dev container is NOT currently running — see CLAUDE.md warning about `.next` collisions; if unsure, ask the user or check `docker ps` for `nexstream_frontend`)
Expected: no new errors (this is an additive-only type change)

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/types.ts
git commit -m "feat(frontend): add owner role and effective_tier to User type"
```

---

### Task 19: Frontend — `i18n.ts` owner-badge and role labels

**Files:**
- Modify: `frontend/lib/i18n.ts`

**Interfaces:**
- Produces: `UI.TR.ownerBadge`, `UI.EN.ownerBadge`, `UI.TR.roleOwner`, `UI.EN.roleOwner`

- [ ] **Step 1: Edit `frontend/lib/i18n.ts`**

In the `TR` block, next to the existing `roleUser: "Kullanıcı", roleModerator: "Moderatör", roleAdmin: "Admin",` line (line 193), add:

```typescript
    roleUser: "Kullanıcı", roleModerator: "Moderatör", roleAdmin: "Admin", roleOwner: "Kurucu",
    ownerBadge: "Kurucu",
```

In the `EN` block, next to `roleUser: "User", roleModerator: "Moderator", roleAdmin: "Admin",` (line 365), add:

```typescript
    roleUser: "User", roleModerator: "Moderator", roleAdmin: "Admin", roleOwner: "Owner",
    ownerBadge: "Founder",
```

- [ ] **Step 2: Verify with the TypeScript compiler**

Run: `cd frontend; npx tsc --noEmit` (respecting the same container-collision caveat as Task 18)
Expected: no new errors

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/i18n.ts
git commit -m "feat(frontend): add owner badge and role label i18n keys"
```

---

### Task 20: Frontend — `TierBadge` owner variant

**Files:**
- Modify: `frontend/components/TierBadge.tsx`

**Interfaces:**
- Consumes: `UI` (Task 19)
- Produces: `TierBadge` accepts an optional `isOwner` prop

- [ ] **Step 1: Edit `frontend/components/TierBadge.tsx`**

Replace the full file content:

```tsx
import type { Tier } from "@/lib/types";
import { UI } from "@/lib/i18n";

const MAP: Record<Tier, { labelTR: string; labelEN: string; style: React.CSSProperties }> = {
  free:       { labelTR: "Ücretsiz", labelEN: "Free",       style: { background: "rgba(120,130,150,.12)", color: "var(--text2)",  borderColor: "var(--border2)",   borderWidth: 1 } },
  pro:        { labelTR: "Pro",       labelEN: "Pro",        style: { background: "var(--accent-soft)",    color: "var(--accent)",  borderColor: "var(--accent-line)", borderWidth: 1 } },
  enterprise: { labelTR: "Kurumsal", labelEN: "Enterprise", style: { background: "var(--accent-soft)",    color: "var(--accent2)", borderColor: "var(--border2)",   borderWidth: 1 } },
};

const ICONS: Record<Tier, string> = { free: "○", pro: "◈", enterprise: "◆" };

export function TierBadge({ tier, lang = "TR", isOwner = false }: { tier: Tier; lang?: "TR" | "EN"; isOwner?: boolean }) {
  if (isOwner) {
    return (
      <span className="badge" style={{ background: "var(--accent-soft)", color: "var(--accent)", borderColor: "var(--accent-line)", borderWidth: 1 }}>
        ★ {UI[lang].ownerBadge}
      </span>
    );
  }
  const t = MAP[tier] ?? MAP.free;
  return (
    <span className="badge" style={t.style}>
      {ICONS[tier]} {lang === "EN" ? t.labelEN : t.labelTR}
    </span>
  );
}
```

- [ ] **Step 2: Verify with the TypeScript compiler**

Run: `cd frontend; npx tsc --noEmit`
Expected: no new errors

- [ ] **Step 3: Commit**

```bash
git add frontend/components/TierBadge.tsx
git commit -m "feat(frontend): TierBadge renders a distinct owner variant"
```

---

### Task 21: Frontend — account page + `EmailVerifyBanner` owner exemptions

**Files:**
- Modify: `frontend/app/account/page.tsx`
- Modify: `frontend/components/EmailVerifyBanner.tsx`

**Interfaces:**
- Consumes: `TierBadge` (Task 20), `User.is_owner`/`effective_tier` (Task 18)

- [ ] **Step 1: Edit `frontend/components/EmailVerifyBanner.tsx`**

Change the early-return guard (line 21) from:

```typescript
  if (!user || user.email_verified || dismissed) return null;
```

to:

```typescript
  if (!user || user.email_verified || user.is_owner || dismissed) return null;
```

- [ ] **Step 2: Edit `frontend/app/account/page.tsx`**

Change the badge at line 205 from:

```tsx
              <TierBadge tier={user.tier} lang={lang} />
```

to:

```tsx
              <TierBadge tier={(user.effective_tier ?? user.tier) as Tier} lang={lang} isOwner={user.is_owner} />
```

(Add `Tier` to the existing type-only import from `@/lib/types` at the top of the file if it isn't already imported.)

Change the upgrade/billing block. Currently (lines 358-402) it's:

```tsx
        {/* Upgrade / billing */}
        {user.tier === "free" ? (
          ... upgrade card ...
        ) : (
          ... billing management card ...
        )}
```

Wrap the whole conditional so owners see neither card (they have nothing to upgrade and no Stripe customer record to manage):

```tsx
        {/* Upgrade / billing — owner'a hiç gösterilmez, satın alınacak/yönetilecek bir şeyi yok */}
        {!user.is_owner && (
          user.tier === "free" ? (
            ... upgrade card (unchanged) ...
          ) : (
            ... billing management card (unchanged) ...
          )
        )}
```

(Keep the inner card JSX exactly as-is — only the outer wrapping condition changes, from `user.tier === "free" ? (...) : (...)` to `!user.is_owner && (user.tier === "free" ? (...) : (...))`.)

- [ ] **Step 3: Verify with the TypeScript compiler**

Run: `cd frontend; npx tsc --noEmit`
Expected: no new errors

- [ ] **Step 4: Commit**

```bash
git add frontend/app/account/page.tsx frontend/components/EmailVerifyBanner.tsx
git commit -m "feat(frontend): hide verify banner and upgrade/billing cards for owner"
```

---

### Task 22: Frontend — `NavbarImpl` badge uses effective tier + owner

**Files:**
- Modify: `frontend/components/NavbarImpl.tsx`

**Interfaces:**
- Consumes: `TierBadge` (Task 20)

- [ ] **Step 1: Edit `frontend/components/NavbarImpl.tsx`**

At both call sites (lines 258 and 414), change:

```tsx
                  <TierBadge tier={user.tier} lang={lang} />
```

to:

```tsx
                  <TierBadge tier={(user.effective_tier ?? user.tier) as Tier} lang={lang} isOwner={user.is_owner} />
```

(Add `Tier` to the existing `@/lib/types` import at the top of the file if not already present.)

- [ ] **Step 2: Verify with the TypeScript compiler**

Run: `cd frontend; npx tsc --noEmit`
Expected: no new errors

- [ ] **Step 3: Commit**

```bash
git add frontend/components/NavbarImpl.tsx
git commit -m "feat(frontend): navbar tier badge reflects effective tier and owner status"
```

---

### Task 23: Frontend — `admin/users` graduated role select

**Files:**
- Modify: `frontend/app/admin/users/page.tsx`

**Interfaces:**
- Consumes: `Role` (Task 18), `UI.roleOwner` (Task 19)

- [ ] **Step 1: Edit `frontend/app/admin/users/page.tsx`**

Replace the constants near the top (lines 20-27):

```tsx
const TIER_VALUES = ["", "free", "pro", "enterprise"];
const ROLE_RANK: Record<Role, number> = { user: 0, moderator: 1, admin: 2, owner: 3 };
const ASSIGNABLE_ROLES: Role[] = ["user", "moderator", "admin"]; // owner asla atanamaz

const ROLE_STYLE: Record<Role, React.CSSProperties> = {
  user:      { background: "rgba(120,130,150,.12)", color: "var(--text2)", borderColor: "var(--border2)" },
  moderator: { background: "var(--neu-bg)",          color: "var(--neu)",  borderColor: "var(--neu)" },
  admin:     { background: "var(--accent-soft)",     color: "var(--accent)", borderColor: "var(--accent-line)" },
  owner:     { background: "var(--accent-soft)",     color: "var(--accent2)", borderColor: "var(--accent-line)" },
};
```

Update `roleLabel` inside the component (line 33) to include owner:

```tsx
  const roleLabel: Record<Role, string> = { user: t.roleUser, moderator: t.roleModerator, admin: t.roleAdmin, owner: t.roleOwner };
```

Update the `isAdmin` line (line 35) — it's no longer used to gate the select (rank comparison replaces it), but the auth-bar section (line 91) still needs `isModerator`. Remove `isAdmin` if nothing else in the file uses it after this change (check with a search inside the file before deleting it); if it's genuinely unused post-edit, drop the line — otherwise leave it.

Add a per-row helper right before the `return` statement (after the `payingCount` line, ~line 81):

```tsx
  const actorRank = ROLE_RANK[(user?.role ?? "user") as Role] ?? 0;
  const assignableForActor = ASSIGNABLE_ROLES.filter((r) => ROLE_RANK[r] <= actorRank);
```

Replace the role cell (currently lines 159-177):

```tsx
                      <td style={{ padding: "12px 20px" }}>
                        {(() => {
                          const targetRank = ROLE_RANK[u.role] ?? 0;
                          const canEdit = u.role !== "owner" && targetRank < actorRank && u.id !== user?.id;
                          return canEdit ? (
                            <select
                              value={u.role}
                              disabled={savingId === u.id}
                              onChange={(e) => handleRoleChange(u.id, e.target.value as Role)}
                              className="input"
                              style={{
                                width: "auto", padding: "4px 10px", fontSize: "0.76rem", fontWeight: 600,
                                ...ROLE_STYLE[u.role],
                              }}
                            >
                              {assignableForActor.map((r) => <option key={r} value={r}>{roleLabel[r]}</option>)}
                            </select>
                          ) : (
                            <span className="badge" style={ROLE_STYLE[u.role]}>{roleLabel[u.role]}</span>
                          );
                        })()}
                      </td>
```

- [ ] **Step 2: Verify with the TypeScript compiler**

Run: `cd frontend; npx tsc --noEmit`
Expected: no new errors — pay attention to whether `isAdmin` is still referenced elsewhere in the file (the auth-bar `isModerator` branch is unaffected; only the role-select gating logic changed)

- [ ] **Step 3: Commit**

```bash
git add frontend/app/admin/users/page.tsx
git commit -m "feat(frontend): admin/users role select is graduated by actor rank, owner rows read-only"
```

---

### Task 24: Deploy config — prod `.env` passthrough for `app`/`worker`

**Files:**
- Modify: `docker-compose.prod.yml`
- Modify: `CLAUDE.md` (env var reference list)

**Interfaces:** none (infrastructure config only, no test — verified via `docker compose config`)

- [ ] **Step 1: Add new env vars to the `app` service block in `docker-compose.prod.yml`**

Right after `- ADMIN_EMAILS=${ADMIN_EMAILS:-}` (line 83), add:

```yaml
      # v2.1: owner rolü — sadece app'te gerekli (route-level yetki kontrolü burada yapılır)
      - OWNER_EMAILS=${OWNER_EMAILS:-}
```

Replace the RESEND_API_KEY/EMAIL_FROM lines in the `app` block (lines 87-88) with:

```yaml
      # v2.1: EMAIL_PROVIDER=auto ise SMTP kimlikleri doluysa SMTP, yoksa Resend,
      # o da yoksa Console'a düşer (artık sessizce değil — bkz. warn_if_email_disabled).
      - EMAIL_PROVIDER=${EMAIL_PROVIDER:-auto}
      - RESEND_API_KEY=${RESEND_API_KEY:-}
      - EMAIL_FROM=${EMAIL_FROM:-NexStream <no-reply@nexstream.news>}
      - SMTP_HOST=${SMTP_HOST:-smtp.gmail.com}
      - SMTP_PORT=${SMTP_PORT:-587}
      - SMTP_USER=${SMTP_USER:-}
      - SMTP_PASSWORD=${SMTP_PASSWORD:-}
      - SMTP_FROM=${SMTP_FROM:-}
      - SMTP_STARTTLS=${SMTP_STARTTLS:-true}
```

- [ ] **Step 2: Add the same email vars (no `OWNER_EMAILS`) to the `worker` service block**

Worker sends keyword-alert emails from the ingest pipeline but never does per-request role gating, so it needs the email vars but not `OWNER_EMAILS`. Replace the RESEND_API_KEY/EMAIL_FROM lines in the `worker` block (lines 204-205) with:

```yaml
      - EMAIL_PROVIDER=${EMAIL_PROVIDER:-auto}
      - RESEND_API_KEY=${RESEND_API_KEY:-}
      - EMAIL_FROM=${EMAIL_FROM:-NexStream <no-reply@nexstream.news>}
      - SMTP_HOST=${SMTP_HOST:-smtp.gmail.com}
      - SMTP_PORT=${SMTP_PORT:-587}
      - SMTP_USER=${SMTP_USER:-}
      - SMTP_PASSWORD=${SMTP_PASSWORD:-}
      - SMTP_FROM=${SMTP_FROM:-}
      - SMTP_STARTTLS=${SMTP_STARTTLS:-true}
```

Do **not** add anything to the `scheduler` block — it only publishes scrape trigger messages and never calls `get_email_adapter()` (confirmed: the newsletter job runs inside `app`'s lifespan task, not in `scheduler`).

Note for dev `docker-compose.yml`: no change needed there — `app` and `worker` both mount `.:/app`, so the project's `.env` file is read directly inside the container by Pydantic Settings' `env_file=".env"`, without needing explicit `environment:` passthrough (this is why dev compose never had `RESEND_API_KEY` listed either).

- [ ] **Step 3: Validate the compose file parses**

Run: `docker compose -f docker-compose.prod.yml config --quiet`
Expected: no output, exit code 0 (Docker Desktop must be running for this check)

- [ ] **Step 4: Update `CLAUDE.md`'s env var reference list**

In the `## BİLİNEN NOTLAR` section, find the line listing v2.0 embedder env vars (ends with `EMBEDDER_RETRIES (1)`) and append after it:

```
, **v2.1 owner rolü + gerçek e-posta:** `OWNER_EMAILS` (boş — virgülle ayrılmış, DB'ye dokunmadan owner sayılır, tek kaynak bu env veya elle yazılan `role='owner'`), `EMAIL_PROVIDER` (`auto` — `smtp`/`resend`/`console` ile zorlanabilir), `SMTP_HOST` (`smtp.gmail.com`), `SMTP_PORT` (587), `SMTP_USER`/`SMTP_PASSWORD` (Gmail app password — normal login şifresi DEĞİL), `SMTP_FROM` (boşsa `EMAIL_FROM` kullanılır), `SMTP_STARTTLS` (`true`).
```

- [ ] **Step 5: Commit**

```bash
git add docker-compose.prod.yml CLAUDE.md
git commit -m "chore: wire owner/SMTP env vars into prod compose (app + worker only)"
```

---

### Task 25: Final full-suite verification + frontend build check

**Files:** none (verification-only)

- [ ] **Step 1: Full backend suite**

Run: `venv\Scripts\python.exe -m pytest tests/ -v --timeout=120`
Expected: all PASS

- [ ] **Step 2: Frontend type check** (only if frontend dev container is not running `npm run dev` against a live volume mount conflict — safe either way since `tsc --noEmit` never touches `.next`)

Run: `cd frontend; npx tsc --noEmit`
Expected: no errors

- [ ] **Step 3: Report back to the user**

Summarize: owner role + graduated role management + SmtpEmailAdapter are implemented and tested. Remaining manual steps before this is live (per the design spec's "Canlı doğrulama" section, cannot be automated):

1. User has already added `SMTP_USER`/`SMTP_PASSWORD` to local `.env` (done earlier this session).
2. Add `OWNER_EMAILS=erenk897@gmail.com`, `EMAIL_PROVIDER=smtp`, and the `SMTP_*` values to the **production** `.env` on the AWS server (via SSM — see `DEPLOY.md` §2-AWS).
3. Run `docker compose -f docker-compose.prod.yml up -d app worker` on the server (`restart` is not enough — env vars are read at container start).
4. Live-verify: log in as the owner, confirm the badge reads "Kurucu", confirm `boeingb747.800@gmail.com` actually receives a real registration email (the one thing Resend's sandbox could never do), confirm `/health`'s `email` field reads `"smtp"`.

Do not perform steps 2-4 without the user's explicit go-ahead (they touch the live production server).

---

## Self-Review Notes (for whoever executes this plan)

- **Spec coverage:** all four parts of the design doc are covered — owner role (Tasks 1, 3), effective-tier access (Tasks 1, 3, 5-11), graduated role management (Task 12), real email (Tasks 2, 13-16). The one spec item with no live caller (`require_owner`) is implemented and tested per the spec's explicit test-plan line, but not wired into a route — no route was specified for it in the design doc, so none was invented.
- **Order matters:** Tasks 1-3 must land before any of Tasks 4-12 (they all depend on `user_effective_tier`/`has_owner_role`). Tasks 13-14 must land before 15-16 (main.py and health_router both import from the refactored `email_adapter.py`). Task 17 is a hard gate — do not start frontend tasks (18+) on a red backend.
- **Known test-breakage points already handled inline:** `test_update_user_role_success`, `test_update_user_role_rejects_self_demotion` → renamed `test_update_user_role_rejects_self_change`, `test_update_user_role_404_for_missing_user` (Task 12); `test_get_email_adapter_returns_console_without_api_key`, `test_get_email_adapter_returns_resend_with_api_key` (Task 14); `test_health_response_has_all_required_fields` (Task 16). If subagents executing this plan encounter *other* unexpected breakages, treat that as a signal to re-read the affected file rather than force the test to pass.
