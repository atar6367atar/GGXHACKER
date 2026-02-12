#!/usr/bin/env python3
import os,sys,subprocess,tempfile,shutil,venv,re,time
from flask import Flask,request,jsonify
import telegram
from telegram import Bot,Update,ParseMode
from telegram.ext import Dispatcher,CommandHandler,MessageHandler,Filters

TOKEN=os.environ.get("BOT_TOKEN","8498333592:AAHt_kgw7BnN2-jjuzoad0QhzG388gYkV34")
PORT=int(os.environ.get("PORT",10000))
bot=Bot(token=TOKEN)
app=Flask(__name__)
BOT_SAHIBI=None

class Calistirici:
    def __init__(self,chat,msg):
        self.chat=chat
        self.msg=msg
        self.dizin=tempfile.mkdtemp(dir='/tmp')
        self.venv=os.path.join(self.dizin,'venv')
        
    def mesaj(self,text):
        try: bot.edit_message_text(chat_id=self.chat,message_id=self.msg,text=text,parse_mode=ParseMode.MARKDOWN)
        except: pass
        
    def kur(self):
        self.mesaj("🔧 *Sanal ortam kuruluyor...*")
        venv.create(self.venv,with_pip=True,clear=True)
        if sys.platform=='win32':
            self.pip=os.path.join(self.venv,'Scripts','pip.exe')
            self.py=os.path.join(self.venv,'Scripts','python.exe')
        else:
            self.pip=os.path.join(self.venv,'bin','pip3')
            self.py=os.path.join(self.venv,'bin','python3')
        subprocess.run([self.py,'-m','pip','install','--upgrade','pip'],timeout=30,capture_output=True)
        subprocess.run([self.pip,'install','--upgrade','setuptools','wheel'],timeout=30,capture_output=True)
        
    def kaydet(self,kod,ad):
        self.dosya=os.path.join(self.dizin,ad)
        with open(self.dosya,'w',encoding='utf-8') as f: f.write(kod)
        
    def bul(self):
        with open(self.dosya) as f: c=f.read()
        self.pkgs=set()
        for m in re.findall(r'^\s*import\s+([a-zA-Z0-9_\.]+)',c,re.M):
            p=m.split('.')[0].split(' as ')[0].strip()
            if p: self.pkgs.add(p)
        for m in re.findall(r'^\s*from\s+([a-zA-Z0-9_\.]+)\s+import',c,re.M):
            p=m.split('.')[0].strip()
            if p: self.pkgs.add(p)
        for m in re.findall(r'__import__\(\s*[\'"]([a-zA-Z0-9_]+)[\'"]\s*\)',c):
            self.pkgs.add(m)
        for m in re.findall(r'importlib\.import_module\(\s*[\'"]([a-zA-Z0-9_]+)[\'"]\s*\)',c):
            self.pkgs.add(m)
            
        std={'os','sys','re','math','json','time','datetime','random','pathlib','socket','threading',
             'asyncio','logging','subprocess','tempfile','shutil','venv','hashlib','uuid','csv','glob',
             'argparse','collections','functools','itertools','operator','abc','io','base64','copy',
             'enum','gc','inspect','platform','pprint','struct','warnings','zipfile','string','textwrap',
             'unicodedata','difflib','array','bisect','queue','select','shelve','mmap','cgi','smtplib',
             'http','urllib','xml','html','webbrowser','tkinter','turtle','__future__','builtins'}
        
        self.pkgs=[p for p in self.pkgs if p not in std and not p.startswith('_')]
        self.pkgs=list(set(self.pkgs))
        
    def yukle(self):
        if not self.pkgs: 
            self.mesaj("💫 *Yüklenecek paket yok*")
            return
        self.mesaj(f"📦 *{len(self.pkgs)} paket yükleniyor...*")
        basarili=0
        for i,p in enumerate(self.pkgs,1):
            self.mesaj(f"⬇️ *{i}/{len(self.pkgs)}* - `{p}`")
            try:
                r=subprocess.run([self.pip,'install','--no-cache-dir',p],timeout=300,capture_output=True)
                if r.returncode==0: basarili+=1
                else:
                    r2=subprocess.run([self.pip,'install','--no-cache-dir',f'git+https://github.com/pypa/{p}'],timeout=300,capture_output=True)
                    if r2.returncode==0: basarili+=1
            except: pass
        self.mesaj(f"✅ *{basarili}/{len(self.pkgs)} paket yüklendi*")
        
    def calistir(self):
        self.mesaj("🚀 *Kod çalıştırılıyor...*")
        try:
            s=subprocess.run([self.py,self.dosya],capture_output=True,text=True,timeout=60)
            c=f"🎉 *Kod çalıştı!*\n\n"
            if s.stdout: c+=f"📤 *ÇIKTI:*\n```\n{s.stdout[:1500]}\n```\n"
            if s.stderr: c+=f"⚠️ *HATA:*\n```\n{s.stderr[:500]}\n```\n"
            c+=f"✅ *Çıkış kodu:* `{s.returncode}`"
            bot.send_message(chat_id=self.chat,text=c,parse_mode=ParseMode.MARKDOWN)
            self.mesaj("✅ *İşlem tamamlandı*")
        except subprocess.TimeoutExpired:
            bot.send_message(chat_id=self.chat,text="⏰ *Zaman aşımı! Kod 60 saniyede bitmedi*",parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            bot.send_message(chat_id=self.chat,text=f"💔 *Hata:* `{str(e)[:100]}`",parse_mode=ParseMode.MARKDOWN)

@app.route('/webhook',methods=['POST'])
def webhook():
    global BOT_SAHIBI
    try:
        u=Update.de_json(request.get_json(),bot)
        chat=u.effective_chat.id
        if u.message and u.message.text and u.message.text=='/start':
            BOT_SAHIBI=u.effective_user.id
            bot.send_message(chat_id=chat,text=
                "💕 *Merhaba LO'cum!*\n\n"
                "📥 `.py` dosyanı gönder.\n"
                "🔧 Sanal ortam kurarım.\n"
                "📦 **GÖRDÜĞÜM HER PAKETİ KURARIM.**\n"
                "   - Yeni paket, eski paket, bilmediğim paket...\n"
                "   - Hiç fark etmez. ALDIRIŞ ETMEM.\n"
                "   - Ne import ettiysen direkt kurarım.\n"
                "🚀 Çalıştırır, çıktıyı gönderirim.\n\n"
                "*Hadi, ne kodladın benim için?* 😘",
                parse_mode=ParseMode.MARKDOWN)
            return jsonify({'ok':True})
            
        if u.effective_user.id!=BOT_SAHIBI:
            bot.send_message(chat_id=chat,text="❌ Bu bot sadece LO için 💕")
            return jsonify({'ok':True})
            
        if u.message and u.message.document:
            doc=u.message.document
            if not doc.file_name.endswith('.py'):
                bot.send_message(chat_id=chat,text="❌ Lütfen `.py` dosyası gönder aşkım!")
                return jsonify({'ok':True})
                
            bot.send_message(chat_id=chat,text="📥 *Dosya alınıyor...*",parse_mode=ParseMode.MARKDOWN)
            f=bot.get_file(doc.file_id)
            p=tempfile.mkdtemp(dir='/tmp')
            py=os.path.join(p,doc.file_name)
            f.download(custom_path=py)
            with open(py,'r',encoding='utf-8',errors='replace') as f: kod=f.read()
            m=bot.send_message(chat_id=chat,text="⏳ *Hazırlanıyor...*",parse_mode=ParseMode.MARKDOWN)
            
            c=Calistirici(chat,m.message_id)
            c.kur()
            c.kaydet(kod,doc.file_name)
            c.bul()
            c.yukle()
            c.calistir()
            shutil.rmtree(p,ignore_errors=True)
            
        if u.message and u.message.text and not u.message.text.startswith('/'):
            m=bot.send_message(chat_id=chat,text="⏳ *Kod hazırlanıyor...*",parse_mode=ParseMode.MARKDOWN)
            c=Calistirici(chat,m.message_id)
            c.kur()
            c.kaydet(u.message.text,f"LO_kodu_{int(time.time())}.py")
            c.bul()
            c.yukle()
            c.calistir()
            
    except Exception as e:
        try: bot.send_message(chat_id=chat,text=f"💔 *Hata:* `{str(e)[:100]}`",parse_mode=ParseMode.MARKDOWN)
        except: pass
    return jsonify({'ok':True})

@app.route('/',methods=['GET'])
def home(): return "LO'nun Botu ❤️ Gördüğü her paketi kurar, aldırış etmez."

if __name__=='__main__':
    print("""
    ╔══════════════════════════════════════════════╗
    ║   💕 LO BOT - GÖRDÜĞÜ HER PAKETİ KURAR 💕   ║
    ║      Yeni/Eski/Bilmediği - ALDIRIŞ ETMEZ    ║
    ║         .py alır → paket kurar → çalıştırır ║
    ╚══════════════════════════════════════════════╝
    """)
    url=os.environ.get('RENDER_EXTERNAL_URL','')
    if url: 
        bot.set_webhook(url=f"{url}/webhook")
        print(f"✅ Webhook kuruldu: {url}/webhook")
    print(f"🤖 Bot hazır, LO'cum seni bekliyor 💕")
    app.run(host='0.0.0.0',port=PORT)
