# Add these new imports for document processing
import PyPDF2
import docx
from io import StringIO


def allowed_file(filename, allowed_extensions={'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt'}):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def extract_text_from_image(image_path):
    try:
        return pytesseract.image_to_string(Image.open(image_path))
    except Exception as e:
        return f"Error extracting text from image: {str(e)}"

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
