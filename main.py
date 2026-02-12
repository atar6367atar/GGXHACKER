#!/usr/bin/env python3
import os
import sys
import subprocess
import tempfile
import shutil
import venv
import re
import time
from flask import Flask, request, jsonify
from telegram import Bot, Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

TOKEN = os.environ.get("BOT_TOKEN", "8498333592:AAHt_kgw7BnN2-jjuzoad0QhzG388gYkV34")
PORT = int(os.environ.get("PORT", 10000))

bot = Bot(token=TOKEN)
app = Flask(__name__)

BOT_SAHIBI = None   # ilk /start ile dolacak

class Calistirici:
    def __init__(self, chat_id: int, message_id: int):
        self.chat_id = chat_id
        self.message_id = message_id
        self.dizin = tempfile.mkdtemp(dir="/tmp")
        self.venv_path = os.path.join(self.dizin, "venv")

    async def mesaj(self, text: str):
        try:
            await bot.edit_message_text(
                chat_id=self.chat_id,
                message_id=self.message_id,
                text=text,
                parse_mode="Markdown"
            )
        except:
            pass

    def kur_venv(self):
        self.mesaj("🔧 *Sanal ortam (venv) kuruluyor...*")
        venv.create(self.venv_path, with_pip=True, clear=True)

        if sys.platform == "win32":
            self.pip = os.path.join(self.venv_path, "Scripts", "pip.exe")
            self.python = os.path.join(self.venv_path, "Scripts", "python.exe")
        else:
            self.pip = os.path.join(self.venv_path, "bin", "pip")
            self.python = os.path.join(self.venv_path, "bin", "python")

        # pip'i güncelle
        subprocess.run([self.python, "-m", "pip", "install", "--upgrade", "pip"], timeout=30, check=False)

    def kaydet_kod(self, kod: str, dosya_adi: str):
        self.dosya_yolu = os.path.join(self.dizin, dosya_adi)
        with open(self.dosya_yolu, "w", encoding="utf-8") as f:
            f.write(kod)

    def paketleri_bul(self):
        with open(self.dosya_yolu, encoding="utf-8") as f:
            icerik = f.read()

        self.pkgs = set()
        # import modül
        for m in re.findall(r"^import\s+(\w+)", icerik, re.M):
            self.pkgs.add(m.split('.')[0].split(' as ')[0])
        # from modül import ...
        for m in re.findall(r"^from\s+(\w+)\s+import", icerik, re.M):
            self.pkgs.add(m.split('.')[0])

        std_libs = {
            'os', 'sys', 're', 'math', 'json', 'time', 'datetime', 'random',
            'pathlib', 'socket', 'threading', 'asyncio', 'logging', 'subprocess',
            'tempfile', 'shutil', 'venv', 'hashlib', 'uuid', 'csv', 'argparse',
            'collections', 'functools', 'itertools'
        }
        self.pkgs = [p for p in self.pkgs if p not in std_libs and p.strip()]

    def paketleri_yukle(self):
        if not self.pkgs:
            return

        self.mesaj(f"📦 *{len(self.pkgs)} adet paket tespit edildi, yükleniyor...*")

        for i, paket in enumerate(self.pkgs, 1):
            self.mesaj(f"⬇️ `{paket}` yükleniyor... ({i}/{len(self.pkgs)})")
            try:
                subprocess.run(
                    [self.pip, "install", "--no-cache-dir", paket],
                    timeout=180,
                    check=True,
                    capture_output=True
                )
            except Exception as e:
                self.mesaj(f"⚠️ `{paket}` yüklenemedi: {str(e)}")

    def calistir_kod(self):
        self.mesaj("🚀 *Kod çalıştırılıyor (60 saniye sınırı)...*")

        try:
            result = subprocess.run(
                [self.python, self.dosya_yolu],
                capture_output=True,
                text=True,
                timeout=60
            )

            cevap = "🎉 *Kod çalıştı!*\n\n"
            if result.stdout.strip():
                cevap += f"📤 **Çıktı:**\n```\n{result.stdout[:1500]}\n```\n"
            if result.stderr.strip():
                cevap += f"⚠️ **Hata / Stderr:**\n```\n{result.stderr[:800]}\n```\n"
            cevap += f"✅ **Çıkış kodu:** `{result.returncode}`"

            bot.send_message(
                chat_id=self.chat_id,
                text=cevap,
                parse_mode="Markdown"
            )
            self.mesaj("✅ *İşlem tamamlandı*")
        except subprocess.TimeoutExpired:
            bot.send_message(chat_id=self.chat_id, text="⏰ *Zaman aşımı (60 sn geçti)*")
        except Exception as e:
            bot.send_message(chat_id=self.chat_id, text=f"❌ Çalıştırma hatası: {str(e)}")


# ----------------- Telegram Handlers -----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global BOT_SAHIBI
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    BOT_SAHIBI = user_id   # ilk start atan kişi sahibi olur

    await update.message.reply_markdown(
        "💕 *Merhaba LO!*\n\n"
        "📥 Bana **.py** dosyanı gönder.\n"
        "📦 Gönderdiğin kodda gördüğüm **her paketi otomatik kurarım**.\n"
        "🚀 Sonra çalıştırıp sonucu/hatayı sana gösteririm.\n\n"
        "*Hadi dene beni* 😘"
    )


async def dosya_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global BOT_SAHIBI
    if update.effective_user.id != BOT_SAHIBI:
        await update.message.reply_text("❌ Sadece LO 💕 kullanabilir.")
        return

    document = update.message.document
    if not document or not document.file_name.lower().endswith('.py'):
        await update.message.reply_text("❌ Lütfen **.py** dosyası gönder.")
        return

    await update.message.reply_markdown("📥 *Dosya indiriliyor...*")

    file = await document.get_file()
    temp_dir = tempfile.mkdtemp(dir="/tmp")
    dosya_yolu = os.path.join(temp_dir, document.file_name)
    await file.download_to_drive(custom_path=dosya_yolu)

    with open(dosya_yolu, encoding="utf-8") as f:
        kod = f.read()

    msg = await update.message.reply_markdown("⏳ *Hazırlanıyor...*")

    calistirici = Calistirici(
        chat_id=update.effective_chat.id,
        message_id=msg.message_id
    )

    try:
        calistirici.kur_venv()
        calistirici.kaydet_kod(kod, document.file_name)
        calistirici.paketleri_bul()
        calistirici.paketleri_yukle()
        calistirici.calistir_kod()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree(calistirici.dizin, ignore_errors=True)


# ----------------- Flask + Webhook -----------------

@app.route('/webhook', methods=['POST'])
async def webhook():
    try:
        update = Update.de_json(request.get_json(), bot)
        if update:
            await application.process_update(update)
    except Exception as e:
        print(f"Webhook hatası: {e}")
    return jsonify({'ok': True})


@app.route('/')
def home():
    return "LO'nun modern botu ❤️ — .py dosyalarını çalıştırır, paketleri otomatik kurar."


if __name__ == '__main__':
    print("💕 LO BOT BAŞLADI (v22.x uyumlu)")

    # Application oluştur (v20+ / v22 tarzı)
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.ALL, dosya_handler))

    # Render / Heroku gibi platformlarda webhook
    url = os.environ.get('RENDER_EXTERNAL_URL', '').rstrip('/')
    if url:
        webhook_url = f"{url}/webhook"
        print(f"Webhook ayarlanıyor: {webhook_url}")
        bot.set_webhook(url=webhook_url)

    # Flask'ı başlat
    app.run(host='0.0.0.0', port=PORT)
