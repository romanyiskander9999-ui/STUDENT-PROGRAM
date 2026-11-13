# -*- coding: utf-8 -*-
"""مدير شئون الطلاب - إصدار مستقل بدون كلمة مرور | 2026/2027"""
import os, sys, sqlite3, shutil, webbrowser, urllib.parse, uuid
from datetime import datetime, date
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_NAME='مدير شئون الطلاب Pro'
APP_VERSION='2.3'
ACADEMIC_YEAR='2026/2027'
BASE=Path(os.environ.get('LOCALAPPDATA') or Path.home())/'StudentManagerPro'
BASE.mkdir(parents=True, exist_ok=True)
DB=BASE/'students.db'

FIELDS=[('student_code','كود الطالب'),('full_name','اسم الطالب'),('national_id','الرقم القومي'),('gender','النوع'),('birth_date','تاريخ الميلاد'),('grade','الصف الدراسي'),('class_name','الفصل'),('enrollment_date','تاريخ القيد'),('nationality','الجنسية'),('religion','الديانة'),('address','العنوان'),('guardian_name','اسم ولي الأمر'),('guardian_phone','هاتف ولي الأمر'),('guardian_job','وظيفة ولي الأمر'),('special_needs','حالة خاصة'),('notes','ملاحظات')]

class Store:
 def __init__(self):
  self.db=sqlite3.connect(DB); self.db.row_factory=sqlite3.Row; self.db.execute('PRAGMA foreign_keys=ON'); self.init()
 def init(self):
  self.db.execute('''CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY AUTOINCREMENT, student_code TEXT UNIQUE, full_name TEXT NOT NULL, national_id TEXT, gender TEXT, birth_date TEXT, grade TEXT, class_name TEXT, enrollment_date TEXT, nationality TEXT, religion TEXT, address TEXT, guardian_name TEXT, guardian_phone TEXT, guardian_job TEXT, special_needs TEXT, notes TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
  self.db.execute('''CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL, day TEXT NOT NULL, status TEXT NOT NULL, note TEXT, UNIQUE(student_id,day), FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE)''')
  self.db.execute('''CREATE TABLE IF NOT EXISTS school(key TEXT PRIMARY KEY,value TEXT)''')
  self.db.execute('''CREATE TABLE IF NOT EXISTS grades(id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL, subject TEXT NOT NULL, term TEXT DEFAULT 'الفصل الدراسي الأول', assessment TEXT, score REAL DEFAULT 0, max_score REAL DEFAULT 100, exam_date TEXT, notes TEXT, FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE)''')
  self.db.execute('''CREATE TABLE IF NOT EXISTS behavior(id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL, event_date TEXT NOT NULL, category TEXT NOT NULL, points INTEGER DEFAULT 0, details TEXT, action_taken TEXT, FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE)''')
  self.db.execute('''CREATE TABLE IF NOT EXISTS transfers(id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL, request_date TEXT, from_school TEXT, to_school TEXT, status TEXT DEFAULT 'قيد المراجعة', notes TEXT, FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE)''')
  self.db.execute('''CREATE TABLE IF NOT EXISTS student_history(id INTEGER PRIMARY KEY AUTOINCREMENT,student_id INTEGER NOT NULL,changed_at TEXT NOT NULL,field_name TEXT NOT NULL,old_value TEXT,new_value TEXT,change_note TEXT,FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE)''')
  self.db.execute('''CREATE TABLE IF NOT EXISTS promotions(id INTEGER PRIMARY KEY AUTOINCREMENT,student_id INTEGER NOT NULL,academic_year TEXT NOT NULL,from_grade TEXT,to_grade TEXT,from_class TEXT,to_class TEXT,decision TEXT NOT NULL,created_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE)''')
  self.db.execute('''CREATE TABLE IF NOT EXISTS student_status_events(id INTEGER PRIMARY KEY AUTOINCREMENT,student_id INTEGER NOT NULL,event_type TEXT NOT NULL,event_date TEXT NOT NULL,academic_year TEXT,reason TEXT,decision_no TEXT,notes TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE)''')
  self.db.execute('''CREATE TABLE IF NOT EXISTS student_documents(id INTEGER PRIMARY KEY AUTOINCREMENT,student_id INTEGER NOT NULL,title TEXT NOT NULL,category TEXT,relative_path TEXT NOT NULL,original_name TEXT NOT NULL,added_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE)''')
  self.db.execute('''CREATE TABLE IF NOT EXISTS guardian_contacts(id INTEGER PRIMARY KEY AUTOINCREMENT,student_id INTEGER NOT NULL,contact_date TEXT NOT NULL,channel TEXT NOT NULL,purpose TEXT NOT NULL,outcome TEXT NOT NULL,notes TEXT,next_followup TEXT,staff_name TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE)''')
  self.db.execute('CREATE INDEX IF NOT EXISTS idx_guardian_contacts_student_date ON guardian_contacts(student_id,contact_date DESC,id DESC)')
  self.db.commit()
 def all(self, q='', grade='', cls=''):
  sql='SELECT * FROM students WHERE 1=1'; p=[]
  if q: sql+=' AND (full_name LIKE ? OR student_code LIKE ? OR national_id LIKE ? OR guardian_phone LIKE ?)'; p += [f'%{q}%']*4
  if grade: sql+=' AND grade=?'; p.append(grade)
  if cls: sql+=' AND class_name=?'; p.append(cls)
  return self.db.execute(sql+' ORDER BY grade,class_name,full_name',p).fetchall()
 def save(self, data, sid=None):
  cols=[x[0] for x in FIELDS]; vals=[data.get(c,'').strip() for c in cols]; vals[0]=vals[0] or None
  if not data.get('full_name','').strip(): raise ValueError('اسم الطالب مطلوب')
  if sid:
   before=self.db.execute('SELECT * FROM students WHERE id=?',(sid,)).fetchone()
   if before:
    for c,v in zip(cols,vals):
     old=before[c] or ''; new=v or ''
     if str(old)!=str(new):
      self.db.execute('INSERT INTO student_history(student_id,changed_at,field_name,old_value,new_value,change_note) VALUES(?,?,?,?,?,?)',(sid,datetime.now().isoformat(timespec='seconds'),c,str(old),str(new),'تعديل بيانات الطالب'))
   self.db.execute('UPDATE students SET '+','.join(c+'=?' for c in cols)+',updated_at=CURRENT_TIMESTAMP WHERE id=?',vals+[sid])
  else:
   cur=self.db.execute('INSERT INTO students('+','.join(cols)+') VALUES('+','.join('?' for _ in cols)+')',vals)
   sid=cur.lastrowid
   self.db.execute('INSERT INTO student_history(student_id,changed_at,field_name,old_value,new_value,change_note) VALUES(?,?,?,?,?,?)',(sid,datetime.now().isoformat(timespec='seconds'),'ملف الطالب','','تم إنشاء الملف','قيد طالب جديد'))
  self.db.commit()
 def delete(self,sid):
  self.db.execute('DELETE FROM students WHERE id=?',(sid,)); self.db.commit()
  folder=BASE/'documents'/str(sid)
  if folder.exists():
   try: shutil.rmtree(folder)
   except OSError: pass
 def document_path(self,sid,relative_path):
  candidate=(BASE/relative_path).resolve()
  expected=(BASE/'documents'/str(sid)).resolve()
  try: candidate.relative_to(expected)
  except ValueError: raise ValueError('مسار المستند غير آمن أو لا يخص هذا الطالب')
  return candidate
 def latest_status_rows(self, academic_year='', grade='', cls=''):
  sql='''SELECT s.id,s.student_code,s.full_name,s.grade,s.class_name,
   e.event_type,e.event_date,e.academic_year,e.reason,e.decision_no
   FROM students s LEFT JOIN student_status_events e ON e.id=(
    SELECT e2.id FROM student_status_events e2 WHERE e2.student_id=s.id
    AND (?='' OR e2.academic_year=?) ORDER BY e2.event_date DESC,e2.id DESC LIMIT 1)
   WHERE 1=1'''
  args=[academic_year,academic_year]
  if grade: sql+=' AND s.grade=?'; args.append(grade)
  if cls: sql+=' AND s.class_name=?'; args.append(cls)
  return self.db.execute(sql+' ORDER BY s.grade,s.class_name,s.full_name',args).fetchall()
 def enrollment_summary(self, academic_year='', grade='', cls=''):
  rows=self.latest_status_rows(academic_year,grade,cls)
  result={'إجمالي الطلاب':len(rows),'مقيد':0,'منقطع':0,'ترك المدرسة':0,'غير محدد':0,'حسب الصف':{},'حسب الفصل':{}}
  for r in rows:
   event=r['event_type']
   status='مقيد' if event in ('قيد','إعادة قيد') or event is None else event
   if status not in ('مقيد','منقطع','ترك المدرسة'): status='غير محدد'
   result[status]+=1
   grade_name=r['grade'] or 'غير محدد'; cls_name=r['class_name'] or 'غير محدد'
   bucket=result['حسب الصف'].setdefault(grade_name,{'إجمالي':0,'مقيد':0,'منقطع':0,'ترك المدرسة':0})
   bucket['إجمالي']+=1
   if status in bucket: bucket[status]+=1
   class_key=(grade_name,cls_name)
   class_bucket=result['حسب الفصل'].setdefault(class_key,{'إجمالي':0,'مقيد':0,'منقطع':0,'ترك المدرسة':0})
   class_bucket['إجمالي']+=1
   if status in class_bucket: class_bucket[status]+=1
  return result
 def attendance_period_rows(self, start_date, end_date, grade='', cls=''):
  datetime.strptime(start_date, '%Y-%m-%d'); datetime.strptime(end_date, '%Y-%m-%d')
  if start_date > end_date: raise ValueError('تاريخ البداية يجب ألا يتجاوز تاريخ النهاية')
  sql='''SELECT s.id,s.student_code,s.full_name,s.grade,s.class_name,
   SUM(CASE WHEN a.status='حاضر' THEN 1 ELSE 0 END) AS present,
   SUM(CASE WHEN a.status='غائب' THEN 1 ELSE 0 END) AS absent,
   SUM(CASE WHEN a.status='متأخر' THEN 1 ELSE 0 END) AS late,
   SUM(CASE WHEN a.status='إذن' THEN 1 ELSE 0 END) AS permission,
   SUM(CASE WHEN a.status='غياب بعذر' THEN 1 ELSE 0 END) AS excused
   FROM students s LEFT JOIN attendance a ON a.student_id=s.id AND a.day BETWEEN ? AND ? WHERE 1=1'''
  args=[start_date,end_date]
  if grade: sql+=' AND s.grade=?'; args.append(grade)
  if cls: sql+=' AND s.class_name=?'; args.append(cls)
  sql+=' GROUP BY s.id ORDER BY s.grade,s.class_name,s.full_name'
  result=[]
  for r in self.db.execute(sql,args).fetchall():
   counts={'حاضر':r['present'] or 0,'غائب':r['absent'] or 0,'متأخر':r['late'] or 0,'إذن':r['permission'] or 0,'غياب بعذر':r['excused'] or 0}
   recorded=sum(counts.values()); attended=counts['حاضر']+counts['متأخر']
   result.append({'id':r['id'],'student_code':r['student_code'] or '', 'full_name':r['full_name'],'grade':r['grade'] or '', 'class_name':r['class_name'] or '',**counts,'أيام مسجلة':recorded,'نسبة الحضور':round(attended*100/recorded,1) if recorded else None})
  return result
 def attendance_period_summary(self, start_date, end_date, grade='', cls=''):
  rows=self.attendance_period_rows(start_date,end_date,grade,cls)
  totals={'عدد الطلاب':len(rows),'أيام مسجلة':0,'حاضر':0,'غائب':0,'متأخر':0,'إذن':0,'غياب بعذر':0,'طلاب بلا تسجيل':0}
  for r in rows:
   for key in ('أيام مسجلة','حاضر','غائب','متأخر','إذن','غياب بعذر'): totals[key]+=r[key]
   if not r['أيام مسجلة']: totals['طلاب بلا تسجيل']+=1
  totals['نسبة الحضور العامة']=round((totals['حاضر']+totals['متأخر'])*100/totals['أيام مسجلة'],1) if totals['أيام مسجلة'] else None
  return totals
 def absence_followup_rows(self, start_date, end_date, total_threshold=5, streak_threshold=3, grade='', cls=''):
  '''Return follow-up cases. Consecutive means consecutive recorded attendance entries, not calendar days.'''
  datetime.strptime(start_date, '%Y-%m-%d'); datetime.strptime(end_date, '%Y-%m-%d')
  if start_date > end_date: raise ValueError('تاريخ البداية يجب ألا يتجاوز تاريخ النهاية')
  if not isinstance(total_threshold, int) or total_threshold < 1: raise ValueError('حد الغياب الكلي يجب أن يكون رقماً صحيحاً موجباً')
  if not isinstance(streak_threshold, int) or streak_threshold < 1: raise ValueError('حد الغياب المتتابع يجب أن يكون رقماً صحيحاً موجباً')
  sql="""SELECT s.id,s.student_code,s.full_name,s.grade,s.class_name,s.guardian_name,s.guardian_phone,a.day,a.status
   FROM students s JOIN attendance a ON a.student_id=s.id
   WHERE a.day BETWEEN ? AND ? AND a.status IN ('غائب','غياب بعذر','حاضر','متأخر','إذن')"""
  args=[start_date,end_date]
  if grade: sql+=' AND s.grade=?'; args.append(grade)
  if cls: sql+=' AND s.class_name=?'; args.append(cls)
  sql+=' ORDER BY s.grade,s.class_name,s.full_name,a.day DESC'
  grouped={}
  for r in self.db.execute(sql,args).fetchall():
   item=grouped.setdefault(r['id'],{'id':r['id'],'student_code':r['student_code'] or '', 'full_name':r['full_name'],'grade':r['grade'] or '', 'class_name':r['class_name'] or '', 'guardian_name':r['guardian_name'] or '', 'guardian_phone':r['guardian_phone'] or '', 'غائب':0,'غياب بعذر':0,'آخر غياب':'','التتابع الحالي':0,'_streak_open':True})
   if r['status']=='غائب':
    item['غائب']+=1
    if item['_streak_open']:
     item['التتابع الحالي']+=1
     if not item['آخر غياب']: item['آخر غياب']=r['day']
   elif r['status']=='غياب بعذر':
    item['غياب بعذر']+=1; item['_streak_open']=False
   else: item['_streak_open']=False
  result=[]
  for item in grouped.values():
   if item['غائب']>=total_threshold or item['التتابع الحالي']>=streak_threshold:
    item['سبب التنبيه']='غياب متكرر ومتتابع' if item['غائب']>=total_threshold and item['التتابع الحالي']>=streak_threshold else ('تجاوز حد الغياب الكلي' if item['غائب']>=total_threshold else 'غياب متتابع')
    item.pop('_streak_open',None); result.append(item)
  return sorted(result,key=lambda x:(x['grade'],x['class_name'],-x['غائب'],-x['التتابع الحالي'],x['full_name']))
 def add_guardian_contact(self, student_id, contact_date, channel, purpose, outcome, notes='', next_followup='', staff_name=''):
  datetime.strptime(contact_date, '%Y-%m-%d')
  if next_followup: datetime.strptime(next_followup, '%Y-%m-%d')
  if not self.db.execute('SELECT 1 FROM students WHERE id=?',(student_id,)).fetchone(): raise ValueError('الطالب غير موجود')
  if channel not in ('هاتف','واتساب','مقابلة شخصية','خطاب ورقي','رسالة نصية'): raise ValueError('وسيلة التواصل غير صحيحة')
  if outcome not in ('تم التواصل','لم يتم الرد','تعذر التواصل','تم تحديد موعد','حضر ولي الأمر'): raise ValueError('نتيجة التواصل غير صحيحة')
  if not purpose.strip(): raise ValueError('سبب التواصل مطلوب')
  with self.db:
   cur=self.db.execute('INSERT INTO guardian_contacts(student_id,contact_date,channel,purpose,outcome,notes,next_followup,staff_name) VALUES(?,?,?,?,?,?,?,?)',(student_id,contact_date,channel,purpose.strip(),outcome,notes.strip(),next_followup or None,staff_name.strip()))
  return cur.lastrowid
 def guardian_contact_rows(self, student_id=None, start_date='', end_date='', grade='', cls=''):
  sql='''SELECT c.*,s.full_name,s.student_code,s.grade,s.class_name,s.guardian_name,s.guardian_phone FROM guardian_contacts c JOIN students s ON s.id=c.student_id WHERE 1=1'''; args=[]
  if student_id is not None: sql+=' AND c.student_id=?'; args.append(student_id)
  if start_date:
   datetime.strptime(start_date,'%Y-%m-%d'); sql+=' AND c.contact_date>=?'; args.append(start_date)
  if end_date:
   datetime.strptime(end_date,'%Y-%m-%d'); sql+=' AND c.contact_date<=?'; args.append(end_date)
  if start_date and end_date and start_date>end_date: raise ValueError('تاريخ البداية يجب ألا يتجاوز تاريخ النهاية')
  if grade: sql+=' AND s.grade=?'; args.append(grade)
  if cls: sql+=' AND s.class_name=?'; args.append(cls)
  return self.db.execute(sql+' ORDER BY c.contact_date DESC,c.id DESC',args).fetchall()
 def absence_contact_status_rows(self, start_date, end_date, total_threshold=5, streak_threshold=3, grade='', cls=''):
  cases=self.absence_followup_rows(start_date,end_date,total_threshold,streak_threshold,grade,cls); result=[]
  for case in cases:
   contact=self.db.execute('''SELECT contact_date,channel,purpose,outcome,next_followup,staff_name FROM guardian_contacts WHERE student_id=? AND contact_date BETWEEN ? AND ? ORDER BY contact_date DESC,id DESC LIMIT 1''',(case['id'],start_date,end_date)).fetchone()
   result.append({**case,'حالة الإخطار':'تم التواصل' if contact and contact['outcome'] in ('تم التواصل','تم تحديد موعد','حضر ولي الأمر') else ('محاولة غير مكتملة' if contact else 'لم تتم المتابعة'),'آخر تواصل':contact['contact_date'] if contact else '', 'وسيلة التواصل':contact['channel'] if contact else '', 'نتيجة التواصل':contact['outcome'] if contact else '', 'المتابعة التالية':contact['next_followup'] if contact else '', 'المسؤول':contact['staff_name'] if contact else ''})
  return result
 def choices(self,col): return [r[0] for r in self.db.execute(f'SELECT DISTINCT {col} FROM students WHERE {col} IS NOT NULL AND {col}<>"" ORDER BY {col}')]
 def validate_database(self, path):
  source=Path(path).resolve()
  if not source.is_file(): raise ValueError('ملف قاعدة البيانات غير موجود')
  try:
   check=sqlite3.connect('file:'+urllib.parse.quote(str(source))+'?mode=ro',uri=True,timeout=10)
   integrity=check.execute('PRAGMA integrity_check').fetchone()[0]
   tables={r[0] for r in check.execute("SELECT name FROM sqlite_master WHERE type='table'")}
   check.close()
  except sqlite3.DatabaseError as exc:
   raise ValueError('تعذر قراءة قاعدة البيانات أو أنها تالفة') from exc
  if integrity!='ok' or 'students' not in tables:
   raise ValueError('الملف تالف أو ليس قاعدة بيانات برنامج شئون الطلاب')
  return True
 def backup_to(self, path):
  target=Path(path).resolve(); target.parent.mkdir(parents=True,exist_ok=True)
  if target==DB.resolve(): raise ValueError('لا يمكن حفظ النسخة فوق قاعدة البيانات الحالية')
  temp=target.with_name(target.name+'.tmp')
  try:
   self.db.commit()
   out=sqlite3.connect(temp)
   try: self.db.backup(out)
   finally: out.close()
   self.validate_database(temp)
   os.replace(temp,target)
  finally:
   if temp.exists(): temp.unlink()
  return target
 def restore_from(self, path):
  source=Path(path).resolve()
  if source==DB.resolve(): raise ValueError('اختر ملف نسخة احتياطية مختلفاً عن قاعدة البيانات الحالية')
  self.validate_database(source)
  safety=BASE/('قبل_الاستعادة_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.db')
  self.backup_to(safety)
  incoming=sqlite3.connect('file:'+urllib.parse.quote(str(source))+'?mode=ro',uri=True,timeout=10)
  try:
   incoming.backup(self.db)
   self.db.commit()
  finally: incoming.close()
  self.init()
  return safety
 def close(self): self.db.close()

def build_student_form_html(student, form_type, school_name='اسم المدرسة'):
 import html
 titles={'طلب قبول':'طلب قبول تلميذ','طلب إعادة قيد':'طلب إعادة قيد تلميذ','طلب تحويل':'طلب تحويل تلميذ'}
 title=titles.get(form_type, 'نموذج بيانات تلميذ')
 labels=[('اسم التلميذ','full_name'),('الرقم القومي','national_id'),('النوع','gender'),('تاريخ الميلاد','birth_date'),('الصف الدراسي','grade'),('الفصل','class_name'),('تاريخ القيد','enrollment_date'),('الجنسية','nationality'),('العنوان','address'),('اسم ولي الأمر','guardian_name'),('هاتف ولي الأمر','guardian_phone')]
 fields=''.join('<tr><th>'+html.escape(label)+'</th><td>'+html.escape(str(student[key] or ''))+'</td></tr>' for label,key in labels)
 if form_type=='طلب تحويل': fields += '<tr><th>المدرسة المحول إليها</th><td style="height:38px"></td></tr><tr><th>سبب التحويل</th><td style="height:48px"></td></tr>'
 elif form_type=='طلب إعادة قيد': fields += '<tr><th>سبب الانقطاع</th><td style="height:48px"></td></tr><tr><th>تاريخ العودة المطلوب</th><td></td></tr>'
 else: fields += '<tr><th>المستندات المقدمة</th><td style="height:48px"></td></tr>'
 page="<!doctype html><html lang='ar' dir='rtl'><meta charset='utf-8'><title>"+html.escape(title)+"</title><style>body{font-family:Tahoma,Arial;margin:18mm;color:#172b40}h2,p{text-align:center}table{border-collapse:collapse;width:100%;margin-top:24px}th,td{border:1px solid #52677b;padding:10px;text-align:right}th{width:25%;background:#eef3f8}.sign{display:flex;justify-content:space-between;margin-top:65px}.sign div{width:28%;text-align:center;border-top:1px solid #333;padding-top:10px}.toolbar{margin-bottom:20px}@media print{.toolbar{display:none}body{margin:10mm}}</style><button class='toolbar' onclick='window.print()'>طباعة النموذج</button><h2>"+html.escape(str(school_name))+"</h2><h2>"+html.escape(title)+"</h2><p>العام الدراسي 2026 / 2027</p><table>"+fields+"</table><p style='margin-top:24px'>أقر بصحة البيانات الواردة بهذا الطلب، وأتحمل مسئولية ما يثبت خلاف ذلك.</p><div class='sign'><div>ولي الأمر</div><div>شئون الطلاب</div><div>مدير المدرسة</div></div><p style='margin-top:35px'>التاريخ: …… / …… / …………　　رقم الطلب: ……………</p></html>"
 return page

class App(tk.Tk):
 def __init__(self):
  super().__init__(); self.title(APP_NAME+' | '+ACADEMIC_YEAR+' | v'+APP_VERSION); self.geometry('1360x820'); self.minsize(1050,680); self.configure(bg='#f2f5f9')
  self.store=Store(); self.selected=None; self.vars={}; self.style(); self.build(); self.refresh()
  self.protocol('WM_DELETE_WINDOW',self.quit_app)
 def style(self):
  s=ttk.Style(self); s.theme_use('clam'); s.configure('Treeview',font=('Tahoma',10),rowheight=30,background='white',fieldbackground='white'); s.configure('Treeview.Heading',font=('Tahoma',10,'bold'),background='#e8eef6'); s.configure('TButton',font=('Tahoma',10),padding=7); s.configure('TLabel',font=('Tahoma',10)); s.configure('TEntry',padding=6); s.configure('TCombobox',padding=5)
 def build(self):
  top=tk.Frame(self,bg='#12345a',height=82); top.pack(fill='x'); top.pack_propagate(False)
  tk.Label(top,text='مدير شئون الطلاب Pro',font=('Tahoma',21,'bold'),fg='white',bg='#12345a').pack(side='right',padx=24,pady=8)
  tk.Label(top,text='نظام مدرسي مستقل • 2026 / 2027 • الإصدار 2.3 • لا يحتاج إلى كلمة مرور',font=('Tahoma',10),fg='#d6e5f5',bg='#12345a').pack(side='right',pady=18)
  self.tabs=ttk.Notebook(self); self.tabs.pack(fill='both',expand=True,padx=14,pady=12)
  self.home= tk.Frame(self.tabs,bg='#f2f5f9'); self.students_tab=tk.Frame(self.tabs,bg='#f2f5f9'); self.att_tab=tk.Frame(self.tabs,bg='#f2f5f9'); self.grades_tab=tk.Frame(self.tabs,bg='#f2f5f9'); self.behavior_tab=tk.Frame(self.tabs,bg='#f2f5f9'); self.reports_tab=tk.Frame(self.tabs,bg='#f2f5f9'); self.transfers_tab=tk.Frame(self.tabs,bg='#f2f5f9'); self.school_tab=tk.Frame(self.tabs,bg='#f2f5f9')
  self.tabs.add(self.home,text='الرئيسية'); self.tabs.add(self.students_tab,text='قاعدة بيانات الطلاب'); self.tabs.add(self.att_tab,text='الغياب والحضور'); self.tabs.add(self.grades_tab,text='سجل الدرجات'); self.tabs.add(self.behavior_tab,text='السلوك والتقييم'); self.tabs.add(self.reports_tab,text='التقارير والنماذج'); self.tabs.add(self.transfers_tab,text='التحويلات والنقل'); self.tabs.add(self.school_tab,text='بيانات المدرسة والنسخ الاحتياطي')
  self.build_home(); self.build_students(); self.build_attendance(); self.build_grades(); self.build_behavior(); self.build_reports(); self.build_transfers(); self.build_school()
  self.status=tk.StringVar(value='جاهز للعمل — البيانات محفوظة على هذا الجهاز'); tk.Label(self,bg='#e5ebf2',fg='#40536a',textvariable=self.status,anchor='e',font=('Tahoma',9),padx=12,pady=5).pack(fill='x',side='bottom')
 def build_home(self):
  f=self.home; tk.Label(f,text='لوحة متابعة المدرسة',font=('Tahoma',19,'bold'),bg='#f2f5f9',fg='#183b60').pack(anchor='e',padx=22,pady=(22,12))
  cards=tk.Frame(f,bg='#f2f5f9'); cards.pack(fill='x',padx=18)
  self.stats=[]
  for title in ['إجمالي الطلاب','عدد الصفوف','عدد الفصول','طلاب لديهم هاتف ولي أمر']:
   c=tk.Frame(cards,bg='white',highlightbackground='#dce4ee',highlightthickness=1); c.pack(side='right',fill='both',expand=True,padx=6,pady=5)
   tk.Label(c,text=title,bg='white',fg='#60748a',font=('Tahoma',10)).pack(anchor='e',padx=14,pady=(14,3)); v=tk.Label(c,text='0',bg='white',fg='#1263a0',font=('Tahoma',24,'bold')); v.pack(anchor='e',padx=14,pady=(0,12)); self.stats.append(v)
  tk.Label(f,text='إجراءات سريعة',font=('Tahoma',15,'bold'),bg='#f2f5f9',fg='#183b60').pack(anchor='e',padx=22,pady=(25,10))
  actions=tk.Frame(f,bg='#f2f5f9'); actions.pack(anchor='e',padx=20)
  for label,cmd in [('إضافة طالب جديد',self.new_student),('استيراد ملف Excel',self.import_excel),('تصدير بيانات الطلاب',self.export_excel),('نسخة احتياطية الآن',self.backup)]: ttk.Button(actions,text=label,command=cmd).pack(side='right',padx=5)
  note=tk.Frame(f,bg='white',highlightbackground='#dce4ee',highlightthickness=1); note.pack(fill='x',padx=24,pady=30)
  tk.Label(note,text='مبادئ النظام',font=('Tahoma',13,'bold'),bg='white',fg='#183b60').pack(anchor='e',padx=16,pady=(14,5))
  for t in ['لا توجد كلمة مرور أو آلية تفعيل.','قاعدة البيانات محلية على الجهاز ولا تُرسل إلى أي خادم.','يمكن استيراد ملفات Excel وتصدير البيانات وحفظ نسخة احتياطية.','تأكد من الاحتفاظ بنسخة احتياطية دورية على وسيط خارجي.']:
   tk.Label(note,text='• '+t,font=('Tahoma',10),bg='white',fg='#40536a').pack(anchor='e',padx=20,pady=3)
 def build_students(self):
  f=self.students_tab
  bar=tk.Frame(f,bg='#f2f5f9'); bar.pack(fill='x',padx=10,pady=10)
  self.search=tk.StringVar(); self.grade_filter=tk.StringVar(); self.class_filter=tk.StringVar()
  tk.Label(bar,text='بحث:',bg='#f2f5f9').pack(side='right'); e=ttk.Entry(bar,textvariable=self.search,width=27,justify='right'); e.pack(side='right',padx=5); e.bind('<KeyRelease>',lambda e:self.refresh())
  tk.Label(bar,text='الصف:',bg='#f2f5f9').pack(side='right',padx=(12,3)); self.gf=ttk.Combobox(bar,textvariable=self.grade_filter,width=16,state='readonly'); self.gf.pack(side='right'); self.gf.bind('<<ComboboxSelected>>',lambda e:self.refresh())
  tk.Label(bar,text='الفصل:',bg='#f2f5f9').pack(side='right',padx=(12,3)); self.cf=ttk.Combobox(bar,textvariable=self.class_filter,width=12,state='readonly'); self.cf.pack(side='right'); self.cf.bind('<<ComboboxSelected>>',lambda e:self.refresh())
  for t,cmd in [('إضافة',self.new_student),('تعديل',self.edit_student),('حذف',self.delete_student),('استيراد Excel',self.import_excel),('تصدير Excel',self.export_excel),('واتساب ولي الأمر',self.whatsapp),('بطاقة الطالب QR',self.student_card),('الملف الشامل',self.student_profile),('الترحيل الدراسي',self.promote_students),('القيد والانقطاع',self.status_event_dialog),('مستندات الطالب',self.documents_dialog),('تواصل ولي الأمر',self.guardian_contact_dialog),('تقارير الحالة',self.status_report),('نماذج الطباعة',self.student_form_dialog)]: ttk.Button(bar,text=t,command=cmd).pack(side='left',padx=3)
  cols=('id','student_code','full_name','national_id','gender','grade','class_name','guardian_name','guardian_phone')
  self.tree=ttk.Treeview(f,columns=cols,show='headings',selectmode='browse')
  heads={'id':'م','student_code':'كود الطالب','full_name':'اسم الطالب','national_id':'الرقم القومي','gender':'النوع','grade':'الصف','class_name':'الفصل','guardian_name':'ولي الأمر','guardian_phone':'هاتف ولي الأمر'}
  widths={'id':45,'student_code':105,'full_name':240,'national_id':150,'gender':70,'grade':115,'class_name':80,'guardian_name':160,'guardian_phone':125}
  for c in cols: self.tree.heading(c,text=heads[c],anchor='center'); self.tree.column(c,width=widths[c],anchor='center')
  self.tree.pack(fill='both',expand=True,padx=10,pady=(0,10)); self.tree.bind('<Double-1>',lambda e:self.edit_student())
 def guardian_contact_dialog(self):
  sid=self.selected_id()
  if not sid:return
  student=self.store.db.execute('SELECT * FROM students WHERE id=?',(sid,)).fetchone()
  win=tk.Toplevel(self);win.title('سجل التواصل مع ولي الأمر');win.geometry('1120x690');win.transient(self)
  tk.Label(win,text='سجل التواصل مع ولي أمر: '+student['full_name'],font=('Tahoma',15,'bold'),fg='#183b60').pack(anchor='e',padx=16,pady=10)
  info=tk.Frame(win);info.pack(fill='x',padx=16)
  tk.Label(info,text=f"ولي الأمر: {student['guardian_name'] or '—'}    الهاتف: {student['guardian_phone'] or '—'}",font=('Tahoma',10)).pack(anchor='e')
  form=tk.LabelFrame(win,text='إضافة متابعة جديدة',padx=8,pady=8);form.pack(fill='x',padx=12,pady=8)
  day=tk.StringVar(value=date.today().isoformat()); channel=tk.StringVar(value='هاتف'); purpose=tk.StringVar(value='متابعة الغياب'); outcome=tk.StringVar(value='تم التواصل'); notes=tk.StringVar(); next_day=tk.StringVar(); staff=tk.StringVar()
  fields=[('التاريخ YYYY-MM-DD',day,14),('وسيلة التواصل',channel,14),('سبب التواصل',purpose,24),('نتيجة التواصل',outcome,18),('المتابعة التالية YYYY-MM-DD',next_day,17),('اسم المسؤول',staff,18)]
  for i,(label,var,width) in enumerate(fields):
   row=i//3; col=(i%3)*2
   tk.Label(form,text=label).grid(row=row,column=col+1,padx=3,pady=5,sticky='e')
   if var is channel: widget=ttk.Combobox(form,textvariable=var,values=['هاتف','واتساب','مقابلة شخصية','خطاب ورقي','رسالة نصية'],state='readonly',width=width)
   elif var is outcome: widget=ttk.Combobox(form,textvariable=var,values=['تم التواصل','لم يتم الرد','تعذر التواصل','تم تحديد موعد','حضر ولي الأمر'],state='readonly',width=width)
   else: widget=ttk.Entry(form,textvariable=var,width=width,justify='right')
   widget.grid(row=row,column=col,padx=3,pady=5)
  tk.Label(form,text='تفاصيل / ملاحظات').grid(row=2,column=5,padx=3,pady=5,sticky='e');ttk.Entry(form,textvariable=notes,width=45,justify='right').grid(row=2,column=4,padx=3,pady=5)
  cols=('date','channel','purpose','outcome','next','staff','notes');tree=ttk.Treeview(win,columns=cols,show='headings')
  heads={'date':'التاريخ','channel':'الوسيلة','purpose':'سبب التواصل','outcome':'النتيجة','next':'المتابعة التالية','staff':'المسؤول','notes':'ملاحظات'}
  widths={'date':100,'channel':100,'purpose':180,'outcome':120,'next':120,'staff':120,'notes':250}
  for c in cols:tree.heading(c,text=heads[c]);tree.column(c,width=widths[c],anchor='center')
  tree.pack(fill='both',expand=True,padx=12,pady=8)
  def load():
   tree.delete(*tree.get_children())
   for r in self.store.guardian_contact_rows(student_id=sid):tree.insert('','end',iid=str(r['id']),values=(r['contact_date'],r['channel'],r['purpose'],r['outcome'],r['next_followup'] or '—',r['staff_name'] or '—',r['notes'] or ''))
  def save():
   try:self.store.add_guardian_contact(sid,day.get().strip(),channel.get(),purpose.get(),outcome.get(),notes.get(),next_day.get().strip(),staff.get());load();notes.set('');self.status.set('تم حفظ متابعة ولي الأمر بنجاح')
   except Exception as e:messagebox.showerror('تعذر الحفظ',str(e),parent=win)
  def delete():
   selected=tree.selection()
   if not selected:return messagebox.showinfo('تنبيه','اختر سجلاً لحذفه.',parent=win)
   if messagebox.askyesno('تأكيد','هل تريد حذف سجل التواصل المحدد؟',parent=win):
    self.store.db.execute('DELETE FROM guardian_contacts WHERE id=?',(int(selected[0]),));self.store.db.commit();load()
  actions=tk.Frame(win);actions.pack(fill='x',padx=12,pady=8)
  ttk.Button(actions,text='حفظ التواصل',command=save).pack(side='right',padx=4);ttk.Button(actions,text='حذف السجل المحدد',command=delete).pack(side='right',padx=4);ttk.Button(actions,text='تصدير السجل CSV',command=lambda:self.export_guardian_contacts(sid)).pack(side='right',padx=4)
  load()
 def export_guardian_contacts(self, student_id=None):
  rows=self.store.guardian_contact_rows(student_id=student_id)
  if not rows:return messagebox.showinfo('تنبيه','لا توجد سجلات تواصل للتصدير.')
  import csv
  path=filedialog.asksaveasfilename(defaultextension='.csv',filetypes=[('CSV','*.csv')],initialfile='سجل_التواصل_مع_أولياء_الأمور.csv')
  if not path:return
  with open(path,'w',newline='',encoding='utf-8-sig') as f:
   w=csv.writer(f);w.writerow(['كود الطالب','اسم الطالب','الصف','الفصل','ولي الأمر','الهاتف','التاريخ','الوسيلة','سبب التواصل','النتيجة','المتابعة التالية','المسؤول','ملاحظات'])
   for r in rows:w.writerow([r['student_code'],r['full_name'],r['grade'],r['class_name'],r['guardian_name'],r['guardian_phone'],r['contact_date'],r['channel'],r['purpose'],r['outcome'],r['next_followup'],r['staff_name'],r['notes']])
  messagebox.showinfo('تم','تم تصدير سجل التواصل.',parent=self)
 def guardian_followup_report(self):
  win=tk.Toplevel(self);win.title('متابعة إخطار أولياء الأمور');win.geometry('1200x650');win.transient(self)
  today=date.today();start=tk.StringVar(value=today.replace(day=1).isoformat());end=tk.StringVar(value=today.isoformat());total=tk.StringVar(value='5');streak=tk.StringVar(value='3');grade=tk.StringVar();cls=tk.StringVar()
  bar=tk.Frame(win);bar.pack(fill='x',padx=10,pady=8)
  for label,var,width in [('من',start,12),('إلى',end,12),('حد الغياب',total,5),('حد التتابع',streak,5)]:tk.Label(bar,text=label).pack(side='right',padx=3);ttk.Entry(bar,textvariable=var,width=width).pack(side='right',padx=3)
  ttk.Combobox(bar,textvariable=grade,values=['',*self.store.choices('grade')],state='readonly',width=12).pack(side='right',padx=3);ttk.Combobox(bar,textvariable=cls,values=['',*self.store.choices('class_name')],state='readonly',width=10).pack(side='right',padx=3)
  cols=('name','grade','class','absent','reason','guardian','phone','status','last','next');tree=ttk.Treeview(win,columns=cols,show='headings');tree.pack(fill='both',expand=True,padx=10,pady=8)
  heads={'name':'اسم الطالب','grade':'الصف','class':'الفصل','absent':'غياب بدون عذر','reason':'سبب التنبيه','guardian':'ولي الأمر','phone':'الهاتف','status':'حالة الإخطار','last':'آخر تواصل','next':'المتابعة التالية'}
  for c in cols:tree.heading(c,text=heads[c]);tree.column(c,width=110 if c not in ('name','reason','guardian') else 150,anchor='center')
  state={'rows':[]}
  def load():
   try:
    rows=self.store.absence_contact_status_rows(start.get().strip(),end.get().strip(),int(total.get()),int(streak.get()),grade.get(),cls.get());state['rows']=rows;tree.delete(*tree.get_children())
    for r in rows:tree.insert('','end',values=(r['full_name'],r['grade'],r['class_name'],r['غائب'],r['سبب التنبيه'],r['guardian_name'],r['guardian_phone'],r['حالة الإخطار'],r['آخر تواصل'] or '—',r['المتابعة التالية'] or '—'))
    pending=sum(1 for r in rows if r['حالة الإخطار']!='تم التواصل');summary.set(f'إجمالي الحالات: {len(rows)} | لم يكتمل التواصل: {pending} | تم التواصل: {len(rows)-pending}')
   except Exception as e:messagebox.showerror('بيانات غير صحيحة',str(e),parent=win)
  def export():
   if not state['rows']:return messagebox.showinfo('تنبيه','لا توجد بيانات للتصدير.',parent=win)
   import csv
   path=filedialog.asksaveasfilename(parent=win,defaultextension='.csv',filetypes=[('CSV','*.csv')],initialfile='متابعة_إخطار_أولياء_الأمور.csv')
   if not path:return
   with open(path,'w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f);w.writerow(['اسم الطالب','الصف','الفصل','غياب بدون عذر','سبب التنبيه','ولي الأمر','الهاتف','حالة الإخطار','آخر تواصل','وسيلة التواصل','نتيجة التواصل','المتابعة التالية','المسؤول'])
    for r in state['rows']:w.writerow([r['full_name'],r['grade'],r['class_name'],r['غائب'],r['سبب التنبيه'],r['guardian_name'],r['guardian_phone'],r['حالة الإخطار'],r['آخر تواصل'],r['وسيلة التواصل'],r['نتيجة التواصل'],r['المتابعة التالية'],r['المسؤول']])
   messagebox.showinfo('تم','تم تصدير تقرير متابعة الإخطار.',parent=win)
  summary=tk.StringVar(value='');tk.Label(win,textvariable=summary,font=('Tahoma',10,'bold')).pack(anchor='e',padx=14,pady=4)
  ttk.Button(bar,text='عرض التقرير',command=load).pack(side='left',padx=4);ttk.Button(bar,text='تصدير CSV',command=export).pack(side='left',padx=4)
  load()
 def student_profile(self):
  sid=self.selected_id()
  if not sid:return
  student=self.store.db.execute('SELECT * FROM students WHERE id=?',(sid,)).fetchone()
  win=tk.Toplevel(self);win.title('الملف الشامل للطالب');win.geometry('1050x700');win.transient(self)
  tk.Label(win,text='الملف الشامل للطالب: '+student['full_name'],font=('Tahoma',16,'bold'),fg='#183b60').pack(anchor='e',padx=18,pady=12)
  info=tk.Frame(win);info.pack(fill='x',padx=18)
  labels=[('كود الطالب','student_code'),('الرقم القومي','national_id'),('الصف','grade'),('الفصل','class_name'),('ولي الأمر','guardian_name'),('الهاتف','guardian_phone'),('تاريخ الميلاد','birth_date'),('العنوان','address')]
  for i,(label,key) in enumerate(labels):
   tk.Label(info,text=f'{label}: {student[key] or "—"}',font=('Tahoma',10),anchor='e').grid(row=i//4,column=3-(i%4),sticky='e',padx=12,pady=5)
  nb=ttk.Notebook(win);nb.pack(fill='both',expand=True,padx=14,pady=10)
  sections=[('الحضور','SELECT day,status,note FROM attendance WHERE student_id=? ORDER BY day DESC'),('الدرجات','SELECT subject,term,score,max_score,exam_date,notes FROM grades WHERE student_id=? ORDER BY exam_date DESC'),('السلوك','SELECT event_date,category,points,details,action_taken FROM behavior WHERE student_id=? ORDER BY event_date DESC'),('التحويلات','SELECT request_date,from_school,to_school,status,notes FROM transfers WHERE student_id=? ORDER BY request_date DESC'),('تاريخ التعديلات','SELECT changed_at,field_name,old_value,new_value,change_note FROM student_history WHERE student_id=? ORDER BY id DESC'),('الترحيل الدراسي','SELECT academic_year,from_grade,to_grade,from_class,to_class,decision,created_at FROM promotions WHERE student_id=? ORDER BY id DESC'),('حالة القيد والانقطاع','SELECT event_type,event_date,academic_year,reason,decision_no,notes FROM student_status_events WHERE student_id=? ORDER BY event_date DESC'),('المستندات','SELECT title,category,original_name,added_at FROM student_documents WHERE student_id=? ORDER BY id DESC'),('تواصل ولي الأمر','SELECT contact_date,channel,purpose,outcome,next_followup,staff_name,notes FROM guardian_contacts WHERE student_id=? ORDER BY contact_date DESC,id DESC')]
  for title,sql in sections:
   frame=tk.Frame(nb);nb.add(frame,text=title);rows=self.store.db.execute(sql,(sid,)).fetchall()
   tree=ttk.Treeview(frame,columns=tuple(f'c{i}' for i in range(6)),show='headings')
   for i,col in enumerate(tree['columns']):tree.heading(col,text=f'بيان {i+1}');tree.column(col,width=150,anchor='center')
   tree.pack(fill='both',expand=True)
   for row in rows:tree.insert('','end',values=tuple(row))
   if not rows:tk.Label(frame,text='لا توجد سجلات مسجلة حتى الآن',fg='#60748a').pack(pady=20)
 def status_event_dialog(self):
  sid=self.selected_id()
  if not sid:return
  win=tk.Toplevel(self);win.title('سجل القيد وإعادة القيد والانقطاع');win.geometry('540x430');win.transient(self);win.grab_set()
  tk.Label(win,text='تسجيل حركة في الحالة الدراسية',font=('Tahoma',15,'bold')).pack(pady=12)
  fields={}
  for key,label,value,choices in [('event_type','نوع الحركة','قيد',['قيد','إعادة قيد','انقطاع','ترك المدرسة']),('event_date','التاريخ',date.today().isoformat(),None),('academic_year','العام الدراسي','2026/2027',None),('reason','السبب','',None),('decision_no','رقم القرار','',None),('notes','ملاحظات','',None)]:
   row=tk.Frame(win);row.pack(fill='x',padx=16,pady=5);tk.Label(row,text=label,width=18,anchor='e').pack(side='right');v=tk.StringVar(value=value);w=ttk.Combobox(row,textvariable=v,values=choices,state='readonly',width=32) if choices else ttk.Entry(row,textvariable=v,width=35,justify='right');w.pack(side='right',padx=8);fields[key]=v
  def save():
   d={k:v.get().strip() for k,v in fields.items()}
   try: datetime.strptime(d['event_date'],'%Y-%m-%d')
   except ValueError: return messagebox.showerror('تاريخ غير صحيح','اكتب التاريخ بصيغة YYYY-MM-DD')
   if not d['academic_year']:return messagebox.showwarning('بيانات ناقصة','أدخل العام الدراسي')
   with self.store.db:self.store.db.execute('INSERT INTO student_status_events(student_id,event_type,event_date,academic_year,reason,decision_no,notes) VALUES(?,?,?,?,?,?,?)',(sid,d['event_type'],d['event_date'],d['academic_year'],d['reason'],d['decision_no'],d['notes']))
   win.destroy();self.status.set('تم حفظ حركة الحالة الدراسية');messagebox.showinfo('تم','تم تسجيل الحركة في سجل الطالب.')
  ttk.Button(win,text='حفظ الحركة',command=save).pack(pady=14)
 def documents_dialog(self):
  sid=self.selected_id()
  if not sid:return
  root=BASE/'documents'/str(sid);root.mkdir(parents=True,exist_ok=True)
  win=tk.Toplevel(self);win.title('أرشيف مستندات الطالب');win.geometry('850x500');win.transient(self)
  tk.Label(win,text='مستندات الطالب — تحفظ محلياً على هذا الجهاز',font=('Tahoma',14,'bold')).pack(pady=10)
  tree=ttk.Treeview(win,columns=('id','title','category','file','date'),show='headings');
  for c,h,w in [('id','م',45),('title','اسم المستند',190),('category','التصنيف',120),('file','اسم الملف',300),('date','تاريخ الإضافة',140)]:tree.heading(c,text=h);tree.column(c,width=w,anchor='center')
  tree.pack(fill='both',expand=True,padx=12,pady=8)
  def refresh_docs():
   tree.delete(*tree.get_children())
   for r in self.store.db.execute('SELECT * FROM student_documents WHERE student_id=? ORDER BY id DESC',(sid,)):tree.insert('','end',iid=str(r['id']),values=(r['id'],r['title'],r['category'],r['original_name'],r['added_at']))
  def add_doc():
   src=filedialog.askopenfilename(title='اختيار مستند الطالب')
   if not src:return
   srcp=Path(src);dest=root/(uuid.uuid4().hex+'_'+srcp.name)
   try:
    shutil.copy2(srcp,dest)
    try:
     with self.store.db:self.store.db.execute('INSERT INTO student_documents(student_id,title,category,relative_path,original_name) VALUES(?,?,?,?,?)',(sid,srcp.stem,'مستند طالب',str(dest.relative_to(BASE)),srcp.name))
    except Exception:
     dest.unlink(missing_ok=True);raise
    refresh_docs()
   except Exception as e:messagebox.showerror('تعذر الإرفاق',str(e))
  def open_doc():
   sel=tree.selection()
   if not sel:return messagebox.showinfo('تنبيه','حدد مستنداً أولاً')
   r=self.store.db.execute('SELECT relative_path FROM student_documents WHERE id=? AND student_id=?',(int(sel[0]),sid)).fetchone()
   if not r:return messagebox.showerror('خطأ','لم يتم العثور على المستند')
   try:path=self.store.document_path(sid,r[0])
   except ValueError as e:return messagebox.showerror('مسار غير آمن',str(e))
   if not path.is_file():return messagebox.showerror('الملف غير موجود','تعذر العثور على الملف المحفوظ')
   try:
    if hasattr(os,'startfile'):os.startfile(str(path))
    else:webbrowser.open(path.as_uri())
   except Exception as e:messagebox.showerror('تعذر الفتح',str(e))
  def delete_doc():
   sel=tree.selection()
   if not sel:return messagebox.showinfo('تنبيه','حدد مستنداً أولاً')
   if not messagebox.askyesno('تأكيد','حذف المستند المحدد نهائياً؟'):return
   r=self.store.db.execute('SELECT relative_path FROM student_documents WHERE id=? AND student_id=?',(int(sel[0]),sid)).fetchone()
   if not r:return messagebox.showerror('خطأ','لم يتم العثور على المستند')
   try:path=self.store.document_path(sid,r[0])
   except ValueError as e:return messagebox.showerror('مسار غير آمن',str(e))
   with self.store.db:self.store.db.execute('DELETE FROM student_documents WHERE id=?',(int(sel[0]),))
   try:path.unlink(missing_ok=True)
   except OSError:pass
   refresh_docs()
  bar=tk.Frame(win);bar.pack(pady=8)
  for label,cmd in [('إرفاق مستند',add_doc),('فتح المحدد',open_doc),('حذف المحدد',delete_doc)]:ttk.Button(bar,text=label,command=cmd).pack(side='right',padx=5)
  refresh_docs()
 def student_form_dialog(self):
  sid=self.selected_id()
  if not sid:return
  student=self.store.db.execute('SELECT * FROM students WHERE id=?',(sid,)).fetchone()
  if not student:return
  win=tk.Toplevel(self);win.title('نماذج شئون الطلاب');win.geometry('430x190');win.transient(self);win.grab_set()
  tk.Label(win,text='اختر النموذج المطلوب للطالب: '+student['full_name'],font=('Tahoma',11,'bold')).pack(pady=18)
  kind=tk.StringVar(value='طلب قبول')
  ttk.Combobox(win,textvariable=kind,values=['طلب قبول','طلب إعادة قيد','طلب تحويل'],state='readonly',width=28).pack(pady=8)
  def create():
   school=self.store.db.execute("SELECT value FROM school WHERE key='school_name'").fetchone();school_name=school[0] if school else 'اسم المدرسة'
   content=build_student_form_html(student,kind.get(),school_name)
   out=BASE/('student_form_'+str(sid)+'.html');out.write_text(content,encoding='utf-8')
   webbrowser.open(out.as_uri());win.destroy()
  ttk.Button(win,text='إنشاء النموذج وفتحه للطباعة',command=create).pack(pady=14)
 def status_report(self):
  win=tk.Toplevel(self);win.title('تقارير حالة القيد');win.geometry('1000x580');win.transient(self)
  tk.Label(win,text='تقرير القيد وإعادة القيد والانقطاع وترك المدرسة',font=('Tahoma',15,'bold')).pack(pady=10)
  bar=tk.Frame(win);bar.pack(fill='x',padx=12);kind=tk.StringVar(value='الكل');ttk.Combobox(bar,textvariable=kind,values=['الكل','قيد','إعادة قيد','انقطاع','ترك المدرسة'],state='readonly',width=18).pack(side='right');
  tree=ttk.Treeview(win,columns=('student','code','type','date','year','reason','decision'),show='headings')
  heads={'student':'اسم الطالب','code':'الكود','type':'الحركة','date':'التاريخ','year':'العام الدراسي','reason':'السبب','decision':'رقم القرار'}
  for c,h in heads.items():tree.heading(c,text=h);tree.column(c,width=135,anchor='center')
  tree.pack(fill='both',expand=True,padx=12,pady=10)
  rows=[]
  def load():
   tree.delete(*tree.get_children());q='SELECT s.full_name,s.student_code,e.event_type,e.event_date,e.academic_year,e.reason,e.decision_no FROM student_status_events e JOIN students s ON s.id=e.student_id';args=[]
   if kind.get()!='الكل':q+=' WHERE e.event_type=?';args.append(kind.get())
   rows[:]=[tuple(r) for r in self.store.db.execute(q+' ORDER BY e.event_date DESC',args)]
   for r in rows:tree.insert('','end',values=r)
  def export():
   from tkinter import filedialog
   import csv
   dest=filedialog.asksaveasfilename(defaultextension='.csv',filetypes=[('CSV','*.csv')],initialfile='تقرير_حالة_القيد.csv')
   if not dest:return
   with open(dest,'w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f);w.writerow(list(heads.values()));w.writerows(rows)
   messagebox.showinfo('تم','تم تصدير التقرير.')
  ttk.Button(bar,text='تحديث',command=load).pack(side='right',padx=5);ttk.Button(bar,text='تصدير CSV',command=export).pack(side='left',padx=5);load()
 def promote_students(self):
  win=tk.Toplevel(self);win.title('الترحيل الدراسي الجماعي');win.geometry('520x390');win.transient(self);win.grab_set()
  tk.Label(win,text='ترحيل الطلاب إلى العام الدراسي التالي',font=('Tahoma',15,'bold'),fg='#183b60').pack(pady=14)
  fields={}
  for key,label,value in [('academic_year','العام الدراسي الجديد','2027/2028'),('from_grade','الصف الحالي',''),('to_grade','الصف الجديد',''),('from_class','الفصل الحالي',''),('to_class','الفصل الجديد (اختياري)','')]:
   line=tk.Frame(win);line.pack(fill='x',padx=18,pady=6);tk.Label(line,text=label,width=22,anchor='e').pack(side='right');v=tk.StringVar(value=value);w=ttk.Combobox(line,textvariable=v,width=27) if key in ('from_grade','to_grade','from_class') else ttk.Entry(line,textvariable=v,width=30);w.pack(side='right',padx=8)
   if key=='from_grade':w['values']=self.store.choices('grade')
   if key=='from_class':w['values']=self.store.choices('class_name')
   fields[key]=v
  scope=tk.StringVar(value='all');line=tk.Frame(win);line.pack(fill='x',padx=18,pady=8);tk.Label(line,text='نطاق الترحيل:',width=22,anchor='e').pack(side='right');ttk.Radiobutton(line,text='كل طلاب الصف',variable=scope,value='all').pack(side='right');ttk.Radiobutton(line,text='الطالب المحدد فقط',variable=scope,value='one').pack(side='right')
  def run():
   d={k:v.get().strip() for k,v in fields.items()}
   if not d['academic_year'] or not d['from_grade'] or not d['to_grade']:
    messagebox.showwarning('بيانات ناقصة','أدخل العام الدراسي والصف الحالي والصف الجديد.');return
   sid=None
   if scope.get()=='one':
    sel=self.tree.selection();sid=int(sel[0]) if sel else None
    if not sid:messagebox.showwarning('اختيار مطلوب','حدد طالباً من جدول الطلاب أولاً.');return
    students=self.store.db.execute('SELECT * FROM students WHERE id=? AND grade=?',(sid,d['from_grade'])).fetchall()
   else:
    sql='SELECT * FROM students WHERE grade=?';args=[d['from_grade']]
    if d['from_class']:sql+=' AND class_name=?';args.append(d['from_class'])
    students=self.store.db.execute(sql,args).fetchall()
   if not students:messagebox.showinfo('لا توجد نتائج','لا يوجد طلاب مطابقون لشروط الترحيل.');return
   if not messagebox.askyesno('تأكيد الترحيل',f'سيتم ترحيل {len(students)} طالب إلى {d["to_grade"]} للعام {d["academic_year"]}.\nسيتم حفظ سجل تاريخي قبل التغيير. هل تريد المتابعة؟'):return
   with self.store.db:
    for st in students:
     self.store.db.execute('INSERT INTO promotions(student_id,academic_year,from_grade,to_grade,from_class,to_class,decision) VALUES(?,?,?,?,?,?,?)',(st['id'],d['academic_year'],st['grade'],d['to_grade'],st['class_name'],d['to_class'] or st['class_name'],'ترحيل'))
     self.store.db.execute('INSERT INTO student_history(student_id,changed_at,field_name,old_value,new_value,change_note) VALUES(?,?,?,?,?,?)',(st['id'],datetime.now().isoformat(timespec='seconds'),'الصف الدراسي',st['grade'],d['to_grade'],'ترحيل للعام '+d['academic_year']))
     if d['to_class']:
      self.store.db.execute('INSERT INTO student_history(student_id,changed_at,field_name,old_value,new_value,change_note) VALUES(?,?,?,?,?,?)',(st['id'],datetime.now().isoformat(timespec='seconds'),'الفصل',st['class_name'],d['to_class'],'توزيع الفصول للعام '+d['academic_year']))
     self.store.db.execute('UPDATE students SET grade=?,class_name=?,updated_at=CURRENT_TIMESTAMP WHERE id=?',(d['to_grade'],d['to_class'] or st['class_name'],st['id']))
   win.destroy();self.refresh();messagebox.showinfo('اكتمل الترحيل',f'تم ترحيل {len(students)} طالب مع حفظ سجل الترحيل والتعديلات.')
  ttk.Button(win,text='تنفيذ الترحيل مع حفظ السجل',command=run).pack(pady=14)
 def build_attendance(self):
  f=self.att_tab
  bar=tk.Frame(f,bg='#f2f5f9'); bar.pack(fill='x',padx=12,pady=10)
  tk.Label(bar,text='التاريخ:',bg='#f2f5f9').pack(side='right'); self.att_date=tk.StringVar(value=date.today().isoformat()); ttk.Entry(bar,textvariable=self.att_date,width=13,justify='center').pack(side='right',padx=5)
  tk.Label(bar,text='الصف:',bg='#f2f5f9').pack(side='right',padx=(10,2)); self.att_grade=tk.StringVar(); self.att_grade_box=ttk.Combobox(bar,textvariable=self.att_grade,width=14,state='readonly'); self.att_grade_box.pack(side='right'); self.att_grade_box.bind('<<ComboboxSelected>>',lambda e:self.refresh_attendance())
  tk.Label(bar,text='الفصل:',bg='#f2f5f9').pack(side='right',padx=(10,2)); self.att_class=tk.StringVar(); self.att_class_box=ttk.Combobox(bar,textvariable=self.att_class,width=12,state='readonly'); self.att_class_box.pack(side='right'); self.att_class_box.bind('<<ComboboxSelected>>',lambda e:self.refresh_attendance())
  ttk.Button(bar,text='عرض السجل',command=self.refresh_attendance).pack(side='right',padx=4)
  ttk.Button(bar,text='تسجيل الحالة للمحدد',command=self.mark_attendance).pack(side='left',padx=3)
  ttk.Button(bar,text='تسجيل الكل حاضراً',command=lambda:self.bulk_attendance('حاضر')).pack(side='left',padx=3)
  ttk.Button(bar,text='تسجيل الكل غائباً',command=lambda:self.bulk_attendance('غائب')).pack(side='left',padx=3)
  ttk.Button(bar,text='تصدير كشف CSV',command=self.attendance_csv).pack(side='left',padx=3)
  ttk.Button(bar,text='كشف شهري / سنوي',command=self.attendance_period_dialog).pack(side='left',padx=3)
  ttk.Button(bar,text='تنبيهات الغياب المتكرر',command=self.absence_followup_dialog).pack(side='left',padx=3)
  summary=tk.Frame(f,bg='#f2f5f9'); summary.pack(fill='x',padx=15,pady=(0,8)); self.att_summary=tk.StringVar(value=''); tk.Label(summary,textvariable=self.att_summary,bg='#f2f5f9',fg='#145b91',font=('Tahoma',11,'bold')).pack(anchor='e')
  cols=('id','code','name','grade','class','status','note'); self.att_tree=ttk.Treeview(f,columns=cols,show='headings',selectmode='extended')
  heads={'id':'م','code':'كود الطالب','name':'اسم الطالب','grade':'الصف','class':'الفصل','status':'الحالة','note':'ملاحظات'}
  widths={'id':45,'code':110,'name':250,'grade':120,'class':90,'status':110,'note':250}
  for c in cols:self.att_tree.heading(c,text=heads[c]);self.att_tree.column(c,width=widths[c],anchor='center')
  self.att_tree.pack(fill='both',expand=True,padx=12,pady=8)
  self.att_tree.bind('<Double-1>',lambda e:self.mark_attendance())
  self.att_info=tk.StringVar(value='حدد طالباً أو أكثر ثم اختر الحالة لتسجيلها.'); tk.Label(f,textvariable=self.att_info,bg='#f2f5f9',fg='#52677e').pack(anchor='e',padx=18,pady=5)
  self.att_status=tk.StringVar(value='حاضر'); ttk.Combobox(f,textvariable=self.att_status,values=['حاضر','غائب','متأخر','إذن','غياب بعذر'],state='readonly',width=14).pack(anchor='e',padx=18,pady=(0,5))
  note_line=tk.Frame(f,bg='#f2f5f9'); note_line.pack(fill='x',padx=18,pady=(0,8)); tk.Label(note_line,text='ملاحظة للحالة:',bg='#f2f5f9').pack(side='right'); self.att_note=tk.StringVar(); ttk.Entry(note_line,textvariable=self.att_note,width=70,justify='right').pack(side='right',padx=6)
  self.refresh_attendance()
 def build_transfers(self):
  f=self.transfers_tab; bar=tk.Frame(f,bg='#f2f5f9');bar.pack(fill='x',padx=14,pady=12)
  ttk.Button(bar,text='تسجيل طلب تحويل للطالب المحدد',command=self.add_transfer).pack(side='right',padx=4)
  ttk.Button(bar,text='حذف الطلب المحدد',command=self.delete_transfer).pack(side='right',padx=4)
  ttk.Button(bar,text='تحديث السجل',command=self.refresh_transfers).pack(side='right',padx=4)
  tk.Label(f,text='سجل طلبات التحويل والنقل بين المدارس',font=('Tahoma',16,'bold'),bg='#f2f5f9',fg='#183b60').pack(anchor='e',padx=20,pady=8)
  cols=('id','student','date','from','to','status','notes');self.transfer_tree=ttk.Treeview(f,columns=cols,show='headings')
  heads={'id':'م','student':'اسم الطالب','date':'تاريخ الطلب','from':'من مدرسة','to':'إلى مدرسة','status':'حالة الطلب','notes':'ملاحظات'}
  widths={'id':45,'student':220,'date':110,'from':190,'to':190,'status':130,'notes':230}
  for c in cols:self.transfer_tree.heading(c,text=heads[c]);self.transfer_tree.column(c,width=widths[c],anchor='center')
  self.transfer_tree.pack(fill='both',expand=True,padx=12,pady=8);self.refresh_transfers()
 def refresh_transfers(self):
  if not hasattr(self,'transfer_tree'):return
  self.transfer_tree.delete(*self.transfer_tree.get_children())
  rows=self.store.db.execute('SELECT t.*,s.full_name FROM transfers t JOIN students s ON s.id=t.student_id ORDER BY t.request_date DESC,t.id DESC').fetchall()
  for r in rows:self.transfer_tree.insert('','end',iid=str(r['id']),values=(r['id'],r['full_name'],r['request_date'],r['from_school'],r['to_school'],r['status'],r['notes']))
 def add_transfer(self):
  sid=self.selected_id()
  if not sid:return
  self.simple_record_dialog('تسجيل طلب تحويل',[('request_date','تاريخ الطلب'),('from_school','المدرسة المحول منها'),('to_school','المدرسة المحول إليها'),('status','حالة الطلب'),('notes','ملاحظات')],lambda d:self.store.db.execute('INSERT INTO transfers(student_id,request_date,from_school,to_school,status,notes) VALUES(?,?,?,?,?,?)',(sid,d['request_date'],d['from_school'],d['to_school'],d['status'] or 'قيد المراجعة',d['notes'])))
 def delete_transfer(self):
  sel=self.transfer_tree.selection()
  if not sel:return messagebox.showinfo('تنبيه','حدد طلب التحويل المطلوب')
  if messagebox.askyesno('تأكيد الحذف','هل تريد حذف طلب التحويل المحدد؟'):
   self.store.db.execute('DELETE FROM transfers WHERE id=?',(int(sel[0]),));self.store.db.commit();self.refresh_transfers();self.status.set('تم حذف طلب التحويل')
 def build_school(self):
  f=self.school_tab; tk.Label(f,text='بيانات المدرسة',font=('Tahoma',17,'bold'),bg='#f2f5f9',fg='#183b60').pack(anchor='e',padx=22,pady=18)
  self.school_vars={}
  for key,label in [('directorate','المديرية'),('administration','الإدارة التعليمية'),('school_name','اسم المدرسة'),('principal','مدير المدرسة'),('deputy','وكيل المدرسة'),('student_affairs','مسؤول شئون الطلبة')]:
   row=tk.Frame(f,bg='#f2f5f9'); row.pack(fill='x',padx=30,pady=5); tk.Label(row,text=label,width=23,anchor='e',bg='#f2f5f9').pack(side='right'); saved=self.store.db.execute('SELECT value FROM school WHERE key=?',(key,)).fetchone(); v=tk.StringVar(value=(saved[0] if saved else '')); self.school_vars[key]=v; ttk.Entry(row,textvariable=v,justify='right',width=60).pack(side='right',padx=8)
  ttk.Button(f,text='حفظ بيانات المدرسة',command=self.save_school).pack(anchor='e',padx=40,pady=12)
  tk.Label(f,text='النسخ الاحتياطي',font=('Tahoma',15,'bold'),bg='#f2f5f9',fg='#183b60').pack(anchor='e',padx=22,pady=(25,8))
  row=tk.Frame(f,bg='#f2f5f9'); row.pack(anchor='e',padx=30); ttk.Button(row,text='إنشاء نسخة احتياطية',command=self.backup).pack(side='right',padx=5); ttk.Button(row,text='استعادة نسخة قاعدة بيانات',command=self.restore).pack(side='right',padx=5)
  tk.Label(f,text=f'مكان حفظ قاعدة البيانات: {DB}',bg='#f2f5f9',fg='#66798d',font=('Tahoma',9)).pack(anchor='e',padx=30,pady=18)
 def refresh(self):
  if not hasattr(self,'tree'): return
  rows=self.store.all(self.search.get(),self.grade_filter.get(),self.class_filter.get())
  self.tree.delete(*self.tree.get_children())
  for i,r in enumerate(rows,1): self.tree.insert('', 'end', iid=str(r['id']), values=(i,*[r[k] or '' for k in ['student_code','full_name','national_id','gender','grade','class_name','guardian_name','guardian_phone']]))
  grades=self.store.choices('grade'); classes=self.store.choices('class_name')
  self.gf['values']=['',*grades]; self.cf['values']=['',*classes]
  self.stats[0].config(text=str(self.store.db.execute('select count(*) from students').fetchone()[0])); self.stats[1].config(text=str(len(grades))); self.stats[2].config(text=str(len(classes))); self.stats[3].config(text=str(self.store.db.execute("select count(*) from students where guardian_phone<>'' and guardian_phone is not null").fetchone()[0]))
  if hasattr(self,'rep_grade_box'): self.refresh_report_filters()
  if self.selected:
   r=self.store.db.execute('select full_name from students where id=?',(self.selected,)).fetchone(); self.att_info.set('الطالب المحدد: '+r[0] if r else 'لم يتم اختيار طالب')
 def selected_id(self):
  s=self.tree.selection()
  if not s: messagebox.showinfo('تنبيه','اختر طالباً أولاً من الجدول.'); return None
  self.selected=int(s[0]); self.refresh(); return self.selected
 def student_dialog(self, row=None):
  win=tk.Toplevel(self); win.title('بيانات الطالب'); win.geometry('650x720'); win.transient(self); win.grab_set(); win.configure(bg='#f2f5f9')
  tk.Label(win,text='إضافة / تعديل بيانات طالب',font=('Tahoma',16,'bold'),bg='#f2f5f9',fg='#183b60').pack(pady=12)
  entries={}
  canvas=tk.Canvas(win,bg='#f2f5f9',highlightthickness=0); frame=tk.Frame(canvas,bg='#f2f5f9'); sb=ttk.Scrollbar(win,orient='vertical',command=canvas.yview); canvas.configure(yscrollcommand=sb.set); sb.pack(side='left',fill='y'); canvas.pack(side='right',fill='both',expand=True); canvas.create_window((0,0),window=frame,anchor='ne',width=610); frame.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
  for key,label in FIELDS:
   line=tk.Frame(frame,bg='#f2f5f9'); line.pack(fill='x',padx=15,pady=4); tk.Label(line,text=label,width=19,anchor='e',bg='#f2f5f9').pack(side='right')
   v=tk.StringVar(value=(row[key] or '') if row else '')
   if key=='gender': w=ttk.Combobox(line,textvariable=v,values=['ذكر','أنثى'],width=38,state='readonly')
   elif key=='religion': w=ttk.Combobox(line,textvariable=v,values=['مسلم','مسيحي','أخرى'],width=38)
   elif key=='special_needs': w=ttk.Combobox(line,textvariable=v,values=['لا يوجد','دمج','إعاقة حركية','إعاقة سمعية','إعاقة بصرية','أخرى'],width=38)
   else: w=ttk.Entry(line,textvariable=v,width=42,justify='right')
   w.pack(side='right',padx=8); entries[key]=v
  def save():
   try: self.store.save({k:v.get() for k,v in entries.items()},row['id'] if row else None); self.refresh(); win.destroy(); self.status.set('تم حفظ بيانات الطالب بنجاح')
   except sqlite3.IntegrityError: messagebox.showerror('تكرار','كود الطالب مستخدم بالفعل. غيّر الكود أو اتركه فارغاً.')
   except Exception as e: messagebox.showerror('خطأ',str(e))
  ttk.Button(win,text='حفظ البيانات',command=save).pack(pady=10)
 def new_student(self): self.student_dialog()
 def edit_student(self):
  sid=self.selected_id()
  if sid: self.student_dialog(self.store.db.execute('select * from students where id=?',(sid,)).fetchone())
 def delete_student(self):
  sid=self.selected_id()
  if sid and messagebox.askyesno('تأكيد الحذف','هل تريد حذف بيانات الطالب نهائياً؟'): self.store.delete(sid); self.selected=None; self.refresh()
 def import_excel(self):
  path=filedialog.askopenfilename(filetypes=[('Excel','*.xlsx *.xlsm')])
  if not path:return
  try:
   from openpyxl import load_workbook
   wb=load_workbook(path,data_only=True,read_only=True); ws=wb.active; headers=[str(c or '').strip() for c in next(ws.iter_rows(min_row=1,max_row=1,values_only=True))]
   aliases={'كود التلميذ':'student_code','كود الطالب':'student_code','اسم التلميذ':'full_name','اسم الطالب':'full_name','الرقم القومى':'national_id','الرقم القومي':'national_id','الصف':'grade','الصف الدراسي':'grade','الفصل':'class_name','النوع':'gender','الجنس':'gender','تاريخ الميلاد':'birth_date','اسم ولي الأمر':'guardian_name','ولي الأمر':'guardian_name','رقم ولي الأمر':'guardian_phone','هاتف ولي الأمر':'guardian_phone','موبايل ولي الأمر':'guardian_phone','العنوان':'address','الديانة':'religion','الجنسية':'nationality'}
   mapping={i:aliases[h] for i,h in enumerate(headers) if h in aliases}; count=0; skipped=0
   for vals in ws.iter_rows(min_row=2,values_only=True):
    d={}
    for i,k in mapping.items():
     if i<len(vals) and vals[i] is not None: d[k]=str(vals[i]).strip()
    if not d.get('full_name'): skipped+=1; continue
    try:self.store.save(d); count+=1
    except sqlite3.IntegrityError: skipped+=1
   wb.close(); self.refresh(); messagebox.showinfo('اكتمل الاستيراد',f'تم استيراد {count} طالب.\nتم تجاوز {skipped} صف (اسم فارغ أو كود مكرر).')
  except Exception as e: messagebox.showerror('تعذر الاستيراد',f'تحقق من الملف وأنه بصيغة XLSX.\n{e}')
 def export_excel(self):
  path=filedialog.asksaveasfilename(defaultextension='.xlsx',filetypes=[('Excel','*.xlsx')],initialfile='بيانات_الطلاب.xlsx')
  if not path:return
  try:
   from openpyxl import Workbook
   from openpyxl.styles import Font,PatternFill,Alignment
   wb=Workbook(); ws=wb.active; ws.title='بيانات الطلاب'; ws.sheet_view.rightToLeft=True
   ws.append([label for _,label in FIELDS])
   for c in ws[1]: c.font=Font(name='Arial',bold=True,color='FFFFFF'); c.fill=PatternFill('solid',fgColor='173D63'); c.alignment=Alignment(horizontal='center')
   for r in self.store.all(): ws.append([r[k] or '' for k,_ in FIELDS])
   ws.freeze_panes='A2'; ws.auto_filter.ref=ws.dimensions
   for col in ws.columns:
    letter=col[0].column_letter; ws.column_dimensions[letter].width=min(max(max(len(str(c.value or '')) for c in col)+3,14),35)
   wb.save(path); messagebox.showinfo('تم التصدير','تم حفظ ملف Excel بنجاح.')
  except Exception as e: messagebox.showerror('خطأ',str(e))
 def whatsapp(self):
  sid=self.selected_id()
  if not sid:return
  r=self.store.db.execute('select guardian_phone,full_name from students where id=?',(sid,)).fetchone(); phone=''.join(ch for ch in (r['guardian_phone'] or '') if ch.isdigit())
  if not phone: messagebox.showwarning('لا يوجد رقم','لا يوجد رقم هاتف مسجل لولي الأمر.'); return
  if phone.startswith('0'): phone='20'+phone[1:]
  msg=urllib.parse.quote('مرحباً، نود التواصل معكم بخصوص الطالب/ة '+r['full_name'])
  webbrowser.open('https://wa.me/'+phone+'?text='+msg)
 def refresh_attendance(self):
  if not hasattr(self,'att_tree'): return
  self.att_tree.delete(*self.att_tree.get_children())
  try: datetime.strptime(self.att_date.get().strip(),'%Y-%m-%d')
  except ValueError:
   self.att_summary.set('التاريخ غير صحيح — استخدم YYYY-MM-DD'); return
  grades=self.store.choices('grade'); classes=self.store.choices('class_name')
  self.att_grade_box['values']=['',*grades]; self.att_class_box['values']=['',*classes]
  sql='''SELECT s.id,s.student_code,s.full_name,s.grade,s.class_name,a.status,a.note FROM students s LEFT JOIN attendance a ON a.student_id=s.id AND a.day=? WHERE 1=1'''; args=[self.att_date.get().strip()]
  if self.att_grade.get(): sql+=' AND s.grade=?'; args.append(self.att_grade.get())
  if self.att_class.get(): sql+=' AND s.class_name=?'; args.append(self.att_class.get())
  sql+=' ORDER BY s.grade,s.class_name,s.full_name'
  rows=self.store.db.execute(sql,args).fetchall(); counts={'حاضر':0,'غائب':0,'متأخر':0,'إذن':0,'غياب بعذر':0,'غير مسجل':0}
  for i,r in enumerate(rows,1):
   status=r['status'] or 'غير مسجل'; counts[status]=counts.get(status,0)+1
   self.att_tree.insert('','end',iid=str(r['id']),values=(i,r['student_code'] or '',r['full_name'],r['grade'] or '',r['class_name'] or '',status,r['note'] or ''))
  self.att_summary.set('إجمالي: %s | حاضر: %s | غائب: %s | متأخر: %s | إذن: %s | غياب بعذر: %s | غير مسجل: %s' % (len(rows),counts['حاضر'],counts['غائب'],counts['متأخر'],counts['إذن'],counts['غياب بعذر'],counts['غير مسجل']))
 def mark_attendance(self):
  selected=self.att_tree.selection() if hasattr(self,'att_tree') else ()
  if not selected:
   sid=self.selected_id()
   if not sid:return
   selected=(str(sid),)
  try:
   d=self.att_date.get().strip(); datetime.strptime(d,'%Y-%m-%d')
   for sid in selected:
    self.store.db.execute('''INSERT INTO attendance(student_id,day,status,note) VALUES(?,?,?,?) ON CONFLICT(student_id,day) DO UPDATE SET status=excluded.status,note=excluded.note''',(int(sid),d,self.att_status.get(),self.att_note.get().strip()))
   self.store.db.commit(); self.refresh_attendance(); self.status.set('تم تسجيل الحالة لعدد %s طالب' % len(selected))
  except Exception as e: messagebox.showerror('خطأ','راجع التاريخ والبيانات المدخلة.\n'+str(e))
 def bulk_attendance(self,status):
  try:
   d=self.att_date.get().strip(); datetime.strptime(d,'%Y-%m-%d')
   sql='SELECT id FROM students WHERE 1=1'; args=[]
   if self.att_grade.get():sql+=' AND grade=?';args.append(self.att_grade.get())
   if self.att_class.get():sql+=' AND class_name=?';args.append(self.att_class.get())
   ids=[r[0] for r in self.store.db.execute(sql,args)]
   if not ids:return messagebox.showinfo('تنبيه','لا يوجد طلاب في التصفية الحالية.')
   if not messagebox.askyesno('تأكيد جماعي',f'سيتم تسجيل {status} لعدد {len(ids)} طالب بتاريخ {d}. هل تريد المتابعة؟'):return
   self.store.db.executemany('''INSERT INTO attendance(student_id,day,status) VALUES(?,?,?) ON CONFLICT(student_id,day) DO UPDATE SET status=excluded.status''',[(sid,d,status) for sid in ids]); self.store.db.commit(); self.att_status.set(status); self.refresh_attendance(); self.status.set(f'تم تسجيل {status} لجميع الطلاب ({len(ids)})')
  except Exception as e:messagebox.showerror('خطأ','تعذر التسجيل الجماعي: '+str(e))
 def attendance_csv(self):
  import csv
  path=filedialog.asksaveasfilename(defaultextension='.csv',filetypes=[('CSV','*.csv')],initialfile='غياب_اليوم.csv')
  if not path:return
  try: datetime.strptime(self.att_date.get().strip(),'%Y-%m-%d')
  except ValueError:return messagebox.showerror('تاريخ غير صحيح','استخدم YYYY-MM-DD')
  sql="SELECT s.student_code,s.full_name,s.grade,s.class_name,COALESCE(a.status,'غير مسجل'),COALESCE(a.note,'') FROM students s LEFT JOIN attendance a ON a.student_id=s.id AND a.day=? WHERE 1=1";args=[self.att_date.get().strip()]
  if self.att_grade.get():sql+=' AND s.grade=?';args.append(self.att_grade.get())
  if self.att_class.get():sql+=' AND s.class_name=?';args.append(self.att_class.get())
  rows=self.store.db.execute(sql+' ORDER BY s.grade,s.class_name,s.full_name',args).fetchall()
  with open(path,'w',newline='',encoding='utf-8-sig') as f:
   w=csv.writer(f); w.writerow(['كود الطالب','اسم الطالب','الصف','الفصل','الحالة','ملاحظات']); w.writerows([tuple(r) for r in rows])
  messagebox.showinfo('تم','تم حفظ التقرير: '+str(len(rows))+' سجل')
 def absence_followup_dialog(self):
  win=tk.Toplevel(self);win.title('متابعة الغياب المتكرر');win.geometry('1120x650');win.transient(self)
  bar=tk.Frame(win);bar.pack(fill='x',padx=12,pady=10)
  today=date.today(); start=tk.StringVar(value=today.replace(day=1).isoformat()); end=tk.StringVar(value=today.isoformat())
  total_limit=tk.StringVar(value='5'); streak_limit=tk.StringVar(value='3'); grade=tk.StringVar(); cls=tk.StringVar()
  for label,var,width in [('من تاريخ YYYY-MM-DD',start,12),('إلى تاريخ YYYY-MM-DD',end,12),('حد الغياب الكلي',total_limit,5),('حد الغياب المتتابع',streak_limit,5)]:
   tk.Label(bar,text=label).pack(side='right',padx=(7,2));ttk.Entry(bar,textvariable=var,width=width,justify='center').pack(side='right',padx=2)
  tk.Label(bar,text='الصف').pack(side='right',padx=(7,2));ttk.Combobox(bar,textvariable=grade,width=12,state='readonly',values=['',*self.store.choices('grade')]).pack(side='right')
  tk.Label(bar,text='الفصل').pack(side='right',padx=(7,2));ttk.Combobox(bar,textvariable=cls,width=10,state='readonly',values=['',*self.store.choices('class_name')]).pack(side='right')
  cols=('code','name','grade','class','absent','excused','streak','last','reason','guardian','phone')
  tree=ttk.Treeview(win,columns=cols,show='headings');tree.pack(fill='both',expand=True,padx=12,pady=8)
  heads={'code':'الكود','name':'اسم الطالب','grade':'الصف','class':'الفصل','absent':'غياب بدون عذر','excused':'غياب بعذر','streak':'المتتابع','last':'آخر غياب','reason':'سبب التنبيه','guardian':'ولي الأمر','phone':'الهاتف'}
  widths={'code':80,'name':180,'grade':90,'class':65,'absent':95,'excused':85,'streak':75,'last':95,'reason':150,'guardian':130,'phone':110}
  for c in cols:tree.heading(c,text=heads[c]);tree.column(c,width=widths[c],anchor='center')
  summary=tk.StringVar(value='حدد الفترة وحدود التنبيه ثم اضغط عرض التقرير.')
  tk.Label(win,textvariable=summary,anchor='e',font=('Tahoma',10,'bold')).pack(fill='x',padx=16,pady=5)
  current={'rows':[]}
  def load():
   try:
    rows=self.store.absence_followup_rows(start.get().strip(),end.get().strip(),int(total_limit.get()),int(streak_limit.get()),grade.get(),cls.get())
    tree.delete(*tree.get_children())
    for r in rows:tree.insert('','end',values=(r['student_code'],r['full_name'],r['grade'],r['class_name'],r['غائب'],r['غياب بعذر'],r['التتابع الحالي'],r['آخر غياب'] or '—',r['سبب التنبيه'],r['guardian_name'],r['guardian_phone']))
    current['rows']=rows;summary.set(f'عدد الطلاب الذين يحتاجون متابعة: {len(rows)} | الغياب المتتابع محسوب من أيام التسجيل المتتالية وليس أيام التقويم.')
   except Exception as e:messagebox.showerror('بيانات غير صحيحة',str(e),parent=win)
  def export():
   if not current['rows']:return messagebox.showinfo('تنبيه','لا توجد نتائج للتصدير.',parent=win)
   import csv
   path=filedialog.asksaveasfilename(parent=win,defaultextension='.csv',filetypes=[('CSV','*.csv')],initialfile='متابعة_الغياب_المتكرر.csv')
   if not path:return
   with open(path,'w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f);w.writerow(['كود الطالب','اسم الطالب','الصف','الفصل','غياب بدون عذر','غياب بعذر','الغياب المتتابع','آخر غياب','سبب التنبيه','ولي الأمر','الهاتف'])
    for r in current['rows']:w.writerow([r['student_code'],r['full_name'],r['grade'],r['class_name'],r['غائب'],r['غياب بعذر'],r['التتابع الحالي'],r['آخر غياب'],r['سبب التنبيه'],r['guardian_name'],r['guardian_phone']])
   messagebox.showinfo('تم','تم تصدير تقرير المتابعة.',parent=win)
  ttk.Button(bar,text='عرض التقرير',command=load).pack(side='left',padx=4);ttk.Button(bar,text='تصدير CSV',command=export).pack(side='left',padx=4);ttk.Button(bar,text='متابعة إخطار أولياء الأمور',command=self.guardian_followup_report).pack(side='left',padx=4)
  load()
 def attendance_period_dialog(self):
  win=tk.Toplevel(self);win.title('كشف الحضور الشهري والسنوي');win.geometry('1120x650');win.transient(self)
  bar=tk.Frame(win);bar.pack(fill='x',padx=12,pady=10)
  tk.Label(bar,text='السنة:').pack(side='right');year=tk.StringVar(value=str(date.today().year));ttk.Entry(bar,textvariable=year,width=7,justify='center').pack(side='right',padx=5)
  tk.Label(bar,text='الشهر (1-12 أو فارغ للعام):').pack(side='right',padx=(12,2));month=tk.StringVar(value=str(date.today().month));ttk.Entry(bar,textvariable=month,width=5,justify='center').pack(side='right',padx=5)
  tk.Label(bar,text='الصف:').pack(side='right');grade=tk.StringVar(value=self.att_grade.get());ttk.Combobox(bar,textvariable=grade,values=['',*self.store.choices('grade')],width=14,state='readonly').pack(side='right',padx=5)
  tk.Label(bar,text='الفصل:').pack(side='right');cls=tk.StringVar(value=self.att_class.get());ttk.Combobox(bar,textvariable=cls,values=['',*self.store.choices('class_name')],width=12,state='readonly').pack(side='right',padx=5)
  summary=tk.StringVar();tk.Label(win,textvariable=summary,anchor='e',justify='right',font=('Tahoma',10,'bold'),fg='#145b91').pack(fill='x',padx=16,pady=6)
  cols=('code','name','grade','class','days','present','absent','late','permission','excused','rate');tree=ttk.Treeview(win,columns=cols,show='headings')
  heads={'code':'الكود','name':'اسم الطالب','grade':'الصف','class':'الفصل','days':'أيام مسجلة','present':'حاضر','absent':'غائب','late':'متأخر','permission':'إذن','excused':'بعذر','rate':'نسبة الحضور %'}
  widths={'code':85,'name':210,'grade':105,'class':80,'days':90,'present':75,'absent':75,'late':75,'permission':65,'excused':65,'rate':100}
  for c in cols:tree.heading(c,text=heads[c]);tree.column(c,width=widths[c],anchor='center')
  tree.pack(fill='both',expand=True,padx=12,pady=8);current={'rows':[],'start':'','end':''}
  def load():
   try:
    raw_year=year.get().strip();y=int(raw_year)
    if len(raw_year)!=4 or y<2000 or y>2100:raise ValueError('السنة غير صحيحة')
    raw_month=month.get().strip()
    if raw_month:
     m=int(raw_month)
     if not 1<=m<=12:raise ValueError('الشهر يجب أن يكون من 1 إلى 12')
     from calendar import monthrange
     start=f'{y:04d}-{m:02d}-01';end=f'{y:04d}-{m:02d}-{monthrange(y,m)[1]:02d}';period=f'شهر {m} / {y}'
    else:start=f'{y:04d}-01-01';end=f'{y:04d}-12-31';period=f'عام {y}'
    rows=self.store.attendance_period_rows(start,end,grade.get(),cls.get());tot=self.store.attendance_period_summary(start,end,grade.get(),cls.get())
    tree.delete(*tree.get_children())
    for r in rows:tree.insert('','end',values=(r['student_code'],r['full_name'],r['grade'],r['class_name'],r['أيام مسجلة'],r['حاضر'],r['غائب'],r['متأخر'],r['إذن'],r['غياب بعذر'],('—' if r['نسبة الحضور'] is None else str(r['نسبة الحضور'])+'%')))
    rate='—' if tot['نسبة الحضور العامة'] is None else str(tot['نسبة الحضور العامة'])+'%'
    summary.set(f'{period} | الطلاب: {tot["عدد الطلاب"]} | الأيام المسجلة: {tot["أيام مسجلة"]} | حاضر: {tot["حاضر"]} | غائب: {tot["غائب"]} | بعذر: {tot["غياب بعذر"]} | بلا تسجيل: {tot["طلاب بلا تسجيل"]} | نسبة الحضور من الأيام المسجلة: {rate}')
    current.update(rows=rows,start=start,end=end)
   except Exception as e:messagebox.showerror('بيانات غير صحيحة','أدخل سنة صحيحة، وشهراً من 1 إلى 12 أو اترك الشهر فارغاً.\n'+str(e),parent=win)
  def export_csv():
   if not current['rows']:return messagebox.showinfo('تنبيه','لا توجد بيانات لتصديرها.',parent=win)
   import csv
   path=filedialog.asksaveasfilename(parent=win,defaultextension='.csv',filetypes=[('CSV','*.csv')],initialfile='كشف_حضور_'+current['start']+'_'+current['end']+'.csv')
   if not path:return
   with open(path,'w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f);w.writerow(['كود الطالب','اسم الطالب','الصف','الفصل','أيام مسجلة','حاضر','غائب','متأخر','إذن','غياب بعذر','نسبة الحضور %'])
    for r in current['rows']:w.writerow([r['student_code'],r['full_name'],r['grade'],r['class_name'],r['أيام مسجلة'],r['حاضر'],r['غائب'],r['متأخر'],r['إذن'],r['غياب بعذر'],r['نسبة الحضور'] if r['نسبة الحضور'] is not None else ''])
   messagebox.showinfo('تم','تم تصدير الكشف بنجاح.',parent=win)
  def print_report():
   if not current['rows']:return messagebox.showinfo('تنبيه','اعرض التقرير أولاً.',parent=win)
   import html
   headers=['كود الطالب','اسم الطالب','الصف','الفصل','أيام مسجلة','حاضر','غائب','متأخر','إذن','غياب بعذر','نسبة الحضور'];keys=['student_code','full_name','grade','class_name','أيام مسجلة','حاضر','غائب','متأخر','إذن','غياب بعذر','نسبة الحضور']
   body=''.join('<tr>'+''.join('<td>'+html.escape(str(r[k] if r[k] is not None else '—'))+'</td>' for k in keys)+'</tr>' for r in current['rows'])
   page="<!doctype html><html lang='ar' dir='rtl'><meta charset='utf-8'><title>كشف الحضور</title><style>body{font-family:Tahoma;margin:12mm}h2,p{text-align:center}table{border-collapse:collapse;width:100%;font-size:10px}th,td{border:1px solid #555;padding:6px;text-align:center}th{background:#e8eef5}@media print{button{display:none}}</style><button onclick='window.print()'>طباعة</button><h2>كشف الحضور والغياب</h2><p>من "+current['start']+" إلى "+current['end']+"</p><table><thead><tr>"+''.join('<th>'+html.escape(x)+'</th>' for x in headers)+"</tr></thead><tbody>"+body+"</tbody></table></html>"
   out=BASE/'attendance_period_preview.html';out.write_text(page,encoding='utf-8');webbrowser.open(out.as_uri())
  ttk.Button(bar,text='عرض الكشف',command=load).pack(side='left',padx=4);ttk.Button(bar,text='تصدير CSV',command=export_csv).pack(side='left',padx=4);ttk.Button(bar,text='معاينة للطباعة',command=print_report).pack(side='left',padx=4);load()
 def save_school(self):
  for k,v in self.school_vars.items(): self.store.db.execute('INSERT INTO school(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(k,v.get()))
  self.store.db.commit(); self.status.set('تم حفظ بيانات المدرسة')
 def backup(self):
  path=filedialog.asksaveasfilename(defaultextension='.db',filetypes=[('SQLite database','*.db')],initialfile='نسخة_احتياطية_الطلاب_'+date.today().isoformat()+'.db')
  if path:
   try:
    self.store.backup_to(path)
    messagebox.showinfo('نسخة احتياطية','تم إنشاء النسخة الاحتياطية وفحص سلامتها بنجاح.')
   except Exception as e: messagebox.showerror('تعذر النسخ الاحتياطي',str(e))
 def restore(self):
  path=filedialog.askopenfilename(filetypes=[('SQLite database','*.db')])
  if not path:return
  if not messagebox.askyesno('تأكيد الاستعادة','سيتم استبدال قاعدة البيانات الحالية. سيحفظ البرنامج نسخة أمان تلقائية قبل الاستعادة. هل تريد المتابعة؟'):return
  try:
   safety=self.store.restore_from(path)
   self.selected=None; self.refresh()
   messagebox.showinfo('تمت الاستعادة','تمت استعادة النسخة وفحص قاعدة البيانات بنجاح.\nحُفظت نسخة أمان من البيانات السابقة باسم:\n'+safety.name)
  except Exception as e: messagebox.showerror('تعذر الاستعادة',str(e))
 def student_card(self):
  sid=self.selected_id()
  if not sid:return
  import html,base64
  r=self.store.db.execute('SELECT * FROM students WHERE id=?',(sid,)).fetchone()
  # QR يحمل كود الطالب فقط لتقليل كشف البيانات الشخصية عند مسحه.
  payload='STUDENT|'+str(r['student_code'] or r['id'])
  qr_data=''
  try:
   import qrcode,io
   img=qrcode.make(payload);buf=io.BytesIO();img.save(buf,format='PNG');qr_data='data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode('ascii')
  except Exception: qr_data=''
  school=self.store.db.execute("SELECT value FROM school WHERE key='school_name'").fetchone();school=school[0] if school else 'اسم المدرسة'
  qr_html=("<img width='115' src='"+qr_data+"'>") if qr_data else "<div class='qr'>QR غير متاح<br>ثبت مكتبة qrcode</div>"
  page="""<!doctype html><html lang='ar' dir='rtl'><meta charset='utf-8'><title>بطاقة طالب</title><style>body{font-family:Tahoma;background:#eef2f7;padding:25px}.card{width:520px;margin:auto;background:white;border:3px solid #173d63;border-radius:16px;padding:20px;display:flex;align-items:center;gap:22px}.data{flex:1}.data h2{color:#173d63}.data p{border-bottom:1px solid #ddd;padding:7px}.qr{text-align:center;border:1px dashed #777;padding:18px}button{display:block;margin:20px auto;padding:10px 22px}@media print{button{display:none}body{background:white}}</style><div class='card'><div class='data'><h2>"""+html.escape(school)+"</h2><h3>بطاقة بيانات طالب</h3><p>الاسم: "+html.escape(r['full_name'])+"</p><p>الكود: "+html.escape(str(r['student_code'] or r['id']))+"</p><p>الصف: "+html.escape(str(r['grade'] or ''))+"</p><p>الفصل: "+html.escape(str(r['class_name'] or ''))+"</p></div>"+qr_html+"</div><button onclick='window.print()'>طباعة البطاقة</button></html>"
  out=BASE/'student_card.html';out.write_text(page,encoding='utf-8');webbrowser.open(out.as_uri())
 def build_grades(self):
  f=self.grades_tab
  bar=tk.Frame(f,bg='#f2f5f9'); bar.pack(fill='x',padx=14,pady=12)
  tk.Label(bar,text='الطالب المحدد من سجل الطلاب:',bg='#f2f5f9').pack(side='right')
  ttk.Button(bar,text='إضافة درجة',command=self.add_grade).pack(side='left',padx=4)
  ttk.Button(bar,text='حذف الدرجة المحددة',command=self.delete_grade).pack(side='left',padx=4)
  ttk.Button(bar,text='تحديث',command=self.refresh_grades).pack(side='left',padx=4)
  cols=('id','student','grade','class','subject','term','assessment','score','maximum','date')
  self.grade_tree=ttk.Treeview(f,columns=cols,show='headings')
  heads={'id':'م','student':'اسم الطالب','grade':'الصف','class':'الفصل','subject':'المادة','term':'الفصل الدراسي','assessment':'نوع التقييم','score':'الدرجة','maximum':'النهاية الكبرى','date':'التاريخ'}
  for c in cols:self.grade_tree.heading(c,text=heads[c]);self.grade_tree.column(c,width=105,anchor='center')
  self.grade_tree.column('student',width=220); self.grade_tree.pack(fill='both',expand=True,padx=12,pady=8)
  self.refresh_grades()
 def refresh_grades(self):
  if not hasattr(self,'grade_tree'):return
  self.grade_tree.delete(*self.grade_tree.get_children())
  rows=self.store.db.execute('SELECT g.*,s.full_name,s.grade,s.class_name FROM grades g JOIN students s ON s.id=g.student_id ORDER BY s.grade,s.class_name,s.full_name,g.subject').fetchall()
  for r in rows:self.grade_tree.insert('','end',iid=str(r['id']),values=(r['id'],r['full_name'],r['grade'],r['class_name'],r['subject'],r['term'],r['assessment'],r['score'],r['max_score'],r['exam_date']))
 def add_grade(self):
  sid=self.selected_id()
  if not sid:return
  self.simple_record_dialog('إضافة درجة', [('subject','المادة'),('term','الفصل الدراسي'),('assessment','نوع التقييم'),('score','الدرجة'),('max_score','النهاية الكبرى'),('exam_date','التاريخ'),('notes','ملاحظات')], lambda d:self.store.db.execute('INSERT INTO grades(student_id,subject,term,assessment,score,max_score,exam_date,notes) VALUES(?,?,?,?,?,?,?,?)',(sid,d['subject'],d['term'],d['assessment'],float(d['score'] or 0),float(d['max_score'] or 100),d['exam_date'],d['notes'])))
 def delete_grade(self):
  sel=self.grade_tree.selection()
  if not sel:return messagebox.showinfo('تنبيه','حدد درجة من الجدول')
  self.store.db.execute('DELETE FROM grades WHERE id=?',(int(sel[0]),));self.store.db.commit();self.refresh_grades()
 def build_behavior(self):
  f=self.behavior_tab; bar=tk.Frame(f,bg='#f2f5f9');bar.pack(fill='x',padx=14,pady=12)
  ttk.Button(bar,text='تسجيل موقف سلوكي للطالب المحدد',command=self.add_behavior).pack(side='right',padx=4)
  ttk.Button(bar,text='حذف السجل المحدد',command=self.delete_behavior).pack(side='right',padx=4)
  ttk.Button(bar,text='تحديث',command=self.refresh_behavior).pack(side='right',padx=4)
  cols=('id','student','date','category','points','details','action')
  self.beh_tree=ttk.Treeview(f,columns=cols,show='headings')
  heads={'id':'م','student':'اسم الطالب','date':'التاريخ','category':'نوع الموقف','points':'النقاط','details':'التفاصيل','action':'الإجراء المتخذ'}
  for c in cols:self.beh_tree.heading(c,text=heads[c]);self.beh_tree.column(c,width=125,anchor='center')
  self.beh_tree.column('student',width=220);self.beh_tree.column('details',width=260);self.beh_tree.pack(fill='both',expand=True,padx=12,pady=8);self.refresh_behavior()
 def refresh_behavior(self):
  if not hasattr(self,'beh_tree'):return
  self.beh_tree.delete(*self.beh_tree.get_children())
  for r in self.store.db.execute('SELECT b.*,s.full_name FROM behavior b JOIN students s ON s.id=b.student_id ORDER BY event_date DESC,id DESC'):
   self.beh_tree.insert('','end',iid=str(r['id']),values=(r['id'],r['full_name'],r['event_date'],r['category'],r['points'],r['details'],r['action_taken']))
 def add_behavior(self):
  sid=self.selected_id()
  if not sid:return
  self.simple_record_dialog('تسجيل موقف سلوكي',[('event_date','التاريخ'),('category','نوع الموقف'),('points','النقاط (+/-)'),('details','التفاصيل'),('action_taken','الإجراء المتخذ')],lambda d:self.store.db.execute('INSERT INTO behavior(student_id,event_date,category,points,details,action_taken) VALUES(?,?,?,?,?,?)',(sid,d['event_date'],d['category'],int(d['points'] or 0),d['details'],d['action_taken'])))
 def simple_record_dialog(self,title,fields,save_callback):
  win=tk.Toplevel(self);win.title(title);win.geometry('520x520');win.transient(self);win.grab_set();win.configure(bg='#f2f5f9');vars={}
  for key,label in fields:
   row=tk.Frame(win,bg='#f2f5f9');row.pack(fill='x',padx=18,pady=7);tk.Label(row,text=label,width=19,anchor='e',bg='#f2f5f9').pack(side='right');v=tk.StringVar(value=(date.today().isoformat() if key in ('event_date','exam_date','request_date') else 'الفصل الدراسي الأول' if key=='term' else '100' if key=='max_score' else '0' if key in ('score','points') else 'قيد المراجعة' if key=='status' else ''));vars[key]=v
   ttk.Entry(row,textvariable=v,width=38,justify='right').pack(side='right',padx=8)
  def commit():
   try:save_callback({k:v.get().strip() for k,v in vars.items()});self.store.db.commit();win.destroy();self.refresh_grades();self.refresh_behavior();self.refresh_transfers();self.status.set('تم حفظ السجل بنجاح')
   except Exception as e:messagebox.showerror('تعذر الحفظ',str(e),parent=win)
  ttk.Button(win,text='حفظ',command=commit).pack(pady=18)
 def delete_behavior(self):
  sel=self.beh_tree.selection()
  if not sel:return messagebox.showinfo('تنبيه','حدد السجل المطلوب')
  self.store.db.execute('DELETE FROM behavior WHERE id=?',(int(sel[0]),));self.store.db.commit();self.refresh_behavior()
 def build_reports(self):
  f=self.reports_tab
  tk.Label(f,text='مركز التقارير والنماذج المدرسية',font=('Tahoma',18,'bold'),bg='#f2f5f9',fg='#183b60').pack(anchor='e',padx=20,pady=18)
  row=tk.Frame(f,bg='#f2f5f9');row.pack(fill='x',padx=20,pady=8)
  tk.Label(row,text='نوع التقرير:',bg='#f2f5f9').pack(side='right');self.report_type=tk.StringVar(value='سجل قيد الطلاب')
  options=['سجل قيد الطلاب','كشف أسماء فصل','كشف أرقام هواتف أولياء الأمور','كشف الطلاب ذوي الحالات الخاصة','كشف المستجدين نموذج 41','كشف المستجدين نموذج 31','كشف المستجدين نموذج 12','كشف الغياب لفترة','كشف درجات مادة','كشف السلوك والتقييم','سجل التحويلات','بيانات المدرسة DATA','كشف المقبولين والمقيدين للعام','كشف المنقطعين وتاركي المدرسة']
  ttk.Combobox(row,textvariable=self.report_type,values=options,state='readonly',width=34).pack(side='right',padx=8)
  tk.Label(row,text='الصف:',bg='#f2f5f9').pack(side='right');self.rep_grade=tk.StringVar();self.rep_grade_box=ttk.Combobox(row,textvariable=self.rep_grade,width=18);self.rep_grade_box.pack(side='right',padx=5)
  tk.Label(row,text='الفصل:',bg='#f2f5f9').pack(side='right');self.rep_class=tk.StringVar();self.rep_class_box=ttk.Combobox(row,textvariable=self.rep_class,width=14);self.rep_class_box.pack(side='right',padx=5)
  ttk.Button(row,text='تحديث القوائم',command=self.refresh_report_filters).pack(side='right',padx=5)
  actions=tk.Frame(f,bg='#f2f5f9');actions.pack(anchor='e',padx=20,pady=12)
  ttk.Button(actions,text='إحصاءات القيد حسب الصف والفصل',command=self.enrollment_statistics).pack(side='right',padx=5)
  ttk.Button(actions,text='إنشاء التقرير وفتحه للطباعة',command=self.generate_report).pack(side='right',padx=5)
  ttk.Button(actions,text='تصدير التقرير Excel',command=self.export_report).pack(side='right',padx=5)
  tk.Label(f,text='النماذج 41 و31 و12 هنا قوالب تنظيمية قابلة للطباعة، ويجب مطابقة بياناتها مع النموذج الرسمي المعتمد لدى الإدارة التعليمية قبل الاستخدام الرسمي.',wraplength=950,justify='right',bg='#f2f5f9',fg='#8a5b12',font=('Tahoma',10)).pack(anchor='e',padx=24,pady=16)
  self.refresh_report_filters()
 def refresh_report_filters(self):
  self.rep_grade_box['values']=['',*self.store.choices('grade')];self.rep_class_box['values']=['',*self.store.choices('class_name')]
 def report_rows(self):
  sql='SELECT * FROM students WHERE 1=1';args=[]
  if self.rep_grade.get():sql+=' AND grade=?';args.append(self.rep_grade.get())
  if self.rep_class.get():sql+=' AND class_name=?';args.append(self.rep_class.get())
  return self.store.db.execute(sql+' ORDER BY grade,class_name,full_name',args).fetchall()
 def report_data(self):
  typ=self.report_type.get(); students=self.report_rows()
  if typ=='كشف أرقام هواتف أولياء الأمور': headers=['م','اسم الطالب','الصف','الفصل','اسم ولي الأمر','رقم الهاتف']; rows=[[i,r['full_name'],r['grade'],r['class_name'],r['guardian_name'],r['guardian_phone']] for i,r in enumerate(students,1)]
  elif typ=='كشف الطلاب ذوي الحالات الخاصة':
   students=[r for r in students if r['special_needs'] and r['special_needs'] not in ('لا يوجد','')];headers=['م','اسم الطالب','الصف','الفصل','الحالة الخاصة','ملاحظات'];rows=[[i,r['full_name'],r['grade'],r['class_name'],r['special_needs'],r['notes']] for i,r in enumerate(students,1)]
  elif typ.startswith('كشف المستجدين'):
   headers=['م','اسم الطالب','النوع','تاريخ الميلاد','الرقم القومي','الجنسية','العنوان','ولي الأمر','الهاتف','تاريخ القيد'];rows=[[i,r['full_name'],r['gender'],r['birth_date'],r['national_id'],r['nationality'],r['address'],r['guardian_name'],r['guardian_phone'],r['enrollment_date']] for i,r in enumerate(students,1)]
  elif typ=='كشف الغياب لفترة':
   headers=['التاريخ','كود الطالب','اسم الطالب','الصف','الفصل','الحالة'];rows=[list(r) for r in self.store.db.execute('SELECT a.day,s.student_code,s.full_name,s.grade,s.class_name,a.status FROM attendance a JOIN students s ON s.id=a.student_id WHERE s.grade LIKE ? AND s.class_name LIKE ? ORDER BY a.day DESC',(self.rep_grade.get() or '%',self.rep_class.get() or '%'))]
  elif typ=='كشف درجات مادة':
   headers=['اسم الطالب','الصف','الفصل','المادة','الفصل الدراسي','نوع التقييم','الدرجة','النهاية الكبرى'];rows=[list(r) for r in self.store.db.execute('SELECT s.full_name,s.grade,s.class_name,g.subject,g.term,g.assessment,g.score,g.max_score FROM grades g JOIN students s ON s.id=g.student_id WHERE s.grade LIKE ? AND s.class_name LIKE ? ORDER BY s.full_name',(self.rep_grade.get() or '%',self.rep_class.get() or '%'))]
  elif typ=='كشف السلوك والتقييم':
   headers=['اسم الطالب','التاريخ','نوع الموقف','النقاط','التفاصيل','الإجراء'];rows=[list(r) for r in self.store.db.execute('SELECT s.full_name,b.event_date,b.category,b.points,b.details,b.action_taken FROM behavior b JOIN students s ON s.id=b.student_id WHERE s.grade LIKE ? AND s.class_name LIKE ? ORDER BY b.event_date DESC',(self.rep_grade.get() or '%',self.rep_class.get() or '%'))]
  elif typ=='سجل التحويلات':
   headers=['اسم الطالب','تاريخ الطلب','المدرسة المحول منها','المدرسة المحول إليها','حالة الطلب','ملاحظات'];rows=[list(r) for r in self.store.db.execute('SELECT s.full_name,t.request_date,t.from_school,t.to_school,t.status,t.notes FROM transfers t JOIN students s ON s.id=t.student_id WHERE s.grade LIKE ? AND s.class_name LIKE ? ORDER BY t.request_date DESC',(self.rep_grade.get() or '%',self.rep_class.get() or '%'))]
  elif typ in ('كشف المقبولين والمقيدين للعام','كشف المنقطعين وتاركي المدرسة'):
   year='2026/2027'
   latest=self.store.latest_status_rows(year,self.rep_grade.get(),self.rep_class.get())
   wanted=('قيد','إعادة قيد') if typ=='كشف المقبولين والمقيدين للعام' else ('انقطاع','ترك المدرسة')
   selected=[r for r in latest if (r['event_type'] in wanted if r['event_type'] else (typ=='كشف المقبولين والمقيدين للعام'))]
   headers=['م','كود الطالب','اسم الطالب','الصف','الفصل','آخر حركة','تاريخ الحركة','السبب','رقم القرار']
   rows=[[i,r['student_code'] or '',r['full_name'],r['grade'],r['class_name'],r['event_type'] or 'قيد (من سجل الطلاب)',r['event_date'] or '',r['reason'] or '',r['decision_no'] or ''] for i,r in enumerate(selected,1)]
  elif typ=='بيانات المدرسة DATA':
   headers=[label for _,label in FIELDS];rows=[[r[k] or '' for k,_ in FIELDS] for r in students]
  else:
   headers=['م','كود الطالب','اسم الطالب','الرقم القومي','النوع','الصف','الفصل','تاريخ الميلاد','الجنسية','الديانة','العنوان','اسم ولي الأمر','هاتف ولي الأمر','تاريخ القيد'];keys=['student_code','full_name','national_id','gender','grade','class_name','birth_date','nationality','religion','address','guardian_name','guardian_phone','enrollment_date'];rows=[[i]+[r[k] or '' for k in keys] for i,r in enumerate(students,1)]
  return headers,rows
 def enrollment_statistics(self):
  win=tk.Toplevel(self);win.title('إحصاءات القيد حسب الصف والفصل');win.geometry('850x570');win.transient(self)
  top=tk.Frame(win);top.pack(fill='x',padx=12,pady=10)
  tk.Label(top,text='العام الدراسي:',font=('Tahoma',10,'bold')).pack(side='right')
  year=tk.StringVar(value='2026/2027');ttk.Entry(top,textvariable=year,width=14,justify='center').pack(side='right',padx=7)
  tree=ttk.Treeview(win,columns=('grade','class','total','active','absent','left'),show='headings')
  for c,h,w in [('grade','الصف',150),('class','الفصل',130),('total','الإجمالي',110),('active','مقيد',110),('absent','منقطع',110),('left','ترك المدرسة',130)]:tree.heading(c,text=h);tree.column(c,width=w,anchor='center')
  tree.pack(fill='both',expand=True,padx=12,pady=8)
  summary=tk.StringVar();tk.Label(win,textvariable=summary,font=('Tahoma',11,'bold'),justify='right').pack(anchor='e',padx=18,pady=8)
  def load():
   tree.delete(*tree.get_children());data=self.store.enrollment_summary(year.get().strip(),self.rep_grade.get(),self.rep_class.get())
   for (g,c),b in data['حسب الفصل'].items():tree.insert('','end',values=(g,c,b['إجمالي'],b['مقيد'],b['منقطع'],b['ترك المدرسة']))
   summary.set(f"الإجمالي: {data['إجمالي الطلاب']}   |   مقيد: {data['مقيد']}   |   منقطع: {data['منقطع']}   |   ترك المدرسة: {data['ترك المدرسة']}   |   غير محدد: {data['غير محدد']}")
  ttk.Button(top,text='تحديث الإحصاءات',command=load).pack(side='right',padx=8);load()
 def generate_report(self):
  import html
  headers,rows=self.report_data();school=self.store.db.execute("SELECT value FROM school WHERE key='school_name'").fetchone();schoolname=school[0] if school else 'اسم المدرسة'
  table='<table><thead><tr>'+''.join('<th>'+html.escape(str(x))+'</th>' for x in headers)+'</tr></thead><tbody>'
  for row in rows:table+='<tr>'+''.join('<td>'+html.escape(str(x or ''))+'</td>' for x in row)+'</tr>'
  table+='</tbody></table>'
  page="""<!doctype html><html lang='ar' dir='rtl'><meta charset='utf-8'><title>تقرير مدرسي</title><style>body{font-family:Tahoma,Arial;margin:24px;color:#182b40}h2{text-align:center}p{text-align:center}.meta{display:flex;justify-content:space-between}table{border-collapse:collapse;width:100%;font-size:12px}th,td{border:1px solid #60758a;padding:7px;text-align:center}th{background:#dce8f3}tr:nth-child(even){background:#f4f7fa}.print{padding:9px 18px;background:#16466e;color:white;border:0;border-radius:5px}@media print{.print{display:none}body{margin:8mm}table{font-size:9px}}</style><body><button class='print' onclick='window.print()'>طباعة التقرير</button><h2>"""+html.escape(schoolname)+'</h2><p>'+html.escape(self.report_type.get())+' — العام الدراسي 2026 / 2027</p><div class="meta"><span>تاريخ الاستخراج: '+date.today().isoformat()+'</span><span>عدد السجلات: '+str(len(rows))+'</span></div>'+table+'</body></html>' 
  out=BASE/('report_preview.html');out.write_text(page,encoding='utf-8');webbrowser.open(out.as_uri());self.status.set(f'تم تجهيز التقرير: {len(rows)} سجل')
 def export_report(self):
  path=filedialog.asksaveasfilename(defaultextension='.xlsx',filetypes=[('Excel','*.xlsx')],initialfile='تقرير_مدرسي.xlsx')
  if not path:return
  try:
   from openpyxl import Workbook
   from openpyxl.styles import Font,PatternFill,Alignment
   h,rows=self.report_data();wb=Workbook();ws=wb.active;ws.title='التقرير';ws.sheet_view.rightToLeft=True;ws.append(h)
   for c in ws[1]:c.font=Font(bold=True,color='FFFFFF');c.fill=PatternFill('solid',fgColor='173D63');c.alignment=Alignment(horizontal='center',wrap_text=True)
   for r in rows:ws.append(r)
   ws.freeze_panes='A2';ws.auto_filter.ref=ws.dimensions
   for col in ws.columns:ws.column_dimensions[col[0].column_letter].width=min(32,max(14,max(len(str(c.value or '')) for c in col)+2))
   wb.save(path);messagebox.showinfo('تم','تم تصدير التقرير بنجاح')
  except Exception as e:messagebox.showerror('خطأ',str(e))

 def quit_app(self): self.store.close(); self.destroy()

if __name__=='__main__':
 try: App().mainloop()
 except Exception as e:
  try: messagebox.showerror('خطأ في التشغيل',str(e))
  except: print(e)
