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
    return get_display(arabic_reshaper.reshape(text))

def generate_pdf(context=None):
    """توليد تقرير PDF"""
    buffer = BytesIO()
    
    font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'NotoNaskhArabic.ttf')
    
    if os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont('ArabicFont', font_path))
            arabic_font = 'ArabicFont'
        except:
            arabic_font = 'Helvetica'
    else:
        arabic_font = 'Helvetica'
    
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
        leading=12
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
                    Paragraph(ar_text(item['component']), body_style)
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
                    Paragraph(ar_text(log.get('personnel', '')), body_style),
                    Paragraph(ar_text(log.get('notes', '')), body_style),
                    str(log.get('value', '')),
                    Paragraph(ar_text(log.get('component', '')), body_style),
                    str(log.get('date', ''))
                ])
            
            logs_table = Table(logs_data, colWidths=[2.5*cm, 6*cm, 1.5*cm, 3.5*cm, 2.5*cm])
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


def get_openai_response(message):
    """استدعاء Gemini API باستخدام requests"""
    api_key = current_app.config.get('GEMINI_API_KEY')
    if not api_key or api_key == '':
        return "عذراً، لم يتم إعداد مفتاح Gemini API. يرجى إضافته في ملف .env"
    
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key
        }
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"أنت مساعد ذكي لتطبيق إدارة الصيانة الكهربائية. سؤال المستخدم: {message}"
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
        elif response.status_code == 403:
            return "خطأ: المفتاح غير مصرح له"
        else:
            return f"خطأ: {response.status_code}"
    
    except requests.exceptions.ConnectionError:
        return "خطأ في الاتصال بخوادم Google"
    except Exception as e:
        return f"حدث خطأ: {str(e)}"