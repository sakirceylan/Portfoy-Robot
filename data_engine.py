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

def piyasa_verisi_cek():
    m_list = {"DOLAR": "USDTRY=X", "EURO": "EURTRY=X", "ONS_ALTIN": "GC=F", "ONS_GUMUS": "SI=F"}
    d = {"DOLAR": 0.0, "EURO": 0.0, "ALTIN": 0.0, "GÜMÜŞ": 0.0}
    for k in ["DOLAR", "EURO"]:
        try:
            h = yf.Ticker(m_list[k]).history(period="5d")
            if not h.empty: d[k] = round(float(h['Close'].dropna().iloc[-1]), 2)
        except: pass
    
    try:
        g_altin = yf.Ticker("GAU-TRY.IS").history(period="5d")
        if not g_altin.empty and g_altin['Close'].iloc[-1] > 0:
            d["ALTIN"] = round(float(g_altin['Close'].dropna().iloc[-1]), 2)
        else:
            ons = yf.Ticker(m_list["ONS_ALTIN"]).history(period="5d")
            ons_fiyat = float(ons['Close'].iloc[-1]) if not ons.empty else 0.0
            d["ALTIN"] = round((ons_fiyat / 31.1035) * d["DOLAR"], 2)
    except: pass
    
    try:
        g_gumus = yf.Ticker("SILVER-TRY.IS").history(period="5d")
        if not g_gumus.empty and g_gumus['Close'].iloc[-1] > 0:
            d["GÜMÜŞ"] = round(float(g_gumus['Close'].dropna().iloc[-1]), 2)
        else:
            ons_g = yf.Ticker(m_list["ONS_GUMUS"]).history(period="5d")
            ons_g_fiyat = float(ons_g['Close'].iloc[-1]) if not ons_g.empty else 0.0
            d["GÜMÜŞ"] = round((ons_g_fiyat / 31.1035) * d["DOLAR"], 2)
    except: pass
    return d

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
