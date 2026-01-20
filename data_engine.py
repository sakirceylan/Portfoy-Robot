import yfinance as yf
import pandas as pd
import json
import os
import datetime

def veri_yukle():
    if os.path.exists("portfoy.json"):
        try:
            with open("portfoy.json", "r") as f: return json.load(f)
        except: return []
    return []

def veri_kaydet(v):
    with open("portfoy.json", "w") as f: json.dump(v, f)

def piyasa_verisi_cek(semboller):
    fiyatlar = {}
    if not semboller: return fiyatlar
    try:
        # 2026 Dolar kuru çekimi
        dolar_verisi = yf.download("USDTRY=X", period="1d", interval="1m")
        usd_try = dolar_verisi['Close'].iloc[-1]
    except:
        usd_try = 45.50 # Hata durumunda varsayılan kur

    for s in semboller:
        try:
            if not s or str(s) == 'nan': continue
            veri = yf.download(s, period="1d", interval="1m")
            if not veri.empty:
                fiyat = veri['Close'].iloc[-1]
                # Altın ve Gümüşü TL Grama Çevir
                if s == "GC=F":
                    fiyatlar[s] = (fiyat / 31.1034) * usd_try
                elif s == "SI=F":
                    fiyatlar[s] = (fiyat / 31.1034) * usd_try
                else:
                    fiyatlar[s] = fiyat
            else:
                fiyatlar[s] = 0.0
        except:
            fiyatlar[s] = 0.0
    
    # Raporlama kısmında hata vermemesi için dolar kurunu da ekleyelim
    fiyatlar['USDTRY=X'] = usd_try
    return fiyatlar

def portfoy_analiz(portfoy_listesi, p):
    if not portfoy_listesi: return pd.DataFrame()
    df = pd.DataFrame(portfoy_listesi)
    
    # Sütun isimlerini garantiye alalım
    df.columns = [str(c).lower().strip() for c in df.columns]
    
    g_list = []
    for _, row in df.iterrows():
        sem = str(row['sembol']).upper().strip()
        
        # Fiyatı p sözlüğünden çek, bulamazsa yfinance ile anlık dene
        fiyat = p.get(sem, 0.0)
        
        if fiyat == 0.0:
            try:
                h = yf.Ticker(sem).history(period="1d")
                if not h.empty:
                    fiyat = round(float(h['Close'].iloc[-1]), 2)
            except:
                fiyat = 0.0
        g_list.append(fiyat)
    
    df['güncel'] = g_list
    df['değer_tl'] = df['güncel'] * df['adet']
    df['kar_tl'] = df['değer_tl'] - (df['maliyet'] * df['adet'])
    # Hata payını engellemek için +0.0001
    df['% değişim'] = (df['kar_tl'] / (df['maliyet'] * df['adet'] + 0.0001)) * 100
    
    if 'hedef' not in df.columns: df['hedef'] = 0.0
    df['hedef_durum'] = df.apply(lambda x: (x['güncel'] / x['hedef'] * 100) if x.get('hedef', 0) > 0 else 0, axis=1)
    
    return df

def gecmis_kaydet(toplam_tl):
    tarih = datetime.datetime.now().strftime("%Y-%m-%d")
    gecmis_data = gecmis_yukle()
    gecmis_data[tarih] = round(toplam_tl, 2)
    with open("gecmis.json", "w") as f: json.dump(gecmis_data, f)

def gecmis_yukle():
    if os.path.exists("gecmis.json"):
        try:
            with open("gecmis.json", "r") as f: return json.load(f)
        except: return {}
    return {}

def temettu_kaydet(temettu_listesi):
    with open("temettu.json", "w") as f: json.dump(temettu_listesi, f)

def temettu_yukle():
    if os.path.exists("temettu.json"):
        try:
            with open("temettu.json", "r") as f: return json.load(f)
        except: return []
    return []
