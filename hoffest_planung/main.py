from datetime import timedelta
from flask import (
    Flask,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    Blueprint,
    url_for,
)
from logger import get_logger
from flask_cors import CORS
import db
from werkzeug.middleware.proxy_fix import ProxyFix

db_manager = db.DatabaseManager()

logger = get_logger("main")
secretAuthKey = open("./secretAuthCode.txt", "r").readline()

admin = Blueprint("admin", __name__, url_prefix="/admin")


# Global admin verification
@admin.before_request
def check_admin():
    print("checking admin")
    if not isinstance(session.get("adminName"), str):
        return redirect(url_for("login_route"))


app = Flask(__name__)


# Global user verification
@app.before_request
def check_auth():
    print("checking auth............")
    print(request.path)
    if request.path in [
        "/login",
        "/",
        "/favicon.ico",
        "/moodleApi",
    ] or request.path.startswith("/admin"):
        print("ok")
        return  # Authentifizierung nicht erforderlich für diese Endpunkte
    if not checkAuth(session.get("id")):
        print("not ok")
        session.clear()
        return redirect(url_for("index"))


app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1)
CORS(app)
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(weeks=99999)
app.config["SECRET_KEY"] = open("./flaskSecretKey.txt", "r").readline()


def checkAuth(user_id):
    """Prüft, ob die Authentifizierung gültig ist und ob der Benutzer vertrauenswürdig ist."""
    if user_id == "bypass":
        return True  # Erlaubt Bypass-Benutzer

    if not validate_auth(user_id):
        return False  # Ungültige Authentifizierung

    if not db_manager.check_trusted_id(user_id):
        print("User ID is not trusted")
        return False  # Nicht vertrauenswürdig

    return True


@app.route("/")
def index():
    id = request.args.get("id", "")
    if id != "":
        if checkAuth(id):  # important local check!
            session["id"] = id
            return redirect("/")
        return (
            jsonify(
                error="Invalid authentication",
                bypass="https://hoffest.t-auer.com/?id=bypass",
            ),
            401,
        )

    sessionValue = session.get("id", "")
    print("SESSION VALUE: " + sessionValue)
    if not checkAuth(sessionValue):
        session.clear()
        return (
            jsonify(
                error="Invalid authentication",
                bypass="https://hoffest.t-auer.com/?id=bypass",
            ),
            401,
        )

    questions = db_manager.get_questions()
    logger.debug("Got questions: " + str(questions))

    already_submitted_data = db_manager.get_submitted_data_from_id(session.get("id"))
    return render_template(
        "index.html", already_submitted_data=already_submitted_data, questions=questions
    )


@app.route("/commitStand", methods=["POST"])
def commitStand():
    data = request.json
    print(data)
    if db_manager.addNewStand(data, auth_id=session.get("id")):
        return jsonify({"ok": "ok"}), 200
    return jsonify({"error": "error"}), 401


@app.route("/test")
def test():
    print("test")
    return jsonify(ok=True), 200


@app.route("/register", methods=["POST"])
def register():
    data = request.json
    id = data["id"]
    secret = data["secret"] == secretAuthKey
    if secret and validate_auth(id):
        if db_manager.addNewTrustedId(id):
            print("success")
            return jsonify(ok=True), 200
        return jsonify(error="Failed to add ID"), 400


@admin.route("/", methods=["POST", "GET"])
def admin_route():
    data = {
        "active": 0,
        "pending": [],
        "completed": [],
    }
    pending_ids = db_manager.get_pending()
    for id in pending_ids:
        tempData = db_manager.get_submitted_data_from_stand_id(id)
        data["pending"].append(
            {
                "lehrer": tempData[2],
                "klasse": tempData[3],
                "titel": tempData[4],
                "beschreibung": tempData[5],
                "ort": tempData[0],
                "ort_spezifikation": tempData[1],
                "question_ids": tempData[6],
                "id": tempData[9],
            }
        )
    pending_ids = db_manager.get_completed()
    for id in pending_ids:
        tempData = db_manager.get_submitted_data_from_stand_id(id)
        data["completed"].append(
            {
                "lehrer": tempData[2],
                "klasse": tempData[3],
                "titel": tempData[4],
                "beschreibung": tempData[5],
                "ort": tempData[0],
                "ort_spezifikation": tempData[1],
                "question_ids": tempData[6],
                "kommentar": tempData[8],
                "id": tempData[9]
            }
        )
    return render_template("dashBASE.html", data=data)


@admin.route("/loader/<page>")
def loader(page):
    return app.send_static_file(f"loader/{page}")

@admin.route("/stand/<path_id>", methods=["GET", "POST"])
def admin_stand_route(path_id):
    if request.method == "POST":
        data = request.json
        print(data)
        if not db_manager.approve_stand(path_id, data["status"], data["comment"]):
            logger.error(f"Error approving stand")
            return jsonify({"error": "Error approving stand"}), 500
        return jsonify({"ok": "ok"}), 200
    stand_data = db_manager.get_submitted_data_from_stand_id(path_id)
    return render_template("review.html", data=stand_data)


@app.route("/moodleApi")
def moodleApi():
    id = request.args.get("id", "nothing")

    if not checkAuth(id):
        return jsonify({"error": "Invalid authentication"}), 401
    confirmedIDS = db_manager.get_completed()
    confirmed = []
    for id in confirmedIDS:
        data = db_manager.get_submitted_data_from_stand_id(id)
        confirmed.append({"lehrer": data[2], "name": data[4]})

    pendingIDS = db_manager.get_pending()
    pending = []
    for id in pendingIDS:
        data = db_manager.get_submitted_data_from_stand_id(id)
        pending.append({"lehrer": data[2], "name": data[4]})
    return jsonify({"confirmed": confirmed, "pending": pending}), 200


@app.route("/login", methods=["POST", "GET"])
def login_route(data=None):
    if request.method == "POST":
        data = request.json
    if data:
        print("login route")
        username = data["username"]
        password = data["password"]
        if db_manager.authenticateAdmin(username, password):
            session["adminName"] = username
            return "ok", 200
        else:
            return "failed", 401
    return render_template("/login.html")


@app.route("/robots.txt")
def static_robots():
    return "<pre>" + open("robots.txt").read().replace("\n", "<br>") + "</pre>"


def validate_auth(auth):
    try:
        id, checksum = auth.split(":")
    except Exception:
        return False
    logger.info("validating auth")
    logger.info(
        f"checksum: {type(checksum)}\nhashed: {type(reverse_obfuscated_algorithm(id))}"
    )
    return str(checksum) == str(reverse_obfuscated_algorithm(id))


def reverse_obfuscated_algorithm(input_string):
    input_string = str(input_string)
    hash_value = 0

    if len(input_string) == 0:
        return hash_value

    for char in input_string:
        char_code = ord(char)
        hash_value = ((hash_value << 5) - hash_value) + char_code
        hash_value = hash_value & 0xFFFFFFFF

    if hash_value >= 0x80000000:
        hash_value -= 0x100000000

    logger.info(hash_value)
    return hash_value


if __name__ == "__main__":
    app.register_blueprint(admin)
    app.run(port=8000, host="0.0.0.0", threaded=True, debug=True)
