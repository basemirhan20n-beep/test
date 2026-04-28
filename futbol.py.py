"""
Cumhuriyet Süper Ligi — Futbol Modülü
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from futbol_db import FutbolDB
import random
from datetime import date

fdb = FutbolDB()
POZ_EMOJI = {"Kaleci":"🧤","Defans":"🛡️","Orta Saha":"⚙️","Forvet":"⚡"}
LIG_ADI = "🏆 CUMHURİYET SÜPER LİGİ"
LIG_TAKIM_LIMITI = 15

GROUP_CHAT_ID = None
def set_group_chat_id(cid): global GROUP_CHAT_ID; GROUP_CHAT_ID = cid

async def _gonder(update, metin, markup=None, parse_mode="Markdown"):
    if update.callback_query:
        await update.callback_query.edit_message_text(metin, parse_mode=parse_mode, reply_markup=markup)
    else:
        await update.message.reply_text(metin, parse_mode=parse_mode, reply_markup=markup)

def _piyasa_markup(sayfa, toplam, sayfa_boyut=8):
    satirlar, nav = [], []
    if sayfa>0: nav.append(InlineKeyboardButton("◀️ Önceki", callback_data=f"piyasa_{sayfa-1}"))
    toplam_sayfa = (toplam+sayfa_boyut-1)//sayfa_boyut
    nav.append(InlineKeyboardButton(f"{sayfa+1}/{toplam_sayfa}", callback_data="piyasa_noop"))
    if (sayfa+1)*sayfa_boyut < toplam: nav.append(InlineKeyboardButton("Sonraki ▶️", callback_data=f"piyasa_{sayfa+1}"))
    if nav: satirlar.append(nav)
    satirlar.append([InlineKeyboardButton("🔄 Yenile", callback_data=f"piyasa_{sayfa}")])
    return InlineKeyboardMarkup(satirlar)

# ---- KOMUTLAR ----
async def cmd_takim_kur(update, context):
    user = update.effective_user
    if not context.args: return await update.message.reply_text("⚽ Kullanım: `/takim_kur Takım Adı`", parse_mode="Markdown")
    isim = " ".join(context.args)
    basari, mesaj = fdb.takim_kur(user.id, isim)
    if not basari: return await update.message.reply_text(f"❌ {mesaj}")
    fdb.para_getir(user.id)
    takim_sayisi = fdb.takim_sayisi()
    fikstur_mesaj = ""
    if takim_sayisi >= LIG_TAKIM_LIMITI and not fdb.fikstur_var_mi(1):
        fdb.fikstur_olustur(1,1)
        fikstur_mesaj = f"\n\n🎉 *{LIG_TAKIM_LIMITI}. takım tamamlandı!* {LIG_ADI} fikstürü oluşturuldu! 🎊"
    await update.message.reply_text(f"✅ *{isim}* takımı kuruldu!\n💰 Başlangıç bütçen: *100.000₺*\n👥 Şu an ligde *{takim_sayisi}/{LIG_TAKIM_LIMITI}* takım var.\n📋 Oyuncu almak için: `/piyasa`{fikstur_mesaj}", parse_mode="Markdown")

async def cmd_takim(update, context):
    user = update.effective_user
    takim = fdb.takim_user(user.id)
    if not takim: return await _gonder(update, "❌ Takımın yok. `/takim_kur <Ad>` ile kur.", parse_mode="Markdown")
    oyuncular = fdb.takim_oyunculari(takim["takim_id"])
    para = fdb.para_getir(user.id)
    guc = round(fdb.takim_gucu(takim["takim_id"]),1)
    metin = f"🏟️ *{takim['isim']}*\n{'─'*30}\n💰 Bütçe: *{para:,}₺*\n⚽ Ortalama Güç: *{guc}*\n📊 {takim['puan']} puan — {takim['galibiyet']}G {takim['beraberlik']}B {takim['maglubiyet']}M — {takim['atilan_gol']}:{takim['yenilen_gol']}\n👥 Kadro: *{len(oyuncular)}/23* oyuncu\n{'─'*30}\n"
    if oyuncular:
        for o in sorted(oyuncular, key=lambda x: -x["guc"]):
            satis = f" 🔖{o['satis_fiyati']:,}₺" if o["satista"] else ""
            metin += f"{POZ_EMOJI.get(o['pozisyon'],'⚽')} [{o['oyuncu_id']}] *{o['isim']}* — {o['pozisyon']} | Güç:{o['guc']}{satis}\n"
    else: metin += "_Kadronuzda henüz oyuncu yok._\n"
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("🛒 Piyasa", callback_data="piyasa_0"), InlineKeyboardButton("🏋️ Antrenman", callback_data="antrenman"), InlineKeyboardButton("⚽ Maç", callback_data="mac_oyna")]])
    await _gonder(update, metin, markup=markup)

async def cmd_piyasa(update, context):
    sayfa = int(context.args[0])-1 if context.args and context.args[0].isdigit() else 0
    await _piyasa_goster(update, max(0,sayfa))

async def _piyasa_goster(update, sayfa):
    if not fdb.transfer_acik_mi(): return await _gonder(update, "❌ Transfer dönemi kapalı.")
    oyuncular, toplam = fdb.piyasa(sayfa)
    if not oyuncular: return await _gonder(update, "🛒 Piyasada şu an oyuncu yok.")
    metin = f"🛒 *Transfer Piyasası* ({toplam} oyuncu)\n{'─'*32}\n"
    for o in oyuncular:
        takim_info = "🔓 Serbest" if not o["takim_id"] else "🏟️ Transfer"
        metin += f"{POZ_EMOJI.get(o['pozisyon'],'⚽')} `[{o['oyuncu_id']}]` *{o['isim']}* — {o['pozisyon']}\n   Güç: {o['guc']} | 💰 {o['satis_fiyati']:,}₺ | {takim_info}\n"
    metin += f"\n_Satın almak için: `/satin_al <ID>`_"
    await _gonder(update, metin, markup=_piyasa_markup(sayfa, toplam))

async def cmd_satin_al(update, context):
    user = update.effective_user
    takim = fdb.takim_user(user.id)
    if not takim: return await update.message.reply_text("❌ Önce `/takim_kur` ile takım kur.", parse_mode="Markdown")
    if not fdb.transfer_acik_mi(): return await update.message.reply_text("❌ Transfer dönemi kapalı.")
    if not context.args or not context.args[0].isdigit(): return await update.message.reply_text("⚠️ Kullanım: `/satin_al <oyuncu_id>`", parse_mode="Markdown")
    oyuncu_id = int(context.args[0])
    basari, mesaj = fdb.satin_al(user.id, takim["takim_id"], oyuncu_id)
    para = fdb.para_getir(user.id)
    await update.message.reply_text(f"{mesaj}\n💰 Kalan bakiye: *{para:,}₺*", parse_mode="Markdown")

async def cmd_sat(update, context):
    user = update.effective_user
    takim = fdb.takim_user(user.id)
    if not takim: return await update.message.reply_text("❌ Takımın yok.")
    if len(context.args)<2: return await update.message.reply_text("⚠️ Kullanım: `/sat <oyuncu_id> <fiyat>`\nSatışı iptal: `/sat_iptal <oyuncu_id>`", parse_mode="Markdown")
    try: oyuncu_id, fiyat = int(context.args[0]), int(context.args[1])
    except: return await update.message.reply_text("❌ ID ve fiyat sayısal olmalı.")
    basari, mesaj = fdb.sat(takim["takim_id"], oyuncu_id, fiyat)
    await update.message.reply_text(mesaj, parse_mode="Markdown")

async def cmd_sat_iptal(update, context):
    user = update.effective_user
    takim = fdb.takim_user(user.id)
    if not takim: return await update.message.reply_text("❌ Takımın yok.")
    if not context.args or not context.args[0].isdigit(): return await update.message.reply_text("⚠️ Kullanım: `/sat_iptal <oyuncu_id>`", parse_mode="Markdown")
    oyuncu_id = int(context.args[0])
    basari, mesaj = fdb.sat_iptal(takim["takim_id"], oyuncu_id)
    await update.message.reply_text(mesaj, parse_mode="Markdown")

async def cmd_antrenman(update, context):
    user = update.effective_user
    takim = fdb.takim_user(user.id)
    if not takim: return await _gonder(update, "❌ Takımın yok.", parse_mode="Markdown")
    basari, sonuc = fdb.antrenman_yap(takim["takim_id"])
    if not basari: return await _gonder(update, f"⚠️ {sonuc}")
    metin = f"🏋️ *Antrenman Tamamlandı — {takim['isim']}*\n{'─'*30}\n"
    for o in sonuc: metin += f"{POZ_EMOJI.get(o['pozisyon'],'⚽')} *{o['isim']}*\n   Güç: +{o['artis']} → **{o['yeni_guc']}**\n"
    metin += "\n_Yarın tekrar antrenman yapabilirsin!_"
    await _gonder(update, metin)

async def cmd_mac(update, context):
    user = update.effective_user
    takim = fdb.takim_user(user.id)
    if not takim: return await _gonder(update, "❌ Takımın yok.", parse_mode="Markdown")
    if not fdb.fikstur_var_mi(takim["lig_id"]):
        sayi = fdb.takim_sayisi()
        kalan = (15 if takim["lig_id"]==1 else 10) - sayi
        return await _gonder(update, f"⏳ Fikstür henüz oluşturulmadı. Lig başlaması için *{kalan}* takım daha gerekiyor.", parse_mode="Markdown")
    yeterli, neden = fdb.yeterli_kadro_mu(takim["takim_id"])
    if not yeterli: return await _gonder(update, f"❌ {neden}")
    mac = fdb.sonraki_mac(takim["takim_id"])
    if not mac: return await _gonder(update, "🎉 Sezon bitti! Tüm maçlarını oynadın.")
    ev_takim = fdb.takim_id(mac["ev_takim_id"])
    dep_takim = fdb.takim_id(mac["dep_takim_id"])
    metin = f"⚽ *Cumhuriyet Süper Ligi — {mac['hafta']}. Hafta*\n{'─'*32}\n🏠 {ev_takim['isim']} (Güç: {round(fdb.takim_gucu(mac['ev_takim_id']),1)})\n✈️ {dep_takim['isim']} (Güç: {round(fdb.takim_gucu(mac['dep_takim_id']),1)})\n\nMaçı oynamaya hazır mısın?"
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("⚽ MAÇI BAŞLAT!", callback_data=f"mac_bas_{mac['mac_id']}"), InlineKeyboardButton("❌ Vazgeç", callback_data="futbol_iptal")]])
    await _gonder(update, metin, markup=markup)

async def cmd_lig(update, context):
    takimlar = fdb.tum_takimlar()
    if not takimlar: return await _gonder(update, f"{LIG_ADI}\n\nHenüz takım yok.")
    metin = f"{LIG_ADI}\n{'═'*32}\n{'#':<3} {'Takım':<18} {'O':>2} {'G':>2} {'B':>2} {'M':>2} {'AG':>3} {'YG':>3} {'P':>3}\n{'─'*32}\n"
    rozetler = ["🥇","🥈","🥉"]
    for i,t in enumerate(takimlar):
        rozet = rozetler[i] if i<3 else f"{i+1:>2}."
        metin += f"{rozet} `{t['isim'][:14]:<14} {t['mac_sayisi']:>2} {t['galibiyet']:>2} {t['beraberlik']:>2} {t['maglubiyet']:>2} {t['atilan_gol']:>3} {t['yenilen_gol']:>3} {t['puan']:>3}`\n"
    if not fdb.fikstur_var_mi(1): kalan = LIG_TAKIM_LIMITI - len(takimlar); metin += f"\n⏳ Lig başlaması için *{kalan}* takım daha gerekli."
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Yenile", callback_data="lig_tablosu"), InlineKeyboardButton("📅 Fikstür", callback_data="fikstur_goster")]])
    await _gonder(update, metin, markup=markup)

async def cmd_son_maclar(update, context):
    user = update.effective_user
    takim = fdb.takim_user(user.id)
    if not takim: return await _gonder(update, "❌ Takımın yok.")
    maclar = fdb.son_maclar(takim["takim_id"])
    if not maclar: return await _gonder(update, "📋 Henüz hiç maç oynamadın.")
    metin = f"📋 *{takim['isim']} — Son Maçlar*\n{'─'*30}\n"
    for m in maclar:
        if m["ev_takim_id"] == takim["takim_id"]:
            kendi_gol, rakip_gol, rakip = m["ev_gol"], m["dep_gol"], m["dep_isim"]
            yer = "🏠"
        else:
            kendi_gol, rakip_gol, rakip = m["dep_gol"], m["ev_gol"], m["ev_isim"]
            yer = "✈️"
        skor_emoji = "✅" if kendi_gol>rakip_gol else "🟡" if kendi_gol==rakip_gol else "❌"
        metin += f"{skor_emoji} {yer} *{takim['isim']}* {kendi_gol}–{rakip_gol} *{rakip}*  _(Hafta {m['hafta']})_\n"
    await _gonder(update, metin)

async def cmd_fikstur(update, context):
    hafta = fdb.mevcut_hafta()
    await _fikstur_goster(update, hafta)

async def _fikstur_goster(update, hafta):
    maclar = fdb.haftalik_fikstur(hafta)
    if not maclar: return await _gonder(update, f"📅 {hafta}. haftada maç yok.")
    metin = f"📅 *{LIG_ADI} — {hafta}. Hafta*\n{'─'*32}\n"
    for m in maclar:
        if m["oynanmis"]: skor, durum = f"*{m['ev_gol']}–{m['dep_gol']}*", "✅"
        else: skor, durum = "vs", "⏳"
        metin += f"{durum} {m['ev_isim']} {skor} {m['dep_isim']}\n"
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("◀️", callback_data=f"fikstur_{max(1,hafta-1)}"), InlineKeyboardButton(f"Hafta {hafta}", callback_data="noop"), InlineKeyboardButton("▶️", callback_data=f"fikstur_{hafta+1}")]])
    await _gonder(update, metin, markup=markup)

async def cmd_cuzdan(update, context):
    user = update.effective_user
    para = fdb.para_getir(user.id)
    takim = fdb.takim_user(user.id)
    takim_bilgi = f"🏟️ Takım: *{takim['isim']}*\n" if takim else ""
    await _gonder(update, f"💰 *Cüzdan — {user.first_name}*\n{'─'*28}\n{takim_bilgi}💵 Bakiye: *{para:,}₺*\n\n_Maç kazanınca 5.000₺, beraberlikte 2.500₺, kayıpta 1.000₺ kazanırsın._", parse_mode="Markdown")

# ---- YENİ KOMUTLAR ----
async def cmd_taktik(update, context):
    user = update.effective_user
    takim = fdb.takim_user(user.id)
    if not takim: return await update.message.reply_text("❌ Takımın yok.")
    if not context.args or context.args[0] not in TAKTIKLER: return await update.message.reply_text(f"⚠️ Kullanım: /taktik {'|'.join(TAKTIKLER)}")
    fdb.taktik_degistir(takim["takim_id"], context.args[0])
    await update.message.reply_text(f"✅ Taktik *{context.args[0]}* olarak ayarlandı.", parse_mode="Markdown")

async def cmd_cark(update, context):
    user = update.effective_user
    odul, mesaj = fdb.daily_spin(user.id)
    if odul is None: return await update.message.reply_text(mesaj)
    await update.message.reply_text(f"🎡 Çark çevrildi!\n{mesaj}")

async def cmd_bahis(update, context):
    await update.message.reply_text("⚠️ Bahis sistemi yakında eklenecek.")

async def cmd_lonca_kur(update, context):
    if not context.args: return await update.message.reply_text("⚠️ Kullanım: /lonca_kur LoncaAdı")
    isim = " ".join(context.args)
    basari, mesaj = fdb.lonca_kur(update.effective_user.id, isim)
    await update.message.reply_text(mesaj)

async def cmd_lonca_katil(update, context):
    if not context.args: return await update.message.reply_text("⚠️ Kullanım: /lonca_katil LoncaID")
    try: lid = int(context.args[0])
    except: return await update.message.reply_text("❌ Lonca ID sayı olmalı.")
    mesaj = fdb.lonca_katil(update.effective_user.id, lid)
    await update.message.reply_text(mesaj)

async def cmd_kupa(update, context):
    user = update.effective_user
    takim = fdb.takim_user(user.id)
    if not takim: return await update.message.reply_text("❌ Takımın yok.")
    mac = fdb.kupa_mac(takim["takim_id"])
    if not mac: return await update.message.reply_text("🏆 Şu an aktif kupa maçın yok veya kupa oluşturulmamış.")
    await _gonder(update, f"🏆 *Cumhuriyet Kupası* - {mac['tur']}. Tur\n{mac['ev_isim']} vs {mac['dep_isim']}\nMaçı başlatmak için /mac komutunu kullan.")

async def cmd_sezon_sifirla(update, context):
    if not await is_admin(update, context): return await update.message.reply_text("⛔ Yetkisiz.")
    fdb.sezon_sifirla()
    await update.message.reply_text("✅ Sezon sıfırlandı. Puanlar silindi, şampiyona ödül verildi, fikstür yenilendi.")

async def cmd_oyuncu_istatistik(update, context):
    if not context.args or not context.args[0].isdigit(): return await update.message.reply_text("⚠️ Kullanım: /oyuncu_istatistik <oyuncu_id>")
    istatistik = fdb.oyuncu_istatistikleri(int(context.args[0]))
    if not istatistik: return await update.message.reply_text("Oyuncu bulunamadı.")
    await update.message.reply_text(f"📊 *{istatistik['isim']}* istatistikleri\nGol: {istatistik['gol']}\nAsist: {istatistik['asist']}\nSarı Kart: {istatistik['sari_kart']}\nKırmızı Kart: {istatistik['kirmizi_kart']}\nSakatlık (kalan maç): {istatistik['sakatlik_maç']}", parse_mode="Markdown")

async def cmd_altyapi(update, context):
    user = update.effective_user
    takim = fdb.takim_user(user.id)
    if not takim: return await update.message.reply_text("❌ Takımın yok.")
    oyuncu = fdb.altyapi_oyuncu_cikar(takim["takim_id"])
    if not oyuncu: return await update.message.reply_text("❌ Altyapıdan oyuncu çıkarılamadı. (Kadro dolu veya günlük limit?)")
    await update.message.reply_text(f"🌟 Altyapıdan yeni oyuncu çıktı!\n{POZ_EMOJI.get(oyuncu['pozisyon'],'⚽')} *{oyuncu['isim']}* — {oyuncu['pozisyon']} | Güç: {oyuncu['guc']}\nKadrona eklendi.", parse_mode="Markdown")

# ---- CALLBACK HANDLER ----
async def futbol_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    query = update.callback_query
    data = query.data
    if data.startswith("piyasa_"):
        await query.answer()
        if data=="piyasa_noop": return True
        sayfa = int(data.split("_")[1])
        await _piyasa_goster(update, sayfa)
        return True
    if data == "antrenman": await query.answer(); await cmd_antrenman(update, context); return True
    if data == "mac_oyna": await query.answer(); await cmd_mac(update, context); return True
    if data.startswith("mac_bas_"):
        await query.answer("⚽ Maç başlıyor...")
        mac_id = int(data.split("_")[2])
        user = update.effective_user
        takim = fdb.takim_user(user.id)
        if not takim: await query.edit_message_text("❌ Takımın yok."); return True
        sonuc, hata = fdb.mac_oyna(mac_id, takim["takim_id"], takim.get("taktik","4-4-2"))
        if hata: await query.edit_message_text(f"⚠️ {hata}"); return True
        ev, dep, eg, dg = sonuc["ev_takim"], sonuc["dep_takim"], sonuc["ev_gol"], sonuc["dep_gol"]
        if eg>dg: sonuc_emoji = "🟢 Ev sahibi kazandı!"
        elif dg>eg: sonuc_emoji = "🔵 Deplasman kazandı!"
        else: sonuc_emoji = "🟡 Berabere!"
        metin = f"⚽ *{LIG_ADI}*\n*{sonuc['hafta']}. Hafta Maç Raporu*\n{'═'*32}\n🏠 *{ev}*  {eg} – {dg}  *{dep}* ✈️\n{'─'*32}\n{sonuc_emoji}\n"
        if sonuc["ev_gol_atanlar"]: metin += f"\n⚽ *{ev}* golleri:\n" + "\n".join(f"  ⚡ {isim}" for isim in sonuc["ev_gol_atanlar"])
        if sonuc["dep_gol_atanlar"]: metin += f"\n⚽ *{dep}* golleri:\n" + "\n".join(f"  ⚡ {isim}" for isim in sonuc["dep_gol_atanlar"])
        odul = 5000 if (eg>dg and takim["isim"]==ev) or (dg>eg and takim["isim"]==dep) else (1000 if (eg>dg and takim["isim"]==dep) or (dg>eg and takim["isim"]==ev) else 2500)
        metin += f"\n💰 Kazanılan ödül: *+{odul:,}₺*"
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("📊 Lig Tablosu", callback_data="lig_tablosu"), InlineKeyboardButton("👥 Takımım", callback_data="takim_bilgi")]])
        await query.edit_message_text(metin, parse_mode="Markdown", reply_markup=markup)
        if GROUP_CHAT_ID:
            try: await context.bot.send_message(GROUP_CHAT_ID, f"⚽ {ev} {eg}–{dg} {dep}\n🏆 Hafta {sonuc['hafta']}")
            except: pass
        return True
    if data == "lig_tablosu": await query.answer(); await cmd_lig(update, context); return True
    if data == "takim_bilgi": await query.answer(); await cmd_takim(update, context); return True
    if data == "fikstur_goster": await query.answer(); await _fikstur_goster(update, fdb.mevcut_hafta()); return True
    if data.startswith("fikstur_"): await query.answer(); await _fikstur_goster(update, int(data.split("_")[1])); return True
    if data == "futbol_iptal": await query.answer("İptal edildi."); await query.edit_message_text("❌ İptal edildi."); return True
    if data == "cark": await query.answer(); await cmd_cark(update, context); return True
    if data == "loncalar":
        loncalar = fdb.lonca_listesi()
        metin = "👑 *Loncalar*\n"+"\n".join(f"{l['lonca_id']}: {l['isim']} (Puan:{l['puan']})" for l in loncalar) if loncalar else "Hiç lonca yok."
        await query.edit_message_text(metin, parse_mode="Markdown")
        return True
    return False

# (is_admin fonksiyonu bot.py içinde tanımlanacak, burada kullanıldığı için dummy)
async def is_admin(update, context): return True
TAKTIKLER = fdb.TAKTIKLER