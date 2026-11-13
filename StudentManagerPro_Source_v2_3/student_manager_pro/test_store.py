import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).with_name('student_manager.py')
spec = importlib.util.spec_from_file_location('student_manager', MODULE)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)

class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        app.DB = Path(self.tmp.name) / 'test_students.db'
        self.store = app.Store()

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def student(self, code='T001', name='طالب تجريبي'):
        return {'student_code': code, 'full_name': name, 'grade': 'الصف الأول', 'class_name': '1/1'}

    def test_create_search_and_update(self):
        self.store.save(self.student())
        rows = self.store.all('T001')
        self.assertEqual(len(rows), 1)
        self.store.save(self.student(name='اسم معدل'), rows[0]['id'])
        self.assertEqual(self.store.all()[0]['full_name'], 'اسم معدل')

    def test_duplicate_code_is_rejected(self):
        self.store.save(self.student())
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.save(self.student(name='طالب آخر'))

    def test_attendance_upsert_and_cascade_delete(self):
        self.store.save(self.student())
        sid = self.store.all()[0]['id']
        self.store.db.execute("INSERT INTO attendance(student_id,day,status) VALUES(?,?,?) ON CONFLICT(student_id,day) DO UPDATE SET status=excluded.status", (sid, '2026-11-09', 'حاضر'))
        self.store.db.execute("INSERT INTO attendance(student_id,day,status) VALUES(?,?,?) ON CONFLICT(student_id,day) DO UPDATE SET status=excluded.status", (sid, '2026-11-09', 'غائب'))
        self.store.db.commit()
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM attendance').fetchone()[0], 1)
        self.assertEqual(self.store.db.execute('SELECT status FROM attendance').fetchone()[0], 'غائب')
        self.store.delete(sid)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM attendance').fetchone()[0], 0)


    def test_transfer_records_are_saved_and_cascade_with_student(self):
        self.store.save(self.student())
        sid = self.store.all()[0]['id']
        self.store.db.execute(
            "INSERT INTO transfers(student_id,request_date,from_school,to_school,status,notes) VALUES(?,?,?,?,?,?)",
            (sid, '2026-11-09', 'مدرسة أ', 'مدرسة ب', 'قيد المراجعة', 'طلب تجريبي'),
        )
        self.store.db.commit()
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM transfers').fetchone()[0], 1)
        self.store.delete(sid)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM transfers').fetchone()[0], 0)

    def test_attendance_note_is_persisted(self):
        self.store.save(self.student())
        sid = self.store.all()[0]['id']
        self.store.db.execute(
            "INSERT INTO attendance(student_id,day,status,note) VALUES(?,?,?,?)",
            (sid, '2026-11-09', 'غياب بعذر', 'إفادة ولي الأمر'),
        )
        self.store.db.commit()
        row = self.store.db.execute('SELECT status,note FROM attendance WHERE student_id=?', (sid,)).fetchone()
        self.assertEqual(tuple(row), ('غياب بعذر', 'إفادة ولي الأمر'))

    def test_qr_payload_does_not_embed_personal_details(self):
        source = MODULE.read_text(encoding='utf-8')
        self.assertIn("payload='STUDENT|'+str(r['student_code'] or r['id'])", source)
        self.assertNotIn("payload='STUDENT|'+str(r['student_code'] or r['id'])+'|'+r['full_name']", source)

    def test_sqlite_backup_is_restorable(self):
        self.store.save(self.student())
        backup = Path(self.tmp.name) / 'backup.db'
        target = sqlite3.connect(backup)
        self.store.db.backup(target)
        target.close()
        restored = sqlite3.connect(f'file:{backup.as_posix()}?mode=ro', uri=True)
        self.assertEqual(restored.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
        self.assertEqual(restored.execute('SELECT COUNT(*) FROM students').fetchone()[0], 1)
        restored.close()

    def test_student_change_history_is_recorded(self):
        self.store.save(self.student())
        sid = self.store.all()[0]['id']
        self.store.save(self.student(name='اسم جديد'), sid)
        rows = self.store.db.execute("SELECT field_name,old_value,new_value FROM student_history WHERE student_id=?", (sid,)).fetchall()
        self.assertTrue(any(r['field_name']=='full_name' and r['old_value']=='طالب تجريبي' and r['new_value']=='اسم جديد' for r in rows))

    def test_promotion_history_preserves_previous_grade(self):
        self.store.save(self.student())
        sid = self.store.all()[0]['id']
        with self.store.db:
            self.store.db.execute("INSERT INTO promotions(student_id,academic_year,from_grade,to_grade,from_class,to_class,decision) VALUES(?,?,?,?,?,?,?)", (sid,'2027/2028','الصف الأول','الصف الثاني','1/1','2/1','ترحيل'))
            self.store.db.execute("UPDATE students SET grade='الصف الثاني',class_name='2/1' WHERE id=?", (sid,))
        row = self.store.db.execute('SELECT from_grade,to_grade,academic_year FROM promotions WHERE student_id=?',(sid,)).fetchone()
        self.assertEqual(tuple(row), ('الصف الأول','الصف الثاني','2027/2028'))
        self.assertEqual(self.store.all()[0]['grade'], 'الصف الثاني')


    def test_status_events_are_saved_and_cascade_with_student(self):
        self.store.save(self.student())
        sid = self.store.all()[0]['id']
        with self.store.db:
            self.store.db.execute("INSERT INTO student_status_events(student_id,event_type,event_date,academic_year,reason) VALUES(?,?,?,?,?)", (sid, 'انقطاع', '2026-11-12', '2026/2027', 'سبب تجريبي'))
        row = self.store.db.execute('SELECT event_type,academic_year FROM student_status_events WHERE student_id=?', (sid,)).fetchone()
        self.assertEqual(tuple(row), ('انقطاع', '2026/2027'))
        self.store.delete(sid)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM student_status_events').fetchone()[0], 0)

    def test_latest_status_per_year_is_counted_once(self):
        self.store.save(self.student())
        sid = self.store.all()[0]['id']
        with self.store.db:
            self.store.db.execute("INSERT INTO student_status_events(student_id,event_type,event_date,academic_year) VALUES(?,?,?,?)", (sid, 'انقطاع', '2026-10-01', '2026/2027'))
            self.store.db.execute("INSERT INTO student_status_events(student_id,event_type,event_date,academic_year) VALUES(?,?,?,?)", (sid, 'إعادة قيد', '2026-11-01', '2026/2027'))
            self.store.db.execute("INSERT INTO student_status_events(student_id,event_type,event_date,academic_year) VALUES(?,?,?,?)", (sid, 'ترك المدرسة', '2025-10-01', '2025/2026'))
        rows = self.store.latest_status_rows('2026/2027')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['event_type'], 'إعادة قيد')
        summary = self.store.enrollment_summary('2026/2027')
        self.assertEqual(summary['إجمالي الطلاب'], 1)
        self.assertEqual(summary['مقيد'], 1)
        self.assertEqual(summary['منقطع'], 0)

    def test_enrollment_summary_groups_by_grade_and_class(self):
        self.store.save(self.student('T001', 'طالب أول'))
        self.store.save({'student_code':'T002','full_name':'طالب ثان','grade':'الصف الأول','class_name':'1/2'})
        summary = self.store.enrollment_summary('2026/2027')
        self.assertEqual(summary['إجمالي الطلاب'], 2)
        self.assertEqual(len(summary['حسب الفصل']), 2)
        self.assertEqual(summary['حسب الصف']['الصف الأول']['إجمالي'], 2)

    def test_document_path_rejects_path_traversal(self):
        with self.assertRaises(ValueError):
            self.store.document_path(7, 'documents/8/secret.pdf')
        with self.assertRaises(ValueError):
            self.store.document_path(7, 'documents/7/../../outside.pdf')

    def test_student_documents_metadata_is_saved(self):
        self.store.save(self.student())
        sid = self.store.all()[0]['id']
        with self.store.db:
            self.store.db.execute("INSERT INTO student_documents(student_id,title,category,relative_path,original_name) VALUES(?,?,?,?,?)", (sid, 'شهادة ميلاد', 'مستند طالب', 'documents/1/file.pdf', 'file.pdf'))
        row = self.store.db.execute('SELECT title,relative_path FROM student_documents WHERE student_id=?', (sid,)).fetchone()
        self.assertEqual(tuple(row), ('شهادة ميلاد', 'documents/1/file.pdf'))


    def test_attendance_period_summary_counts_each_status_and_rate(self):
        self.store.save(self.student())
        sid = self.store.all()[0]['id']
        with self.store.db:
            self.store.db.executemany(
                'INSERT INTO attendance(student_id,day,status) VALUES(?,?,?)',
                [(sid, '2026-11-01', 'حاضر'), (sid, '2026-11-02', 'غائب'),
                 (sid, '2026-11-03', 'متأخر'), (sid, '2026-11-04', 'غياب بعذر')],
            )
        rows = self.store.attendance_period_rows('2026-11-01', '2026-11-30')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['أيام مسجلة'], 4)
        self.assertEqual(rows[0]['حاضر'], 1)
        self.assertEqual(rows[0]['غائب'], 1)
        self.assertEqual(rows[0]['متأخر'], 1)
        self.assertEqual(rows[0]['غياب بعذر'], 1)
        self.assertEqual(rows[0]['نسبة الحضور'], 50.0)
        summary = self.store.attendance_period_summary('2026-11-01', '2026-11-30')
        self.assertEqual(summary['أيام مسجلة'], 4)
        self.assertEqual(summary['نسبة الحضور العامة'], 50.0)

    def test_attendance_period_includes_students_without_records_and_filters(self):
        self.store.save(self.student('T001', 'طالب أول'))
        self.store.save({'student_code':'T002','full_name':'طالب ثان','grade':'الصف الثاني','class_name':'2/1'})
        rows = self.store.attendance_period_rows('2026-11-01', '2026-11-30', grade='الصف الأول')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['أيام مسجلة'], 0)
        summary = self.store.attendance_period_summary('2026-11-01', '2026-11-30')
        self.assertEqual(summary['طلاب بلا تسجيل'], 2)
        self.assertIsNone(summary['نسبة الحضور العامة'])

    def test_attendance_period_rejects_invalid_or_reversed_dates(self):
        with self.assertRaises(ValueError):
            self.store.attendance_period_rows('2026-11-31', '2026-12-01')
        with self.assertRaises(ValueError):
            self.store.attendance_period_rows('2026-12-01', '2026-11-01')

    def test_printable_admission_form_contains_student_data(self):
        self.store.save(self.student(name='طالب <تجريبي>'))
        student=self.store.all()[0]
        page=app.build_student_form_html(student,'طلب قبول','مدرسة تجريبية')
        self.assertIn('طلب قبول تلميذ',page)
        self.assertIn('طالب &lt;تجريبي&gt;',page)
        self.assertIn('مدرسة تجريبية',page)

    def test_printable_reenrollment_form_has_reason_field(self):
        self.store.save(self.student())
        page=app.build_student_form_html(self.store.all()[0],'طلب إعادة قيد')
        self.assertIn('سبب الانقطاع',page)
        self.assertIn('تاريخ العودة المطلوب',page)

    def test_printable_transfer_form_has_destination_field(self):
        self.store.save(self.student())
        page=app.build_student_form_html(self.store.all()[0],'طلب تحويل')
        self.assertIn('المدرسة المحول إليها',page)
        self.assertIn('سبب التحويل',page)

    def test_absence_followup_flags_total_and_consecutive_absences(self):
        self.store.save(self.student())
        sid = self.store.all()[0]['id']
        with self.store.db:
            self.store.db.executemany(
                'INSERT INTO attendance(student_id,day,status) VALUES(?,?,?)',
                [(sid, '2026-11-01', 'غائب'), (sid, '2026-11-02', 'غائب'),
                 (sid, '2026-11-03', 'غائب'), (sid, '2026-11-04', 'حاضر'),
                 (sid, '2026-11-05', 'غائب'), (sid, '2026-11-06', 'غياب بعذر')],
            )
        rows = self.store.absence_followup_rows('2026-11-01', '2026-11-30', 4, 3)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['غائب'], 4)
        self.assertEqual(rows[0]['غياب بعذر'], 1)
        self.assertEqual(rows[0]['التتابع الحالي'], 0)
        self.assertEqual(rows[0]['سبب التنبيه'], 'تجاوز حد الغياب الكلي')

    def test_absence_followup_consecutive_streak_resets_on_present(self):
        self.store.save(self.student())
        sid = self.store.all()[0]['id']
        with self.store.db:
            self.store.db.executemany(
                'INSERT INTO attendance(student_id,day,status) VALUES(?,?,?)',
                [(sid, '2026-11-01', 'غائب'), (sid, '2026-11-02', 'غائب'),
                 (sid, '2026-11-03', 'حاضر'), (sid, '2026-11-04', 'غائب'),
                 (sid, '2026-11-05', 'غائب'), (sid, '2026-11-06', 'غائب')],
            )
        rows = self.store.absence_followup_rows('2026-11-01', '2026-11-30', 10, 3)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['التتابع الحالي'], 3)
        self.assertEqual(rows[0]['سبب التنبيه'], 'غياب متتابع')

    def test_absence_followup_filters_grade_and_rejects_bad_thresholds(self):
        self.store.save(self.student())
        sid = self.store.all()[0]['id']
        with self.store.db:
            self.store.db.executemany('INSERT INTO attendance(student_id,day,status) VALUES(?,?,?)',
                [(sid, '2026-11-01', 'غائب'), (sid, '2026-11-02', 'غائب')])
        self.assertEqual(self.store.absence_followup_rows('2026-11-01','2026-11-30',2,3,grade='الصف الثاني'), [])
        with self.assertRaises(ValueError):
            self.store.absence_followup_rows('2026-11-01','2026-11-30',0,3)
        with self.assertRaises(ValueError):
            self.store.absence_followup_rows('2026-11-31','2026-11-30',2,3)


    def test_guardian_contact_is_saved_and_listed_with_student_details(self):
        self.store.save({**self.student(), 'guardian_name':'ولي تجريبي', 'guardian_phone':'01000000000'})
        sid=self.store.all()[0]['id']
        contact_id=self.store.add_guardian_contact(sid,'2026-11-13','هاتف','متابعة الغياب','تم التواصل','تم الاتفاق على الحضور','2026-11-15','الأخصائي')
        rows=self.store.guardian_contact_rows(student_id=sid)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['id'],contact_id)
        self.assertEqual(rows[0]['guardian_phone'],'01000000000')
        self.assertEqual(rows[0]['next_followup'],'2026-11-15')

    def test_guardian_contact_validates_dates_channels_and_required_purpose(self):
        self.store.save(self.student()); sid=self.store.all()[0]['id']
        with self.assertRaises(ValueError): self.store.add_guardian_contact(sid,'2026-02-30','هاتف','متابعة','تم التواصل')
        with self.assertRaises(ValueError): self.store.add_guardian_contact(sid,'2026-11-13','بريد إلكتروني','متابعة','تم التواصل')
        with self.assertRaises(ValueError): self.store.add_guardian_contact(sid,'2026-11-13','هاتف',' ','تم التواصل')
        with self.assertRaises(ValueError): self.store.add_guardian_contact(sid,'2026-11-13','هاتف','متابعة','تم التواصل',next_followup='2026-13-01')

    def test_guardian_contact_status_marks_uncontacted_and_contacted_absence_cases(self):
        self.store.save(self.student()); sid=self.store.all()[0]['id']
        with self.store.db:
            self.store.db.executemany('INSERT INTO attendance(student_id,day,status) VALUES(?,?,?)',[(sid,'2026-11-01','غائب'),(sid,'2026-11-02','غائب'),(sid,'2026-11-03','غائب')])
        rows=self.store.absence_contact_status_rows('2026-11-01','2026-11-30',3,3)
        self.assertEqual(rows[0]['حالة الإخطار'],'لم تتم المتابعة')
        self.store.add_guardian_contact(sid,'2026-11-10','واتساب','متابعة الغياب','لم يتم الرد')
        rows=self.store.absence_contact_status_rows('2026-11-01','2026-11-30',3,3)
        self.assertEqual(rows[0]['حالة الإخطار'],'محاولة غير مكتملة')
        self.store.add_guardian_contact(sid,'2026-11-12','هاتف','متابعة الغياب','تم التواصل')
        rows=self.store.absence_contact_status_rows('2026-11-01','2026-11-30',3,3)
        self.assertEqual(rows[0]['حالة الإخطار'],'تم التواصل')
        self.assertEqual(rows[0]['آخر تواصل'],'2026-11-12')

    def test_guardian_contacts_filter_by_date_and_grade(self):
        self.store.save(self.student()); sid=self.store.all()[0]['id']
        self.store.add_guardian_contact(sid,'2026-11-02','هاتف','متابعة','تم التواصل')
        self.store.add_guardian_contact(sid,'2026-11-12','واتساب','متابعة','لم يتم الرد')
        self.assertEqual(len(self.store.guardian_contact_rows(start_date='2026-11-10',end_date='2026-11-30')),1)
        self.assertEqual(self.store.guardian_contact_rows(grade='الصف الثاني'),[])
        with self.assertRaises(ValueError): self.store.guardian_contact_rows(start_date='2026-11-30',end_date='2026-11-01')

    def test_guardian_contacts_cascade_when_student_is_deleted(self):
        self.store.save(self.student()); sid=self.store.all()[0]['id']
        self.store.add_guardian_contact(sid,'2026-11-13','هاتف','متابعة','تم التواصل')
        self.store.delete(sid)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM guardian_contacts').fetchone()[0],0)


    def test_guardian_contact_table_is_created_when_upgrading_existing_database(self):
        self.store.db.execute('DROP TABLE guardian_contacts')
        self.store.db.commit()
        self.store.close()
        self.store=app.Store()
        row=self.store.db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='guardian_contacts'").fetchone()
        self.assertIsNotNone(row)
        index=self.store.db.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_guardian_contacts_student_date'").fetchone()
        self.assertIsNotNone(index)


    def test_backup_to_creates_verified_database(self):
        self.store.save(self.student())
        backup = Path(self.tmp.name) / 'safe_backup.db'
        self.store.backup_to(backup)
        self.assertTrue(self.store.validate_database(backup))
        restored = sqlite3.connect(backup)
        self.assertEqual(restored.execute('SELECT COUNT(*) FROM students').fetchone()[0], 1)
        restored.close()

    def test_backup_rejects_overwriting_live_database(self):
        with self.assertRaises(ValueError):
            self.store.backup_to(app.DB)

    def test_restore_from_valid_backup_preserves_safety_copy(self):
        self.store.save(self.student('OLD1', 'الطالب الحالي'))
        backup = Path(self.tmp.name) / 'restore_source.db'
        source = sqlite3.connect(backup)
        source.execute('CREATE TABLE students(id INTEGER PRIMARY KEY, student_code TEXT UNIQUE, full_name TEXT NOT NULL, national_id TEXT, gender TEXT, birth_date TEXT, grade TEXT, class_name TEXT, enrollment_date TEXT, nationality TEXT, religion TEXT, address TEXT, guardian_name TEXT, guardian_phone TEXT, guardian_job TEXT, special_needs TEXT, notes TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)')
        source.execute("INSERT INTO students(student_code,full_name,grade,class_name) VALUES('NEW1','الطالب المستعاد','الصف الثاني','2/1')")
        source.commit(); source.close()
        safety = self.store.restore_from(backup)
        self.assertTrue(safety.exists())
        self.assertEqual(self.store.all()[0]['student_code'], 'NEW1')
        self.assertTrue(self.store.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='guardian_contacts'").fetchone())

    def test_restore_rejects_corrupt_file_without_changing_current_data(self):
        self.store.save(self.student('KEEP1', 'لا يحذف'))
        corrupt = Path(self.tmp.name) / 'broken.db'
        corrupt.write_bytes(b'not a sqlite database')
        with self.assertRaises(ValueError):
            self.store.restore_from(corrupt)
        self.assertEqual(self.store.all()[0]['student_code'], 'KEEP1')

if __name__ == '__main__':
    unittest.main(verbosity=2)
