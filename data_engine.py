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
        # 2026 Güncel Dolar Kuru
        dolar_verisi = yf.download("USDTRY=X", period="1d", interval="1m")
        usd_try = dolar_verisi['Close'].iloc[-1]
    except:
        usd_try = 45.50 # Hata olursa varsayılan

    for s in semboller:
        try:
            if not s or str(s) == 'nan': continue
            # Temizleme
            s_clean = str(s).strip().upper()
            
            # Veri Çekme
            veri = yf.download(s_clean, period="1d", interval="1m")
            if not veri.empty:
                fiyat = veri['Close'].iloc[-1]
                
                # --- ALTIN/GÜMÜŞ TL ÇEVİRİ ---
                if "GC=F" in s_clean:
                    fiyatlar[s_clean] = (fiyat / 31.1034) * usd_try
                elif "SI=F" in s_clean:
                    fiyatlar[s_clean] = (fiyat / 31.1034) * usd_try
                else:
                    fiyatlar[s_clean] = fiyat
            else:
                fiyatlar[s_clean] = 0.0
        except:
            fiyatlar[s_clean] = 0.0
    
    # Sistemin hata vermemesi için yedek anahtarlar
    fiyatlar['USDTRY=X'] = usd_try
    return fiyatlar

def portfoy_analiz(portfoy_listesi, p):
    if not portfoy_listesi: return pd.DataFrame()
    df = pd.DataFrame(portfoy_listesi)
    
    # Sütun isimlerini küçült (Hata önleyici)
    df.columns = [str(c).lower().strip() for c in df.columns]
    
    g_list = []
    for _, row in df.iterrows():
        sem = str(row.get('sembol', '')).strip().upper()
        tip = str(row.get('tip', '')).lower()
        
        # Akıllı Fiyat Bulucu
        fiyat = 0.0
        if "GC=F" in sem or "altin" in tip:
            fiyat = p.get("GC=F", 0.0)
        elif "SI=F" in sem or "gümüş" in tip:
            fiyat = p.get("SI=F", 0.0)
        else:
            fiyat = p.get(sem, 0.0)
            
        g_list.append(fiyat)
    
    df['güncel'] = g_list
    df['değer_tl'] = df['güncel'] * df['adet'].astype(float)
    df['maliyet_toplam'] = df['maliyet'].astype(float) * df['adet'].astype(float)
    df['kar_tl'] = df['değer_tl'] - df['maliyet_toplam']
    df['% değişim'] = (df['kar_tl'] / (df['maliyet_toplam'] + 0.0001)) * 100
    
    return df

def gecmis_yukle():
    if os.path.exists("gecmis.json"):
        try:
            with open("gecmis.json", "r") as f: return json.load(f)
        except: return {}
    return {}

def temettu_yukle():
    if os.path.exists("temettu.json"):
        try:
            with open("temettu.json", "r") as f: return json.load(f)
        except: return []
    return []
