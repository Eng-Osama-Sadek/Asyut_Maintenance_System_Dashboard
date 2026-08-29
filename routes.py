from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, send_file, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from models import db, Company, Sector, Engineering, Personnel, ComponentType, MonthlyTarget, MaintenanceLog, User, Media
from datetime import datetime, date, timedelta
import os
import json
import calendar
import pandas as pd
from utils import generate_pdf, allowed_file, get_openai_response

main_bp = Blueprint('main', __name__)

# ================== تسجيل الدخول ==================
@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        flash('بيانات الدخول غير صحيحة')
    return render_template('login.html')

@main_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))

# ================== لوحة التحكم ==================
@main_bp.route('/')
@login_required
def dashboard():
    years = [2026, 2027]  # يمكنك إضافة سنوات أخرى مستقبلاً
    engineerings = Engineering.query.all()
    component_types = ComponentType.query.all()
    personnel = Personnel.query.all()
    today = date.today().isoformat()
    
    return render_template(
        'index.html',
        years=years,
        engineerings=engineerings,
        component_types=component_types,
        personnel=personnel,
        today=today
    )

# ================== API لوحة التحكم ==================
@main_bp.route('/api/dashboard/<int:year>/<int:month>')
@login_required
def dashboard_data(year, month):
    """إرجاع بيانات لوحة التحكم لشهر محدد"""
    data = []
    engineerings = Engineering.query.all()
    
    for eng in engineerings:
        # حساب المستهدف للشهر المحدد
        total_target = db.session.query(db.func.sum(MonthlyTarget.target_value)).filter_by(
            engineering_id=eng.id,
            year=year,
            month=month
        ).scalar() or 0
        
        # حساب المنفذ للشهر المحدد
        total_executed = db.session.query(db.func.sum(MaintenanceLog.executed_value)).filter(
            MaintenanceLog.engineering_id == eng.id,
            db.extract('year', MaintenanceLog.date) == year,
            db.extract('month', MaintenanceLog.date) == month
        ).scalar() or 0
        
        # حساب النسبة المئوية
        percent = (total_executed / total_target * 100) if total_target > 0 else 0
        
        data.append({
            'engineering_id': eng.id,
            'engineering': eng.name,
            'target': round(total_target, 2),
            'executed': round(total_executed, 2),
            'percent': round(percent, 2)
        })
    
    return jsonify(data)

# ================== إضافة سجل صيانة ==================
@main_bp.route('/api/log', methods=['POST'])
@login_required
def add_log():
    """إضافة سجل صيانة جديد"""
    try:
        data = request.form
        engineering_id = int(data['engineering_id'])
        component_type_id = int(data['component_type_id'])
        
        # معالجة التاريخ
        date_str = data.get('date')
        if date_str:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            date_obj = date.today()
        
        executed_value = float(data['executed_value'])
        notes = data.get('notes', '')
        personnel_ids = data.get('personnel_ids', '')
        
        # رفع الملفات (صور وفيديو)
        files = request.files.getlist('files')
        media_paths = []
        
        if files:
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    # إضافة timestamp لتجنب تكرار الأسماء
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    unique_filename = f"{timestamp}_{filename}"
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(file_path)
                    media_paths.append(file_path)
        
        # إنشاء السجل
        log = MaintenanceLog(
            engineering_id=engineering_id,
            component_type_id=component_type_id,
            date=date_obj,
            executed_value=executed_value,
            notes=notes,
            personnel_ids=personnel_ids,
            media_paths=json.dumps(media_paths)
        )
        
        db.session.add(log)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'تم حفظ السجل بنجاح'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'حدث خطأ: {str(e)}'}), 400

# ================== إضافة مستهدف شهري ==================
@main_bp.route('/api/target', methods=['POST'])
@login_required
def add_target():
    """إضافة أو تحديث مستهدف شهري"""
    try:
        data = request.form
        engineering_id = int(data['engineering_id'])
        component_type_id = int(data['component_type_id'])
        year = int(data['year'])
        month = int(data['month'])
        target_value = float(data['target_value'])
        
        # التحقق من عدم التكرار
        existing = MonthlyTarget.query.filter_by(
            engineering_id=engineering_id,
            component_type_id=component_type_id,
            year=year,
            month=month
        ).first()
        
        if existing:
            # تحديث المستهدف الموجود
            existing.target_value = target_value
            message = 'تم تحديث المستهدف بنجاح'
        else:
            # إنشاء مستهدف جديد
            target = MonthlyTarget(
                engineering_id=engineering_id,
                component_type_id=component_type_id,
                year=year,
                month=month,
                target_value=target_value
            )
            db.session.add(target)
            message = 'تم حفظ المستهدف بنجاح'
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': message})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'حدث خطأ: {str(e)}'}), 400

# ================== إضافة هندسة جديدة ==================
@main_bp.route('/api/engineering', methods=['POST'])
@login_required
def add_engineering():
    """إضافة هندسة جديدة"""
    try:
        data = request.json
        name = data.get('name')
        sector_id = data.get('sector_id', 1)  # افتراضياً قطاع أسيوط جنوب
        
        if not name:
            return jsonify({'success': False, 'message': 'اسم الهندسة مطلوب'}), 400
        
        # التحقق من عدم التكرار
        existing = Engineering.query.filter_by(name=name).first()
        if existing:
            return jsonify({'success': False, 'message': 'الهندسة موجودة بالفعل'}), 400
        
        eng = Engineering(name=name, sector_id=sector_id)
        db.session.add(eng)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'تم إضافة الهندسة بنجاح', 'id': eng.id})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'حدث خطأ: {str(e)}'}), 400

# ================== إضافة مكون جديد ==================
@main_bp.route('/api/component', methods=['POST'])
@login_required
def add_component():
    """إضافة مكون شبكة جديد"""
    try:
        data = request.json
        name = data.get('name')
        unit = data.get('unit', 'عدد')
        
        if not name:
            return jsonify({'success': False, 'message': 'اسم المكون مطلوب'}), 400
        
        # التحقق من عدم التكرار
        existing = ComponentType.query.filter_by(name=name).first()
        if existing:
            return jsonify({'success': False, 'message': 'المكون موجود بالفعل'}), 400
        
        comp = ComponentType(name=name, unit=unit)
        db.session.add(comp)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'تم إضافة المكون بنجاح', 'id': comp.id})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'حدث خطأ: {str(e)}'}), 400

# ================== إضافة فرد ==================
@main_bp.route('/api/personnel', methods=['POST'])
@login_required
def add_personnel():
    """إضافة فرد جديد (مهندس، فني، عامل...)"""
    try:
        data = request.json
        name = data.get('name')
        role = data.get('role')
        engineering_id = data.get('engineering_id')
        
        if not name or not role:
            return jsonify({'success': False, 'message': 'الاسم والدور مطلوبان'}), 400
        
        person = Personnel(name=name, role=role, engineering_id=engineering_id)
        db.session.add(person)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'تم إضافة الفرد بنجاح', 'id': person.id})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'حدث خطأ: {str(e)}'}), 400

# ================== تقرير PDF ==================
@main_bp.route('/report/<int:engineering_id>/<int:year>/<int:month>')
@login_required
def report(engineering_id, year, month):
    """توليد تقرير PDF لهندسة محددة في شهر محدد"""
    eng = Engineering.query.get_or_404(engineering_id)
    
    # جلب المستهدفات للشهر المحدد
    targets = MonthlyTarget.query.filter_by(
        engineering_id=engineering_id,
        year=year,
        month=month
    ).all()
    
    # جلب السجلات للشهر المحدد
    logs = MaintenanceLog.query.filter(
        MaintenanceLog.engineering_id == engineering_id,
        db.extract('year', MaintenanceLog.date) == year,
        db.extract('month', MaintenanceLog.date) == month
    ).all()
    
    # حساب ملخص لكل مكون
    summary = []
    for target in targets:
        executed = sum(log.executed_value for log in logs if log.component_type_id == target.component_type_id)
        percent = (executed / target.target_value * 100) if target.target_value > 0 else 0
        summary.append({
            'component': target.component_type.name,
            'target': target.target_value,
            'executed': executed,
            'percent': round(percent, 2)
        })
    
    # اليوم الأخير من الشهر
    last_day = calendar.monthrange(year, month)[1]
    
    # تحويل أسماء الأفراد من IDs إلى أسماء
    for log in logs:
        if log.personnel_ids:
            ids = log.personnel_ids.split(',')
            names = []
            for pid in ids:
                person = Personnel.query.get(int(pid))
                if person:
                    names.append(f"{person.name} ({person.role})")
            log.personnel_names = '، '.join(names)
        else:
            log.personnel_names = ''
    
    # توليد HTML ثم PDF
    html = render_template(
        'report_template.html',
        eng=eng,
        summary=summary,
        logs=logs,
        year=year,
        month=month,
        last_day=last_day
    )
    
    pdf = generate_pdf(html)
    
    return send_file(
        pdf,
        as_attachment=True,
        download_name=f'report_{eng.name}_{year}_{month}.pdf'
    )

# ================== المساعد الذكي ==================
@main_bp.route('/api/assistant', methods=['POST'])
@login_required
def assistant():
    """المساعد الذكي المدعوم بالذكاء الاصطناعي"""
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    
    response = get_openai_response(user_message)
    return jsonify({'response': response})

# ================== استيراد Excel ==================
@main_bp.route('/import_excel', methods=['POST'])
@login_required
def import_excel():
    """استيراد بيانات من ملف Excel"""
    if 'file' not in request.files:
        flash('لا يوجد ملف مرفوع')
        return redirect(url_for('main.dashboard'))
    
    file = request.files['file']
    if file.filename == '':
        flash('لم يتم اختيار ملف')
        return redirect(url_for('main.dashboard'))
    
    if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        flash('يجب أن يكون الملف بصيغة Excel')
        return redirect(url_for('main.dashboard'))
    
    # حفظ الملف مؤقتاً
    filename = secure_filename(file.filename)
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    try:
        # قراءة الملف
        df = pd.read_excel(filepath, sheet_name=0, header=None)
        
        # هنا يمكنك تخصيص منطق الاستخراج حسب بنية ملفك
        # سنقوم بمعالجة بسيطة: نبحث عن أسماء الهندسات في الصف الأول
        # والصفوف التي تحتوي على "مستهدف" في العمود الأول
        
        # استخراج أسماء الهندسات من الصف الأول (من العمود الثاني فصاعداً)
        engineering_names = []
        for col in range(1, len(df.columns)):
            val = df.iloc[0, col]
            if pd.notna(val) and 'الاجمالى' not in str(val):
                eng_name = str(val).strip()
                if eng_name and eng_name not in engineering_names:
                    engineering_names.append(eng_name)
        
        # إنشاء الهندسات إذا لم تكن موجودة
        sector = Sector.query.first()
        if not sector:
            sector = Sector(name='قطاع أسيوط جنوب', company_id=1)
            db.session.add(sector)
            db.session.commit()
        
        for eng_name in engineering_names:
            existing = Engineering.query.filter_by(name=eng_name).first()
            if not existing:
                eng = Engineering(name=eng_name, sector_id=sector.id)
                db.session.add(eng)
        
        db.session.commit()
        
        # هنا يمكنك إضافة منطق استخراج المستهدفات الشهرية
        # هذا يتطلب تخصيصاً دقيقاً حسب بنية الملف
        
        flash(f'تم استيراد {len(engineering_names)} هندسة بنجاح. (تخصيص إضافي مطلوب لاستخراج المستهدفات)')
        
    except Exception as e:
        flash(f'خطأ في قراءة الملف: {str(e)}')
    finally:
        # حذف الملف المؤقت
        if os.path.exists(filepath):
            os.remove(filepath)
    
    return redirect(url_for('main.dashboard'))

# ================== API للحصول على قوائم البيانات ==================
@main_bp.route('/api/engineerings')
@login_required
def get_engineerings():
    """إرجاع قائمة الهندسات"""
    engineerings = Engineering.query.all()
    return jsonify([{'id': eng.id, 'name': eng.name} for eng in engineerings])

@main_bp.route('/api/components')
@login_required
def get_components():
    """إرجاع قائمة المكونات"""
    components = ComponentType.query.all()
    return jsonify([{'id': comp.id, 'name': comp.name, 'unit': comp.unit} for comp in components])

@main_bp.route('/api/personnel')
@login_required
def get_personnel():
    """إرجاع قائمة الأفراد"""
    personnel = Personnel.query.all()
    return jsonify([{'id': p.id, 'name': p.name, 'role': p.role} for p in personnel])