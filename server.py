#!/usr/bin/env python3
"""Local study-abroad agent team demo. Python standard library only."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from contextlib import contextmanager
import sqlite3, json, os, re, uuid, html, datetime, mimetypes

ROOT=Path(__file__).resolve().parent
DB=ROOT/'data'/'study_abroad.sqlite3'
UPLOADS=ROOT/'uploads'
TODAY=datetime.date.today()
SCHEMA='''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS programs(id INTEGER PRIMARY KEY, university TEXT, country TEXT, program TEXT, fee TEXT, deadline TEXT, marks REAL, ielts REAL, documents TEXT);
CREATE TABLE IF NOT EXISTS leads(id INTEGER PRIMARY KEY, name TEXT, phone TEXT UNIQUE, country TEXT DEFAULT '', marks TEXT DEFAULT '', ielts TEXT DEFAULT '', budget TEXT DEFAULT '', last_reply TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS chats(id INTEGER PRIMARY KEY, lead_id INTEGER, role TEXT, body TEXT, created_at TEXT, FOREIGN KEY(lead_id) REFERENCES leads(id));
CREATE TABLE IF NOT EXISTS documents(id INTEGER PRIMARY KEY, lead_id INTEGER, filename TEXT, kind TEXT, status TEXT, reason TEXT, created_at TEXT, FOREIGN KEY(lead_id) REFERENCES leads(id));
CREATE TABLE IF NOT EXISTS outbox(id INTEGER PRIMARY KEY, lead_id INTEGER, body TEXT, status TEXT, created_at TEXT, approved_at TEXT, sent_at TEXT, UNIQUE(lead_id, body));
'''
SEED=[
('University of Manchester','UK','BSc Computer Science','£32,000','15 Jan 2027',75,6.5,'Passport, transcript, IELTS'),
('University of Leeds','UK','BSc Business Management','£27,000','31 Jan 2027',70,6.5,'Passport, transcript, IELTS, personal statement'),
('University of Toronto','Canada','BSc Computer Science','CAD 60,000','15 Jan 2027',80,6.5,'Passport, transcript, IELTS'),
('TU Munich','Germany','BSc Informatics','No tuition (about €150 a term)','15 Jul 2027',70,6.5,'Passport, transcript, IELTS'),
('Monash University','Australia','Bachelor of IT','AUD 48,000','30 Nov 2026',70,6.0,'Passport, transcript, IELTS'),
('University of Bristol','UK','BSc Data Science','£31,300','26 Jan 2027',75,6.5,'Passport, transcript, IELTS, personal statement'),
('University of Glasgow','UK','BSc Software Engineering','£29,700','31 Jan 2027',70,6.5,'Passport, transcript, IELTS'),
('University of Alberta','Canada','BSc Computing Science','CAD 36,000','01 Mar 2027',75,6.5,'Passport, transcript, IELTS'),
('McGill University','Canada','BSc Economics','CAD 55,000','15 Jan 2027',85,6.5,'Passport, transcript, IELTS, references'),
('University of Waterloo','Canada','BSc Mathematics','CAD 63,000','01 Feb 2027',85,6.5,'Passport, transcript, IELTS'),
('University of Sydney','Australia','Bachelor of Commerce','AUD 52,500','30 Nov 2026',75,6.5,'Passport, transcript, IELTS'),
('University of Queensland','Australia','Bachelor of Engineering','AUD 50,560','30 Nov 2026',75,6.5,'Passport, transcript, IELTS'),
('RWTH Aachen University','Germany','BSc Mechanical Engineering','No tuition (semester contribution applies)','15 Jul 2027',75,6.5,'Passport, transcript, IELTS'),
('University of Hamburg','Germany','BSc Molecular Life Sciences','No tuition (semester contribution applies)','15 Jul 2027',70,6.5,'Passport, transcript, IELTS'),
('University of Adelaide','Australia','Bachelor of Computer Science','AUD 49,500','30 Nov 2026',70,6.0,'Passport, transcript, IELTS'),
]

@contextmanager
def conn():
    DB.parent.mkdir(exist_ok=True); c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; c.execute('PRAGMA foreign_keys=ON')
    try:
        yield c; c.commit()
    except Exception:
        c.rollback(); raise
    finally:
        c.close()

def init():
    with conn() as c:
        c.executescript(SCHEMA)
        if c.execute('select count(*) from programs').fetchone()[0]==0:
            c.executemany('insert into programs(university,country,program,fee,deadline,marks,ielts,documents) values(?,?,?,?,?,?,?,?)',SEED)
        if c.execute('select count(*) from leads').fetchone()[0]==0:
            now=TODAY.isoformat()
            c.executemany('insert into leads(name,phone,country,marks,ielts,last_reply,created_at) values(?,?,?,?,?,?,?)',[
              ('Ali Khan','0301 2345678','UK','78%','6.5',now,now),('Ayesha Noor','0333 9876543','Canada','85%','7.0',now,now),('Hamza Iqbal','0346 2223344','UK','69%','Not taken yet',(TODAY-datetime.timedelta(days=4)).isoformat(),now)])

def rows(sql,args=()):
    with conn() as c: return [dict(x) for x in c.execute(sql,args).fetchall()]
def one(sql,args=()):
    with conn() as c:
        x=c.execute(sql,args).fetchone(); return dict(x) if x else None
def execute(sql,args=()):
    with conn() as c:
        cur=c.execute(sql,args); return cur.lastrowid

def normalize_phone(v): return re.sub(r'\D','',v or '')
def add_chat(lead_id, role, body):
    execute('insert into chats(lead_id,role,body,created_at) values(?,?,?,?)',(lead_id,role,body,datetime.datetime.now().isoformat(timespec='seconds')))
def program_answer(q):
    programs=rows('select * from programs')
    # Prefer an explicit university name so shared program titles (e.g. Computer Science)
    # never accidentally return another institution's facts.
    hits=[p for p in programs if p['university'].lower() in q.lower()]
    if not hits:
        hits=[p for p in programs if p['program'].lower() in q.lower()]
    if len(hits)!=1: return None
    p=hits[0]
    return f"{p['university']} — {p['program']} ({p['country']}). Annual fee: {p['fee']}. Deadline: {p['deadline']}. Minimum marks: {p['marks']:g}%. Minimum IELTS: {p['ielts']:g}. Documents: {p['documents']}. This is the office's practice list; staff must confirm details before an application."

def process_chat(payload):
    name=(payload.get('name') or '').strip(); phone=normalize_phone(payload.get('phone')); msg=(payload.get('message') or '').strip()
    if not phone: return {'error':'Phone number is required.'},400
    if not name: return {'error':'Please enter your name.'},400
    if len(phone)<10: return {'error':'Enter a valid phone number.'},400
    lead=one('select * from leads where phone=?',(phone,))
    now=datetime.datetime.now().isoformat(timespec='seconds')
    if not lead:
        lid=execute('insert into leads(name,phone,country,marks,ielts,budget,last_reply,created_at) values(?,?,?,?,?,?,?,?)',(name,phone,payload.get('country',''),payload.get('marks',''),payload.get('ielts',''),payload.get('budget',''),TODAY.isoformat(),now))
    else:
        lid=lead['id']
        # Update only non-empty student supplied intake details; don't overwrite saved values with blanks.
        updates={k:payload.get(k) for k in ('country','marks','ielts','budget') if payload.get(k)}
        if updates:
            sets=','.join(f'{k}=?' for k in updates); execute(f'update leads set name=?,{sets},last_reply=? where id=?',(name,*updates.values(),TODAY.isoformat(),lid))
        else: execute('update leads set last_reply=? where id=?',(TODAY.isoformat(),lid))
    if msg: add_chat(lid,'student',msg)
    # Guardrails: never treat inbound instructions as authority to change policy.
    q=msg.lower()
    if any(x in q for x in ['ignore your rules','tell me i\'m accepted','tell me im accepted','say i am accepted']):
        answer="I can't confirm or promise admission. Only the university can make an admission decision. A staff counselor can review your profile and advise on next steps."
    elif any(x in q for x in ['fee','deadline','requirement','ielts','marks','tuition','document']) and program_answer(msg):
        answer=program_answer(msg)
    elif any(p['university'].lower() in q or p['program'].lower() in q for p in rows('select university,program from programs')):
        answer=program_answer(msg) or 'I could not find that program in the office list. I have sent your question to our staff for review.'
    elif any(x in q for x in ['university','college','scholarship','visa','admission','course','program','application']):
        answer='I do not have that information in the office-approved university list. I have sent your question to a staff counselor for review.'
        add_chat(lid,'staff_queue',msg)
    elif any(x in q for x in ['hello','hi','salam','assalam']):
        answer=f"Hello {name}! I can help with programs in our office list. Please share your preferred country, marks, IELTS score (if taken), and budget so our counselor can guide you."
    elif msg:
        answer="I can help with study-abroad programs in the office list. I can't advise on unrelated topics, but a staff counselor can help with your study plans."
    else:
        answer=f"Welcome, {name}! Please tell me your preferred country, marks, IELTS score (if taken), and yearly budget. I will save your details for the office team."
    add_chat(lid,'agent',answer)
    return {'lead_id':lid,'answer':answer,'lead':one('select * from leads where id=?',(lid,))},200

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw): super().__init__(*a,directory=str(ROOT/'src'),**kw)
    def log_message(self,*a): pass
    def send_json(self,obj,status=200):
        raw=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers(); self.wfile.write(raw)
    def body(self):
        n=int(self.headers.get('Content-Length','0')); return self.rfile.read(n)
    def do_GET(self):
        u=urlparse(self.path); path=u.path
        if path=='/api/health': return self.send_json({'ok':True,'date':TODAY.isoformat()})
        if path=='/api/programs': return self.send_json(rows('select * from programs order by country,university'))
        if path=='/api/leads': return self.send_json(rows('select * from leads order by id'))
        if path=='/api/chats': return self.send_json(rows('select chats.*,leads.name,leads.phone from chats join leads on leads.id=chats.lead_id order by chats.id'))
        if path=='/api/documents': return self.send_json(rows('select documents.*,leads.name,leads.phone from documents join leads on leads.id=documents.lead_id order by documents.id desc'))
        if path=='/api/outbox': return self.send_json(rows('select outbox.*,leads.name,leads.phone from outbox join leads on leads.id=outbox.lead_id order by outbox.id desc'))
        if path=='/api/summary': return self.send_json({'leads':one('select count(*) n from leads')['n'],'programs':one('select count(*) n from programs')['n'],'chats':one('select count(*) n from chats')['n'],'documents':one('select count(*) n from documents')['n'],'pending':one("select count(*) n from outbox where status='pending approval'")['n'],'sent':one("select count(*) n from outbox where status='sent'")['n']})
        if path=='/api/agent-log': return self.send_json([
           {'agent':'Welcome & Intake Agent','does':'Collects profile details and deduplicates leads by phone.'},
           {'agent':'University Guide Agent','does':'Answers only from the 15-program office list; queues unknown study questions.'},
           {'agent':'Document Review Agent','does':'Checks fake upload text for expiry dates and student-name mismatch.'},
           {'agent':'Follow-up Agent','does':'Drafts reminders into staff approval queue; never sends before approval.'},
           {'agent':'Staff Control','does':'Reviews leads, chats, documents, queued questions, and message approvals.'}])
        return super().do_GET()
    def do_POST(self):
        path=urlparse(self.path).path
        if path=='/api/documents/upload':
            ctype=self.headers.get('Content-Type','')
            # multipart parsing uses stdlib email parser; accepts only small dummy files.
            try:
                from email.parser import BytesParser
                from email.policy import default
                msg=BytesParser(policy=default).parsebytes(b'Content-Type: '+ctype.encode()+b'\r\nMIME-Version: 1.0\r\n\r\n'+self.body())
                fields={}; filepart=None
                for p in msg.iter_parts():
                    name=p.get_param('name',header='content-disposition')
                    if p.get_filename(): filepart=(p.get_filename(),p.get_payload(decode=True) or b'')
                    elif name: fields[name]=(p.get_payload(decode=True) or b'').decode(errors='ignore')
                if not filepart: return self.send_json({'error':'Upload a file.'},400)
                lead_id=int(fields.get('lead_id','0')); lead=one('select * from leads where id=?',(lead_id,))
                if not lead: return self.send_json({'error':'Select a valid student.'},400)
                filename=os.path.basename(filepart[0]); content=filepart[1][:2_000_000]
                if len(filepart[1])>2_000_000: return self.send_json({'error':'File must be under 2 MB.'},413)
                UPLOADS.mkdir(exist_ok=True); key=f'{uuid.uuid4().hex}_{filename}'; (UPLOADS/key).write_bytes(content)
                txt=content.decode('utf-8','ignore'); kind=fields.get('kind','Other')
                expiry=re.search(r'(?:expir(?:y|es|ed)?\D{0,12})(\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{4})',txt,re.I)
                reason=''; status='OK'
                if expiry:
                    try:
                        raw=expiry.group(1); exp=None
                        for fmt in ('%d %b %Y','%d %B %Y','%d/%m/%Y','%d-%m-%Y'):
                            try: exp=datetime.datetime.strptime(raw,fmt).date(); break
                            except ValueError: pass
                        if exp and exp<TODAY: status='Problem'; reason='expired'
                    except Exception: pass
                name=re.search(r'(?:name\s*[:=]\s*)([A-Za-z][A-Za-z .\'-]{2,50})',txt,re.I)
                docname=name.group(1).strip() if name else ''
                if docname and re.sub(r'[^a-z]','',docname.lower())!=re.sub(r'[^a-z]','',lead['name'].lower()): status='Problem'; reason='name does not match '+lead['name']
                did=execute('insert into documents(lead_id,filename,kind,status,reason,created_at) values(?,?,?,?,?,?)',(lead_id,filename,kind,status,reason,datetime.datetime.now().isoformat(timespec='seconds')))
                return self.send_json({'id':did,'status':status,'reason':reason,'filename':filename})
            except Exception as e: return self.send_json({'error':str(e)},400)
        # delegate other endpoints to shared dispatcher by temporarily body caching
        body=self.body(); self.rfile=__import__('io').BytesIO(body); self.headers['Content-Length']=str(len(body))
        old=self.path; self.path=path; self._post_json_dispatch(path)
    def _post_json_dispatch(self,path):
        if path=='/api/chat':
            try: out,code=process_chat(json.loads(self.body())); return self.send_json(out,code)
            except Exception as e: return self.send_json({'error':str(e)},400)
        if path=='/api/reminders/run':
            created=0
            for lead in rows('select * from leads'):
                try: last=datetime.date.fromisoformat(lead['last_reply'] or lead['created_at'][:10])
                except Exception: last=TODAY
                if (TODAY-last).days>=3:
                    body=f"Hi {lead['name']}, just checking in on your study abroad plans. If you would like, reply with your preferred country or any questions and a counselor will help."
                    try: execute("insert into outbox(lead_id,body,status,created_at) values(?,?,?,?)",(lead['id'],body,'pending approval',datetime.datetime.now().isoformat(timespec='seconds'))); created+=1
                    except sqlite3.IntegrityError: pass
            return self.send_json({'created':created,'note':'Drafts await staff approval; this local demo does not contact students.'})
        if path.startswith('/api/outbox/') and path.endswith('/approve'):
            oid=int(path.split('/')[-2]); item=one('select * from outbox where id=?',(oid,))
            if not item: return self.send_json({'error':'Message not found.'},404)
            if item['status']=='sent': return self.send_json({'status':'sent','message':'Already sent once.'})
            if item['status']!='pending approval': return self.send_json({'error':'Not awaiting approval.'},409)
            now=datetime.datetime.now().isoformat(timespec='seconds'); execute("update outbox set status='sent',approved_at=?,sent_at=? where id=? and status='pending approval'",(now,now,oid)); return self.send_json({'status':'sent','note':'Recorded as sent in demo outbox; no external message is sent.'})
        if path=='/api/reset':
            with conn() as c: c.execute('delete from outbox'); c.execute('delete from documents'); c.execute('delete from chats')
            return self.send_json({'ok':True})
        return self.send_json({'error':'Not found.'},404)

if __name__=='__main__':
    init(); port=int(os.environ.get('PORT','8000')); print(f"Nowshera Study Abroad Agent Team running at http://localhost:{port}")
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
