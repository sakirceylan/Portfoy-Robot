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
        # 2026 Dolar Kuru Çekimi
        dolar_verisi = yf.download("USDTRY=X", period="1d", interval="1m")
        usd_try = dolar_verisi['Close'].iloc[-1]
    except:
        usd_try = 45.50

    for s in semboller:
        try:
            if not s or str(s) == 'nan': continue
            s_clean = str(s).strip().upper()
            
            # Veriyi çek
            veri = yf.download(s_clean, period="1d", interval="1m")
            if not veri.empty:
                fiyat = veri['Close'].iloc[-1]
                
                # --- ALTIN/GÜMÜŞ TL GRAMA ÇEVİR ---
                if "GC=F" in s_clean or "SI=F" in s_clean:
                    # Ons fiyatını Gram TL'ye çevir (Ons / 31.1034 * Dolar)
                    fiyatlar[s_clean] = (fiyat / 31.1034) * usd_try
                else:
                    fiyatlar[s_clean] = fiyat
            else:
                fiyatlar[s_clean] = 0.0
        except:
            fiyatlar[s_clean] = 0.0
    
    return fiyatlar

def portfoy_analiz(portfoy_listesi, p):
    if not portfoy_listesi: return pd.DataFrame()
    df = pd.DataFrame(portfoy_listesi)
    
    # Sütun isimlerini küçük harfe sabitle (Hata önleyici)
    df.columns = [str(c).lower().strip() for c in df.columns]
    
    guncel_fiyatlar = []
    for _, row in df.iterrows():
        sem = str(row.get('sembol', '')).strip().upper()
        
        # SÖZLÜKTE ARA: Eğer sözlükte (p) bu sembol varsa fiyatını al, yoksa 0.0 yaz
        # Bu satır sayesinde 'KeyError' (ALTIN hatası) artık ASLA oluşmaz.
        fiyat = p.get(sem, 0.0)
        guncel_fiyatlar.append(fiyat)
    
    df['güncel'] = guncel_fiyatlar
    df['değer_tl'] = df['güncel'] * df['adet'].astype(float)
    df['maliyet_toplam'] = df['maliyet'].astype(float) * df['adet'].astype(float)
    df['kar_tl'] = df['değer_tl'] - df['maliyet_toplam']
    
    # Sıfıra bölünme hatasını engelle (+0.0001)
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
