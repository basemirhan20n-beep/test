import logging
import random
from datetime import datetime, date, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)
from database import Database
from config import BOT_TOKEN, ADMIN_IDS
from futbol import (
    cmd_takim_kur, cmd_takim, cmd_piyasa, cmd_satin_al,
    cmd_sat, cmd_sat_iptal, cmd_antrenman, cmd_mac,
    cmd_lig, cmd_son_maclar, cmd_fikstur, cmd_cuzdan,
    cmd_taktik, cmd_cark, cmd_bahis, cmd_lonca_kur,
    cmd_lonca_katil, cmd_kupa, cmd_sezon_sifirla,
    cmd_oyuncu_istatistik, cmd_altyapi,
    futbol_callback, set_group_chat_id
)
from futbol_db import FutbolDB

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

db = Database()
fdb = FutbolDB()   # futbol_db'nin de bir örneği

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    chat = update.effective_chat
    if user.id in ADMIN_IDS: return True
    veri = db.kullanici_getir(user.id)
    if veri and veri.get("role") == "Parti Başkanı": return True
    try:
        if chat and chat.type in ("group", "supergroup", "channel"):
            uye = await context.bot.get_chat_member(chat.id, user.id)
            if uye.status in ("administrator", "creator"): return True
    except: pass
    return False

MAKAMLAR = ["Parti Başkanı","Genel Sekreter","Ekonomi Başkanı","Eğitim Başkanı","Kooperatif Sorumlusu","İçişleri Sorumlusu","Parti Yöneticisi"]
GOREVLER = {
    "Parti Başkanı": ["Parti genel kararını açıkla ve üyeleri bilgilendir."],
    "Genel Sekreter": ["Parti içi düzen raporu hazırla ve sun."],
    "Ekonomi Başkanı": ["Aylık bütçe planı hazırla ve onayla."],
    "Eğitim Başkanı": ["Parti üyeleri için eğitim planı oluştur."],
    "Kooperatif Sorumlusu": ["Bu dönem için üretim planı hazırla."],
    "İçişleri Sorumlusu": ["Parti içi güvenlik denetimi gerçekleştir."],
    "Parti Yöneticisi": ["Üyelere operasyonel destek ver ve takibini yap."]
}
GOREV_MESAJLARI = {
    "Parti Başkanı": ["🏛️ Parti Başkanı genel kararını açıkladı, parti yönü netleşti."],
    "Genel Sekreter": ["📋 Genel Sekreter düzen raporunu tamamladı, sistem sorunsuz işliyor."],
    "Ekonomi Başkanı": ["💰 Ekonomi Başkanı bütçe planını açıkladı, mali denge sağlandı."],
    "Eğitim Başkanı": ["📚 Eğitim Başkanı yeni eğitim planını devreye aldı."],
    "Kooperatif Sorumlusu": ["🌾 Kooperatif Sorumlusu üretim planını onayladı."],
    "İçişleri Sorumlusu": ["🔒 İçişleri Sorumlusu güvenlik denetimini tamamladı."],
    "Parti Yöneticisi": ["⚙️ Parti Yöneticisi üyelere gerekli desteği sağladı."]
}
SEVIYE_ESLEME = {1:0,2:100,3:250,4:500,5:1000,6:2000,7:3500,8:5500,9:8000,10:12000}
def seviye_hesapla(xp): return max([lvl for lvl, req in SEVIYE_ESLEME.items() if xp >= req], default=1)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.kullanici_ekle(user.id, user.username or user.first_name)
    klavye = [[InlineKeyboardButton("📌 Görev Yap", callback_data="gorev_yap"), InlineKeyboardButton("👤 Profil", callback_data="profil")],
              [InlineKeyboardButton("🏛️ Makam Kontrol", callback_data="makam"), InlineKeyboardButton("🏆 Liderler", callback_data="liderler")],
              [InlineKeyboardButton("⚽ Futbol & Lig", callback_data="futbol_menu")]]
    await update.message.reply_text(f"🏛️ *Parti Yönetim Sistemi'ne Hoş Geldiniz*\n\nSayın {user.first_name}, günlük görevinizi yaparak XP ve güven kazanın.", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(klavye))

async def profil_komutu(update, context):
    user = update.effective_user
    veri = db.kullanici_getir(user.id)
    await _profil_goster(update, veri, user.first_name)

async def _profil_goster(update, veri, isim):
    xp, guven, streak, rol = veri["xp"], veri["guven"], veri["streak"], veri["role"] or "Atanmamış"
    level = seviye_hesapla(xp)
    durum = "🟢 Güvenli" if guven>=75 else "🟡 Dikkatli" if guven>=50 else "🟠 Riskli" if guven>=30 else "🔴 Kritik"
    mesaj = f"👤 *{isim} — Profil*\n{'-'*28}\n🏛️ *Makam:* {rol}\n⭐ *Seviye:* {level}\n🔷 *XP:* {xp}\n🛡️ *Güven:* {guven}/100 — {durum}\n🔥 *Seri:* {streak} gün"
    if hasattr(update, "message") and update.message:
        await update.message.reply_text(mesaj, parse_mode="Markdown")
    else:
        await update.callback_query.edit_message_text(mesaj, parse_mode="Markdown")

async def makam_komutu(update, context):
    user = update.effective_user
    veri = db.kullanici_getir(user.id)
    rol, guven = veri["role"], veri["guven"]
    if not rol:
        mesaj = "🏛️ *Makam Durumu*\n─────────────────────\n⚠️ Henüz bir makama atanmadınız."
    else:
        durum = "🟢 Güvenli Koltuk" if guven>=75 else "🟡 Dikkat Gerektiren Koltuk" if guven>=50 else "🔴 Riskli Koltuk" if guven>=30 else "⛔ Kritik — Görevden Alma Süreci"
        mesaj = f"🏛️ *Makam Durumu*\n─────────────────────\n📌 *Makam:* {rol}\n🛡️ *Güven Puanı:* {guven}/100\n📊 *Durum:* {durum}"
        if guven < 50: mesaj += "\n⚠️ _Güven puanınız tehlikeli düzeyde._"
    if update.message: await update.message.reply_text(mesaj, parse_mode="Markdown")
    else: await update.callback_query.edit_message_text(mesaj, parse_mode="Markdown")

async def gorev_yap_komutu(update, context):
    user = update.effective_user
    veri = db.kullanici_getir(user.id)
    if not veri["role"]:
        await (update.message.reply_text if update.message else update.callback_query.edit_message_text)("⚠️ Makam atanmamış.")
        return
    bugun = date.today().isoformat()
    if veri["last_task"] == bugun:
        await (update.message.reply_text if update.message else update.callback_query.edit_message_text)("✅ Bugünkü görevinizi zaten tamamladınız.")
        return
    gorev = random.choice(GOREVLER[veri["role"]])
    context.user_data["aktif_gorev"] = gorev
    klavye = [[InlineKeyboardButton("✅ Görevi Tamamladım", callback_data="gorev_tamamla")]]
    mesaj = f"📌 *Günlük Göreviniz*\n─────────────────────\n🏛️ *Makam:* {veri['role']}\n\n📋 *Görev:*\n_{gorev}_\n\nGörevi tamamladıktan sonra butona basın."
    if update.message:
        await update.message.reply_text(mesaj, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(klavye))
    else:
        await update.callback_query.edit_message_text(mesaj, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(klavye))

async def gorev_tamamla(update, context):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    veri = db.kullanici_getir(user.id)
    if not veri or veri["last_task"] == date.today().isoformat():
        await query.edit_message_text("✅ Bu görevi zaten tamamladınız.")
        return
    rol = veri["role"]
    if not rol:
        await query.edit_message_text("⚠️ Makamınız bulunmamaktadır.")
        return
    streak = veri["streak"] + 1
    bonus_xp = streak * 5
    kazanilan_xp = 20 + bonus_xp
    yeni_xp = veri["xp"] + kazanilan_xp
    yeni_guven = min(100, veri["guven"] + 3)
    yeni_level = seviye_hesapla(yeni_xp)
    db.kullanici_guncelle(user.id, xp=yeni_xp, level=yeni_level, guven=yeni_guven, streak=streak, last_task=date.today().isoformat())
    mesaj_metni = random.choice(GOREV_MESAJLARI[rol])
    seviye_mesaji = f"\n\n🎉 *SEVİYE ATLADI!* → Seviye {yeni_level}" if yeni_level > seviye_hesapla(veri["xp"]) else ""
    mesaj = f"✅ *Görev Tamamlandı*\n─────────────────────\n{mesaj_metni}\n\n🔷 *Kazanılan XP:* +{kazanilan_xp} (Baz:20 + Seri Bonusu:{bonus_xp})\n🛡️ *Güven:* {yeni_guven}/100 (+3)\n🔥 *Seri:* {streak} gün{seviye_mesaji}"
    klavye = [[InlineKeyboardButton("👤 Profilim", callback_data="profil"), InlineKeyboardButton("🏛️ Makamım", callback_data="makam")]]
    await query.edit_message_text(mesaj, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(klavye))

async def liderler_komutu(update, context):
    liderler = db.lider_tablosu()
    if not liderler: mesaj = "📊 Henüz lider tablosunda kimse yok."
    else:
        satirlar = ["🏆 *Lider Tablosu — İlk 10*\n" + "─" * 28]
        for i,(isim,xp,rol,guven) in enumerate(liderler):
            madalya = ["🥇","🥈","🥉"][i] if i<3 else f"{i+1}."
            satirlar.append(f"{madalya} *{isim}* — {xp} XP | {rol or 'Atanmamış'} | Güven:{guven}")
        mesaj = "\n".join(satirlar)
    if update.message: await update.message.reply_text(mesaj, parse_mode="Markdown")
    else: await update.callback_query.edit_message_text(mesaj, parse_mode="Markdown")

async def rol_ver(update, context):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ Yetkisiz.")
    args = context.args
    if len(args)<2: return await update.message.reply_text("⚠️ Kullanım: `/rol_ver @kullanıcı Makam Adı`", parse_mode="Markdown")
    hedef_username, makam = args[0].lstrip("@"), " ".join(args[1:])
    if makam not in MAKAMLAR: return await update.message.reply_text(f"⚠️ Geçersiz makam.\nMevcut makamlar:\n"+"\n".join([f"• {m}" for m in MAKAMLAR]))
    hedef = db.kullanici_username_ile_getir(hedef_username)
    if not hedef: return await update.message.reply_text(f"⚠️ `{hedef_username}` bulunamadı.")
    db.rol_ata(hedef["user_id"], makam)
    await update.message.reply_text(f"✅ *{hedef_username}* kullanıcısına *{makam}* görevi verildi.", parse_mode="Markdown")

async def rol_al(update, context):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ Yetkisiz.")
    if not context.args: return await update.message.reply_text("⚠️ Kullanım: `/rol_al @kullanıcı`", parse_mode="Markdown")
    hedef_username = context.args[0].lstrip("@")
    hedef = db.kullanici_username_ile_getir(hedef_username)
    if not hedef: return await update.message.reply_text(f"⚠️ `{hedef_username}` bulunamadı.")
    db.rol_ata(hedef["user_id"], None)
    await update.message.reply_text(f"✅ *{hedef_username}* kullanıcısının görevi alındı.", parse_mode="Markdown")

async def duyuru(update, context):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ Yetkisiz.")
    if not context.args: return await update.message.reply_text("⚠️ Kullanım: `/duyuru Mesaj`", parse_mode="Markdown")
    duyuru_metni = " ".join(context.args)
    for uid, _ in db.tum_kullanicilari_getir():
        try: await context.bot.send_message(chat_id=uid, text=f"📢 *PARTİ DUYURUSU*\n{'─'*28}\n{duyuru_metni}", parse_mode="Markdown")
        except: pass
    await update.message.reply_text("✅ Duyuru tüm üyelere iletildi.")

async def puan_ver(update, context):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ Yetkisiz.")
    args = context.args
    if len(args)<2: return await update.message.reply_text("⚠️ Kullanım: `/puan_ver @kullanıcı miktar`", parse_mode="Markdown")
    hedef_username, miktar = args[0].lstrip("@"), int(args[1])
    hedef = db.kullanici_username_ile_getir(hedef_username)
    if not hedef: return await update.message.reply_text(f"⚠️ `{hedef_username}` bulunamadı.")
    yeni_xp = hedef["xp"] + miktar
    db.kullanici_guncelle(hedef["user_id"], xp=yeni_xp, level=seviye_hesapla(yeni_xp))
    await update.message.reply_text(f"✅ *{hedef_username}* kullanıcısına *{miktar} XP* verildi. Toplam: {yeni_xp} XP", parse_mode="Markdown")

async def guven_ver(update, context):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ Yetkisiz.")
    args = context.args
    if len(args)<2: return await update.message.reply_text("⚠️ Kullanım: `/guven_ver @kullanıcı miktar`", parse_mode="Markdown")
    hedef_username, miktar = args[0].lstrip("@"), int(args[1])
    hedef = db.kullanici_username_ile_getir(hedef_username)
    if not hedef: return await update.message.reply_text(f"⚠️ `{hedef_username}` bulunamadı.")
    yeni_guven = max(0, min(100, hedef["guven"] + miktar))
    db.kullanici_guncelle(hedef["user_id"], guven=yeni_guven)
    await update.message.reply_text(f"✅ *{hedef_username}* güveni *{miktar}* değişti. Yeni güven: {yeni_guven}", parse_mode="Markdown")

async def set_group(update, context):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ Yetkisiz.")
    global GROUP_CHAT_ID
    GROUP_CHAT_ID = update.effective_chat.id
    set_group_chat_id(GROUP_CHAT_ID)
    await update.message.reply_text("✅ Bu grup maç sonuçları için ayarlandı.")

async def lig_guncelle(update, context):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ Yetkisiz.")
    fdb.fikstur_olustur(1,1)
    fdb.fikstur_olustur(2,1)
    await update.message.reply_text("✅ Fikstürler yenilendi, puanlar korundu.")

async def buton_handler(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    if await futbol_callback(update, context): return
    if data == "profil":
        user = update.effective_user
        veri = db.kullanici_getir(user.id)
        await _profil_goster(update, veri, user.first_name)
    elif data == "makam": await makam_komutu(update, context)
    elif data == "gorev_yap": await gorev_yap_komutu(update, context)
    elif data == "gorev_tamamla": await gorev_tamamla(update, context)
    elif data == "liderler": await liderler_komutu(update, context)
    elif data == "ana_menu":
        klavye = [[InlineKeyboardButton("📌 Görev Yap", callback_data="gorev_yap"), InlineKeyboardButton("👤 Profil", callback_data="profil")],
                  [InlineKeyboardButton("🏛️ Makam Kontrol", callback_data="makam"), InlineKeyboardButton("🏆 Liderler", callback_data="liderler")],
                  [InlineKeyboardButton("⚽ Futbol & Lig", callback_data="futbol_menu")]]
        await query.edit_message_text("🏛️ *Ana Menü*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(klavye))
    elif data == "futbol_menu":
        klavye = [[InlineKeyboardButton("👥 Takımım", callback_data="takim_bilgi"), InlineKeyboardButton("🏆 Lig Tablosu", callback_data="lig_tablosu")],
                  [InlineKeyboardButton("🛒 Transfer Piyasası", callback_data="piyasa_0"), InlineKeyboardButton("⚽ Maç Oyna", callback_data="mac_oyna")],
                  [InlineKeyboardButton("🏋️ Antrenman", callback_data="antrenman"), InlineKeyboardButton("📅 Fikstür", callback_data="fikstur_goster")],
                  [InlineKeyboardButton("🎡 Çark", callback_data="cark"), InlineKeyboardButton("👑 Loncalar", callback_data="loncalar")],
                  [InlineKeyboardButton("🔙 Ana Menü", callback_data="ana_menu")]]
        await query.edit_message_text("⚽ *Cumhuriyet Süper Ligi*", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(klavye))

async def gunluk_ceza_isle(context: ContextTypes.DEFAULT_TYPE):
    bugun = date.today().isoformat()
    for user_id, _ in db.tum_kullanicilari_getir():
        veri = db.kullanici_getir(user_id)
        if not veri or not veri["role"]: continue
        if veri["last_task"] == bugun: continue
        fark = (date.today() - date.fromisoformat(veri["last_task"])).days if veri["last_task"] else 1
        ceza = min(5 * fark, 30)
        yeni_guven = max(0, veri["guven"] - ceza)
        db.kullanici_guncelle(user_id, guven=yeni_guven, streak=0)
        if yeni_guven < 30:
            try: await context.bot.send_message(chat_id=user_id, text=f"🚨 *Kritik Güven Uyarısı*\nGüven puanınız {yeni_guven}'e düştü!", parse_mode="Markdown")
            except: pass

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profil", profil_komutu))
    app.add_handler(CommandHandler("makam", makam_komutu))
    app.add_handler(CommandHandler("gorev", gorev_yap_komutu))
    app.add_handler(CommandHandler("liderler", liderler_komutu))
    app.add_handler(CommandHandler("rol_ver", rol_ver))
    app.add_handler(CommandHandler("rol_al", rol_al))
    app.add_handler(CommandHandler("duyuru", duyuru))
    app.add_handler(CommandHandler("puan_ver", puan_ver))
    app.add_handler(CommandHandler("guven_ver", guven_ver))
    app.add_handler(CommandHandler("set_group", set_group))
    app.add_handler(CommandHandler("lig_guncelle", lig_guncelle))
    # Futbol komutları
    app.add_handler(CommandHandler("takim_kur", cmd_takim_kur))
    app.add_handler(CommandHandler("takim", cmd_takim))
    app.add_handler(CommandHandler("piyasa", cmd_piyasa))
    app.add_handler(CommandHandler("satin_al", cmd_satin_al))
    app.add_handler(CommandHandler("sat", cmd_sat))
    app.add_handler(CommandHandler("sat_iptal", cmd_sat_iptal))
    app.add_handler(CommandHandler("antrenman", cmd_antrenman))
    app.add_handler(CommandHandler("mac", cmd_mac))
    app.add_handler(CommandHandler("lig", cmd_lig))
    app.add_handler(CommandHandler("son_maclar", cmd_son_maclar))
    app.add_handler(CommandHandler("fikstur", cmd_fikstur))
    app.add_handler(CommandHandler("cuzdan", cmd_cuzdan))
    app.add_handler(CommandHandler("taktik", cmd_taktik))
    app.add_handler(CommandHandler("cark", cmd_cark))
    app.add_handler(CommandHandler("bahis", cmd_bahis))
    app.add_handler(CommandHandler("lonca_kur", cmd_lonca_kur))
    app.add_handler(CommandHandler("lonca_katil", cmd_lonca_katil))
    app.add_handler(CommandHandler("kupa", cmd_kupa))
    app.add_handler(CommandHandler("sezon_sifirla", cmd_sezon_sifirla))
    app.add_handler(CommandHandler("oyuncu_istatistik", cmd_oyuncu_istatistik))
    app.add_handler(CommandHandler("altyapi", cmd_altyapi))
    app.add_handler(CallbackQueryHandler(buton_handler))
    app.job_queue.run_daily(gunluk_ceza_isle, time=datetime.strptime("23:59", "%H:%M").time(), name="gunluk_ceza")
    logger.info("Bot başlatılıyor...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
