import os
from twilio.rest import Client
from flask import Flask, render_template, request, redirect, url_for, session
import pyotp
import face_recognition
import cv2
import base64

# --- Flask Configuration ---
app = Flask(__name__)
app.secret_key = "supersecretkey"  # Secret key for session management

# Twilio configuration
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file

account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
client = Client(account_sid, auth_token)
twilio_service_sid = 'VA716f35a278f0a52624c0d00a695ddf56'

PRE_STORED_PASSWORD = "vishwas1234"
KNOWN_FACES_DIR = "known_faces"

# --- Routes ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/password", methods=["GET", "POST"])
def password():
    if request.method == "POST":
        password = request.form["password"]
        if password == PRE_STORED_PASSWORD:
            session["password_auth"] = True
            return redirect(url_for("otp"))
        else:
            return render_template("password.html", error="Incorrect password. Try again.")
    return render_template("password.html")

@app.route("/otp", methods=["GET", "POST"])
def otp():
    if "password_auth" not in session:
        return redirect(url_for("password"))
    
    if request.method == "POST":
        user_input = request.form["otp"]
        
        # Verify the OTP using Twilio Verify API
        verification_check = client.verify \
            .v2 \
            .services(twilio_service_sid) \
            .verification_checks \
            .create(to='+917389645252', code=user_input)

        if verification_check.status == "approved":
            session["otp_auth"] = True
            return redirect(url_for("face_recognition_page"))
        else:
            return render_template("otp.html", error="Invalid OTP. Try again.")
    
    # Start Twilio verification process (Send OTP)
    verification = client.verify \
        .v2 \
        .services(twilio_service_sid) \
        .verifications \
        .create(to='+917389645252', channel='sms')
    
    print(f"Verification SID: {verification.sid}")
    return render_template("otp.html")

@app.route("/face_recognition", methods=["GET", "POST"])
def face_recognition_page():
    if "otp_auth" not in session:
        return redirect(url_for("otp"))

    if request.method == "POST":
        # Start face recognition
        video_capture = cv2.VideoCapture(0)

        if not video_capture.isOpened():
            return render_template("face_recognition.html", error="Unable to access the webcam. Please check your camera.")
        
        known_faces = []
        known_names = []

        # Load known faces
        for filename in os.listdir(KNOWN_FACES_DIR):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                image_path = os.path.join(KNOWN_FACES_DIR, filename)
                image = face_recognition.load_image_file(image_path)
                try:
                    encoding = face_recognition.face_encodings(image)[0]
                    known_faces.append(encoding)
                    known_names.append(os.path.splitext(filename)[0])
                except IndexError:
                    continue

        # Recognize face
        while True:
            ret, frame = video_capture.read()
            if not ret:
                break

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(known_faces, face_encoding)
                if True in matches:
                    matched_index = matches.index(True)
                    name = known_names[matched_index]
                    video_capture.release()
                    cv2.destroyAllWindows()
                    session["face_auth"] = True
                    return redirect(url_for("success"))

            # Convert frame to base64 string to send to the browser
            _, buffer = cv2.imencode('.jpg', frame)
            encoded_frame = base64.b64encode(buffer).decode('utf-8')

            return render_template("face_recognition.html", frame=encoded_frame)

        video_capture.release()
        cv2.destroyAllWindows()
        return render_template("face_recognition.html", error="Face not recognized. Try again.")

    return render_template("face_recognition.html")

@app.route("/success")
def success():
    if "face_auth" not in session:
        return redirect(url_for("face_recognition"))
    return render_template("success.html")

if __name__ == "__main__":
    app.run(debug=True)