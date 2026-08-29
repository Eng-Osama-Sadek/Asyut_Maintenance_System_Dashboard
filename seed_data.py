from app import create_app
from models import db, Company, Sector, Engineering, ComponentType

def seed():
    app = create_app()
    with app.app_context():
        db.create_all()

        # إنشاء شركة وقطاع إذا لم يوجد
        company = Company.query.first()
        if not company:
            company = Company(name='شركة مصر العليا لتوزيع الكهرباء')
            db.session.add(company)
            db.session.commit()

        sector = Sector.query.first()
        if not sector:
            sector = Sector(name='قطاع أسيوط جنوب', company_id=company.id)
            db.session.add(sector)
            db.session.commit()

        # أسماء الهندسات
        engineering_names = [
            'ابوتيج قرى',
            'ابوتيج مدينة',
            'البداري',
            'الخزان',
            'الغنايم',
            'ساحل سليم',
            'شرق أسيوط',
            'صدفا',
            'غرب أسيوط',
            'مبارك',
            'مركز أسيوط جنوب',
            'مركز أسيوط شمال'
        ]

        for name in engineering_names:
            if not Engineering.query.filter_by(name=name).first():
                eng = Engineering(name=name, sector_id=sector.id)
                db.session.add(eng)
        db.session.commit()

        # أسماء المكونات
        component_names = [
            'الموزعات',
            'شبكة الهوائى جهد متوسط',
            'المحولات (كشك+ غرفة)',
            'المحولات (معلق)',
            'اجمالى عدد المحولات',
            'وحدات الربط',
            'شبكة الهوائى جهد منخفض',
            'صناديق توزيع',
            'RECLOSER',
            'AVR'
        ]

        for name in component_names:
            if not ComponentType.query.filter_by(name=name).first():
                comp = ComponentType(name=name, unit='عدد')
                db.session.add(comp)
        db.session.commit()

        print("تم إنشاء البيانات الأساسية بنجاح.")

if __name__ == '__main__':
    seed()