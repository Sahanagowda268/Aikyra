import os
import google.generativeai as genai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel('models/gemini-1.5-flash-002')
filepath="test.jpg"
sample_file = genai.upload_file(path=filepath)
text = "OCR this image"
response = gemini_model.generate_content([text, sample_file])
print(response.text)
