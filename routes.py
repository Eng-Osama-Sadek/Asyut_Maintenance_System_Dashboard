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
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))
        flash('بيانات الدخول غير صحيحة', 'error')
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
    years = [2026, 2027]
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
    data = []
    engineerings = Engineering.query.all()
    
    for eng in engineerings:
        total_target = db.session.query(db.func.sum(MonthlyTarget.target_value)).filter_by(
            engineering_id=eng.id,
            year=year,
            month=month
        ).scalar() or 0
        
        total_executed = db.session.query(db.func.sum(MaintenanceLog.executed_value)).filter(
            MaintenanceLog.engineering_id == eng.id,
            db.extract('year', MaintenanceLog.date) == year,
            db.extract('month', MaintenanceLog.date) == month
        ).scalar() or 0
        
        percent = (total_executed / total_target * 100) if total_target > 0 else 0
        
        data.append({
            'engineering_id': eng.id,
            'engineering': eng.name,
            'target': round(total_target, 2),
            'executed': round(total_executed, 2),
            'percent': round(percent, 2)
        })
    
    return jsonify(data)

# ================== API تفاصيل المكونات ==================
@main_bp.route('/api/dashboard_details/<int:year>/<int:month>')
@login_required
def dashboard_details(year, month):
    data = []
    engineerings = Engineering.query.all()
    components = ComponentType.query.all()
    
    for comp in components:
        comp_data = {
            'component_id': comp.id,
            'component_name': comp.name,
            'engineerings': []
        }
        
        for eng in engineerings:
            target = db.session.query(db.func.sum(MonthlyTarget.target_value)).filter_by(
                engineering_id=eng.id,
                component_type_id=comp.id,
                year=year,
                month=month
            ).scalar() or 0
            
            executed = db.session.query(db.func.sum(MaintenanceLog.executed_value)).filter(
                MaintenanceLog.engineering_id == eng.id,
                MaintenanceLog.component_type_id == comp.id,
                db.extract('year', MaintenanceLog.date) == year,
                db.extract('month', MaintenanceLog.date) == month
            ).scalar() or 0
            
            percent = (executed / target * 100) if target > 0 else 0
            
            comp_data['engineerings'].append({
                'engineering_id': eng.id,
                'engineering_name': eng.name,
                'target': round(target, 2),
                'executed': round(executed, 2),
                'percent': round(percent, 2)
            })
        
        data.append(comp_data)
    
    return jsonify(data)

# ================== إضافة سجل صيانة ==================
@main_bp.route('/api/log', methods=['POST'])
@login_required
def add_log():
    try:
        data = request.form
        engineering_id = int(data['engineering_id'])
        component_type_id = int(data['component_type_id'])
        
        date_str = data.get('date')
        if date_str:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            date_obj = date.today()
        
        executed_value = float(data['executed_value'])
        notes = data.get('notes', '')
        personnel_ids = data.get('personnel_ids', '')
        
        files = request.files.getlist('files')
        media_paths = []
        
        if files:
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    unique_filename = f"{timestamp}_{filename}"
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(file_path)
                    media_paths.append(file_path)
        
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
    try:
        data = request.form
        engineering_id = int(data['engineering_id'])
        component_type_id = int(data['component_type_id'])
        year = int(data['year'])
        month = int(data['month'])
        target_value = float(data['target_value'])
        
        existing = MonthlyTarget.query.filter_by(
            engineering_id=engineering_id,
            component_type_id=component_type_id,
            year=year,
            month=month
        ).first()
        
        if existing:
            existing.target_value = target_value
            message = 'تم تحديث المستهدف بنجاح'
        else:
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

# ================== تقرير PDF ==================
@main_bp.route('/report/<int:engineering_id>/<int:year>/<int:month>')
@login_required
def report(engineering_id, year, month):
    eng = Engineering.query.get_or_404(engineering_id)
    
    targets = MonthlyTarget.query.filter_by(
        engineering_id=engineering_id,
        year=year,
        month=month
    ).all()
    
    logs = MaintenanceLog.query.filter(
        MaintenanceLog.engineering_id == engineering_id,
        db.extract('year', MaintenanceLog.date) == year,
        db.extract('month', MaintenanceLog.date) == month
    ).all()
    
    summary = []
    for target in targets:
        comp = ComponentType.query.get(target.component_type_id)
        comp_name = comp.name if comp else 'غير معروف'
        
        executed = sum(log.executed_value for log in logs if log.component_type_id == target.component_type_id)
        percent = (executed / target.target_value * 100) if target.target_value > 0 else 0
        summary.append({
            'component': comp_name,
            'target': target.target_value,
            'executed': executed,
            'percent': round(percent, 2)
        })
    
    logs_data = []
    for log in logs:
        personnel_names = log.personnel_ids if log.personnel_ids else ''
        
        comp = ComponentType.query.get(log.component_type_id)
        comp_name = comp.name if comp else 'غير معروف'
        
        logs_data.append({
            'date': log.date.strftime('%Y-%m-%d'),
            'component': comp_name,
            'value': log.executed_value,
            'notes': log.notes or '',
            'personnel': personnel_names
        })
    
    last_day = calendar.monthrange(year, month)[1]
    
    context = {
        'eng_name': eng.name,
        'sector_name': eng.sector.name if eng.sector else '',
        'company_name': eng.sector.company.name if eng.sector and eng.sector.company else '',
        'year': year,
        'month': month,
        'last_day': last_day,
        'summary': summary,
        'logs': logs_data
    }
    
    pdf = generate_pdf(context=context)
    
    return send_file(
        pdf,
        as_attachment=True,
        download_name=f'report_{eng.name}_{year}_{month}.pdf'
    )

# ================== المساعد الذكي ==================
@main_bp.route('/api/assistant', methods=['POST'])
@login_required
def assistant():
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        
        # جلب بيانات حقيقية من قاعدة البيانات
        today = date.today()
        year = today.year
        month = today.month
        
        total_target = db.session.query(db.func.sum(MonthlyTarget.target_value)).filter_by(
            year=year, month=month
        ).scalar() or 0
        
        total_executed = db.session.query(db.func.sum(MaintenanceLog.executed_value)).filter(
            db.extract('year', MaintenanceLog.date) == year,
            db.extract('month', MaintenanceLog.date) == month
        ).scalar() or 0
        
        percent = (total_executed / total_target * 100) if total_target > 0 else 0
        
        engineerings = Engineering.query.all()
        components = ComponentType.query.all()
        
        details_lines = []
        for eng in engineerings:
            eng_target = db.session.query(db.func.sum(MonthlyTarget.target_value)).filter_by(
                engineering_id=eng.id, year=year, month=month
            ).scalar() or 0
            
            eng_executed = db.session.query(db.func.sum(MaintenanceLog.executed_value)).filter(
                MaintenanceLog.engineering_id == eng.id,
                db.extract('year', MaintenanceLog.date) == year,
                db.extract('month', MaintenanceLog.date) == month
            ).scalar() or 0
            
            eng_percent = (eng_executed / eng_target * 100) if eng_target > 0 else 0
            details_lines.append(f"{eng.name}: المستهدف {eng_target}, المنفذ {eng_executed}, النسبة {round(eng_percent, 2)}%")
        
        component_lines = []
        for comp in components:
            comp_target = db.session.query(db.func.sum(MonthlyTarget.target_value)).filter_by(
                component_type_id=comp.id, year=year, month=month
            ).scalar() or 0
            
            comp_executed = db.session.query(db.func.sum(MaintenanceLog.executed_value)).filter(
                MaintenanceLog.component_type_id == comp.id,
                db.extract('year', MaintenanceLog.date) == year,
                db.extract('month', MaintenanceLog.date) == month
            ).scalar() or 0
            
            comp_percent = (comp_executed / comp_target * 100) if comp_target > 0 else 0
            component_lines.append(f"{comp.name}: المستهدف {comp_target}, المنفذ {comp_executed}, النسبة {round(comp_percent, 2)}%")
        
        context_data = {
            'total_engineerings': len(engineerings),
            'total_components': len(components),
            'total_target': round(total_target, 2),
            'total_executed': round(total_executed, 2),
            'percent': round(percent, 2),
            'engineering_details': '\n'.join(details_lines),
            'component_details': '\n'.join(component_lines)
        }
        
        response = get_openai_response(user_message, context_data)
        return jsonify({'response': response})
    
    except Exception as e:
        return jsonify({'response': f'حدث خطأ: {str(e)}'}), 500
# ================== استيراد Excel ==================
@main_bp.route('/import_excel', methods=['POST'])
@login_required
def import_excel():
    if 'file' not in request.files:
        flash('لا يوجد ملف مرفوع', 'error')
        return redirect(url_for('main.dashboard'))
    
    file = request.files['file']
    if file.filename == '':
        flash('لم يتم اختيار ملف', 'error')
        return redirect(url_for('main.dashboard'))
    
    if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        flash('يجب أن يكون الملف بصيغة Excel', 'error')
        return redirect(url_for('main.dashboard'))
    
    filename = secure_filename(file.filename)
    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    try:
        df = pd.read_excel(filepath, sheet_name=0, header=None)
        
        sector = Sector.query.first()
        if not sector:
            sector = Sector(name='قطاع أسيوط جنوب', company_id=1)
            db.session.add(sector)
            db.session.commit()
        
        engineering_map = {}
        current_eng = None
        
        for col in range(2, len(df.columns)):
            val = df.iloc[6, col]
            if pd.notna(val):
                val_str = str(val).strip()
                if val_str and 'الاجمالى' not in val_str and val_str != 'nan':
                    current_eng = val_str
                elif 'الاجمالى' in val_str and current_eng:
                    current_eng = None
            if current_eng:
                engineering_map[col] = current_eng
        
        eng_objects = {}
        for eng_name in set(engineering_map.values()):
            existing = Engineering.query.filter_by(name=eng_name).first()
            if not existing:
                eng = Engineering(name=eng_name, sector_id=sector.id)
                db.session.add(eng)
                db.session.flush()
                eng_objects[eng_name] = eng
            else:
                eng_objects[eng_name] = existing
        db.session.commit()
        
        month_map = {}
        
        for col in range(2, len(df.columns)):
            val = df.iloc[7, col]
            if pd.notna(val):
                try:
                    if isinstance(val, datetime):
                        year = val.year
                        month = val.month
                    elif isinstance(val, pd.Timestamp):
                        year = val.year
                        month = val.month
                    else:
                        continue
                    
                    month_map[col] = (year, month)
                except:
                    pass
        
        targets_imported = 0
        
        for row_idx in range(8, len(df)):
            val_col1 = df.iloc[row_idx, 1] if df.shape[1] > 1 else None
            
            if pd.notna(val_col1) and str(val_col1).strip() == 'مستهدف':
                comp_name = str(df.iloc[row_idx, 0]).strip() if pd.notna(df.iloc[row_idx, 0]) else ''
                
                if not comp_name or comp_name == 'nan':
                    continue
                
                comp = ComponentType.query.filter_by(name=comp_name).first()
                if not comp:
                    comp = ComponentType(name=comp_name, unit='عدد')
                    db.session.add(comp)
                    db.session.flush()
                
                for col, eng_name in engineering_map.items():
                    eng = eng_objects.get(eng_name)
                    if not eng:
                        continue
                    
                    if col in month_map:
                        year, month = month_map[col]
                        val = df.iloc[row_idx, col]
                        
                        if pd.notna(val):
                            try:
                                target_value = float(val)
                                
                                existing = MonthlyTarget.query.filter_by(
                                    engineering_id=eng.id,
                                    component_type_id=comp.id,
                                    year=year,
                                    month=month
                                ).first()
                                
                                if existing:
                                    existing.target_value = target_value
                                else:
                                    new_target = MonthlyTarget(
                                        engineering_id=eng.id,
                                        component_type_id=comp.id,
                                        year=year,
                                        month=month,
                                        target_value=target_value
                                    )
                                    db.session.add(new_target)
                                targets_imported += 1
                            except:
                                pass
        
        db.session.commit()
        flash(f'✅ تم استيراد {targets_imported} مستهدف بنجاح!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ خطأ في قراءة الملف: {str(e)}', 'error')
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)
    
    return redirect(url_for('main.dashboard'))