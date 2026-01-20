import yfinance as yf
import pandas as pd
import json
import os
import requests
import re

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
    try:
        # Önce Dolar kurunu çekelim
        usd_try_data = yf.download("USDTRY=X", period="1d", interval="1m")
        usd_try = usd_try_data['Close'].iloc[-1]
    except:
        usd_try = 34.0  # Eğer kur çekilemezse hata vermesin diye sabit bir rakam (örnek)

    for sembol in semboller:
        try:
            # Tek bir sembol için fiyat çek
            ticker = yf.Ticker(sembol)
            veri = ticker.history(period="1d")
            
            if not veri.empty:
                guncel_fiyat = veri['Close'].iloc[-1]

                # --- İŞTE O EKLEYECEĞİN KISIM BURASI ---
                if sembol == "GC=F": # Ons Altın -> Gram Altın TL
                    guncel_fiyat = (guncel_fiyat / 31.1034768) * usd_try
                elif sembol == "SI=F": # Ons Gümüş -> Gram Gümüş TL
                    guncel_fiyat = (guncel_fiyat / 31.1034768) * usd_try
                # ----------------------------------------

                fiyatlar[sembol] = guncel_fiyat
            else:
                fiyatlar[sembol] = 0
        except Exception as e:
            print(f"Hata: {sembol} çekilemedi -> {e}")
            fiyatlar[sembol] = 0
            
    return fiyatlar

def portfoy_analiz(portfoy_listesi, p):
    if not portfoy_listesi: return pd.DataFrame()
    df = pd.DataFrame(portfoy_listesi)
    g_list = []
    
    for _, row in df.iterrows():
        sem = str(row['sembol']).upper().strip()
        tip = row.get('tip', 'Hisse')
        fiyat = 0.0
        
        if tip == "Altın" or "GAU-TRY" in sem: fiyat = p['ALTIN']
        elif tip == "Gümüş" or "SILVER-TRY" in sem: fiyat = p['GÜMÜŞ']
        elif tip == "Döviz" or sem in ["USDTRY=X", "USD/TRY"]: fiyat = p['DOLAR']
        else:
            try:
                h = yf.Ticker(sem).history(period="5d")
                if not h.empty: fiyat = round(float(h['Close'].dropna().iloc[-1]), 2)
            except: fiyat = 0.0
        g_list.append(fiyat)
    
    df['Güncel'] = g_list
    df['Değer_TL'] = df['Güncel'] * df['adet']
    df['Kar_TL'] = df['Değer_TL'] - (df['maliyet'] * df['adet'])
    df['% Değişim'] = (df['Kar_TL'] / (df['maliyet'] * df['adet'] + 0.0001)) * 100
    
    if 'hedef' not in df.columns: df['hedef'] = 0.0
    df['Hedef_Durum'] = df.apply(lambda x: (x['Güncel'] / x['hedef'] * 100) if x['hedef'] > 0 else 0, axis=1)
    return df

def gecmis_kaydet(toplam_tl):
    import datetime
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
