import os
import sqlite3
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime, timedelta
import json
from typing import Optional
import subprocess
import tempfile
import pygame
# Add these new imports for document processing
import PyPDF2
import docx
from io import StringIO
from dotenv import load_dotenv
load_dotenv()

from gtts import gTTS
from mutagen.mp3 import MP3
import google.generativeai as genai
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import email_validator
from PIL import Image, ImageDraw, ImageFont
import pytesseract
import threading
import time
import requests
import speech_recognition as sr
from io import BytesIO
import base64
from email_validator import validate_email, EmailNotValidError
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.config['UPLOAD_FOLDER'] = 'static/images/profile_pics'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Configure Gemini AI
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel('gemini-2.5-flash')
gemini_model1 = genai.GenerativeModel('models/gemini-1.5-flash-002')
# Ensure directories exist
os.makedirs('instance', exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/uploads', exist_ok=True)
os.makedirs('static/images', exist_ok=True)

# Create AI avatar if it doesn't exist
def create_ai_avatar():
    avatar_path = 'static/images/ai-bot.png'
    if not os.path.exists(avatar_path):
        try:
            # Create a simple avatar with AI text
            img = Image.new('RGB', (100, 100), color=(54, 185, 204))
            d = ImageDraw.Draw(img)
            
            try:
                font = ImageFont.truetype("arial.ttf", 30)
            except:
                font = ImageFont.load_default()
            
            d.text((35, 35), "AI", fill=(255, 255, 255), font=font)
            img.save(avatar_path)
            print("AI avatar created successfully")
        except Exception as e:
            print(f"Could not create AI avatar: {e}")
            # Create a fallback avatar using a simple circle
            try:
                img = Image.new('RGB', (100, 100), color=(54, 185, 204))
                d = ImageDraw.Draw(img)
                d.ellipse((10, 10, 90, 90), fill=(54, 185, 204), outline=(255, 255, 255), width=3)
                d.text((40, 40), "AI", fill=(255, 255, 255))
                img.save(avatar_path)
            except:
                print("Failed to create fallback AI avatar")

# Create AI avatar
create_ai_avatar()

# Initialize database
def init_db():
    conn = sqlite3.connect('instance/app.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT UNIQUE NOT NULL,
                 email TEXT UNIQUE NOT NULL,
                 password_hash TEXT NOT NULL,
                 profile_pic TEXT DEFAULT 'default.png',
                 dark_mode INTEGER DEFAULT 0,
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Emails table
    c.execute('''CREATE TABLE IF NOT EXISTS emails
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER NOT NULL,
                 from_email TEXT NOT NULL,
                 to_email TEXT NOT NULL,
                 subject TEXT,
                 body TEXT,
                 sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 hash_code TEXT NOT NULL,
                 FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # Calendar events table
    c.execute('''CREATE TABLE IF NOT EXISTS events
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER NOT NULL,
                 title TEXT NOT NULL,
                 description TEXT,
                 event_date DATE NOT NULL,
                 event_time TIME NOT NULL,
                 priority INTEGER DEFAULT 1,
                 notified INTEGER DEFAULT 0,
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 hash_code TEXT NOT NULL,
                 FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # Tasks table
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER NOT NULL,
                 title TEXT NOT NULL,
                 description TEXT,
                 due_date DATE,
                 due_time TIME,
                 priority INTEGER DEFAULT 1,
                 status TEXT DEFAULT 'pending',
                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 hash_code TEXT NOT NULL,
                 FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # Documents table
    c.execute('''CREATE TABLE IF NOT EXISTS documents
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER NOT NULL,
                 filename TEXT NOT NULL,
                 content_hash TEXT NOT NULL,
                 extracted_text_hash TEXT,
                 uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # Code executions table
    c.execute('''CREATE TABLE IF NOT EXISTS code_executions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER NOT NULL,
                 language TEXT NOT NULL,
                 code TEXT NOT NULL,
                 output TEXT,
                 executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                 FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    """
    Create and return a database connection
    """
    conn = sqlite3.connect('database.db')  # change path if needed
    conn.row_factory = sqlite3.Row
    return conn

def update_database_schema():
    """
    Update database schema to remove priority column from events table
    """
    conn = get_db_connection()
    try:
        # Check if priority column exists
        cursor = conn.execute("PRAGMA table_info(events)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'priority' in columns:
            # Create temporary table without priority
            conn.execute('''CREATE TABLE events_new 
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         user_id INTEGER NOT NULL,
                         title TEXT NOT NULL,
                         description TEXT,
                         event_date DATE NOT NULL,
                         event_time TIME NOT NULL,
                         notified INTEGER DEFAULT 0,
                         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                         hash_code TEXT NOT NULL,
                         FOREIGN KEY (user_id) REFERENCES users (id))''')
            
            # Copy data without priority
            conn.execute('''INSERT INTO events_new 
                         (id, user_id, title, description, event_date, event_time, notified, created_at, hash_code)
                         SELECT id, user_id, title, description, event_date, event_time, notified, created_at, hash_code
                         FROM events''')
            
            # Drop old table and rename new one
            conn.execute('DROP TABLE events')
            conn.execute('ALTER TABLE events_new RENAME TO events')
            conn.commit()
            print("Database schema updated successfully")
            
    except Exception as e:
        print(f"Error updating database schema: {e}")
    finally:
        conn.close()

# Call this function after init_db()
init_db()
update_database_schema()
init_db()

# Helper functions
def get_db_connection():
    conn = sqlite3.connect('instance/app.db')
    conn.row_factory = sqlite3.Row
    return conn

def generate_hash(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

def text_to_speech(text, filename='output.mp3'):
    try:
        tts = gTTS(text=text, lang='en')
        tts.save(filename)
        return filename
    except Exception as e:
        print(f"Error in text_to_speech: {e}")
        return None

# NEW: Function to extract text from PDF files
def extract_text_from_pdf(pdf_path):
    try:
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error extracting text from PDF: {str(e)}"
def send_event_notification(user_email, title, description, event_date, event_time):
    """
    Send email notification when a new event is scheduled
    """
    try:
        sender_email = os.getenv("EMAIL_ADDRESS")
        sender_password = os.getenv("EMAIL_PASSWORD")
        
        # Format the event date and time
        event_datetime = f"{event_date} at {event_time}"
        
        subject = f"New Event Scheduled: {title}"
        body = f"""
        Hello!
        
        You have successfully scheduled a new event:
        
        Event: {title}
        Description: {description}
        Date & Time: {event_datetime}
        
        This event has been added to your calendar.
        
        Best regards,
        Your Calendar App
        """
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = user_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            
        print(f"Event notification sent to {user_email}")
        return True
        
    except Exception as e:
        print(f"Error sending event notification: {e}")
        return False
# NEW: Function to extract text from DOC/DOCX files
def extract_text_from_docx(docx_path):
    try:
        doc = docx.Document(docx_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        return f"Error extracting text from DOCX: {str(e)}"

# NEW: Function to extract text from TXT files
def extract_text_from_txt(txt_path):
    try:
        with open(txt_path, 'r', encoding='utf-8', errors='ignore') as file:
            return file.read()
    except Exception as e:
        return f"Error extracting text from TXT: {str(e)}"

# NEW: Unified text extraction function
def extract_text_from_file(filepath, filename):
    file_extension = filename.lower().split('.')[-1]
    
    if file_extension in ['png', 'jpg', 'jpeg', 'gif']:
        return extract_text_from_image(filepath)
    elif file_extension == 'pdf':
        return extract_text_from_pdf(filepath)
    elif file_extension in ['doc', 'docx']:
        return extract_text_from_docx(filepath)
    elif file_extension == 'txt':
        return extract_text_from_txt(filepath)
    else:
        # Fallback for other file types - try to read as text
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as file:
                return file.read()
        except:
            return "Unable to extract text from this file type"
def notify_user(
    to_email: str,
    sender_override: Optional[str] = None,
    password_override: Optional[str] = None
) -> bool:
    """
    Send a registration notification email.

    Environment variables used (if overrides not provided):
      EMAIL_ADDRESS  -> sender email (e.g. "you@example.com")
      EMAIL_PASSWORD -> sender's SMTP password (app password if using Gmail + 2FA)

    Returns True on success, False on failure.
    """

    # Validate recipient email
    try:
        validated_recipient = validate_email(to_email).email
    except EmailNotValidError as e:
        print("Invalid recipient email:", e)
        return False

    # Get sender and password from overrides or environment variables
    sender = sender_override or os.environ.get("EMAIL_ADDRESS")
    password = password_override or os.environ.get("EMAIL_PASSWORD")

    if not sender:
        print("EMAIL_ADDRESS environment variable not set and no sender_override provided. Aborting send.")
        return False
    if not password:
        print("EMAIL_PASSWORD environment variable not set and no password_override provided. Aborting send.")
        return False

    # Validate sender email too
    try:
        validated_sender = validate_email(sender).email
    except EmailNotValidError as e:
        print("Invalid sender email:", e)
        return False

    subject = "Registration successful"
    body = "User registered successfully. Now you can login to access the features."

    msg = MIMEMultipart()
    msg["From"] = validated_sender
    msg["To"] = validated_recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        # Using Gmail SMTP with STARTTLS (port 587)
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(validated_sender, password)
            server.send_message(msg)
        print("Email sent successfully to", validated_recipient)
        return True
    except smtplib.SMTPAuthenticationError as e:
        print("SMTP authentication failed:", e)
    except smtplib.SMTPException as e:
        print("SMTP error occurred:", e)
    except Exception as e:
        print("Failed to send email:", e)
    return False

def play_audio(filename):
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    except Exception as e:
        print(f"Error playing audio: {e}")

def allowed_file(filename, allowed_extensions={'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt'}):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def extract_text_from_image(image_path):
    try:
        return pytesseract.image_to_string(Image.open(image_path))
    except Exception as e:
        return f"Error extracting text from image: {str(e)}"

# Simple translation function using Gemini AI instead of googletrans
def translate_text(text, dest_lang='en'):
    try:
        # Use Gemini AI for translation
        prompt = f"Translate this text to {dest_lang}: {text}"
        response = gemini_model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Translation error: {str(e)}"

def speech_to_text():
    try:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            print("Listening...")
            audio = r.listen(source)
        text = r.recognize_google(audio)
        return text
    except Exception as e:
        return f"Speech recognition error: {str(e)}"

# # Background task for event notifications
# def check_event_notifications():
#     while True:
#         try:
#             conn = get_db_connection()
#             now = datetime.now()
#             current_time = now.strftime("%H:%M")
#             current_date = now.strftime("%Y-%m-%d")
            
#             events = conn.execute('''SELECT e.*, u.email 
#                                    FROM events e 
#                                    JOIN users u ON e.user_id = u.id 
#                                    WHERE e.event_date = ? AND e.event_time BETWEEN ? AND ? AND e.notified = 0''', 
#                                    (current_date, (now - timedelta(minutes=10)).strftime("%H:%M"), current_time)).fetchall()
            
#             for event in events:
#                 # Send notification (in a real app, this would be email/push notification)
#                 print(f"NOTIFICATION: Event '{event['title']}' is happening now or soon for user {event['email']}")
                
#                 # Mark as notified
#                 conn.execute('UPDATE events SET notified = 1 WHERE id = ?', (event['id'],))
#                 conn.commit()
                
#         except Exception as e:
#             print(f"Error in notification system: {e}")
        
#         time.sleep(60)  # Check every minute


# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember_me = 'remember_me' in request.form
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['dark_mode'] = user['dark_mode']
            
            if remember_me:
                session.permanent = True
                
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html', now=datetime.now())

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        try:
            # Validate email
            email_validator.validate_email(email)
        except email_validator.EmailNotValidError as e:
            flash(str(e), 'error')
            return render_template('register.html')
        
        password_hash = generate_password_hash(password)
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                         (username, email, password_hash))
            conn.commit()
            flash('Registration successful! Please log in.', 'success')
            print('registered')
            notify_user(email,
            sender_override=os.getenv("EMAIL_ADDRESS"),
            password_override=os.getenv("EMAIL_PASSWORD"))
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or email already exists', 'error')
        finally:
            conn.close()
    
    return render_template('register.html', now=datetime.now())

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    # Get recent activities
    recent_emails = conn.execute('SELECT * FROM emails WHERE user_id = ? ORDER BY sent_at DESC LIMIT 5', 
                                (session['user_id'],)).fetchall()
    recent_tasks = conn.execute('SELECT * FROM tasks WHERE user_id = ? ORDER BY created_at DESC LIMIT 5', 
                               (session['user_id'],)).fetchall()
    recent_code = conn.execute('SELECT * FROM code_executions WHERE user_id = ? ORDER BY executed_at DESC LIMIT 5', 
                              (session['user_id'],)).fetchall()
    
    conn.close()
    
    return render_template('dashboard.html', user=user, recent_emails=recent_emails, 
                          recent_tasks=recent_tasks, recent_code=recent_code, now=datetime.now())

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and file.filename != '' and allowed_file(file.filename, {'png', 'jpg', 'jpeg', 'gif'}):
                filename = secure_filename(f"{session['user_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                # Delete old profile pic if it's not the default
                if user['profile_pic'] != 'default.png':
                    old_filepath = os.path.join(app.config['UPLOAD_FOLDER'], user['profile_pic'])
                    if os.path.exists(old_filepath):
                        os.remove(old_filepath)
                
                conn.execute('UPDATE users SET profile_pic = ? WHERE id = ?', (filename, session['user_id']))
                conn.commit()
                flash('Profile picture updated successfully!', 'success')
    
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()
    
    return render_template('profile.html', user=user, now=datetime.now())

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        dark_mode = 1 if 'dark_mode' in request.form else 0
        conn.execute('UPDATE users SET dark_mode = ? WHERE id = ?', (dark_mode, session['user_id']))
        conn.commit()
        session['dark_mode'] = dark_mode
        flash('Settings updated successfully!', 'success')
    
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()
    
    return render_template('settings.html', user=user, now=datetime.now())

@app.route('/email', methods=['GET', 'POST'])
def email_compose():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        from_email = request.form['from_email']
        to_email = request.form['to_email']
        subject = request.form['subject']
        
        # Generate email body using Gemini AI if requested
        if 'generate_body' in request.form and subject:
            try:
                prompt = f"Generate a professional email body about: {subject}"
                response = gemini_model.generate_content(prompt)
                body = response.text
                return render_template('email.html', user=user, subject=subject, body=body, 
                                     from_email=from_email, to_email=to_email, now=datetime.now())
            except Exception as e:
                flash(f'Error generating email content: {str(e)}', 'error')
                body = request.form.get('body', '')
        else:
            body = request.form.get('body', '')
        
        # Validate emails
        try:
            email_validator.validate_email(from_email)
            email_validator.validate_email(to_email)
        except email_validator.EmailNotValidError as e:
            flash(str(e), 'error')
            return render_template('email.html', user=user, now=datetime.now())
        
        # Send email using SMTP (simplified example)
        try:
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            # This is a simplified example - you'll need to configure your SMTP server
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                 server.starttls()
                 server.login(from_email, 'tier nspo sthq xuza')
                 server.send_message(msg)
            
            flash('Email sent successfully!', 'success')
            
            # Store email in database with hash
            email_data = {
                'from': from_email,
                'to': to_email,
                'subject': subject,
                'body': body,
                'timestamp': datetime.now().isoformat()
            }
            hash_code = generate_hash(email_data)
            
            conn.execute('INSERT INTO emails (user_id, from_email, to_email, subject, body, hash_code) VALUES (?, ?, ?, ?, ?, ?)',
                         (session['user_id'], from_email, to_email, subject, body, hash_code))
            conn.commit()
            
        except Exception as e:
            flash(f'Error sending email: {str(e)}', 'error')
    
    conn.close()
    return render_template('email.html', user=user, now=datetime.now())
@app.route('/calendar', methods=['GET', 'POST'])
def calendar():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        event_date = request.form['event_date']
        event_time = request.form['event_time']
        
        event_data = {
            'title': title,
            'description': description,
            'date': event_date,
            'time': event_time,
            'timestamp': datetime.now().isoformat()
        }
        hash_code = generate_hash(event_data)
        
        conn.execute('INSERT INTO events (user_id, title, description, event_date, event_time, hash_code) VALUES (?, ?, ?, ?, ?, ?)',
                     (session['user_id'], title, description, event_date, event_time, hash_code))
        conn.commit()
        
        # Send email notification
        try:
            send_event_notification(user['email'], title, description, event_date, event_time)
            flash('Event added successfully! Notification email sent.', 'success')
        except Exception as e:
            flash(f'Event added but failed to send notification: {str(e)}', 'warning')
    
    # Get all events for the user
    events = conn.execute('SELECT * FROM events WHERE user_id = ? ORDER BY event_date, event_time', 
                          (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('calendar.html', user=user, events=events, now=datetime.now())
@app.route('/code', methods=['GET', 'POST'])
def code_executor():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        # Check if it's a code generation request
        if 'generate_code' in request.form:
            prompt = request.form.get('code_prompt', '')
            language = request.form.get('language', 'python')
            
            try:
                full_prompt = f"Generate {language} code for: {prompt}. Provide only the code without explanations."
                response = gemini_model.generate_content(full_prompt)
                generated_code = response.text
                
                # Store in database
                conn.execute('INSERT INTO code_executions (user_id, language, code, output) VALUES (?, ?, ?, ?)',
                             (session['user_id'], language, generated_code, 'Code generated'))
                conn.commit()
                
                # Create downloadable file
                if 'download' in request.form:
                    filename = f"generated_code_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{language}"
                    with open(filename, 'w') as f:
                        f.write(generated_code)
                    return send_file(filename, as_attachment=True)
                
                return render_template('code.html', user=user, generated_code=generated_code, 
                                     language=language, prompt=prompt, now=datetime.now())
            
            except Exception as e:
                flash(f'Error generating code: {str(e)}', 'error')
        
        # Regular code execution
        else:
            code = request.form['code']
            language = request.form['language']
            
            # Use Gemini AI to execute code
            prompt = f"Execute this {language} code and provide the output:\n\n{code}"
            
            try:
                response = gemini_model.generate_content(prompt)
                output = response.text
                
                # Store in database
                conn.execute('INSERT INTO code_executions (user_id, language, code, output) VALUES (?, ?, ?, ?)',
                             (session['user_id'], language, code, output))
                conn.commit()
                
                # Create downloadable file
                if 'download' in request.form:
                    filename = f"code_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    with open(filename, 'w') as f:
                        f.write(output)
                    return send_file(filename, as_attachment=True)
                
                return render_template('code.html', user=user, output=output, code=code, language=language, now=datetime.now())
            
            except Exception as e:
                flash(f'Error executing code: {str(e)}', 'error')
    
    conn.close()
    return render_template('code.html', user=user, now=datetime.now())

@app.route('/documents', methods=['GET', 'POST'])
def document_processor():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file uploaded', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # Save file
            filename = secure_filename(f"{session['user_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            filepath = os.path.join('static/uploads', filename)
            file.save(filepath)
            
            # Read file content
            content = open(filepath, 'rb').read()
            content_hash = hashlib.sha256(content).hexdigest()
            
            # Extract text using the unified function
            extracted_text = extract_text_from_file(filepath, filename)
            
            # Store in database
            extracted_text_hash = hashlib.sha256(extracted_text.encode()).hexdigest()
            
            conn.execute('INSERT INTO documents (user_id, filename, content_hash, extracted_text_hash) VALUES (?, ?, ?, ?)',
                         (session['user_id'], filename, content_hash, extracted_text_hash))
            conn.commit()
            
            # Text to speech
            if 'read_aloud' in request.form:
                audio_file = text_to_speech(extracted_text[:500])  # Limit text length
                if audio_file:
                    play_audio(audio_file)
                    os.remove(audio_file)
            
            return render_template('documents.html', user=user, extracted_text=extracted_text, filename=filename, now=datetime.now())
        else:
            flash('Invalid file type', 'error')
    
    conn.close()
    return render_template('documents.html', user=user, now=datetime.now())
def check_event_notifications():
    while True:
        try:
            conn = get_db_connection()
            now = datetime.now()
            current_time = now.strftime("%H:%M")
            current_date = now.strftime("%Y-%m-%d")
            
            events = conn.execute('''SELECT e.*, u.email 
                                   FROM events e 
                                   JOIN users u ON e.user_id = u.id 
                                   WHERE e.event_date = ? AND e.event_time BETWEEN ? AND ? AND e.notified = 0''', 
                                   (current_date, (now - timedelta(minutes=10)).strftime("%H:%M"), current_time)).fetchall()
            
            for event in events:
                # Send reminder notification
                send_event_reminder(event['email'], event['title'], event['description'], event['event_date'], event['event_time'])
                
                # Mark as notified
                conn.execute('UPDATE events SET notified = 1 WHERE id = ?', (event['id'],))
                conn.commit()
                
        except Exception as e:
            print(f"Error in notification system: {e}")
        
        time.sleep(60)  # Check every minute
def check_task_reminders():
    """
    Background task to check for upcoming task deadlines and send reminders
    """
    while True:
        try:
            conn = get_db_connection()
            now = datetime.now()
            current_date = now.strftime("%Y-%m-%d")
            
            # Find tasks due today or tomorrow that haven't been completed
            tasks = conn.execute('''SELECT t.*, u.email 
                                  FROM tasks t 
                                  JOIN users u ON t.user_id = u.id 
                                  WHERE t.status != 'completed' 
                                  AND t.due_date IN (?, ?)''', 
                                  (current_date, (now + timedelta(days=1)).strftime("%Y-%m-%d"))).fetchall()
            
            for task in tasks:
                # Check if this task is due today or tomorrow
                due_date = datetime.strptime(task['due_date'], '%Y-%m-%d').date()
                today = now.date()
                
                if due_date == today:
                    # Task due today
                    send_task_reminder(task['email'], task['title'], task['description'], 
                                     task['due_date'], task['due_time'], "today")
                elif due_date == today + timedelta(days=1):
                    # Task due tomorrow
                    send_task_reminder(task['email'], task['title'], task['description'], 
                                     task['due_date'], task['due_time'], "tomorrow")
                
        except Exception as e:
            print(f"Error in task reminder system: {e}")
        
        time.sleep(3600)  # Check every hour

def send_task_reminder(user_email, title, description, due_date, due_time, timeframe):
    """
    Send reminder email for upcoming tasks
    """
    try:
        sender_email = os.getenv("EMAIL_ADDRESS")
        sender_password = os.getenv("EMAIL_PASSWORD")
        
        # Format due time
        due_info = due_date
        if due_time:
            due_info = f"{due_date} at {due_time}"
        
        subject = f"Task Reminder: {title} due {timeframe}"
        body = f"""
        Task Reminder!
        
        You have a task due {timeframe}:
        
        Task: {title}
        Description: {description}
        Due: {due_info}
        
        Don't forget to complete this task!
        
        Best regards,
        Your Task Management App
        """
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = user_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            
        print(f"Task reminder sent to {user_email}")
        return True
        
    except Exception as e:
        print(f"Error sending task reminder: {e}")
        return False
def send_task_notification(user_email, title, description, due_date, due_time, priority):
    """
    Send email notification when a new task is added
    """
    try:
        sender_email = os.getenv("EMAIL_ADDRESS")
        sender_password = os.getenv("EMAIL_PASSWORD")
        
        # Format priority text
        priority_text = {
            '1': 'Low',
            '2': 'Medium', 
            '3': 'High'
        }.get(str(priority), 'Medium')
        
        # Format due date and time
        due_info = "No due date set"
        if due_date:
            if due_time:
                due_info = f"{due_date} at {due_time}"
            else:
                due_info = f"{due_date} (all day)"
        
        subject = f"New Task Added: {title}"
        body = f"""
        Hello!
        
        You have successfully added a new task:
        
        Task: {title}
        Description: {description}
        Due: {due_info}
        Priority: {priority_text}
        
        This task has been added to your task manager.
        
        Best regards,
        Your Task Management App
        """
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = user_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            
        print(f"Task notification sent to {user_email}")
        return True
        
    except Exception as e:
        print(f"Error sending task notification: {e}")
        return False
task_reminder_thread = threading.Thread(target=check_task_reminders, daemon=True)
task_reminder_thread.start()
# Start notification thread
notification_thread = threading.Thread(target=check_event_notifications, daemon=True)
notification_thread.start()

def send_event_reminder(user_email, title, description, event_date, event_time):
    """
    Send reminder email for upcoming events
    """
    try:
        sender_email = os.getenv("EMAIL_ADDRESS")
        sender_password = os.getenv("EMAIL_PASSWORD")
        
        subject = f"Event Reminder: {title}"
        body = f"""
        Reminder!
        
        You have an event starting soon:
        
        Event: {title}
        Description: {description}
        Time: {event_date} at {event_time}
        
        Don't forget to attend!
        
        Best regards,
        Your Calendar App
        """
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = user_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            
        print(f"Event reminder sent to {user_email}")
        return True
        
    except Exception as e:
        print(f"Error sending event reminder: {e}")
        return False
@app.route('/tasks', methods=['GET', 'POST'])
def task_manager():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        due_date = request.form.get('due_date')
        due_time = request.form.get('due_time')
        priority = request.form.get('priority', 2)
        
        task_data = {
            'title': title,
            'description': description,
            'due_date': due_date,
            'due_time': due_time,
            'priority': priority,
            'timestamp': datetime.now().isoformat()
        }
        hash_code = generate_hash(task_data)
        
        conn.execute('INSERT INTO tasks (user_id, title, description, due_date, due_time, priority, hash_code) VALUES (?, ?, ?, ?, ?, ?, ?)',
                     (session['user_id'], title, description, due_date, due_time, priority, hash_code))
        conn.commit()
        
        # Send email notification
        try:
            send_task_notification(user['email'], title, description, due_date, due_time, priority)
            flash('Task added successfully! Notification email sent.', 'success')
        except Exception as e:
            flash(f'Task added but failed to send notification: {str(e)}', 'warning')
    
    # Get all tasks for the user
    tasks = conn.execute('SELECT * FROM tasks WHERE user_id = ? ORDER BY priority DESC, due_date, due_time', 
                         (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('tasks.html', user=user, tasks=tasks, now=datetime.now())


@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    response = None
    extracted_text = ""
    filename = None
    user_input=""
    if request.method == 'POST':
        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            if file and allowed_file(file.filename):
                # Save file
                filename = secure_filename(f"{session['user_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                filepath = os.path.join('static/uploads', filename)
                file.save(filepath)

                try:
                    # Upload file to Gemini
                    sample_file = genai.upload_file(path=filepath)

                    # Tell Gemini to OCR this file
                    text_prompt = "OCR this file and extract all readable text."
                    response_obj = gemini_model1.generate_content([text_prompt, sample_file])

                    extracted_text = response_obj.text

                except Exception as e:
                    extracted_text = f"Error extracting text: {str(e)}"

                return render_template(
                    'chatbot.html',
                    user=user,
                    extracted_text=extracted_text,
                    filename=filename,
                    now=datetime.now()
                )

        # Handle voice input
        elif 'voice_input' in request.form:
            user_input = speech_to_text()
            return render_template('chatbot.html', user=user, user_input=user_input, now=datetime.now())
        
        # Handle text input with translation
        else:
            user_input = request.form.get('message', '')
            target_lang = request.form.get('language', 'en')
            
            # Use Gemini AI for response
            try:
                # If there's extracted text, include it in the prompt
                if 'extracted_text' in request.form and request.form['extracted_text']:
                    extracted_text = request.form['extracted_text']
                    prompt = f"Based on this text: {extracted_text}\n\nAnswer this question: {user_input}"
                else:
                    prompt = user_input
                
                chat = gemini_model.start_chat(history=[])
                gemini_response = chat.send_message(prompt)
                response = gemini_response.text
                
            except Exception as e:
                response = f"Error: {str(e)}"
    
    conn.close()
    return render_template('chatbot.html', user=user, response=response, extracted_text=extracted_text, user_input=user_input, now=datetime.now())

@app.route('/code_history')
def code_history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    code_executions = conn.execute('SELECT * FROM code_executions WHERE user_id = ? ORDER BY executed_at DESC', 
                                  (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('code_history.html', user=user, code_executions=code_executions, now=datetime.now())

@app.route('/toggle_theme', methods=['POST'])
def toggle_theme():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'})
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    dark_mode = 1 - user['dark_mode']  # Toggle between 0 and 1
    conn.execute('UPDATE users SET dark_mode = ? WHERE id = ?', (dark_mode, session['user_id']))
    conn.commit()
    conn.close()
    
    session['dark_mode'] = dark_mode
    return jsonify({'dark_mode': dark_mode})

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)


def generate_hash(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

def text_to_speech(text, filename='output.mp3'):
    try:
        tts = gTTS(text=text, lang='en')
        tts.save(filename)
        return filename
    except Exception as e:
        print(f"Error in text_to_speech: {e}")
        return None

# NEW: Function to extract text from PDF files
def extract_text_from_pdf(pdf_path):
    try:
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error extracting text from PDF: {str(e)}"
def send_event_notification(user_email, title, description, event_date, event_time):
    """
    Send email notification when a new event is scheduled
    """
    try:
        sender_email = os.getenv("EMAIL_ADDRESS")
        sender_password = os.getenv("EMAIL_PASSWORD")
        
        # Format the event date and time
        event_datetime = f"{event_date} at {event_time}"
        
        subject = f"New Event Scheduled: {title}"
        body = f"""
        Hello!
        
        You have successfully scheduled a new event:
        
        Event: {title}
        Description: {description}
        Date & Time: {event_datetime}
        
        This event has been added to your calendar.
        
        Best regards,
        Your Calendar App
        """
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = user_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            
        print(f"Event notification sent to {user_email}")
        return True
        
    except Exception as e:
        print(f"Error sending event notification: {e}")
        return False
# NEW: Function to extract text from DOC/DOCX files
def extract_text_from_docx(docx_path):
    try:
        doc = docx.Document(docx_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        return f"Error extracting text from DOCX: {str(e)}"

# NEW: Function to extract text from TXT files
def extract_text_from_txt(txt_path):
    try:
        with open(txt_path, 'r', encoding='utf-8', errors='ignore') as file:
            return file.read()
    except Exception as e:
        return f"Error extracting text from TXT: {str(e)}"

# NEW: Unified text extraction function
def extract_text_from_file(filepath, filename):
    file_extension = filename.lower().split('.')[-1]
    
    if file_extension in ['png', 'jpg', 'jpeg', 'gif']:
        return extract_text_from_image(filepath)
    elif file_extension == 'pdf':
        return extract_text_from_pdf(filepath)
    elif file_extension in ['doc', 'docx']:
        return extract_text_from_docx(filepath)
    elif file_extension == 'txt':
        return extract_text_from_txt(filepath)
    else:
        # Fallback for other file types - try to read as text
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as file:
                return file.read()
        except:
            return "Unable to extract text from this file type"
def notify_user(
    to_email: str,
    sender_override: Optional[str] = None,
    password_override: Optional[str] = None
) -> bool:
    """
    Send a registration notification email.

    Environment variables used (if overrides not provided):
      EMAIL_ADDRESS  -> sender email (e.g. "you@example.com")
      EMAIL_PASSWORD -> sender's SMTP password (app password if using Gmail + 2FA)

    Returns True on success, False on failure.
    """

    # Validate recipient email
    try:
        validated_recipient = validate_email(to_email).email
    except EmailNotValidError as e:
        print("Invalid recipient email:", e)
        return False

    # Get sender and password from overrides or environment variables
    sender = sender_override or os.environ.get("EMAIL_ADDRESS")
    password = password_override or os.environ.get("EMAIL_PASSWORD")

    if not sender:
        print("EMAIL_ADDRESS environment variable not set and no sender_override provided. Aborting send.")
        return False
    if not password:
        print("EMAIL_PASSWORD environment variable not set and no password_override provided. Aborting send.")
        return False

    # Validate sender email too
    try:
        validated_sender = validate_email(sender).email
    except EmailNotValidError as e:
        print("Invalid sender email:", e)
        return False

    subject = "Registration successful"
    body = "User registered successfully. Now you can login to access the features."

    msg = MIMEMultipart()
    msg["From"] = validated_sender
    msg["To"] = validated_recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        # Using Gmail SMTP with STARTTLS (port 587)
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(validated_sender, password)
            server.send_message(msg)
        print("Email sent successfully to", validated_recipient)
        return True
    except smtplib.SMTPAuthenticationError as e:
        print("SMTP authentication failed:", e)
    except smtplib.SMTPException as e:
        print("SMTP error occurred:", e)
    except Exception as e:
        print("Failed to send email:", e)
    return False

def play_audio(filename):
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(filename)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    except Exception as e:
        print(f"Error playing audio: {e}")

def allowed_file(filename, allowed_extensions={'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt'}):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def extract_text_from_image(image_path):
    try:
        return pytesseract.image_to_string(Image.open(image_path))
    except Exception as e:
        return f"Error extracting text from image: {str(e)}"

# Simple translation function using Gemini AI instead of googletrans
def translate_text(text, dest_lang='en'):
    try:
        # Use Gemini AI for translation
        prompt = f"Translate this text to {dest_lang}: {text}"
        response = gemini_model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Translation error: {str(e)}"

def speech_to_text():
    try:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            print("Listening...")
            audio = r.listen(source)
        text = r.recognize_google(audio)
        return text
    except Exception as e:
        return f"Speech recognition error: {str(e)}"

# # Background task for event notifications
# def check_event_notifications():
#     while True:
#         try:
#             conn = get_db_connection()
#             now = datetime.now()
#             current_time = now.strftime("%H:%M")
#             current_date = now.strftime("%Y-%m-%d")
            
#             events = conn.execute('''SELECT e.*, u.email 
#                                    FROM events e 
#                                    JOIN users u ON e.user_id = u.id 
#                                    WHERE e.event_date = ? AND e.event_time BETWEEN ? AND ? AND e.notified = 0''', 
#                                    (current_date, (now - timedelta(minutes=10)).strftime("%H:%M"), current_time)).fetchall()
            
#             for event in events:
#                 # Send notification (in a real app, this would be email/push notification)
#                 print(f"NOTIFICATION: Event '{event['title']}' is happening now or soon for user {event['email']}")
                
#                 # Mark as notified
#                 conn.execute('UPDATE events SET notified = 1 WHERE id = ?', (event['id'],))
#                 conn.commit()
                
#         except Exception as e:
#             print(f"Error in notification system: {e}")
        
#         time.sleep(60)  # Check every minute

# Start notification thread
notification_thread = threading.Thread(target=check_event_notifications, daemon=True)
notification_thread.start()

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember_me = 'remember_me' in request.form
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['dark_mode'] = user['dark_mode']
            
            if remember_me:
                session.permanent = True
                
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html', now=datetime.now())

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        try:
            # Validate email
            email_validator.validate_email(email)
        except email_validator.EmailNotValidError as e:
            flash(str(e), 'error')
            return render_template('register.html')
        
        password_hash = generate_password_hash(password)
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                         (username, email, password_hash))
            conn.commit()
            flash('Registration successful! Please log in.', 'success')
            print('registered')
            notify_user(email,
            sender_override=os.getenv("EMAIL_ADDRESS"))
            password_override=os.getenv("EMAIL_PASSWORD")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or email already exists', 'error')
        finally:
            conn.close()
    
    return render_template('register.html', now=datetime.now())

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    # Get recent activities
    recent_emails = conn.execute('SELECT * FROM emails WHERE user_id = ? ORDER BY sent_at DESC LIMIT 5', 
                                (session['user_id'],)).fetchall()
    recent_tasks = conn.execute('SELECT * FROM tasks WHERE user_id = ? ORDER BY created_at DESC LIMIT 5', 
                               (session['user_id'],)).fetchall()
    recent_code = conn.execute('SELECT * FROM code_executions WHERE user_id = ? ORDER BY executed_at DESC LIMIT 5', 
                              (session['user_id'],)).fetchall()
    
    conn.close()
    
    return render_template('dashboard.html', user=user, recent_emails=recent_emails, 
                          recent_tasks=recent_tasks, recent_code=recent_code, now=datetime.now())

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file and file.filename != '' and allowed_file(file.filename, {'png', 'jpg', 'jpeg', 'gif'}):
                filename = secure_filename(f"{session['user_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                # Delete old profile pic if it's not the default
                if user['profile_pic'] != 'default.png':
                    old_filepath = os.path.join(app.config['UPLOAD_FOLDER'], user['profile_pic'])
                    if os.path.exists(old_filepath):
                        os.remove(old_filepath)
                
                conn.execute('UPDATE users SET profile_pic = ? WHERE id = ?', (filename, session['user_id']))
                conn.commit()
                flash('Profile picture updated successfully!', 'success')
    
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()
    
    return render_template('profile.html', user=user, now=datetime.now())

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        dark_mode = 1 if 'dark_mode' in request.form else 0
        conn.execute('UPDATE users SET dark_mode = ? WHERE id = ?', (dark_mode, session['user_id']))
        conn.commit()
        session['dark_mode'] = dark_mode
        flash('Settings updated successfully!', 'success')
    
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()
    
    return render_template('settings.html', user=user, now=datetime.now())

@app.route('/email', methods=['GET', 'POST'])
def email_compose():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        from_email = request.form['from_email']
        to_email = request.form['to_email']
        subject = request.form['subject']
        
        # Generate email body using Gemini AI if requested
        if 'generate_body' in request.form and subject:
            try:
                prompt = f"Generate a professional email body about: {subject}"
                response = gemini_model.generate_content(prompt)
                body = response.text
                return render_template('email.html', user=user, subject=subject, body=body, 
                                     from_email=from_email, to_email=to_email, now=datetime.now())
            except Exception as e:
                flash(f'Error generating email content: {str(e)}', 'error')
                body = request.form.get('body', '')
        else:
            body = request.form.get('body', '')
        
        # Validate emails
        try:
            email_validator.validate_email(from_email)
            email_validator.validate_email(to_email)
        except email_validator.EmailNotValidError as e:
            flash(str(e), 'error')
            return render_template('email.html', user=user, now=datetime.now())
        
        # Send email using SMTP (simplified example)
        try:
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            # This is a simplified example - you'll need to configure your SMTP server
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                 server.starttls()
                 server.login(from_email, 'tier nspo sthq xuza')
                 server.send_message(msg)
            
            flash('Email sent successfully!', 'success')
            
            # Store email in database with hash
            email_data = {
                'from': from_email,
                'to': to_email,
                'subject': subject,
                'body': body,
                'timestamp': datetime.now().isoformat()
            }
            hash_code = generate_hash(email_data)
            
            conn.execute('INSERT INTO emails (user_id, from_email, to_email, subject, body, hash_code) VALUES (?, ?, ?, ?, ?, ?)',
                         (session['user_id'], from_email, to_email, subject, body, hash_code))
            conn.commit()
            
        except Exception as e:
            flash(f'Error sending email: {str(e)}', 'error')
    
    conn.close()
    return render_template('email.html', user=user, now=datetime.now())
@app.route('/calendar', methods=['GET', 'POST'])
def calendar():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        event_date = request.form['event_date']
        event_time = request.form['event_time']
        
        event_data = {
            'title': title,
            'description': description,
            'date': event_date,
            'time': event_time,
            'timestamp': datetime.now().isoformat()
        }
        hash_code = generate_hash(event_data)
        
        conn.execute('INSERT INTO events (user_id, title, description, event_date, event_time, hash_code) VALUES (?, ?, ?, ?, ?, ?)',
                     (session['user_id'], title, description, event_date, event_time, hash_code))
        conn.commit()
        
        # Send email notification
        try:
            send_event_notification(user['email'], title, description, event_date, event_time)
            flash('Event added successfully! Notification email sent.', 'success')
        except Exception as e:
            flash(f'Event added but failed to send notification: {str(e)}', 'warning')
    
    # Get all events for the user
    events = conn.execute('SELECT * FROM events WHERE user_id = ? ORDER BY event_date, event_time', 
                          (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('calendar.html', user=user, events=events, now=datetime.now())
@app.route('/code', methods=['GET', 'POST'])
def code_executor():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        # Check if it's a code generation request
        if 'generate_code' in request.form:
            prompt = request.form.get('code_prompt', '')
            language = request.form.get('language', 'python')
            
            try:
                full_prompt = f"Generate {language} code for: {prompt}. Provide only the code without explanations."
                response = gemini_model.generate_content(full_prompt)
                generated_code = response.text
                
                # Store in database
                conn.execute('INSERT INTO code_executions (user_id, language, code, output) VALUES (?, ?, ?, ?)',
                             (session['user_id'], language, generated_code, 'Code generated'))
                conn.commit()
                
                # Create downloadable file
                if 'download' in request.form:
                    filename = f"generated_code_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{language}"
                    with open(filename, 'w') as f:
                        f.write(generated_code)
                    return send_file(filename, as_attachment=True)
                
                return render_template('code.html', user=user, generated_code=generated_code, 
                                     language=language, prompt=prompt, now=datetime.now())
            
            except Exception as e:
                flash(f'Error generating code: {str(e)}', 'error')
        
        # Regular code execution
        else:
            code = request.form['code']
            language = request.form['language']
            
            # Use Gemini AI to execute code
            prompt = f"Execute this {language} code and provide the output:\n\n{code}"
            
            try:
                response = gemini_model.generate_content(prompt)
                output = response.text
                
                # Store in database
                conn.execute('INSERT INTO code_executions (user_id, language, code, output) VALUES (?, ?, ?, ?)',
                             (session['user_id'], language, code, output))
                conn.commit()
                
                # Create downloadable file
                if 'download' in request.form:
                    filename = f"code_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    with open(filename, 'w') as f:
                        f.write(output)
                    return send_file(filename, as_attachment=True)
                
                return render_template('code.html', user=user, output=output, code=code, language=language, now=datetime.now())
            
            except Exception as e:
                flash(f'Error executing code: {str(e)}', 'error')
    
    conn.close()
    return render_template('code.html', user=user, now=datetime.now())

@app.route('/documents', methods=['GET', 'POST'])
def document_processor():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file uploaded', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # Save file
            filename = secure_filename(f"{session['user_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
            filepath = os.path.join('static/uploads', filename)
            file.save(filepath)
            
            # Read file content
            content = open(filepath, 'rb').read()
            content_hash = hashlib.sha256(content).hexdigest()
            
            # Extract text using the unified function
            extracted_text = extract_text_from_file(filepath, filename)
            
            # Store in database
            extracted_text_hash = hashlib.sha256(extracted_text.encode()).hexdigest()
            
            conn.execute('INSERT INTO documents (user_id, filename, content_hash, extracted_text_hash) VALUES (?, ?, ?, ?)',
                         (session['user_id'], filename, content_hash, extracted_text_hash))
            conn.commit()
            
            # Text to speech
            if 'read_aloud' in request.form:
                audio_file = text_to_speech(extracted_text[:500])  # Limit text length
                if audio_file:
                    play_audio(audio_file)
                    os.remove(audio_file)
            
            return render_template('documents.html', user=user, extracted_text=extracted_text, filename=filename, now=datetime.now())
        else:
            flash('Invalid file type', 'error')
    
    conn.close()
    return render_template('documents.html', user=user, now=datetime.now())
def check_event_notifications():
    while True:
        try:
            conn = get_db_connection()
            now = datetime.now()
            current_time = now.strftime("%H:%M")
            current_date = now.strftime("%Y-%m-%d")
            
            events = conn.execute('''SELECT e.*, u.email 
                                   FROM events e 
                                   JOIN users u ON e.user_id = u.id 
                                   WHERE e.event_date = ? AND e.event_time BETWEEN ? AND ? AND e.notified = 0''', 
                                   (current_date, (now - timedelta(minutes=10)).strftime("%H:%M"), current_time)).fetchall()
            
            for event in events:
                # Send reminder notification
                send_event_reminder(event['email'], event['title'], event['description'], event['event_date'], event['event_time'])
                
                # Mark as notified
                conn.execute('UPDATE events SET notified = 1 WHERE id = ?', (event['id'],))
                conn.commit()
                
        except Exception as e:
            print(f"Error in notification system: {e}")
        
        time.sleep(60)  # Check every minute
def check_task_reminders():
    """
    Background task to check for upcoming task deadlines and send reminders
    """
    while True:
        try:
            conn = get_db_connection()
            now = datetime.now()
            current_date = now.strftime("%Y-%m-%d")
            
            # Find tasks due today or tomorrow that haven't been completed
            tasks = conn.execute('''SELECT t.*, u.email 
                                  FROM tasks t 
                                  JOIN users u ON t.user_id = u.id 
                                  WHERE t.status != 'completed' 
                                  AND t.due_date IN (?, ?)''', 
                                  (current_date, (now + timedelta(days=1)).strftime("%Y-%m-%d"))).fetchall()
            
            for task in tasks:
                # Check if this task is due today or tomorrow
                due_date = datetime.strptime(task['due_date'], '%Y-%m-%d').date()
                today = now.date()
                
                if due_date == today:
                    # Task due today
                    send_task_reminder(task['email'], task['title'], task['description'], 
                                     task['due_date'], task['due_time'], "today")
                elif due_date == today + timedelta(days=1):
                    # Task due tomorrow
                    send_task_reminder(task['email'], task['title'], task['description'], 
                                     task['due_date'], task['due_time'], "tomorrow")
                
        except Exception as e:
            print(f"Error in task reminder system: {e}")
        
        time.sleep(3600)  # Check every hour

def send_task_reminder(user_email, title, description, due_date, due_time, timeframe):
    """
    Send reminder email for upcoming tasks
    """
    try:
        sender_email = os.getenv("EMAIL_ADDRESS")
        sender_password = os.getenv("EMAIL_PASSWORD")
        
        # Format due time
        due_info = due_date
        if due_time:
            due_info = f"{due_date} at {due_time}"
        
        subject = f"Task Reminder: {title} due {timeframe}"
        body = f"""
        Task Reminder!
        
        You have a task due {timeframe}:
        
        Task: {title}
        Description: {description}
        Due: {due_info}
        
        Don't forget to complete this task!
        
        Best regards,
        Your Task Management App
        """
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = user_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            
        print(f"Task reminder sent to {user_email}")
        return True
        
    except Exception as e:
        print(f"Error sending task reminder: {e}")
        return False
def send_task_notification(user_email, title, description, due_date, due_time, priority):
    """
    Send email notification when a new task is added
    """
    try:
        sender_email = os.getenv("EMAIL_ADDRESS")
        sender_password = os.getenv("EMAIL_PASSWORD")
        
        # Format priority text
        priority_text = {
            '1': 'Low',
            '2': 'Medium', 
            '3': 'High'
        }.get(str(priority), 'Medium')
        
        # Format due date and time
        due_info = "No due date set"
        if due_date:
            if due_time:
                due_info = f"{due_date} at {due_time}"
            else:
                due_info = f"{due_date} (all day)"
        
        subject = f"New Task Added: {title}"
        body = f"""
        Hello!
        
        You have successfully added a new task:
        
        Task: {title}
        Description: {description}
        Due: {due_info}
        Priority: {priority_text}
        
        This task has been added to your task manager.
        
        Best regards,
        Your Task Management App
        """
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = user_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            
        print(f"Task notification sent to {user_email}")
        return True
        
    except Exception as e:
        print(f"Error sending task notification: {e}")
        return False
task_reminder_thread = threading.Thread(target=check_task_reminders, daemon=True)
task_reminder_thread.start()
def send_event_reminder(user_email, title, description, event_date, event_time):
    """
    Send reminder email for upcoming events
    """
    try:
        sender_email = os.getenv("EMAIL_ADDRESS")
        sender_password = os.getenv("EMAIL_PASSWORD")
        
        subject = f"Event Reminder: {title}"
        body = f"""
        Reminder!
        
        You have an event starting soon:
        
        Event: {title}
        Description: {description}
        Time: {event_date} at {event_time}
        
        Don't forget to attend!
        
        Best regards,
        Your Calendar App
        """
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = user_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            
        print(f"Event reminder sent to {user_email}")
        return True
        
    except Exception as e:
        print(f"Error sending event reminder: {e}")
        return False
@app.route('/tasks', methods=['GET', 'POST'])
def task_manager():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        due_date = request.form.get('due_date')
        due_time = request.form.get('due_time')
        priority = request.form.get('priority', 2)
        
        task_data = {
            'title': title,
            'description': description,
            'due_date': due_date,
            'due_time': due_time,
            'priority': priority,
            'timestamp': datetime.now().isoformat()
        }
        hash_code = generate_hash(task_data)
        
        conn.execute('INSERT INTO tasks (user_id, title, description, due_date, due_time, priority, hash_code) VALUES (?, ?, ?, ?, ?, ?, ?)',
                     (session['user_id'], title, description, due_date, due_time, priority, hash_code))
        conn.commit()
        
        # Send email notification
        try:
            send_task_notification(user['email'], title, description, due_date, due_time, priority)
            flash('Task added successfully! Notification email sent.', 'success')
        except Exception as e:
            flash(f'Task added but failed to send notification: {str(e)}', 'warning')
    
    # Get all tasks for the user
    tasks = conn.execute('SELECT * FROM tasks WHERE user_id = ? ORDER BY priority DESC, due_date, due_time', 
                         (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('tasks.html', user=user, tasks=tasks, now=datetime.now())


@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    response = None
    extracted_text = ""
    filename = None
    user_input=""
    if request.method == 'POST':
        if 'file' in request.files and request.files['file'].filename != '':
            file = request.files['file']
            if file and allowed_file(file.filename):
                # Save file
                filename = secure_filename(f"{session['user_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}")
                filepath = os.path.join('static/uploads', filename)
                file.save(filepath)

                try:
                    # Upload file to Gemini
                    sample_file = genai.upload_file(path=filepath)

                    # Tell Gemini to OCR this file
                    text_prompt = "OCR this file and extract all readable text."
                    response_obj = gemini_model1.generate_content([text_prompt, sample_file])

                    extracted_text = response_obj.text

                except Exception as e:
                    extracted_text = f"Error extracting text: {str(e)}"

                return render_template(
                    'chatbot.html',
                    user=user,
                    extracted_text=extracted_text,
                    filename=filename,
                    now=datetime.now()
                )

        # Handle voice input
        elif 'voice_input' in request.form:
            user_input = speech_to_text()
            return render_template('chatbot.html', user=user, user_input=user_input, now=datetime.now())
        
        # Handle text input with translation
        else:
            user_input = request.form.get('message', '')
            target_lang = request.form.get('language', 'en')
            
            # Use Gemini AI for response
            try:
                # If there's extracted text, include it in the prompt
                if 'extracted_text' in request.form and request.form['extracted_text']:
                    extracted_text = request.form['extracted_text']
                    prompt = f"Based on this text: {extracted_text}\n\nAnswer this question: {user_input}"
                else:
                    prompt = user_input
                
                chat = gemini_model.start_chat(history=[])
                gemini_response = chat.send_message(prompt)
                response = gemini_response.text
                
            except Exception as e:
                response = f"Error: {str(e)}"
    
    conn.close()
    return render_template('chatbot.html', user=user, response=response, extracted_text=extracted_text, user_input=user_input, now=datetime.now())

@app.route('/code_history')
def code_history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    code_executions = conn.execute('SELECT * FROM code_executions WHERE user_id = ? ORDER BY executed_at DESC', 
                                  (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('code_history.html', user=user, code_executions=code_executions, now=datetime.now())

@app.route('/toggle_theme', methods=['POST'])
def toggle_theme():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'})
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    dark_mode = 1 - user['dark_mode']  # Toggle between 0 and 1
    conn.execute('UPDATE users SET dark_mode = ? WHERE id = ?', (dark_mode, session['user_id']))
    conn.commit()
    conn.close()
    
    session['dark_mode'] = dark_mode
    return jsonify({'dark_mode': dark_mode})

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
