import streamlit as st
import pandas as pd

def metrik_paneli(p, toplam_tl, toplam_usd, kar_toplam):
    st.markdown("""
        <style>
        .metric-card {
            background-color: #ffffff;
            border-radius: 12px;
            padding: 15px;
            border: 1px solid #e6e9ef;
            box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
            text-align: center;
            margin-bottom: 10px;
        }
        .market-card {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-left: 5px solid #007bff;
        }
        .profit-card { border-left: 5px solid #28a745; background-color: #f6fff8; }
        .loss-card { border-left: 5px solid #dc3545; background-color: #fff6f6; }
        .metric-label { font-size: 14px; color: #6c757d; font-weight: bold; margin-bottom: 5px; }
        .metric-value { font-size: 20px; font-weight: 800; color: #1c1e21; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("### 🌍 Piyasa Takibi")
    c1, c2, c3, c4 = st.columns(4)
    piyasa_html = '<div class="metric-card market-card"><div class="metric-label">{label}</div><div class="metric-value">₺{val}</div></div>'
    
    c1.markdown(piyasa_html.format(label="GRAM ALTIN", val=p['ALTIN']), unsafe_allow_html=True)
    c2.markdown(piyasa_html.format(label="GRAM GÜMÜŞ", val=p['GÜMÜŞ']), unsafe_allow_html=True)
    c3.markdown(piyasa_html.format(label="DOLAR/TL", val=p['DOLAR']), unsafe_allow_html=True)
    c4.markdown(piyasa_html.format(label="EURO/TL", val=p['EURO']), unsafe_allow_html=True)

    st.markdown("### 💼 Portföy Özeti")
    m1, m2, m3 = st.columns(3)
    ozet_stili = "profit-card" if kar_toplam >= 0 else "loss-card"
    
    m1.markdown(f'<div class="metric-card"><div class="metric-label">TOPLAM VARLIK</div><div class="metric-value">₺{toplam_tl:,.2f}</div></div>', unsafe_allow_html=True)
    m2.markdown(f'<div class="metric-card"><div class="metric-label">DOLAR KARŞILIĞI</div><div class="metric-value">${toplam_usd:,.2f}</div></div>', unsafe_allow_html=True)
    m3.markdown(f'<div class="metric-card {ozet_stili}"><div class="metric-label">NET KAR/ZARAR</div><div class="metric-value">₺{kar_toplam:,.2f}</div></div>', unsafe_allow_html=True)
    st.divider()

def tablolari_goster(df, baslik_metni):
    st.subheader(baslik_metni)
    
    if df.empty:
        st.info("Listelenecek varlık bulunamadı.")
        return

    # Hata verebilecek sütunları garantiye alıyoruz
    display_df = df.copy()
    
    # Renklendirme fonksiyonu (Sadece var olan sütunlara uygulanır)
    def style_df(styler):
        # Kar ve Değişim Renkleri
        if 'Kar_TL' in display_df.columns and '% Değişim' in display_df.columns:
            styler.applymap(lambda v: f'color: {"#28a745" if v > 0 else "#dc3545"}; font-weight: bold;', 
                            subset=['Kar_TL', '% Değişim'])
        
        # Hedef Durum Renkleri (Sarı/Yeşil)
        if 'Hedef_Durum' in display_df.columns:
            styler.applymap(lambda v: 'background-color: #fff3cd;' if 95 <= v < 100 else ('background-color: #d4edda;' if v >= 100 else ''), 
                            subset=['Hedef_Durum'])
        return styler

    # Tabloyu basıyoruz
    st.dataframe(
        style_df(display_df.style),
        use_container_width=True,
        column_config={
            "banka": "Banka",
            "tip": "Tür",
            "sembol": "Sembol",
            "adet": st.column_config.NumberColumn("Miktar/Gram", format="%.2f"), 
            "maliyet": st.column_config.NumberColumn("Maliyet (TL)", format="₺%.2f"),
            "Güncel": st.column_config.NumberColumn("Güncel", format="₺%.2f"),
            "Değer_TL": st.column_config.NumberColumn("Değer (TL)", format="₺%.2f"),
            "Kar_TL": st.column_config.NumberColumn("Kâr/Zarar", format="₺%.2f"),
            "% Değişim": st.column_config.NumberColumn("Değişim %", format="%.2f%%"),
            "Hedef_Durum": st.column_config.NumberColumn("Hedef %", format="%.1f%%")
        },
        hide_index=True
    )