from flask import current_app
import os
from weasyprint import HTML
from io import BytesIO
import openai

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
def allowed_excel_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx', 'xls'}
def generate_pdf(html_string):
    """تحويل HTML إلى PDF وإرجاع BytesIO"""
    pdf_buffer = BytesIO()
    HTML(string=html_string).write_pdf(pdf_buffer)
    pdf_buffer.seek(0)
    return pdf_buffer

def get_openai_response(message):
    """استدعاء OpenAI API للحصول على رد المساعد الذكي"""
    openai.api_key = current_app.config['OPENAI_API_KEY']
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "أنت مساعد ذكي لتطبيق إدارة الصيانة الكهربائية. ساعد المستخدم في استفساراته حول البيانات والإجراءات."},
                {"role": "user", "content": message}
            ],
            max_tokens=500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"حدث خطأ: {str(e)}"

