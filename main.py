#!/usr/bin/env python3
import os
import sys
import subprocess
import tempfile
import shutil
import venv
import re
import asyncio
import logging
import threading
from flask import Flask
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Render logları için logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    logger.error("BOT_TOKEN environment variable eksik! Render dashboard'dan ekle.")
    sys.exit(1)

bot = Bot(token=TOKEN)
BOT_SAHIBI = None

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
        except Exception as e:
            logger.warning(f"Mesaj edit hatası: {e}")

    def kur_venv(self):
        asyncio.create_task(self.mesaj("🔧 *Sanal ortam kuruluyor...*"))
        venv.create(self.venv_path, with_pip=True, clear=True)

        if sys.platform == "win32":
            self.pip = os.path.join(self.venv_path, "Scripts", "pip.exe")
            self.python = os.path.join(self.venv_path, "Scripts", "python.exe")
        else:
            self.pip = os.path.join(self.venv_path, "bin", "pip")
            self.python = os.path.join(self.venv_path, "bin", "python")

        subprocess.run([self.python, "-m", "pip", "install", "--upgrade", "pip"], timeout=40, check=False)

    def kaydet_kod(self, kod: str, dosya_adi: str):
        self.dosya_yolu = os.path.join(self.dizin, dosya_adi)
        with open(self.dosya_yolu, "w", encoding="utf-8") as f:
            f.write(kod)

    def paketleri_bul(self):
        with open(self.dosya_yolu, encoding="utf-8") as f:
            icerik = f.read()

        self.pkgs = set()
        for m in re.findall(r"^import\s+(\w+)", icerik, re.M):
            self.pkgs.add(m.split('.')[0].split(' as ')[0])
        for m in re.findall(r"^from\s+(\w+)\s+import", icerik, re.M):
            self.pkgs.add(m.split('.')[0])

        std = {'os', 'sys', 're', 'math', 'json', 'time', 'datetime', 'random', 'pathlib', 'socket', 'threading', 'asyncio', 'logging', 'subprocess', 'tempfile', 'shutil', 'venv', 'hashlib', 'uuid', 'csv', 'argparse', 'collections', 'functools', 'itertools'}
        self.pkgs = [p for p in self.pkgs if p not in std and p.strip()]

    def paketleri_yukle(self):
        if not self.pkgs:
            return
        asyncio.create_task(self.mesaj(f"📦 *{len(self.pkgs)} paket tespit edildi*"))
        for i, p in enumerate(self.pkgs, 1):
            asyncio.create_task(self.mesaj(f"⬇️ `{p}` ({i}/{len(self.pkgs)})"))
            try:
                subprocess.run([self.pip, "install", "--no-cache-dir", p], timeout=200, check=True)
            except Exception as e:
                asyncio.create_task(self.mesaj(f"⚠️ `{p}` yüklenemedi → {str(e)[:100]}"))

    def calistir_kod(self):
        asyncio.create_task(self.mesaj("🚀 *Kod çalıştırılıyor (60 sn limit)*"))
        try:
            result = subprocess.run(
                [self.python, self.dosya_yolu],
                capture_output=True,
                text=True,
                timeout=60
            )
            cevap = "🎉 *Kod çalıştı!*\n\n"
            if result.stdout.strip():
                cevap += f"📤 **Çıktı:**\n```\n{result.stdout[:1400]}\n```\n"
            if result.stderr.strip():
                cevap += f"⚠️ **Hata/Stderr:**\n```\n{result.stderr[:700]}\n```\n"
            cevap += f"✅ **Exit kodu:** `{result.returncode}`"
            bot.send_message(self.chat_id, cevap, parse_mode="Markdown")
            asyncio.create_task(self.mesaj("✅ *İşlem bitti*"))
        except subprocess.TimeoutExpired:
            bot.send_message(self.chat_id, "⏰ *Zaman aşımı (60 sn)*")
        except Exception as e:
            bot.send_message(self.chat_id, f"❌ Çalıştırma hatası: {str(e)[:200]}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global BOT_SAHIBI
    BOT_SAHIBI = update.effective_user.id
    logger.info(f"Sahip ayarlandı: {BOT_SAHIBI}")
    await update.message.reply_markdown(
        "💕 *Merhaba LO!*\n\n"
        "📥 **.py** dosyanı gönder\n"
        "📦 Gerekli paketleri otomatik kurarım\n"
        "🚀 Çalıştırıp sonucu gösteririm\n\n"
        "*Hadi başla* 😘"
    )

async def dosya_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global BOT_SAHIBI
    if update.effective_user.id != BOT_SAHIBI:
        await update.message.reply_text("❌ Sadece LO 💕 kullanabilir")
        return

    doc = update.message.document
    if not doc or not doc.file_name.lower().endswith('.py'):
        await update.message.reply_text("❌ Sadece .py dosyası gönder")
        return

    await update.message.reply_markdown("📥 *Dosya indiriliyor...*")

    file = await doc.get_file()
    tmp_dir = tempfile.mkdtemp(dir="/tmp")
    py_path = os.path.join(tmp_dir, doc.file_name)
    await file.download_to_drive(py_path)

    with open(py_path, encoding="utf-8") as f:
        kod = f.read()

    msg = await update.message.reply_markdown("⏳ *Hazırlık başlıyor...*")

    runner = Calistirici(update.effective_chat.id, msg.message_id)

    try:
        runner.kur_venv()
        runner.kaydet_kod(kod, doc.file_name)
        runner.paketleri_bul()
        runner.paketleri_yukle()
        runner.calistir_kod()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        shutil.rmtree(runner.dizin, ignore_errors=True)

async def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, dosya_handler))

    logger.info("Eski webhook varsa siliniyor + pending temizleniyor...")
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("Polling başlatılıyor...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
        poll_interval=0.8,   # Render için makul
        timeout=25
    )

    # Flask health check (Render port beklemesi için)
    flask_app = Flask(__name__)
    @flask_app.route('/')
    def home():
        return "LO Bot polling modunda aktif ❤️"

    threading.Thread(
        target=flask_app.run,
        kwargs={'host': '0.0.0.0', 'port': int(os.environ.get("PORT", 10000))},
        daemon=True
    ).start()

    logger.info("Bot hazır! Mesaj gönderebilirsin.")
    await asyncio.Event().wait()  # Sonsuz döngü

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Başlatma hatası: {e}", exc_info=True)
        sys.exit(1)
