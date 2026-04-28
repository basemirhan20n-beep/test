import sqlite3
import random
from datetime import date, datetime, timedelta
from typing import Optional

DB_PATH = "parti.db"

ISIMLER = [
    "Ahmet","Mehmet","Ali","Hasan","İbrahim","Mustafa","Ömer","Hüseyin",
    "Murat","Emre","Serkan","Burak","Kemal","Tarık","Barış","Volkan",
    "Selim","Arda","Ferhat","Caner","Sinan","Fatih","Taner","Okan",
    "Yasin","Levent","Ercan","Tolga","Uğur","Kadir","Savaş","Alper",
    "Kerem","Furkan","Mert","Doruk","Tuncay","Orhan","Cemal","Haluk"
]
SOYADLAR = [
    "Yılmaz","Kaya","Demir","Çelik","Şahin","Koç","Arslan","Kurt",
    "Doğan","Aydın","Polat","Güneş","Yıldız","Öztürk","Erdoğan",
    "Kılıç","Çetin","Toprak","Balcı","Özdemir","Kaplan","Bozkurt",
    "Akgün","Yurt","Güler","Şen","Duman","Özer","Sarı","Albayrak",
    "Ateş","Bulut","Karaca","Taş","Demirci","Tuncer","Işık","Avcı",
    "Özkan","Sever","Yıldırım","Aslan","Doğru","Gürbüz","Çevik"
]
POZISYONLAR_AGIRLIKLI = ["Kaleci"]*2 + ["Defans"]*5 + ["Orta Saha"]*5 + ["Forvet"]*3
BASLANGIC_PARASI = 100_000
TAKTIKLER = ["4-4-2","4-3-3","3-5-2","5-4-1","4-5-1"]
TAKTIK_AVANTAJ = {
    ("4-4-2","4-3-3"):0.05, ("4-3-3","5-4-1"):0.07,
    ("5-4-1","4-3-3"):-0.05, ("4-5-1","4-4-2"):0.03,
    ("3-5-2","4-4-2"):0.04
}

def rastgele_isim(kullanilmis):
    for _ in range(50):
        isim = f"{random.choice(ISIMLER)} {random.choice(SOYADLAR)}"
        if isim not in kullanilmis: return isim
    return f"{random.choice(ISIMLER)} {random.choice(SOYADLAR)}{random.randint(2,9)}"

class FutbolDB:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_tables()
        self._piyasa_doldur()
        self._ligleri_kontrol_et()

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        with self._conn() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS futbol_para (user_id INTEGER PRIMARY KEY, para INTEGER DEFAULT 100000)")
            conn.execute("CREATE TABLE IF NOT EXISTS takimlar (takim_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER UNIQUE, isim TEXT UNIQUE, lig_id INTEGER DEFAULT 1, puan INTEGER DEFAULT 0, galibiyet INTEGER DEFAULT 0, beraberlik INTEGER DEFAULT 0, maglubiyet INTEGER DEFAULT 0, atilan_gol INTEGER DEFAULT 0, yenilen_gol INTEGER DEFAULT 0, mac_sayisi INTEGER DEFAULT 0, son_mac TEXT, olusturma_tarihi TEXT, taktik TEXT DEFAULT '4-4-2')")
            conn.execute("CREATE TABLE IF NOT EXISTS oyuncular (oyuncu_id INTEGER PRIMARY KEY AUTOINCREMENT, takim_id INTEGER, isim TEXT, pozisyon TEXT, guc INTEGER, deger INTEGER, antrenman_tarihi TEXT, satista INTEGER DEFAULT 0, satis_fiyati INTEGER DEFAULT 0, gol INTEGER DEFAULT 0, asist INTEGER DEFAULT 0, sari_kart INTEGER DEFAULT 0, kirmizi_kart INTEGER DEFAULT 0, sakatlik_maç INTEGER DEFAULT 0, ceza_maç INTEGER DEFAULT 0, altyapi INTEGER DEFAULT 0)")
            conn.execute("CREATE TABLE IF NOT EXISTS fikstur (mac_id INTEGER PRIMARY KEY AUTOINCREMENT, ev_takim_id INTEGER, dep_takim_id INTEGER, hafta INTEGER, oynanma_tarihi TEXT, ev_gol INTEGER, dep_gol INTEGER, oynanmis INTEGER DEFAULT 0, sezon_id INTEGER DEFAULT 1)")
            conn.execute("CREATE TABLE IF NOT EXISTS ligler (lig_id INTEGER PRIMARY KEY, isim TEXT, seviye INTEGER, min_takim INTEGER)")
            conn.execute("CREATE TABLE IF NOT EXISTS transfer_donemleri (id INTEGER PRIMARY KEY, acik_mi BOOLEAN, baslangic TEXT, bitis TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS kupalar (kupa_id INTEGER PRIMARY KEY AUTOINCREMENT, isim TEXT, sezon INTEGER, kazanan_id INTEGER)")
            conn.execute("CREATE TABLE IF NOT EXISTS kupa_maclari (mac_id INTEGER PRIMARY KEY AUTOINCREMENT, kupa_id INTEGER, tur INTEGER, ev_id INTEGER, dep_id INTEGER, ev_gol INTEGER, dep_gol INTEGER, oynandi BOOLEAN, kazanan_id INTEGER)")
            conn.execute("CREATE TABLE IF NOT EXISTS daily_spin (user_id INTEGER PRIMARY KEY, son_spin TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS loncalar (lonca_id INTEGER PRIMARY KEY AUTOINCREMENT, isim TEXT, lider_id INTEGER, puan INTEGER DEFAULT 0)")
            conn.execute("CREATE TABLE IF NOT EXISTS lonca_uyeleri (lonca_id INTEGER, user_id INTEGER, PRIMARY KEY(lonca_id, user_id))")
            conn.execute("CREATE TABLE IF NOT EXISTS achievements (ach_id INTEGER PRIMARY KEY, isim TEXT, aciklama TEXT, kriter_tip TEXT, kriter_deger INTEGER)")
            conn.execute("CREATE TABLE IF NOT EXISTS user_achievements (user_id INTEGER, ach_id INTEGER, kazanma_tarihi TEXT, PRIMARY KEY(user_id, ach_id))")
            conn.commit()
            self._default_ligler()
            self._default_achievements()

    def _default_ligler(self):
        with self._conn() as conn:
            conn.execute("INSERT OR IGNORE INTO ligler VALUES (1, 'Cumhuriyet Süper Ligi', 1, 15)")
            conn.execute("INSERT OR IGNORE INTO ligler VALUES (2, 'Cumhuriyet 1. Ligi', 2, 10)")
            conn.execute("INSERT OR IGNORE INTO transfer_donemleri VALUES (1, 1, '2025-01-01', '2025-12-31')")

    def _default_achievements(self):
        ach = [(1,"İlk Galibiyet","İlk maçını kazan","mac_gal",1),
               (2,"Seri Galib","Arka arkaya 5 maç kazan","seri_gal",5),
               (3,"Gol Kralı","Bir sezonda 20 gol","gol_say",20)]
        with self._conn() as conn:
            for a in ach: conn.execute("INSERT OR IGNORE INTO achievements VALUES (?,?,?,?,?)", a)

    def _ligleri_kontrol_et(self):
        pass

    # ---- PARA ----
    def para_getir(self, user_id):
        with self._conn() as conn:
            r = conn.execute("SELECT para FROM futbol_para WHERE user_id=?", (user_id,)).fetchone()
            if not r:
                conn.execute("INSERT INTO futbol_para VALUES (?,?)", (user_id, BASLANGIC_PARASI))
                return BASLANGIC_PARASI
            return r["para"]

    def para_guncelle(self, user_id, miktar):
        with self._conn() as conn:
            conn.execute("UPDATE futbol_para SET para=para+? WHERE user_id=?", (miktar, user_id))

    # ---- TAKIM ----
    def takim_kur(self, user_id, isim):
        isim = isim.strip()
        if len(isim)<2 or len(isim)>30: return False, "Takım adı 2-30 karakter olmalı."
        with self._conn() as conn:
            try:
                lig_id = 2 if self.takim_sayisi() >= 15 else 1
                conn.execute("INSERT INTO takimlar (user_id, isim, lig_id, olusturma_tarihi) VALUES (?,?,?,?)", (user_id, isim, lig_id, date.today().isoformat()))
                return True, "ok"
            except sqlite3.IntegrityError as e:
                if "user_id" in str(e): return False, "Zaten bir takımınız var."
                return False, "Bu takım adı zaten kullanılıyor."

    def takim_user(self, user_id):
        with self._conn() as conn:
            r = conn.execute("SELECT * FROM takimlar WHERE user_id=?", (user_id,)).fetchone()
            return dict(r) if r else None

    def takim_id(self, takim_id):
        with self._conn() as conn:
            r = conn.execute("SELECT * FROM takimlar WHERE takim_id=?", (takim_id,)).fetchone()
            return dict(r) if r else None

    def takim_sayisi(self, lig_id=None):
        with self._conn() as conn:
            if lig_id: return conn.execute("SELECT COUNT(*) FROM takimlar WHERE lig_id=?", (lig_id,)).fetchone()[0]
            return conn.execute("SELECT COUNT(*) FROM takimlar").fetchone()[0]

    def tum_takimlar(self, lig_id=None):
        with self._conn() as conn:
            if lig_id:
                rows = conn.execute("SELECT * FROM takimlar WHERE lig_id=? ORDER BY puan DESC, (atilan_gol-yenilen_gol) DESC, atilan_gol DESC", (lig_id,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM takimlar ORDER BY puan DESC, (atilan_gol-yenilen_gol) DESC, atilan_gol DESC").fetchall()
            return [dict(r) for r in rows]

    # ---- OYUNCU ----
    def _piyasa_doldur(self):
        with self._conn() as conn:
            mevcut = conn.execute("SELECT COUNT(*) FROM oyuncular WHERE takim_id IS NULL AND satista=1").fetchone()[0]
            if mevcut >= 30: return
            kullanilmis = {r[0] for r in conn.execute("SELECT isim FROM oyuncular").fetchall()}
            for _ in range(40 - mevcut):
                isim = rastgele_isim(kullanilmis)
                kullanilmis.add(isim)
                poz = random.choice(POZISYONLAR_AGIRLIKLI)
                guc = random.randint(45,82)
                deger = max(8000, guc*1000 + random.randint(-3000,5000))
                conn.execute("INSERT INTO oyuncular (takim_id,isim,pozisyon,guc,deger,satista,satis_fiyati) VALUES (NULL,?,?,?,?,1,?)", (isim, poz, guc, deger, deger))

    def takim_oyunculari(self, takim_id):
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM oyuncular WHERE takim_id=? ORDER BY guc DESC", (takim_id,)).fetchall()
            return [dict(r) for r in rows]

    def piyasa(self, sayfa=0, sayfa_boyut=8):
        offset = sayfa * sayfa_boyut
        with self._conn() as conn:
            toplam = conn.execute("SELECT COUNT(*) FROM oyuncular WHERE satista=1").fetchone()[0]
            rows = conn.execute("SELECT * FROM oyuncular WHERE satista=1 ORDER BY guc DESC LIMIT ? OFFSET ?", (sayfa_boyut, offset)).fetchall()
            return [dict(r) for r in rows], toplam

    def oyuncu_getir(self, oyuncu_id):
        with self._conn() as conn:
            r = conn.execute("SELECT * FROM oyuncular WHERE oyuncu_id=?", (oyuncu_id,)).fetchone()
            return dict(r) if r else None

    def satin_al(self, user_id, takim_id, oyuncu_id):
        if not self.transfer_acik_mi(): return False, "Transfer dönemi kapalı."
        oyuncu = self.oyuncu_getir(oyuncu_id)
        if not oyuncu or not oyuncu["satista"]: return False, "Oyuncu satışta değil."
        fiyat = oyuncu["satis_fiyati"]
        para = self.para_getir(user_id)
        if para < fiyat: return False, f"Yeterli paran yok. Gerekli: {fiyat:,}₺"
        if len(self.takim_oyunculari(takim_id)) >= 23: return False, "Kadro dolu (max 23)."
        self.para_guncelle(user_id, -fiyat)
        if oyuncu["takim_id"]:
            with self._conn() as conn:
                satici = conn.execute("SELECT user_id FROM takimlar WHERE takim_id=?", (oyuncu["takim_id"],)).fetchone()
                if satici: self.para_guncelle(satici["user_id"], fiyat)
        with self._conn() as conn:
            conn.execute("UPDATE oyuncular SET takim_id=?, satista=0, satis_fiyati=0 WHERE oyuncu_id=?", (takim_id, oyuncu_id))
        self._piyasa_doldur()
        return True, f"✅ {oyuncu['isim']} ({oyuncu['pozisyon']}, Güç:{oyuncu['guc']}) satın alındı! -{fiyat:,}₺"

    def sat(self, takim_id, oyuncu_id, fiyat):
        oyuncu = self.oyuncu_getir(oyuncu_id)
        if not oyuncu or oyuncu["takim_id"] != takim_id: return False, "Bu oyuncu senin takımında değil."
        if oyuncu["satista"]: return False, "Oyuncu zaten satışta."
        if fiyat < 1000: return False, "Min satış fiyatı 1.000₺."
        with self._conn() as conn:
            conn.execute("UPDATE oyuncular SET satista=1, satis_fiyati=? WHERE oyuncu_id=?", (fiyat, oyuncu_id))
        return True, f"✅ {oyuncu['isim']} {fiyat:,}₺ fiyatıyla piyasaya çıkarıldı."

    def sat_iptal(self, takim_id, oyuncu_id):
        oyuncu = self.oyuncu_getir(oyuncu_id)
        if not oyuncu or oyuncu["takim_id"] != takim_id: return False, "Bu oyuncu senin takımında değil."
        with self._conn() as conn:
            conn.execute("UPDATE oyuncular SET satista=0, satis_fiyati=0 WHERE oyuncu_id=?", (oyuncu_id,))
        return True, "✅ Satış iptal edildi."

    # ---- ANTRENMAN ----
    def antrenman_yap(self, takim_id):
        bugun = date.today().isoformat()
        oyuncular = self.takim_oyunculari(takim_id)
        if not oyuncular: return False, "Kadronuzda oyuncu yok."
        if any(o.get("antrenman_tarihi")==bugun for o in oyuncular): return False, "Bugün antrenman yaptınız."
        secilen = random.sample(oyuncular, min(5, len(oyuncular)))
        gelismeler = []
        with self._conn() as conn:
            for o in secilen:
                artis = random.randint(1,3)
                yeni_guc = min(99, o["guc"]+artis)
                conn.execute("UPDATE oyuncular SET guc=?, antrenman_tarihi=? WHERE oyuncu_id=?", (yeni_guc, bugun, o["oyuncu_id"]))
                gelismeler.append({"isim":o["isim"],"pozisyon":o["pozisyon"],"artis":artis,"yeni_guc":yeni_guc})
        return True, gelismeler

    # ---- TAKIM GÜCÜ ----
    def takim_gucu(self, takim_id):
        oyuncular = self.takim_oyunculari(takim_id)
        if not oyuncular: return 50.0
        gucler = sorted([o["guc"] for o in oyuncular], reverse=True)[:11]
        return sum(gucler)/len(gucler)

    def yeterli_kadro_mu(self, takim_id):
        oyuncular = self.takim_oyunculari(takim_id)
        if len(oyuncular) < 11: return False, f"Kadroda {len(oyuncular)} oyuncu var (en az 11 gerekli)."
        if "Kaleci" not in [o["pozisyon"] for o in oyuncular]: return False, "Kadroda kaleci yok!"
        return True, "ok"

    # ---- FİKSTÜR ----
    def fikstur_var_mi(self, lig_id=1):
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM fikstur WHERE ev_takim_id IN (SELECT takim_id FROM takimlar WHERE lig_id=?)", (lig_id,)).fetchone()[0] > 0

    def fikstur_olustur(self, lig_id=1, sezon_id=1):
        takimlar = self.tum_takimlar(lig_id)
        min_takim = 15 if lig_id==1 else 10
        if len(takimlar) < min_takim: return False
        ids = [t["takim_id"] for t in takimlar]
        if len(ids)%2==1: ids.append(None)
        n = len(ids)
        maclar = []
        ids_rot = ids[1:]
        for tur in range(n-1):
            hafta = tur+1
            eslemeler = [(ids[0], ids_rot[0])] + [(ids_rot[-(i)], ids_rot[i]) for i in range(1, n//2)]
            for ev, dep in eslemeler:
                if ev and dep: maclar.append((ev,dep,hafta))
            ids_rot = [ids_rot[-1]] + ids_rot[:-1]
        toplam_hafta = n-1
        for ev,dep,hafta in list(maclar):
            maclar.append((dep,ev,hafta+toplam_hafta))
        with self._conn() as conn:
            conn.execute("DELETE FROM fikstur WHERE sezon_id=? AND (ev_takim_id IN (SELECT takim_id FROM takimlar WHERE lig_id=?) OR dep_takim_id IN (SELECT takim_id FROM takimlar WHERE lig_id=?))", (sezon_id, lig_id, lig_id))
            for ev,dep,h in maclar:
                conn.execute("INSERT INTO fikstur (ev_takim_id,dep_takim_id,hafta,sezon_id) VALUES (?,?,?,?)", (ev,dep,h,sezon_id))
        return True

    def sonraki_mac(self, takim_id):
        with self._conn() as conn:
            r = conn.execute("SELECT * FROM fikstur WHERE (ev_takim_id=? OR dep_takim_id=?) AND oynanmis=0 ORDER BY hafta ASC LIMIT 1", (takim_id, takim_id)).fetchone()
            return dict(r) if r else None

    def bugun_mac_oynadim_mi(self, takim_id):
        bugun = date.today().isoformat()
        with self._conn() as conn:
            return conn.execute("SELECT COUNT(*) FROM fikstur WHERE (ev_takim_id=? OR dep_takim_id=?) AND oynanmis=1 AND oynanma_tarihi=?", (takim_id, takim_id, bugun)).fetchone()[0] > 0

    def mac_oyna(self, mac_id, talep_eden_takim, taktik=None):
        with self._conn() as conn:
            r = conn.execute("SELECT * FROM fikstur WHERE mac_id=?", (mac_id,)).fetchone()
            if not r: return None, "Maç bulunamadı."
            mac = dict(r)
        if mac["oynanmis"]: return None, "Maç oynanmış."
        if talep_eden_takim not in (mac["ev_takim_id"], mac["dep_takim_id"]): return None, "Bu maç sana ait değil."
        if self.bugun_mac_oynadim_mi(talep_eden_takim): return None, "Bugün maç oynadın, yarın gel."
        ev_takim = self.takim_id(mac["ev_takim_id"])
        dep_takim = self.takim_id(mac["dep_takim_id"])
        ev_guc = self.takim_gucu(mac["ev_takim_id"])
        dep_guc = self.takim_gucu(mac["dep_takim_id"])
        taktik_ev = ev_takim["taktik"] if ev_takim else "4-4-2"
        taktik_dep = dep_takim["taktik"] if dep_takim else "4-4-2"
        avantaj = TAKTIK_AVANTAJ.get((taktik_ev, taktik_dep), 0)
        ev_guc_adj = ev_guc * (1.08 + avantaj)
        toplam = ev_guc_adj + dep_guc
        ev_oran = ev_guc_adj / toplam
        ev_gol = max(0, min(9, round(random.gauss(ev_oran*3.2, 1.1))))
        dep_gol = max(0, min(9, round(random.gauss((1-ev_oran)*3.2, 1.1))))
        ev_oyuncular = self.takim_oyunculari(mac["ev_takim_id"])
        dep_oyuncular = self.takim_oyunculari(mac["dep_takim_id"])
        def gol_atan(oyuncular, sayi):
            forvetler = [o for o in oyuncular if o["pozisyon"] in ("Forvet","Orta Saha")]
            havuz = forvetler or oyuncular
            return [random.choice(havuz)["isim"] for _ in range(sayi)] if havuz else []
        ev_gol_atanlar = gol_atan(ev_oyuncular, ev_gol)
        dep_gol_atanlar = gol_atan(dep_oyuncular, dep_gol)
        for isim in ev_gol_atanlar:
            with self._conn() as conn:
                conn.execute("UPDATE oyuncular SET gol=gol+1 WHERE isim=? AND takim_id=?", (isim, mac["ev_takim_id"]))
        for isim in dep_gol_atanlar:
            with self._conn() as conn:
                conn.execute("UPDATE oyuncular SET gol=gol+1 WHERE isim=? AND takim_id=?", (isim, mac["dep_takim_id"]))
        bugun = date.today().isoformat()
        with self._conn() as conn:
            conn.execute("UPDATE fikstur SET ev_gol=?, dep_gol=?, oynanmis=1, oynanma_tarihi=? WHERE mac_id=?", (ev_gol, dep_gol, bugun, mac_id))
            def update_takim(tid, atti, yedi):
                if atti>yedi: conn.execute("UPDATE takimlar SET puan=puan+3, galibiyet=galibiyet+1, atilan_gol=atilan_gol+?, yenilen_gol=yenilen_gol+?, mac_sayisi=mac_sayisi+1 WHERE takim_id=?", (atti, yedi, tid))
                elif atti<yedi: conn.execute("UPDATE takimlar SET maglubiyet=maglubiyet+1, atilan_gol=atilan_gol+?, yenilen_gol=yenilen_gol+?, mac_sayisi=mac_sayisi+1 WHERE takim_id=?", (atti, yedi, tid))
                else: conn.execute("UPDATE takimlar SET puan=puan+1, beraberlik=beraberlik+1, atilan_gol=atilan_gol+?, yenilen_gol=yenilen_gol+?, mac_sayisi=mac_sayisi+1 WHERE takim_id=?", (atti, yedi, tid))
            update_takim(mac["ev_takim_id"], ev_gol, dep_gol)
            update_takim(mac["dep_takim_id"], dep_gol, ev_gol)
        if ev_gol>dep_gol:
            self.para_guncelle(ev_takim["user_id"], 5000); self.para_guncelle(dep_takim["user_id"], 1000)
        elif dep_gol>ev_gol:
            self.para_guncelle(dep_takim["user_id"], 5000); self.para_guncelle(ev_takim["user_id"], 1000)
        else:
            self.para_guncelle(ev_takim["user_id"], 2500); self.para_guncelle(dep_takim["user_id"], 2500)
        return {"mac_id":mac_id,"hafta":mac["hafta"],"ev_takim":ev_takim["isim"],"dep_takim":dep_takim["isim"],"ev_gol":ev_gol,"dep_gol":dep_gol,"ev_gol_atanlar":ev_gol_atanlar,"dep_gol_atanlar":dep_gol_atanlar}, None

    def son_maclar(self, takim_id, limit=5):
        with self._conn() as conn:
            rows = conn.execute("SELECT f.*, (SELECT isim FROM takimlar WHERE takim_id=f.ev_takim_id) AS ev_isim, (SELECT isim FROM takimlar WHERE takim_id=f.dep_takim_id) AS dep_isim FROM fikstur f WHERE (f.ev_takim_id=? OR f.dep_takim_id=?) AND f.oynanmis=1 ORDER BY f.oynanma_tarihi DESC LIMIT ?", (takim_id, takim_id, limit)).fetchall()
            return [dict(r) for r in rows]

    def haftalik_fikstur(self, hafta):
        with self._conn() as conn:
            rows = conn.execute("SELECT f.*, (SELECT isim FROM takimlar WHERE takim_id=f.ev_takim_id) AS ev_isim, (SELECT isim FROM takimlar WHERE takim_id=f.dep_takim_id) AS dep_isim FROM fikstur f WHERE f.hafta=? ORDER BY f.mac_id", (hafta,)).fetchall()
            return [dict(r) for r in rows]

    def mevcut_hafta(self):
        with self._conn() as conn:
            r = conn.execute("SELECT MAX(hafta) FROM fikstur WHERE oynanmis=1").fetchone()[0]
            if r: return r
            r2 = conn.execute("SELECT MIN(hafta) FROM fikstur WHERE oynanmis=0").fetchone()[0]
            return r2 or 1

    # ---- YENİ METODLAR (Transfer dönemi, taktik, çark, lonca, sezon sıfırlama, altyapı, istatistik) ----
    def transfer_acik_mi(self):
        with self._conn() as conn:
            r = conn.execute("SELECT acik_mi FROM transfer_donemleri LIMIT 1").fetchone()
            return r["acik_mi"] == 1 if r else True

    def taktik_degistir(self, takim_id, taktik):
        with self._conn() as conn:
            conn.execute("UPDATE takimlar SET taktik=? WHERE takim_id=?", (taktik, takim_id))

    def daily_spin(self, user_id):
        bugun = date.today().isoformat()
        with self._conn() as conn:
            r = conn.execute("SELECT son_spin FROM daily_spin WHERE user_id=?", (user_id,)).fetchone()
            if r and r["son_spin"] == bugun:
                return None, "❌ Bugün çarkı çevirdiniz."
            odul = random.choice(["para","para","xp","ozel"])
            if odul == "para":
                miktar = random.randint(500,5000)
                self.para_guncelle(user_id, miktar)
                mesaj = f"💰 {miktar}₺ kazandınız!"
            elif odul == "xp":
                miktar = random.randint(10,50)
                mesaj = f"⭐ {miktar} XP kazandınız! (Admin eliyle eklenmeli)"
            else:
                mesaj = "🎁 Özel ödül: Bir sonraki transfer %50 indirim!"
            conn.execute("INSERT OR REPLACE INTO daily_spin VALUES (?,?)", (user_id, bugun))
            return odul, mesaj

    def lonca_kur(self, user_id, isim):
        with self._conn() as conn:
            try:
                conn.execute("INSERT INTO loncalar (isim, lider_id) VALUES (?,?)", (isim, user_id))
                lid = conn.lastrowid
                conn.execute("INSERT INTO lonca_uyeleri VALUES (?,?)", (lid, user_id))
                return True, f"✅ {isim} loncası kuruldu (ID:{lid})"
            except: return False, "Bu isimde lonca var."

    def lonca_katil(self, user_id, lonca_id):
        with self._conn() as conn:
            if not conn.execute("SELECT * FROM loncalar WHERE lonca_id=?", (lonca_id,)).fetchone():
                return "Lonca yok."
            conn.execute("INSERT OR IGNORE INTO lonca_uyeleri VALUES (?,?)", (lonca_id, user_id))
            return "Loncaya katıldınız."

    def lonca_listesi(self):
        with self._conn() as conn:
            return [dict(r) for r in conn.execute("SELECT lonca_id, isim, puan FROM loncalar").fetchall()]

    def sezon_sifirla(self):
        with self._conn() as conn:
            samp = conn.execute("SELECT takim_id, user_id FROM takimlar WHERE lig_id=1 ORDER BY puan DESC LIMIT 1").fetchone()
            if samp:
                self.para_guncelle(samp["user_id"], 50000)
            conn.execute("UPDATE takimlar SET puan=0, galibiyet=0, beraberlik=0, maglubiyet=0, atilan_gol=0, yenilen_gol=0, mac_sayisi=0")
            self.fikstur_olustur(1,1)
            self.fikstur_olustur(2,1)

    def altyapi_oyuncu_cikar(self, takim_id):
        if len(self.takim_oyunculari(takim_id)) >= 23: return None
        isim = f"Genç {random.choice(ISIMLER[:5])} {random.choice(SOYADLAR[:5])}"
        poz = random.choice(["Forvet","Orta Saha","Defans"])
        guc = random.randint(40,65)
        with self._conn() as conn:
            conn.execute("INSERT INTO oyuncular (takim_id, isim, pozisyon, guc, deger, altyapi) VALUES (?,?,?,?,?,1)", (takim_id, isim, poz, guc, guc*800))
            oid = conn.lastrowid
        return self.oyuncu_getir(oid)

    def oyuncu_istatistikleri(self, oyuncu_id):
        with self._conn() as conn:
            r = conn.execute("SELECT isim, gol, asist, sari_kart, kirmizi_kart, sakatlik_maç FROM oyuncular WHERE oyuncu_id=?", (oyuncu_id,)).fetchone()
            return dict(r) if r else None
