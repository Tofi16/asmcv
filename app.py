import os, io, re, csv, time, json, glob, hashlib, sqlite3, base64, datetime, secrets, zipfile, calendar
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for, session,
                   send_file, abort, make_response, send_from_directory)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image, ImageOps, ImageFilter

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
UP = os.path.join(DATA, "uploads")
os.makedirs(UP, exist_ok=True)

app = Flask(__name__)
APP_ENV = os.environ.get("APP_ENV", "development").lower()
SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret")
PASSWORD = os.environ.get("ASM_PASSWORD", "asm12345")
if APP_ENV == "production":
    if len(SECRET_KEY) < 32 or SECRET_KEY == "change-this-secret":
        raise RuntimeError("Production requires a random SECRET_KEY of at least 32 characters.")
    if len(PASSWORD) < 12 or PASSWORD == "asm12345":
        raise RuntimeError("Production requires an ASM_PASSWORD of at least 12 characters.")
app.secret_key = SECRET_KEY
app.config.update(
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=APP_ENV == "production",
    MAX_CONTENT_LENGTH=40 * 1024 * 1024,
)
CSRFProtect(app)
AGENCY_PHONE = os.environ.get("AGENCY_PHONE", "")
MEDICAL_MONTHS = int(os.environ.get("MEDICAL_MONTHS", "2"))   # how long a medical stays valid
BK = os.path.join(DATA, "backups")
CACHE = os.path.join(DATA, "cache")

LV = ["Good", "Fair"]
LANG = ["Good", "Fair", "Basic"]
SECTIONS = [
    ("Job · الوظيفة", [
        ("ref", "Reference no", "رقم الطلب"),
        ("post", "Post applied for", "الوظيفة", "select", ["Housemaid", "Baby sitter", "Cook", "Cleaner", "Elderly care"]),
        ("salary", "Monthly salary", "الراتب الشهري"),
        ("contract", "Contract period", "مدة العقد")]),
    ("Personal · البيانات الشخصية", [
        ("name", "Full name", "الاسم الكامل"),
        ("phone", "Telephone", "رقم الجوال"),
        ("dob", "Date of birth", "تاريخ الميلاد", "date"),
        ("birthplace", "Place of birth", "مكان الميلاد"),
        ("address", "Address", "العنوان"),
        ("nationality", "Nationality", "الجنسية"),
        ("religion", "Religion", "الديانة", "select", ["Muslim", "Christian"]),
        ("marital", "Marital status", "الحالة الاجتماعية", "select", ["Single", "Married", "Divorced", "Widowed"]),
        ("children", "Children", "عدد الأطفال"),
        ("height", "Height (m)", "الطول"),
        ("weight", "Weight (kg)", "الوزن"),
        ("education", "Education", "المؤهل العلمي", "select", ["Primary", "Secondary complete", "Diploma", "Degree"])]),
    ("Passport · بيانات الجواز", [
        ("passport_no", "Passport no", "رقم الجواز"),
        ("issue_place", "Issue place", "مكان الإصدار"),
        ("issue_date", "Issue date", "تاريخ الإصدار", "date"),
        ("expiry_date", "Expiry date", "تاريخ الانتهاء", "date")]),
    ("Languages · اللغات", [
        ("english", "English", "الإنجليزية", "select", LANG),
        ("arabic", "Arabic", "العربية", "select", LANG)]),
    ("Skills · المهارات", [
        ("cooking", "Cooking", "الطبخ", "select", LV),
        ("cleaning", "Cleaning", "التنظيف", "select", LV),
        ("washing", "Washing", "الغسيل", "select", LV),
        ("ironing", "Ironing", "الكوي", "select", LV),
        ("baby", "Baby sitting", "رعاية الأطفال", "select", LV),
        ("elderly", "Elderly care", "رعاية كبار السن", "select", LV)]),
    ("Emergency contact · شخص للاتصال", [
        ("contact_name", "Contact name", "الاسم"),
        ("contact_address", "Contact address", "العنوان"),
        ("contact_phone", "Contact telephone", "رقم الهاتف")]),
    ("Documents & guarantor · ሰነዶች እና ተያዥ (private, not on CV)", [
        ("id_no", "ID number", "መታወቂያ ቁጥር"),
        ("guarantor_name", "Guarantor name", "የተያዥ ስም"),
        ("guarantor_phone", "Guarantor phone", "የተያዥ ስልክ"),
        ("guarantor_id_no", "Guarantor ID number", "የተያዥ መታወቂያ ቁጥር"),
        ("labor_id", "Labor ID number", "የLabor ID ቁጥር"),
        ("coc1_no", "COC certificate 1 no.", "COC 1 ቁጥር"),
        ("coc2_no", "COC certificate 2 no.", "COC 2 ቁጥር")]),
    ("Visa & ticket · ቪዛ እና ትኬት (private, not on CV)", [
        ("employer", "Employer / sponsor", "ቀጣሪ"),
        ("destination", "Destination", "መዳረሻ"),
        ("visa_no", "Visa number", "የቪዛ ቁጥር"),
        ("flight_date", "Flight date", "የበረራ ቀን", "date"),
        ("airline", "Airline / ticket no.", "አየር መንገድ / ትኬት ቁጥር")]),
]
FIELDS = [f for _, fs in SECTIONS for f in fs]
L = {f[0]: (f[1], f[2]) for f in FIELDS}
SKILLS = ["cooking", "cleaning", "washing", "ironing", "baby", "elderly"]
KINDS = [("face", "Face photo", "ጉርድ"), ("body", "Full-body photo", "ሙሉ ፎቶ"), ("passport", "Passport page", "ፓስፖርት")]
DOCS = [("idcard", "Traveler ID", "የተጓዥ መታወቂያ"), ("guarantor_id", "Guarantor ID", "የተያዥ መታወቂያ"),
        ("coc1", "COC certificate 1", "COC 1"), ("coc2", "COC certificate 2", "COC 2"),
        ("consent", "Signed consent", "የፈቃድ ቅጽ")]
STAGES = [("CV ready", "ሲቪ ዝግጁ"), ("Selected", "ተመርጧል"), ("Medical", "ሜዲካል"),
          ("Embassy", "ኤምባሲ"), ("Ticket booked", "ትኬት"), ("Travelled", "ተጓዘ")]


@app.context_processor
def inject():
    return dict(L=L, SECTIONS=SECTIONS, KINDS=KINDS, DOCS=DOCS, STAGES=STAGES, MEDICAL_DAYS=MEDICAL_MONTHS * 30)


def db():
    c = sqlite3.connect(os.path.join(DATA, "asm.db"))
    c.row_factory = sqlite3.Row
    c.execute("create table if not exists app(id integer primary key, name text, ref text, data text, created text)")
    c.execute("create table if not exists log(id integer primary key, ts text, action text, aid integer, detail text)")
    c.execute("create table if not exists user(id integer primary key, username text unique, pw text, role text, active integer default 1, created text)")
    try:
        c.execute("alter table log add column who text")
    except sqlite3.OperationalError:
        pass
    return c


def log(action, aid=None, detail=""):
    c = db()
    c.execute("insert into log(ts,action,aid,detail,who) values(?,?,?,?,?)",
              (datetime.datetime.now().isoformat(timespec="seconds"), action, aid, detail, session.get("user", "")))
    c.commit()


def make_backup(force=False):
    os.makedirs(BK, exist_ok=True)
    f = os.path.join(BK, "asm-%s.zip" % datetime.date.today().isoformat())
    if os.path.exists(f) and not force:
        return f
    tmp = os.path.join(DATA, "snapshot.db")
    src, dst = db(), sqlite3.connect(tmp)
    src.backup(dst)
    dst.close(); src.close()
    with zipfile.ZipFile(f, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(tmp, "asm.db")
        for root, _, files in os.walk(UP):
            for n in files:
                q = os.path.join(root, n)
                z.write(q, os.path.relpath(q, DATA))
    os.remove(tmp)
    for old in sorted(os.listdir(BK))[:-14]:
        os.remove(os.path.join(BK, old))
    return f


@app.before_request
def auto_backup():
    if session.get("ok") and request.endpoint != "static":
        try:
            make_backup()
        except Exception:
            pass


def login_required(f):
    @wraps(f)
    def w(*a, **k):
        u = db().execute("select active from user where id=?", (session.get("uid"),)).fetchone() if session.get("ok") else None
        if not u or not u["active"]:
            session.clear()
            return redirect(url_for("login"))
        return f(*a, **k)
    return w


def admin_required(f):
    @wraps(f)
    @login_required
    def w(*a, **k):
        if session.get("role") != "admin":
            return make_response("Only an administrator can do this.", 403)
        return f(*a, **k)
    return w


def enhance(im):
    """Uniform look for face/body photos: crop face to 3:4, balance contrast, sharpen (optional background removal)."""
    if os.environ.get("REMBG") == "1":
        try:
            from rembg import remove
            cut = remove(im).convert("RGBA")
            bg = Image.new("RGBA", cut.size, "white")
            bg.alpha_composite(cut)
            im = bg.convert("RGB")
        except ImportError:
            pass
    y, cb, cr = im.convert("YCbCr").split()   # balance brightness only, so skin tones keep their natural color
    im = Image.merge("YCbCr", (ImageOps.autocontrast(y, cutoff=1), cb, cr)).convert("RGB")
    return im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=3))


def save_photo(f, aid, kind):
    if not f or not f.filename:
        return
    im = ImageOps.exif_transpose(Image.open(f)).convert("RGB")
    if kind in ("face", "body"):
        if kind == "face":
            w, h = im.size
            if w / h > .75:
                x = int((w - h * .75) / 2)
                im = im.crop((x, 0, w - x, h))
            else:
                im = im.crop((0, 0, w, int(w / .75)))
        im = enhance(im)
    im.thumbnail((2400, 2400))
    d = os.path.join(UP, str(aid))
    os.makedirs(d, exist_ok=True)
    im.save(os.path.join(d, kind + ".jpg"), quality=95, subsampling=0)


def photos(aid, embed=False, kinds=KINDS):
    out = {}
    for k, _, _ in kinds:
        p = os.path.join(UP, str(aid), k + ".jpg")
        if os.path.exists(p):
            if embed:
                out[k] = "data:image/jpeg;base64," + base64.b64encode(open(p, "rb").read()).decode()
            else:
                out[k] = url_for("media", aid=aid, kind=k) + "?v=%d" % os.path.getmtime(p)
    return out


def track(d):
    t = d.get("_track") or {}
    return {"stage": int(t.get("stage", 0)), "dates": t.get("dates", {}), "note": t.get("note", "")}


def has(aid, k):
    return os.path.exists(os.path.join(UP, str(aid), k + ".jpg"))


def readiness(d, aid):
    h = lambda k: has(aid, k)
    items = [
        (("Traveler ID", "የተጓዥ መታወቂያ"), h("idcard")),
        (("Guarantor ID", "የተያዥ መታወቂያ"), bool(d.get("guarantor_name")) and h("guarantor_id")),
        (("Labor ID", "Labor ID"), bool(d.get("labor_id"))),
        (("COC 1", "ሰርተፊኬት 1"), h("coc1")),
        (("COC 2", "ሰርተፊኬት 2"), h("coc2")),
        (("Passport", "ፓስፖርት"), bool(d.get("passport_no")) and h("passport")),
        (("Consent", "ፈቃድ"), h("consent")),
    ]
    return items, round(100 * sum(bool(ok) for _, ok in items) / len(items))


def add_months(dt, m):
    y, mo = divmod(dt.month - 1 + m, 12)
    y += dt.year
    return datetime.date(y, mo + 1, min(dt.day, calendar.monthrange(y, mo + 1)[1]))


def medical(t):
    """(valid_until, days_left) once the Medical stage has a date, else None."""
    try:
        d0 = datetime.date.fromisoformat(t["dates"].get("2", ""))
    except ValueError:
        return None
    if t["stage"] < 2:
        return None
    u = add_months(d0, MEDICAL_MONTHS)
    return u, (u - datetime.date.today()).days


def soon(iso):
    try:
        return datetime.date.fromisoformat(iso) < datetime.date.today() + datetime.timedelta(days=183)
    except ValueError:
        return False


def wa(phone):
    n = "".join(ch for ch in phone or "" if ch.isdigit())
    return ("251" + n[1:]) if n.startswith("0") else n


def save_data(aid, d):
    c = db()
    c.execute("update app set name=?, ref=?, data=? where id=?", (d.get("name", ""), d.get("ref", ""), json.dumps(d), aid))
    c.commit()


def exp_list(d):
    """Experience abroad as a list of {country, period}. Older records stored exp1_/exp2_ fields."""
    if "exp" in d:
        return d["exp"]
    return [{"country": d["exp%d_country" % n], "period": d.get("exp%d_period" % n, "")}
            for n in (1, 2) if d.get("exp%d_country" % n)]


def exp_total(lst):
    months = 0
    for e in lst:
        m = re.search(r"(\d+(?:\.\d+)?)\s*(year|yr|y|month|mo)", e["period"].lower())
        if not m:
            return ""
        months += float(m.group(1)) * (12 if m.group(2).startswith("y") else 1)
    y, mo = divmod(round(months), 12)
    return " ".join(x for x in ("%d year%s" % (y, "" if y == 1 else "s") if y else "",
                                "%d month%s" % (mo, "" if mo == 1 else "s") if mo else "") if x)


def badges(d, aid):
    out, today = [], datetime.date.today()
    ex = iso(d.get("expiry_date"))
    if ex and ex > today + datetime.timedelta(days=183):
        out.append(("Passport valid to %s" % ex.strftime("%b %Y"), "جواز ساري"))
    if has(aid, "coc1") and has(aid, "coc2"):
        out.append(("COC certified ×2", "شهادات COC"))
    t = track(d)
    md = iso(t["dates"].get("2"))
    if t["stage"] >= 2 and md:
        out.append(("Medical done %s" % md.strftime("%d %b %Y"), "فحص طبي مكتمل"))
    return out


def quality(d, aid):
    """Pre-send check: tips about weak photos or missing details."""
    tips = []
    size = lambda k: Image.open(os.path.join(UP, str(aid), k + ".jpg")).size if has(aid, k) else None
    f, b, pp = size("face"), size("body"), size("passport")
    if not f: tips.append("face photo missing")
    elif f[0] < 500: tips.append("face photo is small (%d px)" % f[0])
    if not b: tips.append("full-body photo missing")
    elif b[1] < 1000: tips.append("full-body photo is low resolution")
    if not pp: tips.append("passport page missing")
    elif pp[0] < 1400: tips.append("passport page may be hard to read (%d px wide)" % pp[0])
    miss = [L[k][0] for k in ("name", "dob", "nationality", "passport_no", "expiry_date", "post") if not d.get(k)]
    if miss: tips.append("missing " + ", ".join(miss))
    return tips


def pretty(d):
    d = dict(d)
    try:
        b = datetime.date.fromisoformat(d.get("dob", ""))
        t = datetime.date.today()
        d["age"] = t.year - b.year - ((t.month, t.day) < (b.month, b.day))
    except ValueError:
        d["age"] = ""
    for k in ("dob", "issue_date", "expiry_date"):
        try:
            d[k] = datetime.date.fromisoformat(d[k]).strftime("%d %b %Y")
        except (KeyError, ValueError):
            pass
    num = lambda v: v.replace(".", "", 1).isdigit()
    if d.get("height") and num(d["height"]): d["height"] += " m"
    if d.get("weight") and num(d["weight"]): d["weight"] += " kg"
    return d


def load(aid):
    r = db().execute("select * from app where id=?", (aid,)).fetchone()
    if not r:
        abort(404)
    return json.loads(r["data"])


FAILS = {}   # ip -> [count, first_time]  (simple brute-force guard)


@app.route("/login", methods=["GET", "POST"])
def login():
    err, username = "", ""
    c = db()
    if not c.execute("select 1 from user").fetchone():     # first run: create the admin from ASM_PASSWORD
        c.execute("insert into user(username,pw,role,active,created) values(?,?,?,1,?)",
                  ("admin", generate_password_hash(PASSWORD), "admin", datetime.datetime.now().isoformat()))
        c.commit()
    if request.method == "POST":
        ip = request.remote_addr
        n, t0 = FAILS.get(ip, [0, time.time()])
        if time.time() - t0 > 600:
            n, t0 = 0, time.time()
        username = request.form.get("username", "").strip().lower()
        u = c.execute("select * from user where username=?", (username,)).fetchone()
        if n >= 5:
            err = "Too many attempts. Try again in 10 minutes."
        elif u and u["active"] and check_password_hash(u["pw"], request.form.get("password", "")):
            FAILS.pop(ip, None)
            session.clear()
            session.update(ok=True, uid=u["id"], user=u["username"], role=u["role"])
            log("login")
            return redirect(url_for("index"))
        else:
            FAILS[ip] = [n + 1, t0]
            err = "Wrong username or password"
    return render_template("login.html", err=err, username=username)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def default_pw():
    """True if the signed-in admin still uses the factory password."""
    if session.get("role") != "admin":
        return False
    u = db().execute("select pw from user where id=?", (session.get("uid"),)).fetchone()
    return bool(u) and check_password_hash(u["pw"], "asm12345")


def employers():
    out = set()
    for r in db().execute("select data from app"):
        d = json.loads(r["data"])
        if d.get("employer"):
            out.add(d["employer"])
        out.update(o["employer"] for o in d.get("_offers", []))
    return sorted(out)


def iso(v):
    try:
        return datetime.date.fromisoformat(v)
    except (TypeError, ValueError):
        return None


@app.route("/")
@login_required
def index():
    q = request.args.get("q", "").strip()
    sel = request.args.get("s", "")
    rows = db().execute("select * from app where data like ? order by id desc", ("%" + q + "%",)).fetchall()
    counts, items, pp, attn = [0] * len(STAGES), [], {}, []
    today = datetime.date.today()
    for r in rows:
        pn = json.loads(r["data"]).get("passport_no", "").strip().upper()
        if pn:
            pp[pn] = pp.get(pn, 0) + 1
    for r in rows:
        d = json.loads(r["data"])
        t = track(d)
        counts[t["stage"]] += 1
        rd, pct = readiness(d, r["id"])
        m = medical(t)
        warn = []

        def add(lv, msg, pill=None):
            attn.append(dict(id=r["id"], name=d.get("name", ""), msg=msg, lv=lv))

        if m and t["stage"] in (2, 3, 4) and m[1] <= 14:
            txt = "Medical expired" if m[1] < 0 else "Medical expires in %d days" % m[1]
            warn.append(txt); add("red" if m[1] <= 7 else "amb", txt)
        fd = iso(d.get("flight_date"))
        if fd and t["stage"] == 4 and 0 <= (fd - today).days <= 7:
            add("blue", "Flight in %d days" % (fd - today).days)
        if t["stage"] >= 1 and pct < 100:
            add("red" if t["stage"] >= 2 else "amb", "Missing: " + ", ".join(i[0][0] for i in rd if not i[1]))
        if soon(d.get("expiry_date", "")):
            warn.append("Passport expires within 6 months"); add("amb", "Passport expires within 6 months")
        if pp.get(d.get("passport_no", "").strip().upper(), 0) > 1:
            warn.append("Duplicate passport no.")
        sd = iso(t["dates"].get(str(t["stage"])))
        if sd and 1 <= t["stage"] <= 4 and (today - sd).days > 10:
            add("amb", "No update for %d days at %s" % ((today - sd).days, STAGES[t["stage"]][0]))
        for nt in d.get("_notes", []):
            dd = iso(nt.get("due"))
            if dd and not nt["done"] and dd <= today:
                add("red" if dd < today else "amb", "Follow-up %s: %s" % ("overdue" if dd < today else "today", nt["text"][:38]))
        for o in d.get("_offers", []):
            od = iso(o["date"])
            if o["status"] == "Sent" and od and (today - od).days > 7:
                add("amb", "No reply from %s for %d days" % (o["employer"], (today - od).days))
        if sel != "" and str(t["stage"]) != sel:
            continue
        items.append(dict(id=r["id"], d=d, face=photos(r["id"]).get("face"), stage=t["stage"], ready=pct, warn=warn))
    attn.sort(key=lambda a: ("red", "amb", "blue").index(a["lv"]))
    return render_template("index.html", items=items, q=q, sel=sel, counts=counts, total=sum(counts), attn=attn[:8], default_pw=default_pw())


@app.route("/case/<int:aid>")
@login_required
def case(aid):
    d = load(aid)
    t = track(d)
    items, pct = readiness(d, aid)
    fd = iso(d.get("flight_date"))
    msg = "ሰላም %s፣ የጉዳይዎ ሁኔታ፦ %s።" % (d.get("name", "").split(" ")[0], STAGES[t["stage"]][1])
    if fd and t["stage"] >= 4:
        msg += "\nየበረራ ቀን፦ %s" % fd.strftime("%d %b %Y")
    if t["note"]:
        msg += "\n" + t["note"]
    return render_template("case.html", d=d, t=t, aid=aid, items=items, pct=pct, med=medical(t),
                           ph=photos(aid, kinds=KINDS + DOCS), wa=wa(d.get("phone")), msg=msg,
                           flight_days=(fd - datetime.date.today()).days if fd else None,
                           notes=d.get("_notes", []), offers=d.get("_offers", []), employers=employers(),
                           soon=soon(d.get("expiry_date", "")), today=datetime.date.today().isoformat())


@app.route("/case/<int:aid>/stage", methods=["POST"])
@login_required
def set_stage(aid):
    d = load(aid)
    t = track(d)
    n = max(0, min(len(STAGES) - 1, int(request.form.get("stage", t["stage"]))))
    items, pct = readiness(d, aid)
    if n >= 3 and n > t["stage"] and pct < 100:
        return redirect(url_for("case", aid=aid, err=", ".join(i[0][0] for i in items if not i[1])))
    t["stage"] = n
    t["dates"][str(n)] = request.form.get("date") or datetime.date.today().isoformat()
    t["note"] = request.form.get("note", "").strip()
    d["_track"] = t
    save_data(aid, d)
    log("stage", aid, "%s · %s" % (d.get("name", ""), STAGES[n][0]))
    return redirect(url_for("case", aid=aid))


@app.route("/log")
@login_required
def activity():
    rows = db().execute("select * from log order by id desc limit 300").fetchall()
    return render_template("log.html", rows=rows)


@app.route("/backup")
@admin_required
def backup():
    log("backup downloaded")
    return send_file(make_backup(True), as_attachment=True)


@app.route("/new", methods=["GET", "POST"], defaults={"aid": None})
@app.route("/edit/<int:aid>", methods=["GET", "POST"])
@login_required
def edit(aid):
    d = load(aid) if aid else {"nationality": "Ethiopian", "post": "Housemaid"}
    if request.method == "POST":
        d = dict(d)
        d.update({f[0]: request.form.get(f[0], "").strip() for f in FIELDS})
        d["exp"] = [{"country": c.strip(), "period": p.strip()} for c, p in
                    zip(request.form.getlist("exp_country"), request.form.getlist("exp_period")) if c.strip()][:6]
        c = db()
        if aid:
            c.execute("update app set name=?, ref=?, data=? where id=?", (d["name"], d["ref"], json.dumps(d), aid))
        else:
            aid = c.execute("insert into app(name,ref,data,created) values(?,?,?,?)",
                            (d["name"], d["ref"], json.dumps(d), datetime.datetime.now().isoformat())).lastrowid
        c.commit()
        for k, _, _ in KINDS + DOCS:
            save_photo(request.files.get(k), aid, k)
        log("saved", aid, d.get("name", ""))
        return redirect(url_for("cv", aid=aid))
    return render_template("form.html", d=dict(d, exp=exp_list(d)), aid=aid, ph=photos(aid, kinds=KINDS + DOCS) if aid else {})


@app.route("/delete/<int:aid>", methods=["POST"])
@admin_required
def delete(aid):
    c = db()
    log("deleted", aid, load(aid).get("name", ""))
    c.execute("delete from app where id=?", (aid,))
    c.commit()
    import shutil
    shutil.rmtree(os.path.join(UP, str(aid)), ignore_errors=True)
    for f in glob.glob(os.path.join(CACHE, "%d-*.pdf" % aid)):
        os.remove(f)
    return redirect(url_for("index"))


@app.route("/media/<int:aid>/<kind>")
@login_required
def media(aid, kind):
    p = os.path.join(UP, str(aid), os.path.basename(kind) + ".jpg")
    return send_file(p) if os.path.exists(p) else abort(404)


def logo(embed):
    if not embed:
        return url_for("static", filename="logo.jpg")
    return "data:image/jpeg;base64," + base64.b64encode(open(os.path.join(BASE, "static", "logo.jpg"), "rb").read()).decode()


def render_cv(aid, embed, mask=False):
    raw = load(aid)
    d = pretty(raw)
    skills = [(k, d[k]) for k in SKILLS if d.get(k)]
    ex = exp_list(raw)
    return render_template("cv.html", d=d, ph=photos(aid, embed), skills=skills, embed=embed, mask=mask,
                           logo=logo(embed), aid=aid, agency_phone=AGENCY_PHONE, exp=ex, exp_total=exp_total(ex),
                           badges=badges(raw, aid), issued=datetime.date.today().strftime("%d %b %Y"),
                           tips=None if embed else quality(raw, aid), dense=len(ex) > 4 or len(d.get("name", "")) > 34)


def pdf_bytes(aid, mask=False):
    """Vector PDF from the CV page (photos embedded at full resolution). Cached until the data changes."""
    from playwright.sync_api import sync_playwright
    d = load(aid)
    core = {k: v for k, v in d.items() if not k.startswith("_")}
    stamp = "".join(str(os.path.getmtime(p)) for p in sorted(glob.glob(os.path.join(UP, str(aid), "*.jpg"))))
    tpl = str(os.path.getmtime(os.path.join(BASE, "templates", "cv.html")))
    key = hashlib.md5((json.dumps(core, sort_keys=True) + stamp + tpl).encode()).hexdigest()[:16]
    os.makedirs(CACHE, exist_ok=True)
    f = os.path.join(CACHE, "%d-%d-%s.pdf" % (aid, mask, key))
    if os.path.exists(f):
        return open(f, "rb").read()
    html = render_cv(aid, True, mask=mask)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.set_content(html, wait_until="load")
        pg.evaluate("document.fonts.ready")
        over = "(()=>{const b=document.querySelector('.bottom');return b.scrollHeight>b.clientHeight+2})()"
        for cls in ("dense", "tight"):          # auto-fit: shrink spacing step by step if the content is too long
            if pg.evaluate(over):
                pg.evaluate("document.querySelector('.page').classList.add('%s')" % cls)
        pdf = pg.pdf(prefer_css_page_size=True, print_background=True)
        b.close()
    from pypdf import PdfReader, PdfWriter
    wr = PdfWriter(clone_from=PdfReader(io.BytesIO(pdf)))
    wr.add_metadata({"/Title": "%s - CV %s" % (d.get("name", ""), d.get("ref", "")), "/Author": "ASM Foreign Employment Agent",
                     "/Subject": "Job application CV", "/Keywords": ", ".join(x for x in (d.get("post"), d.get("nationality")) if x)})
    buf = io.BytesIO()
    wr.write(buf)
    pdf = buf.getvalue()
    for old in glob.glob(os.path.join(CACHE, "%d-%d-*.pdf" % (aid, mask))):
        os.remove(old)
    open(f, "wb").write(pdf)
    return pdf


def pdf_response(data, name):
    r = make_response(data)
    r.headers["Content-Type"] = "application/pdf"
    r.headers["Content-Disposition"] = 'inline; filename="%s"' % name
    return r


@app.route("/cv/<int:aid>")
@login_required
def cv(aid):
    return render_cv(aid, False, mask=request.args.get("mask") == "1")


@app.route("/cv/<int:aid>.pdf")
@login_required
def cv_pdf(aid):
    mask = request.args.get("mask") == "1"
    name = (load(aid).get("name") or "cv").replace(" ", "_") + ("_employer" if mask else "") + "_CV.pdf"
    return pdf_response(pdf_bytes(aid, mask), name)


def pack_ids():
    return [int(x) for x in request.args.get("ids", "").split(",") if x.isdigit()][:30]


@app.route("/pack")
@login_required
def pack():
    ids = pack_ids()
    return render_template("pack.html", ids=ids, names=[load(i).get("name", "") for i in ids],
                           mask=request.args.get("mask") == "1", q=",".join(map(str, ids)))


@app.route("/pack.pdf")
@login_required
def pack_pdf():
    from pypdf import PdfWriter, PdfReader
    mask = request.args.get("mask") == "1"
    w = PdfWriter()
    for i in pack_ids():
        w.append(PdfReader(io.BytesIO(pdf_bytes(i, mask))))
    buf = io.BytesIO()
    w.write(buf)
    log("cv pack", None, "%d CVs" % len(pack_ids()))
    return pdf_response(buf.getvalue(), "ASM_CV_pack.pdf")


@app.route("/export.csv")
@admin_required
def export():
    cols = ["ref", "name", "post", "phone", "nationality", "dob", "passport_no", "issue_date", "expiry_date",
            "labor_id", "id_no", "guarantor_name", "guarantor_phone", "employer", "visa_no", "destination", "flight_date"]
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow([L[c][0] for c in cols] + ["Experience abroad", "Stage", "Stage date", "Docs %"])
    for r in db().execute("select * from app order by id"):
        d = json.loads(r["data"])
        t = track(d)
        w.writerow([d.get(c, "") for c in cols] + ["; ".join("%s %s" % (e["country"], e["period"]) for e in exp_list(d)), STAGES[t["stage"]][0], t["dates"].get(str(t["stage"]), ""), readiness(d, r["id"])[1]])
    log("csv export")
    resp = make_response("\ufeff" + out.getvalue())   # BOM so Excel shows Amharic/Arabic correctly
    resp.headers["Content-Type"] = "text/csv; charset=utf-8"
    resp.headers["Content-Disposition"] = 'attachment; filename="asm_applicants_%s.csv"' % datetime.date.today().isoformat()
    return resp


@app.route("/sw.js")
def sw():
    return send_from_directory(os.path.join(BASE, "static"), "sw.js", mimetype="application/javascript")


OFFER = ["Sent", "Interview", "Accepted", "Rejected"]


def next_id(lst):
    return max([x["id"] for x in lst], default=0) + 1


@app.route("/case/<int:aid>/note", methods=["POST"])
@login_required
def add_note(aid):
    d = load(aid)
    text = request.form.get("text", "").strip()
    if text:
        notes = d.setdefault("_notes", [])
        notes.append({"id": next_id(notes), "ts": datetime.datetime.now().strftime("%d %b %Y %H:%M"), "who": session.get("user", ""),
                      "text": text, "due": request.form.get("due", ""), "done": False})
        save_data(aid, d)
        log("note", aid, d.get("name", ""))
    return redirect(url_for("case", aid=aid) + "#notes")


@app.route("/case/<int:aid>/note/<int:nid>/done", methods=["POST"])
@login_required
def done_note(aid, nid):
    d = load(aid)
    for n in d.get("_notes", []):
        if n["id"] == nid:
            n["done"] = True
    save_data(aid, d)
    return redirect(url_for("case", aid=aid) + "#notes")


@app.route("/case/<int:aid>/offer", methods=["POST"])
@login_required
def add_offer(aid):
    d = load(aid)
    emp = request.form.get("employer", "").strip()
    st = request.form.get("status", "Sent")
    if emp and st in OFFER:
        offers = d.setdefault("_offers", [])
        offers.append({"id": next_id(offers), "employer": emp, "date": datetime.date.today().isoformat(), "status": st})
        if st == "Accepted" and not d.get("employer"):
            d["employer"] = emp
        save_data(aid, d)
        log("cv sent", aid, "%s to %s" % (d.get("name", ""), emp))
    return redirect(url_for("case", aid=aid) + "#offers")


@app.route("/case/<int:aid>/offer/<int:oid>", methods=["POST"])
@login_required
def set_offer(aid, oid):
    d = load(aid)
    st = request.form.get("status", "")
    for o in d.get("_offers", []):
        if o["id"] == oid and st in OFFER:
            o["status"] = st
            if st == "Accepted" and not d.get("employer"):
                d["employer"] = o["employer"]
            log("employer reply", aid, "%s: %s" % (o["employer"], st))
    save_data(aid, d)
    return redirect(url_for("case", aid=aid) + "#offers")


def events():
    ev, today = [], datetime.date.today()
    for r in db().execute("select id,data from app"):
        d = json.loads(r["data"])
        t = track(d)

        def add(dt, kind, text):
            if dt:
                ev.append(dict(date=dt, days=(dt - today).days, kind=kind, text=text, id=r["id"], name=d.get("name", "")))

        if t["stage"] < 5:
            add(iso(d.get("flight_date")), "flight", "Flight" + (" to " + d["destination"] if d.get("destination") else ""))
        m = medical(t)
        if m and t["stage"] in (2, 3, 4):
            add(m[0], "medical", "Medical expires")
        ex = iso(d.get("expiry_date"))
        if ex and ex < today + datetime.timedelta(days=365):
            add(ex, "passport", "Passport expires")
        for nt in d.get("_notes", []):
            if not nt["done"] and nt.get("due"):
                add(iso(nt["due"]), "note", nt["text"][:60])
    ev.sort(key=lambda e: e["date"])
    return ev


@app.route("/agenda")
@login_required
def agenda():
    ev = events()
    groups = [("Overdue", [e for e in ev if e["days"] < 0]), ("This week", [e for e in ev if 0 <= e["days"] <= 7]),
              ("Next 30 days", [e for e in ev if 8 <= e["days"] <= 30]), ("Later", [e for e in ev if e["days"] > 30])]
    return render_template("agenda.html", groups=[g for g in groups if g[1]])


@app.route("/agenda.ics")
@login_required
def agenda_ics():
    esc = lambda x: x.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", " ")
    stamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//ASM CV Studio//EN"]
    for e in events():
        if e["days"] >= -30:
            lines += ["BEGIN:VEVENT", "UID:%s-%s-%s@asm" % (e["id"], e["kind"], e["date"].isoformat()), "DTSTAMP:" + stamp,
                      "DTSTART;VALUE=DATE:" + e["date"].strftime("%Y%m%d"), "SUMMARY:" + esc("%s: %s" % (e["name"], e["text"])), "END:VEVENT"]
    lines.append("END:VCALENDAR")
    r = make_response("\r\n".join(lines))
    r.headers["Content-Type"] = "text/calendar; charset=utf-8"
    r.headers["Content-Disposition"] = 'attachment; filename="asm_agenda.ics"'
    return r


@app.route("/stats")
@login_required
def stats():
    today = datetime.date.today()
    counts, months, docs = [0] * len(STAGES), {}, []
    gaps = {i: [] for i in range(1, len(STAGES))}
    flights = 0
    for r in db().execute("select * from app"):
        d = json.loads(r["data"])
        t = track(d)
        counts[t["stage"]] += 1
        months[(r["created"] or "")[:7]] = months.get((r["created"] or "")[:7], 0) + 1
        docs.append(readiness(d, r["id"])[1])
        for i in range(1, len(STAGES)):
            a = iso(r["created"][:10]) if i == 1 else iso(t["dates"].get(str(i - 1)))
            b = iso(t["dates"].get(str(i)))
            if a and b and t["stage"] >= i:
                gaps[i].append((b - a).days)
        fd = iso(d.get("flight_date"))
        flights += bool(fd and t["stage"] < 5 and 0 <= (fd - today).days <= 30)
    keys, y, m = [], today.year, today.month
    for k in range(5, -1, -1):
        mm, yy = m - k, y
        while mm <= 0:
            mm, yy = mm + 12, yy - 1
        keys.append((datetime.date(yy, mm, 1).strftime("%b"), months.get("%04d-%02d" % (yy, mm), 0)))
    total = sum(counts)
    return render_template("stats.html", counts=counts, total=total, keys=keys, flights=flights,
                           avg_docs=round(sum(docs) / len(docs)) if docs else 0,
                           gaps=[(STAGES[i - 1][0], STAGES[i][0], round(sum(v) / len(v), 1)) for i, v in gaps.items() if v],
                           moving=total - counts[0] - counts[-1], travelled=counts[-1])


def render_pdf(html):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.set_content(html, wait_until="load")
        pg.evaluate("document.fonts.ready")
        pdf = pg.pdf(prefer_css_page_size=True, print_background=True)
        b.close()
    return pdf


@app.route("/case/<int:aid>/file.pdf")
@login_required
def travel_file(aid):
    d = load(aid)
    items, pct = readiness(d, aid)
    cap = {"passport": d.get("passport_no", ""), "idcard": d.get("id_no", ""), "coc1": d.get("coc1_no", ""), "coc2": d.get("coc2_no", ""),
           "guarantor_id": " · ".join(x for x in (d.get("guarantor_name"), d.get("guarantor_phone"), d.get("guarantor_id_no")) if x)}
    ph = photos(aid, True, KINDS + DOCS)
    pages = [(t, k, cap.get(k, "")) for k, t in (("passport", "Passport page"), ("idcard", "Traveler ID"), ("guarantor_id", "Guarantor ID"),
                                                  ("coc1", "COC certificate 1"), ("coc2", "COC certificate 2"), ("consent", "Signed consent")) if ph.get(k)]
    facts = [(L[k][0], pretty(d)[k]) for k in ("ref", "post", "phone", "nationality", "dob", "passport_no", "expiry_date", "id_no", "labor_id",
                                                "guarantor_name", "guarantor_phone", "guarantor_id_no", "coc1_no", "coc2_no",
                                                "employer", "destination", "visa_no", "flight_date", "airline") if d.get(k)]
    html = render_template("filepack.html", d=d, t=track(d), items=items, pct=pct, ph=ph, pages=pages, facts=facts, logo=logo(True),
                           issued=datetime.date.today().strftime("%d %b %Y"))
    log("travel file", aid, d.get("name", ""))
    return pdf_response(render_pdf(html), (d.get("name") or "case").replace(" ", "_") + "_travel_file.pdf")


@app.route("/staff")
@admin_required
def staff():
    users = db().execute("select id,username,role,active from user order by id").fetchall()
    return render_template("staff.html", users=users, admin=True, m=request.args.get("m", ""))


@app.route("/staff/add", methods=["POST"])
@admin_required
def staff_add():
    u, pw, role = request.form.get("username", "").strip().lower(), request.form.get("password", ""), request.form.get("role", "staff")
    if not re.fullmatch(r"[a-z0-9._-]{3,20}", u) or len(pw) < 8 or role not in ("admin", "staff"):
        return redirect(url_for("staff", m="Username: 3-20 letters/numbers. Password: at least 8 characters."))
    try:
        c = db()
        c.execute("insert into user(username,pw,role,active,created) values(?,?,?,1,?)", (u, generate_password_hash(pw), role, datetime.datetime.now().isoformat()))
        c.commit()
    except sqlite3.IntegrityError:
        return redirect(url_for("staff", m="That username already exists."))
    log("staff added", None, "%s (%s)" % (u, role))
    return redirect(url_for("staff", m="Added " + u))


@app.route("/staff/<int:uid>/toggle", methods=["POST"])
@admin_required
def staff_toggle(uid):
    if uid != session.get("uid"):
        c = db()
        c.execute("update user set active = 1 - active where id=?", (uid,))
        c.commit()
        log("staff toggled", None, str(uid))
    return redirect(url_for("staff"))


@app.route("/staff/<int:uid>/password", methods=["POST"])
@admin_required
def staff_password(uid):
    pw = request.form.get("password", "")
    if len(pw) < 8:
        return redirect(url_for("staff", m="Password: at least 8 characters."))
    c = db()
    c.execute("update user set pw=? where id=?", (generate_password_hash(pw), uid))
    c.commit()
    log("password reset", None, str(uid))
    return redirect(url_for("staff", m="Password updated."))


@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    m = ""
    if request.method == "POST":
        c = db()
        u = c.execute("select pw from user where id=?", (session["uid"],)).fetchone()
        new = request.form.get("new", "")
        if not check_password_hash(u["pw"], request.form.get("current", "")):
            m = "Current password is wrong."
        elif len(new) < 8:
            m = "New password: at least 8 characters."
        else:
            c.execute("update user set pw=? where id=?", (generate_password_hash(new), session["uid"]))
            c.commit()
            log("password changed")
            m = "Password changed."
    return render_template("staff.html", users=[], admin=False, m=m)


if __name__ == "__main__":
    app.run(debug=APP_ENV != "production", host="0.0.0.0", port=5000)
