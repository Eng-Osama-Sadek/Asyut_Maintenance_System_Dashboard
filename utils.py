from flask import current_app
import os
from io import BytesIO
import json
import requests
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_excel_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx', 'xls'}

def ar_text(text):
    """تحويل النص العربي للعرض الصحيح"""
    if not text:
        return ''
    text_str = str(text).strip()
    if not text_str:
        return ''
    reshaped_text = arabic_reshaper.reshape(text_str)
    return get_display(reshaped_text)

def ar_cell_lines(text, width_cm=6.0, font_name='ArabicFont', font_size=9, style=None):
    """
    تقطيع النص العربي يدوياً لتحضيره للجدول مع حماية التشكيل العربي
    """
    if not text:
        return ''
    
    text_str = str(text).strip()
    if not text_str:
        return ''
        
    max_width_pt = (width_cm - 0.3) * 28.3465
    words = text_str.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        try:
            w = pdfmetrics.stringWidth(arabic_reshaper.reshape(test_line), font_name, font_size)
        except Exception:
            w = len(test_line) * font_size * 0.55
            
        if w <= max_width_pt or not current_line:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
            
    if current_line:
        lines.append(' '.join(current_line))
        
    elements = []
    for line in lines:
        reshaped_line = get_display(arabic_reshaper.reshape(line))
        elements.append(Paragraph(reshaped_line, style))
        
    return elements

def get_arabic_font():
    """تسجيل الخط العربي وضمان تنزيل خط Amiri يدعم UTF-8 كاملاً لتجنب المربعات السوداء"""
    font_name = 'ArabicFont'
    
    if font_name in pdfmetrics.getRegisteredFontNames():
        return font_name

    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # قائمة بمسارات الخطوط للتأكد من المحاولة
    possible_paths = [
        os.path.join(base_dir, 'Amiri-Regular.ttf'),
        os.path.join(base_dir, 'NotoNaskhArabic.ttf'),
        "C:\\Windows\\Fonts\\arial.ttf"  # للأنظمة التي تعمل على ويندوز
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(font_name, path))
                return font_name
            except Exception:
                continue

    # تنزيل خط Amiri-Regular تلقائياً إن لم يوجد أي خط محلي
    amiri_path = os.path.join(base_dir, 'Amiri-Regular.ttf')
    try:
        url = "https://raw.githubusercontent.com/google/fonts/main/ofl/amiri/Amiri-Regular.ttf"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            with open(amiri_path, 'wb') as f:
                f.write(r.content)
            pdfmetrics.registerFont(TTFont(font_name, amiri_path))
            return font_name
    except Exception:
        pass

    return 'Helvetica'


def generate_pdf(context=None):
    """توليد تقرير PDF"""
    buffer = BytesIO()
    
    arabic_font = get_arabic_font()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Title'],
        fontSize=18,
        fontName=arabic_font,
        textColor=colors.HexColor('#0d1b2a'),
        alignment=TA_CENTER,
        spaceAfter=10
    )
    
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Normal'],
        fontSize=12,
        fontName=arabic_font,
        textColor=colors.HexColor('#0d1b2a'),
        alignment=TA_CENTER,
        spaceAfter=10
    )
    
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontSize=9,
        fontName=arabic_font,
        textColor=colors.black,
        alignment=TA_CENTER,
        leading=11,
        spaceAfter=0,
        spaceBefore=0
    )
    
    if context:
        title_text = ar_text("تقرير أعمال الصيانة الشهرية")
        elements.append(Paragraph(title_text, title_style))
        
        eng_info = ar_text(
            f"هندسة {context.get('eng_name', '')} - قطاع {context.get('sector_name', '')} - شركة {context.get('company_name', '')}"
        )
        elements.append(Paragraph(eng_info, subtitle_style))
        
        period = ar_text(
            f"الفترة من {context.get('year', '')}-{context.get('month', '')}-01 إلى {context.get('year', '')}-{context.get('month', '')}-{context.get('last_day', '')}"
        )
        elements.append(Paragraph(period, subtitle_style))
        
        elements.append(Spacer(1, 10))
        
        if context.get('summary'):
            summary_data = [
                [ar_text('النسبة'), ar_text('المنفذ'), ar_text('المستهدف'), ar_text('المكون')]
            ]
            
            for item in context['summary']:
                summary_data.append([
                    f"{item['percent']}%",
                    str(item['executed']),
                    str(item['target']),
                    ar_cell_lines(item['component'], width_cm=8.0, font_name=arabic_font, font_size=10, style=body_style)
                ])
            
            summary_table = Table(summary_data, colWidths=[2.5*cm, 2.5*cm, 2.5*cm, 8*cm])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d1b2a')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#ffc107')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, -1), arabic_font),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#0d1b2a')),
                ('FONTSIZE', (0, 1), (-1, -1), 10),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ]))
            elements.append(summary_table)
            elements.append(Spacer(1, 15))
        
        if context.get('logs'):
            logs_data = [
                [ar_text('الأفراد'), ar_text('الملاحظات'), ar_text('الكمية'), ar_text('المكون'), ar_text('التاريخ')]
            ]
            
            for log in context['logs']:
                logs_data.append([
                    ar_cell_lines(log.get('personnel', ''), width_cm=2.5, font_name=arabic_font, font_size=9, style=body_style),
                    ar_cell_lines(log.get('notes', ''), width_cm=6.5, font_name=arabic_font, font_size=9, style=body_style),
                    str(log.get('value', '')),
                    ar_cell_lines(log.get('component', ''), width_cm=3.0, font_name=arabic_font, font_size=9, style=body_style),
                    str(log.get('date', ''))
                ])
            
            logs_table = Table(logs_data, colWidths=[2.5*cm, 6.5*cm, 1.5*cm, 3*cm, 2.5*cm])
            logs_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d1b2a')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#ffc107')),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, -1), arabic_font),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#0d1b2a')),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ]))
            elements.append(logs_table)
            elements.append(Spacer(1, 30))
        
        signatures_data = [
            [ar_text('مدير عام الصيانة'), '', ar_text('مدير إدارة الصيانة')],
            ['', '', ''],
            ['________________', '', '________________'],
        ]
        
        sig_table = Table(signatures_data, colWidths=[5*cm, 5*cm, 5*cm])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), arabic_font),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0d1b2a')),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
        ]))
        elements.append(sig_table)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer


def get_openai_response(message, context_data=None):
    """استدعاء Gemini API مع بيانات التطبيق"""
    api_key = current_app.config.get('GEMINI_API_KEY')
    if not api_key or api_key == '':
        return "عذراً، لم يتم إعداد مفتاح Gemini API"
    
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key
        }
        
        context_text = ""
        if context_data:
            context_text = f"""
            أنت متصل بقاعدة بيانات حقيقية لتطبيق إدارة الصيانة. أجب بناءً على هذه البيانات الفعلية:
            
            إجمالي الإحصائيات:
            - عدد الهندسات: {context_data.get('total_engineerings', 0)}
            - عدد المكونات: {context_data.get('total_components', 0)}
            - إجمالي المستهدف: {context_data.get('total_target', 0)}
            - إجمالي المنفذ: {context_data.get('total_executed', 0)}
            - نسبة الإنجاز الكلية: {context_data.get('percent', 0)}%
            
            تفاصيل الهندسات:
            {context_data.get('engineering_details', '')}
            
            تفاصيل المكونات:
            {context_data.get('component_details', '')}
            """
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"""
                            {context_text}
                            
                            سؤال المستخدم: {message}
                            
                            أجب باللغة العربية بناءً على البيانات الفعلية أعلاه.
                            """
                        }
                    ]
                }
            ]
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            candidates = result.get('candidates', [])
            if candidates:
                parts = candidates[0].get('content', {}).get('parts', [])
                if parts:
                    return parts[0].get('text', 'لا يوجد رد')
            return "لم أستطع توليد رد"
        
        elif response.status_code == 400:
            return "خطأ: مفتاح API غير صالح"
        else:
            return f"خطأ: {response.status_code}"
    
    except Exception as e:
        return f"حدث خطأ: {str(e)}"