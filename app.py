import streamlit as st
import pandas as pd
from data_engine import veri_yukle, veri_kaydet, piyasa_verisi_cek, portfoy_analiz
import ui_components as ui
import plotly.express as px
import io # Raporlama için gerekli
import smtplib
from email.mime.text import MIMEText
import datetime

from streamlit_gsheets import GSheetsConnection
import yfinance as yf

# Excel Bağlantısı
conn = st.connection("gsheets", type=GSheetsConnection)


def verileri_cek():
    try:
        # ttl=0 diyerek her saniye taze veri almasını sağlıyoruz
        df = conn.read(worksheet="Sayfa1", ttl=0)
        
        if df is not None and not df.empty:
            # 1. Sütun isimlerindeki boşlukları temizle ve küçük harfe çevir
            df.columns = [str(c).strip().lower() for c in df.columns]
            
            # 2. Excel'deki mavi linkli hisseleri (sembol) düz metne çevir
            # (Bazı durumlarda link olması robotu bozabiliyor)
            if 'sembol' in df.columns:
                df['sembol'] = df['sembol'].astype(str).str.strip()
            
            # 3. Boş satırları tamamen temizle
            df = df.dropna(subset=['sembol'])
            
            # Başarılıysa veriyi dön
            return df.to_dict('records')
        return []
    except Exception as e:
        st.error(f"Excel Okuma Hatası: {e}")
        return []


def veri_kaydet_excel(yeni_portfoy):
    """Excel'i günceller."""
    df = pd.DataFrame(yeni_portfoy)
    conn.update(data=df)        
        
# Eski veri_yukle() yerine direkt Excel'den çekiyoruz
if 'portfoy' not in st.session_state:
    st.session_state.portfoy = verileri_cek()


# MAİL GÖNDERME FONKSİYONU
def mail_gonder(konu, icerik):
    # Şifreleri koddan sildik, Streamlit'in gizli ayarlarından çekeceğiz
    gonderici = st.secrets["mail_bilgileri"]["eposta"]
    sifre = st.secrets["mail_bilgileri"]["sifre"]
    
    msg = MIMEText(icerik)
    msg['Subject'] = konu
    msg['From'] = gonderici
    msg['To'] = gonderici 

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(gonderici, sifre)
            server.sendmail(gonderici, gonderici, msg.as_string())
    except Exception as e:
        print(f"Hata: {e}")

def haftalik_ozet_gonder(df):
    toplam_deger = df['Değer_TL'].sum()
    toplam_kar = df['KarZarar_TL'].sum()
    en_iyi = df.loc[df['KarZarar_Oran'].idxmax()]['sembol']
    
    konu = "📊 Haftalık Portföy Raporun Hazır!"
    icerik = f"""
    Selam kanka, bu haftaki borsa serüvenin şöyle bitti:
    
    💰 Toplam Portföy Değeri: {toplam_deger:,.2f} ₺
    📈 Toplam Kar/Zarar Durumu: {toplam_kar:,.2f} ₺
    🚀 Haftanın Yıldızı: {en_iyi}
    
    Haftaya bol kazançlar dilerim!
    """
    mail_gonder(konu, icerik)

# 1. Sayfa Ayarı
st.set_page_config(page_title="Portföy v5.0", layout="wide")

# 2. Veri Başlatma
if 'portfoy' not in st.session_state:
    st.session_state.portfoy = veri_yukle()


# 3. Sidebar - Yeni Varlık Ekleme
with st.sidebar:
    st.header("➕ Yeni Varlık")
    b_sec = st.selectbox("Banka", ["Ziraat", "Kuveyt Türk", "Vakıfbank"])
    t_sec = st.selectbox("Tür", ["Hisse", "Altın", "Gümüş", "Döviz"])
    
    if t_sec in ["Altın", "Gümüş"]:
        s_in = "GAU-TRY.IS" if t_sec == "Altın" else "SILVER-TRY.IS"
        st.info(f"Varlık: {t_sec} (Canlı Takip)")
        a_in = st.number_input("Kaç Gram?", min_value=0.0, step=0.01)
        m_in = st.number_input("Maliyet (₺/Gram)", min_value=0.0, step=0.01)
    else:
        def_s = "USDTRY=X" if t_sec == "Döviz" else ""
        s_in = st.text_input("Sembol", value=def_s).upper().strip()
        a_in = st.number_input("Adet", min_value=0.0, step=0.01)
        m_in = st.number_input("Maliyet (TL)", min_value=0.0, step=0.01)
    
    if st.button("Kaydet", use_container_width=True):
        if t_sec == "Hisse" and not s_in.endswith(".IS"): s_in += ".IS"
        if s_in == "THYO": s_in = "THYAO.IS"
        
        # Sektör ve Hedef Fiyat alanlarını burada varsayılan (0 veya Diğer) olarak kaydediyoruz
        st.session_state.portfoy.append({
            "banka": b_sec, 
            "tip": t_sec, 
            "sembol": s_in, 
            "adet": a_in, 
            "maliyet": m_in, 
            "sektor": "Diğer",      # Gizli ama veri yapısı bozulmasın diye ekli
            "satis_hedefi": 0.0,    # Gizli varsayılan
            "alim_hedefi": 0.0      # Gizli varsayılan
        })
        from data_engine import veri_kaydet
        veri_kaydet_excel(st.session_state.portfoy)
        st.success(f"{s_in} Başarıyla Eklendi!")
        st.rerun()
        
    # --- 5. MADDE: EXCEL RAPOR ÇIKTISI ---
    st.divider()
    st.subheader("📑 Raporlama")
    if st.session_state.portfoy:
        # Mevcut veriyi excel'e dönüştür
        p_temp = piyasa_verisi_cek()
        df_export = portfoy_analiz(st.session_state.portfoy, p_temp)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Portfoy_Analizi')
        st.download_button(label="📥 Excel Raporu İndir", data=output.getvalue(), 
                           file_name="Portfoy_Rapor.xlsx", mime="application/vnd.ms-excel")

# 4. Hesaplamalar
p = piyasa_verisi_cek()
df = portfoy_analiz(st.session_state.portfoy, p)

# 5. Ana Ekran
st.title("💹 Finansal Portföy Yönetimi")

if not df.empty:
    toplam_tl = df['Değer_TL'].sum()
    toplam_usd = toplam_tl / (p['DOLAR'] if p['DOLAR'] > 0 else 1)
    
    # Üstteki metrikleri basıyoruz
    ui.metrik_paneli(p, toplam_tl, toplam_usd, df['Kar_TL'].sum())


    t1, t2, t3, t4, t5, t6= st.tabs(["📊 Genel Bakış", "🏦 Banka Yönetimi", "📅 Halka Arz", "💰 Temettü", "🚨 Alarmlar", "📰 Haber/KAP"])
    
    with t1:
        # --- 1. BİLDİRİM MERKEZİ (Tüm Alarmlar Burada) ---
        with st.expander("🔔 Kritik Portföy Uyarıları & Alarmlar", expanded=False):
            uyari_sayisi = 0
            
            # Sütun ismini kontrol et (Senin tablondaki gerçek ismi kullanıyoruz)
            oran_sutunu = '% Değişim' if '% Değişim' in df.columns else 'KarZarar_Oran'
            
            if oran_sutunu in df.columns:
                # 1. Zarar Kes Kontrolü
                riskli_varliklar = df[df[oran_sutunu] <= -10.0]
                if not riskli_varliklar.empty:
                    for _, row in riskli_varliklar.iterrows():
                        st.warning(f"📉 **Zarar Kes:** {row['sembol']} zarar %{abs(row[oran_sutunu]):.2f} seviyesinde!")
                        uyari_sayisi += 1
                
                # 2. Hedef Fiyat ve Alım Alarmları Kontrolü
                hisse_takip = df[df['tip'] == 'Hisse']
                if not hisse_takip.empty:
                    for _, row in hisse_takip.iterrows():
                        guncel_f = row['Değer_TL'] / row['adet'] if row['adet'] > 0 else 0
                        
                        # Satış Hedefi
                        if row.get('satis_hedefi', 0) > 0 and guncel_f >= row['satis_hedefi']:
                            st.success(f"🚀 **Hedef Fiyat:** {row['sembol']} beklediğin **{row['satis_hedefi']:.2f}₺** seviyesine ulaştı!")
                            uyari_sayisi += 1
                        
                        # Alım Fırsatı
                        if row.get('alim_hedefi', 0) > 0 and guncel_f <= row['alim_hedefi']:
                            st.info(f"💎 **Alım Fırsatı:** {row['sembol']} dip seviye olan **{row['alim_hedefi']:.2f}₺** altına indi!")
                            uyari_sayisi += 1
                
                if uyari_sayisi == 0:
                    st.success("✅ Şu an kritik bir alarm bulunmuyor kanka.")
            else:
                # Eğer hala bulamazsa tabloyu inceleyebilmen için bir ipucu verir
                st.info("🔄 Oranlar hesaplanıyor, lütfen bekleyin...")

        # --- 2. VARLIK DAĞILIMI GRAFİKLERİ ---
        c1, c2 = st.columns(2)
        with c1: 
            st.plotly_chart(px.pie(df, values='Değer_TL', names='tip', hole=0.5, title="Genel Varlık Dağılımı"), use_container_width=True)
        with c2: 
            st.plotly_chart(px.bar(df, x='sembol', y='Değer_TL', color='banka', title="Varlık Değerleri (Banka Bazlı)"), use_container_width=True)
        
        # --- 3. PORTFÖY HAREKETLERİ (3 SÜTUNLU & RENKLİ - GÜNCEL) ---
        st.divider()
        st.subheader("📊 Portföyündeki Günlük Hareketler")

        @st.cache_data(ttl=60)
        def portfoy_trend_analiz_v3(semboller, adetler_dict):
            import yfinance as yf
            sonuclar = []
            if not semboller: return pd.DataFrame()
            
            try:
                for s in semboller:
                    t = yf.Ticker(s)
                    hist = t.history(period="2d")
                    if not hist.empty and len(hist) >= 2:
                        son = hist['Close'].iloc[-1]
                        onceki = hist['Close'].iloc[-2]
                        yuzde_degisim = ((son - onceki) / onceki) * 100
                        
                        # Adetle çarparak TL bazlı günlük kâr/zararı bul
                        adet = adetler_dict.get(s, 0)
                        tl_degisim = (son - onceki) * adet
                        
                        sonuclar.append({
                            "Hisse": s.replace(".IS", ""), 
                            "Fiyat": son, 
                            "Günlük %": yuzde_degisim,
                            "Değişim (TL)": tl_degisim
                        })
            except: pass
            return pd.DataFrame(sonuclar)

        hisse_verileri = df[df['tip'] == 'Hisse'][['sembol', 'adet']].set_index('sembol')['adet'].to_dict()
        h_semboller = list(hisse_verileri.keys())

        if h_semboller:
            analiz_verisi = portfoy_trend_analiz_v3(h_semboller, hisse_verileri)
            
            if not analiz_verisi.empty:
                c_sol, c_sag = st.columns(2)
                tablo_config = {
                    "Fiyat": st.column_config.NumberColumn("Fiyat", format="₺%.2f"),
                    "Günlük %": st.column_config.NumberColumn("Günlük %", format="%%%.2f"),
                    "Değişim (TL)": st.column_config.NumberColumn("Değişim (TL)", format="₺%.2f")
                }

                with c_sol:
                    st.write("🚀 **En Çok Artanlar**")
                    en_iyi = analiz_verisi.sort_values("Günlük %", ascending=False).head(5)
                    # POZİTİF RENKLENDİRME (Yeşil)
                    st.dataframe(en_iyi.style.map(lambda x: 'color: #27ae60; font-weight: bold' if x > 0 else '', subset=['Günlük %', 'Değişim (TL)']), 
                                 column_config=tablo_config, hide_index=True, use_container_width=True)

                with c_sag:
                    st.write("🔻 **En Çok Azalanlar**")
                    en_kotu = analiz_verisi.sort_values("Günlük %", ascending=True).head(5)
                    # NEGATİF RENKLENDİRME (Kırmızı)
                    st.dataframe(en_kotu.style.map(lambda x: 'color: #e74c3c; font-weight: bold' if x < 0 else '', subset=['Günlük %', 'Değişim (TL)']), 
                                 column_config=tablo_config, hide_index=True, use_container_width=True)
    
            if 'analiz_verisi' in locals() and not analiz_verisi.empty:
                    # Sadece hisseleri kontrol edelim
                    hisseler_kontrol = df[df['tip'] == 'Hisse']
                    
                    for idx, row in hisseler_kontrol.iterrows():
                        # .IS ekini temizleyip kısa adı alıyoruz
                        h_kisa = row['sembol'].replace(".IS", "")
                        
                        # Analiz verisindeki canlı fiyatı bul
                        canli_row = analiz_verisi[analiz_verisi['Hisse'] == h_kisa]
                        
                        if not canli_row.empty:
                            anlik_f = canli_row['Fiyat'].values[0]
                    
                            # SATIŞ HEDEFİ KONTROLÜ
                            if row.get('satis_hedefi', 0) > 0 and anlik_f >= row['satis_hedefi']:
                                # 1. Ekranda görsel bildirim
                                st.balloons() 
                                st.toast(f"🚀 {h_kisa} Hedefe Uçtu!", icon="🔥")
                        
                                # 2. Mail Gönder
                                mail_gonder(
                                    f"🚀 HEDEF GÖRÜLDÜ: {h_kisa}", 
                                    f"Selam kanka, {h_kisa} hissesi {anlik_f}₺ oldu! Hedefine ulaştın. Alarm otomatik olarak silindi."
                                )

                                # 3. ALARMI SİL (Portföyde o sıradaki hissenin hedefini 0 yapar)
                                st.session_state.portfoy[idx]['satis_hedefi'] = 0
                                st.session_state.portfoy[idx]['alim_hedefi'] = 0
                                
                                # 4. VERİTABANINA KAYDET
                                from data_engine import veri_kaydet
                                veri_kaydet_excel(st.session_state.portfoy)
                                
                                # 5. SAYFAYI YENİLE (Mailin tekrar tekrar gitmesini engeller)
                                st.rerun()

        # --- 4. SEKTÖREL ANALİZ ---
        hisse_df = df[df['tip'] == 'Hisse']
        if not hisse_df.empty and 'sektor' in hisse_df.columns:
            st.divider()
            col_s1, col_s2 = st.columns([1, 1.5])
            with col_s1:
                st.plotly_chart(px.pie(hisse_df, values='Değer_TL', names='sektor', hole=0.4, title="🏗️ Sektörel Dağılım"), use_container_width=True)
            with col_s2:
                sektor_toplam = hisse_df.groupby('sektor')['Değer_TL'].sum()
                en_buyuk_sektor = sektor_toplam.idxmax()
                oran = (sektor_toplam.max() / hisse_df['Değer_TL'].sum()) * 100
                st.write(f"### 🛡️ Risk Analiz Raporu")
                if oran > 50:
                    st.error(f"**Yüksek Risk:** Portföyünün %{oran:.1f}'i **{en_buyuk_sektor}** sektöründe!")
                else:
                    st.success(f"**Dengeli:** Dağılımın gayet güzel.")

        # --- 5. GEÇMİŞ VERİLER ---
        from data_engine import gecmis_kaydet, gecmis_yukle
        gecmis_kaydet(toplam_tl)
        gecmis_veriler = gecmis_yukle()
        if len(gecmis_veriler) > 1:
            st.divider()
            st.subheader("📈 Portföy Değer Değişimi")
            g_df = pd.DataFrame(list(gecmis_veriler.items()), columns=['Tarih', 'Toplam Değer (TL)']).sort_values('Tarih')
            st.plotly_chart(px.line(g_df, x='Tarih', y='Toplam Değer (TL)', markers=True, line_shape='spline'), use_container_width=True)

    with t2:
        st.subheader("🏦 Banka Bazlı Performans Özeti")
        banka_ozet = df.groupby('banka').agg({'Değer_TL': 'sum', 'Kar_TL': 'sum'}).reset_index()
        banka_ozet['Maliyet_TL'] = banka_ozet['Değer_TL'] - banka_ozet['Kar_TL']
        banka_ozet['% Performans'] = (banka_ozet['Kar_TL'] / (banka_ozet['Maliyet_TL'] + 0.001)) * 100
        
        def style_ozet(styler):
            styler.applymap(lambda v: f'color: {"#28a745" if v > 0 else "#dc3545"}; font-weight: bold;', subset=['Kar_TL', '% Performans'])
            return styler

        st.dataframe(style_ozet(banka_ozet.style), column_config={
                "banka": "Banka",
                "Maliyet_TL": st.column_config.NumberColumn("Toplam Maliyet", format="₺%.2f"),
                "Değer_TL": st.column_config.NumberColumn("Güncel Değer", format="₺%.2f"),
                "Kar_TL": st.column_config.NumberColumn("Net Kâr/Zarar", format="₺%.2f"),
                "% Performans": st.column_config.NumberColumn("Verim (%)", format="%.2f%%")
            }, hide_index=True, use_container_width=True)
        
        st.divider()
        sec_banka = st.radio("Banka seçin:", ["Ziraat", "Kuveyt Türk", "Vakıfbank", "Tümü"], horizontal=True)
        b_df = df if sec_banka == "Tümü" else df[df['banka'] == sec_banka]

        if not b_df.empty:
            c_v, c_h = st.columns(2)
            with c_v: st.plotly_chart(px.pie(b_df, values='Değer_TL', names='tip', hole=0.4, title="Varlık Tipi Dağılımı"), use_container_width=True)
            with c_h:
                h_df = b_df[b_df['tip'] == 'Hisse']
                if not h_df.empty: st.plotly_chart(px.pie(h_df, values='Değer_TL', names='sembol', hole=0.4, title="Hisse Dağılımı"), use_container_width=True)

            ui.tablolari_goster(b_df, f"📍 {sec_banka} Portföy Listesi") 
            
            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                with st.expander("🎯 Hedef Fiyat Belirle/Güncelle"):
                    sec_h = st.selectbox("Varlık Seç:", options=b_df.index, format_func=lambda x: f"{df.loc[x, 'sembol']} (Mevcut: {df.loc[x, 'hedef']})")
                    yeni_h = st.number_input("Yeni Hedef Fiyat:", min_value=0.0, step=0.1)
                    if st.button("Hedefi Kaydet"):
                        st.session_state.portfoy[sec_h]['hedef'] = yeni_h
                        veri_kaydet_excel(st.session_state.portfoy); st.rerun()
            with col2:
                with st.expander("🗑️ Varlık Yönetimi (Silme)"):
                    silinecek = st.multiselect("Seç:", options=b_df.index, format_func=lambda x: f"{df.loc[x, 'sembol']}")
                    if st.button("Seçilenleri Sil", type="primary"):
                        st.session_state.portfoy = [v for i, v in enumerate(st.session_state.portfoy) if i not in silinecek]
                        veri_kaydet_excel(st.session_state.portfoy); st.rerun()
            
    with t3:
        # Halka arz takvimi (Dokunulmadı)
        st.subheader("📅 Halka Arz Takvimi (2026)")
        @st.cache_data(ttl=3600)
        def halka_arz_getir():
            import requests; from bs4 import BeautifulSoup; import io
            url = "https://halkaarz.com/takvim/"
            try:
                res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                soup = BeautifulSoup(res.text, 'html.parser')
                tablo = soup.find('table')
                if tablo:
                    df_arz = pd.read_html(io.StringIO(str(tablo)))[0]
                    if df_arz.empty or len(df_arz) < 1: return None, "Bos"
                    return df_arz.iloc[:, :5], "success"
                else: return None, "Bos"
            except: return None, "Hata"

        arz_data, durum = halka_arz_getir()
        if durum == "success": st.dataframe(arz_data, use_container_width=True, hide_index=True)
        elif durum == "Bos": st.info("📌 Aktif halka arz bulunamadı.")
        else: st.warning("⚠️ Halka arz takvimi çekilemiyor.")

    with t4:
        st.subheader("🎯 Temettü Emekliliği Planı")
        
        # --- EMEKLİLİK HEDEFLERİ ---
        col_set1, col_set2 = st.columns(2)
        with col_set1:
            hedef_aylik = st.number_input("Hedef Aylık Maaş (₺):", value=50000, step=1000)
            yillik_beklenti_orani = st.slider("Portföy Ortalama Temettü Verimi (%):", 1, 15, 6)
        
        yillik_hedef = hedef_aylik * 12
        tahmini_yillik_gelir = toplam_tl * (yillik_beklenti_orani / 100)
        karsilama_orani = (tahmini_yillik_gelir / yillik_hedef) * 100
        kalan_tutar = max(0.0, yillik_hedef - tahmini_yillik_gelir)
        
        # --- DURUM GÖSTERGELERİ ---
        st.divider()
        m1, m2, m3 = st.columns(3)
        m1.metric("Yıllık Tahmini Getiri", f"₺{tahmini_yillik_gelir:,.2f}")
        m2.metric("Emeklilik Karşılama Oranı", f"%{karsilama_orani:.1f}")
        m3.metric("Hedefe Kalan Yıllık Tutar", f"₺{kalan_tutar:,.2f}")
        
        st.progress(min(karsilama_orani/100, 1.0), text=f"Finansal Özgürlük Yolculuğu: %{karsilama_orani:.1f}")

        st.divider()
        
        # --- MANUEL TEMETTÜ GİRİŞİ ---
        st.subheader("💰 Temettü Tahsilatlarını İşle")
        from data_engine import temettu_kaydet, temettu_yukle
        if 'temettuler' not in st.session_state: st.session_state.temettuler = temettu_yukle()
        
        c1, c2, c3 = st.columns(3)
        h_liste = df[df['tip']=='Hisse']['sembol'].unique() if not df.empty else []
        with c1: t_hisse = st.selectbox("Hisse Seç", options=h_liste if len(h_liste)>0 else ["Yok"], key="manual_h_sel")
        with c2: t_miktar = st.number_input("Tahsil Edilen Tutar (₺)", min_value=0.0, key="manual_m_in")
        with c3: t_tarih = st.date_input("Tahsil Tarihi", key="manual_d_in")
        
        if st.button("Temettü Kaydını Tamamla", use_container_width=True):
            if t_hisse != "Yok" and t_miktar > 0:
                st.session_state.temettuler.append({"hisse": t_hisse, "miktar": t_miktar, "tarih": str(t_tarih)})
                temettu_kaydet(st.session_state.temettuler); st.rerun()

        # --- GÖRSEL ANALİZ (MANUEL VERİLERDEN) ---
        if st.session_state.temettuler:
            tdf = pd.DataFrame(st.session_state.temettuler)
            tdf['tarih'] = pd.to_datetime(tdf['tarih'])
            tdf['Ay'] = tdf['tarih'].dt.strftime('%B')
            
            col_a, col_b = st.columns([1, 1])
            with col_a:
                st.plotly_chart(px.pie(tdf, values='miktar', names='hisse', title="Hisse Bazlı Dağılım"), use_container_width=True)
            with col_b:
                # Aylık Takvim Grafiği (Senin girdiğin tarihlere göre)
                ay_sirasi = ['January', 'February', 'March', 'April', 'May', 'June', 
                             'July', 'August', 'September', 'October', 'November', 'December']
                aylik_ozet = tdf.groupby('Ay')['miktar'].sum().reindex(ay_sirasi).fillna(0)
                st.plotly_chart(px.bar(x=aylik_ozet.index, y=aylik_ozet.values, title="Aylık Tahsilat Takvimi", 
                                     labels={'x':'Ay', 'y':'₺'}, color_discrete_sequence=['#f39c12']), use_container_width=True)
            
            st.dataframe(tdf.sort_values('tarih', ascending=False), use_container_width=True, hide_index=True)
            if st.button("Tüm Geçmişi Temizle", type="primary"):
                temettu_kaydet([]); st.session_state.temettuler = []; st.rerun()
        else:
            st.info("Henüz bir temettü kaydı girmedin. İlk temettünü yukarıdan işleyebilirsin!")

    with t5:
        st.subheader("🎯 Hedef Fiyat ve Alarm Yönetimi")
    
        # --- 1. MANUEL ALARM KURMA ALANI ---
        with st.expander("➕ Yeni Hedef/Alarm Kur"):
            c1, c2, c3 = st.columns(3)
            hisse_opsiyonlari = df[df['tip']=='Hisse']
            if not hisse_opsiyonlari.empty:
                h_idx = c1.selectbox("Hisse Seç", options=hisse_opsiyonlari.index, 
                                    format_func=lambda x: f"{df.loc[x, 'sembol']}")
                h_tip = c2.selectbox("Alarm Tipi", ["Satış Hedefi (Üst)", "Alım Fırsatı (Alt)"])
                h_fiyat = c3.number_input("Hedef Fiyat (₺)", min_value=0.0, step=0.1)
                
                if st.button("Alarmı Kaydet", use_container_width=True):
                    if h_tip == "Satış Hedefi (Üst)":
                        st.session_state.portfoy[h_idx]['satis_hedefi'] = h_fiyat
                    else:
                        st.session_state.portfoy[h_idx]['alim_hedefi'] = h_fiyat
                    
                    from data_engine import veri_kaydet
                    veri_kaydet_excel(st.session_state.portfoy)
                    st.success(f"✅ {df.loc[h_idx, 'sembol']} için alarm kuruldu!")
                    st.rerun()
            else:
                st.info("Henüz portföyünde hisse bulunmuyor.")

        st.divider()
        st.subheader("🔔 Aktif Alarm Takibi")
    
        # --- 2. ALARMLARI KONTROL ETME VE LİSTELEME ---
        hisseler = df[df['tip']=='Hisse']
        if not hisseler.empty:
            for idx, row in hisseler.iterrows():
                guncel = row['Değer_TL'] / row['adet'] if row['adet'] > 0 else 0
                
                if row.get('satis_hedefi', 0) > 0:
                    if guncel >= row['satis_hedefi']:
                        st.success(f"🚀 **{row['sembol']}** Satış Hedefine Ulaştı! \n\n Güncel: {guncel:.2f}₺ | Hedef: {row['satis_hedefi']:.2f}₺")
                        st.balloons()
                    else:
                        st.info(f"⏳ {row['sembol']} Satış Bekleniyor... Hedef: {row['satis_hedefi']:.2f}₺")

                if row.get('alim_hedefi', 0) > 0:
                    if guncel <= row['alim_hedefi']:
                        st.warning(f"💎 **{row['sembol']}** Alım Bölgesinde! \n\n Güncel: {guncel:.2f}₺ | Hedef: {row['alim_hedefi']:.2f}₺")
                    else:
                        st.info(f"🔍 {row['sembol']} Alım İçin İzleniyor... Hedef: {row['alim_hedefi']:.2f}₺")
        else:
            st.write("Takip edilecek hisse bulunamadı.")

        # --- 3. ROBOT: KAR AL / ZARAR KES STRATEJİSİ (YENİ) ---
        st.divider()
        st.subheader("🤖 Kar Al / Zarar Kes Robotu")
        
        with st.expander("📉 Risk ve Kazanç Stratejisi Hesapla", expanded=True):
            if not hisseler.empty:
                c_robot1, c_robot2, c_robot3 = st.columns(3)
                with c_robot1:
                    secili_idx = st.selectbox("Strateji Kurulacak Hisse:", options=hisseler.index, 
                                            format_func=lambda x: f"{df.loc[x, 'sembol']}", key="robot_hisse_sec")
                    h_data = df.loc[secili_idx]
                    g_fiyat = h_data['Değer_TL'] / h_data['adet'] if h_data['adet'] > 0 else 0
                    st.info(f"💰 Maliyet: **{h_data['maliyet']:.2f}₺**\n\n📍 Güncel: **{g_fiyat:.2f}₺**")

                with c_robot2:
                    kar_oran = st.slider("Hedef Kar Oranı (%)", 5, 100, 20, key="robot_kar_slider")
                    hedef_satis = h_data['maliyet'] * (1 + kar_oran/100)
                    st.write(f"🎯 **Hedef Satış:**")
                    st.write(f"### ₺{hedef_satis:.2f}")

                with c_robot3:
                    stop_oran = st.slider("Zarar Kes Oranı (%)", 2, 20, 5, key="robot_stop_slider")
                    stop_fiyat = h_data['maliyet'] * (1 - stop_oran/100)
                    st.write(f"🛡️ **Zarar Kes (Stop):**")
                    st.write(f"### ₺{stop_fiyat:.2f}")

                st.divider()
                r1, r2, r3 = st.columns(3)
                beklenen_kar = (hedef_satis - h_data['maliyet']) * h_data['adet']
                beklenen_zarar = (h_data['maliyet'] - stop_fiyat) * h_data['adet']
                
                r1.metric("Hedeflenen Net Kar", f"₺{beklenen_kar:,.2f}", delta=f"%{kar_oran}")
                r2.metric("Maksimum Risk", f"-₺{beklenen_zarar:,.2f}", delta=f"-%{stop_oran}", delta_color="inverse")
                r3.metric("Toplam Tahsilat", f"₺{(hedef_satis * h_data['adet']):,.2f}")

                if st.button("🚀 Bu Stratejiyi Alarmlara Kaydet", use_container_width=True):
                    # 1. Veriyi Kaydet
                    st.session_state.portfoy[secili_idx]['satis_hedefi'] = round(hedef_satis, 2)
                    st.session_state.portfoy[secili_idx]['alim_hedefi'] = round(stop_fiyat, 2)
                    from data_engine import veri_kaydet
                    veri_kaydet_excel(st.session_state.portfoy)
                    
                    # 2. Mail Gönder (Burada mail fonksiyonunu çağırıyoruz)
                    mail_konu = f"🤖 Robotik Strateji Kuruldu: {h_data['sembol']}"
                    mail_icerik = f"""
                    Merhaba, {h_data['sembol']} için stratejin aktif edildi:
                    
                    🎯 Satış Hedefi: {hedef_satis:.2f} ₺
                    🛡️ Zarar Kes (Stop): {stop_fiyat:.2f} ₺
                    💰 Beklenen Net Kar: {beklenen_kar:,.2f} ₺
                    
                    Fiyat bu seviyelere gelince sana tekrar mail atacağım!
                    """
                    mail_gonder(mail_konu, mail_icerik)
                    
                    st.success(f"✅ {h_data['sembol']} stratejisi kaydedildi ve bilgilendirme maili gönderildi!")
                    st.rerun()
            else:
                st.info("Hesaplama yapmak için portföyünde hisse olmalı.")


    with t6:
        st.subheader("🎯 Hisse Analiz Terminali")
        
        # .IS uzantısını temizle
        hisse_listesi = [s.split('.')[0] for s in df[df['tip']=='Hisse']['sembol'].unique()]
        
        if hisse_listesi:
            secilen_hisse = st.selectbox("İncelemek istediğin hisseyi seç:", hisse_listesi)
            
            # --- ÜST PANEL: ÖZET KISIMLAR (İçeride Kalanlar) ---
            col_sol, col_sag = st.columns([1, 1])

            with col_sol:
                st.write(f"### 📊 Teknik Özet")
                # Çalışan meşhur ibre
                ta_html = f"""
                <div style="height:430px;">
                  <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-technical-analysis.js" async>
                  {{
                    "interval": "1D", "width": "100%", "isTransparent": false, "height": 400,
                    "symbol": "BIST:{secilen_hisse}", "showIntervalTabs": true, "locale": "tr", "colorTheme": "light"
                  }}
                  </script>
                </div>
                """
                st.components.v1.html(ta_html, height=430)

            with col_sag:
                st.write(f"### 📑 Finansal Özet")
                # Şirket finansal tablosu (Bu da içeride hatasız çalışıyor)
                profile_html = f"""
                <div class="tradingview-widget-container">
                  <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-financials.js" async>
                  {{
                    "symbol": "BIST:{secilen_hisse}",
                    "colorTheme": "light", "isTransparent": false, "displayMode": "regular",
                    "width": "100%", "height": 400, "locale": "tr"
                  }}
                  </script>
                </div>
                """
                st.components.v1.html(profile_html, height=430)

            st.divider()

            # --- ALT PANEL: BUTONLAR (Dışarıya Açılanlar) ---
            st.write(f"###  {secilen_hisse} Detaylı Takip")
            
            c1, c2 = st.columns(2)
            with c1:
                # 'type="primary"' kısmını sildik, böylece yanındakiyle aynı renk oldu
                st.link_button(
                    f"📰 {secilen_hisse} Haberlerini Aç", 
                    f"https://tr.tradingview.com/symbols/BIST-{secilen_hisse}/news/", 
                    use_container_width=True
                )
            with c2:
                # Grafik Butonu (TradingView'e gider)
                st.link_button(
                    f"📈 {secilen_hisse} Detaylı Grafiği Aç", 
                    f"https://tr.tradingview.com/chart/?symbol=BIST:{secilen_hisse}", 
                    use_container_width=True,
                    type="secondary"
                )

        else:
            st.info("Terminali kullanmak için portföyüne hisse eklemelisin.") 

# --- BURADAN İTİBAREN EN SOLA YASLI OLACAK ---
simdi = datetime.datetime.now()

# Cuma 18:10 kontrolü
if simdi.weekday() == 4 and simdi.hour == 18 and simdi.minute == 10:
    if 'rapor_gonderildi' not in st.session_state:
        # df değişkenini kullanarak raporu gönder
        if not df.empty:
            haftalik_ozet_gonder(df)
            st.session_state['rapor_gonderildi'] = True
            st.toast("📩 Haftalık özet raporun gönderildi!", icon="📊")

# Kilidi açma (Bir sonraki hafta için)
if simdi.hour == 18 and simdi.minute == 11:
    if 'rapor_gonderildi' in st.session_state:
        del st.session_state['rapor_gonderildi']
