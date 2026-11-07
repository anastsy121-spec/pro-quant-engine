import streamlit as st
import numpy as np
import pandas as pd
from scipy.stats import poisson
from PIL import Image

st.set_page_config(
    page_title="PRO QUANT Engine",
    page_icon="⚽",
    layout="centered"
)

def dixon_coles_adjustment(x, y, lambda_x, mu_y, rho):
    if x == 0 and y == 0:
        return 1 - (lambda_x * mu_y * rho)
    elif x == 0 and y == 1:
        return 1 + (lambda_x * rho)
    elif x == 1 and y == 0:
        return 1 + (mu_y * rho)
    elif x == 1 and y == 1:
        return 1 - rho
    else:
        return 1.0

def calculate_match_engine(att_home, def_away, att_away, def_home, avg_home=1.50, avg_away=1.10, rho=-0.13, max_goals=6):
    lambda_x = att_home * def_away * avg_home
    mu_y = att_away * def_home * avg_away
    
    matrix = np.zeros((max_goals + 1, max_goals + 1))
    for x in range(max_goals + 1):
        for y in range(max_goals + 1):
            p_x = poisson.pmf(x, lambda_x)
            p_y = poisson.pmf(y, mu_y)
            adj = dixon_coles_adjustment(x, y, lambda_x, mu_y, rho)
            matrix[x, y] = p_x * p_y * adj

    matrix = np.maximum(matrix, 0)
    matrix /= matrix.sum()

    prob_home = np.sum(np.tril(matrix, -1))
    prob_draw = np.sum(np.diag(matrix))
    prob_away = np.sum(np.triu(matrix, 1))
    
    return {
        "xG_Home": lambda_x, "xG_Away": mu_y,
        "prob_home": prob_home, "prob_draw": prob_draw, "prob_away": prob_away,
        "fair_home": 1 / prob_home if prob_home > 0 else 0,
        "fair_draw": 1 / prob_draw if prob_draw > 0 else 0,
        "fair_away": 1 / prob_away if prob_away > 0 else 0
    }

st.title("⚽ PRO QUANT (التحليل الذكي)")
st.caption("ارفع لقطة الشاشة للمباراة وأدخل الأسعار للتحليل الفوري")

uploaded_image = st.file_uploader("اختر لقطة الشاشة من هاتفك", type=["jpg", "jpeg", "png"])

if uploaded_image is not None:
    img = Image.open(uploaded_image)
    st.image(img, caption="لقطة الشاشة الحالية", use_container_width=True)

with st.form("match_form"):
    st.subheader("📝 بيانات المباراة والأودز")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        mkt_h = st.number_input("سعر 1", value=2.00, step=0.01)
    with c2:
        mkt_d = st.number_input("سعر التعادل X", value=3.20, step=0.01)
    with c3:
        mkt_a = st.number_input("سعر 2", value=3.00, step=0.01)
        
    st.subheader("⚙️ قوة الفريقين")
    col1, col2 = st.columns(2)
    with col1:
        att_h = st.number_input("هجوم المستضيف", value=1.20, step=0.05)
        def_h = st.number_input("دفاع المستضيف", value=1.00, step=0.05)
    with col2:
        att_a = st.number_input("هجوم الضيف", value=1.10, step=0.05)
        def_a = st.number_input("دفاع الضيف", value=1.00, step=0.05)

    submitted = st.form_submit_button("🚀 تشغيل التحليل الرياضي", use_container_width=True)

if submitted:
    res = calculate_match_engine(att_h, def_a, att_a, def_h)
    
    st.markdown("---")
    st.success(f"xG المستضيف: **{res['xG_Home']:.2f}** | xG الضيف: **{res['xG_Away']:.2f}**")
    
    edge_h = (res['prob_home'] * mkt_h) - 1
    edge_d = (res['prob_draw'] * mkt_d) - 1
    edge_a = (res['prob_away'] * mkt_a) - 1
    
    st.write(f"**فوز المستضيف (1):** عادل `{res['fair_home']:.2f}` | السوق `{mkt_h:.2f}` | الهامش: **{edge_h*100:+.1f}%** {'🟢' if edge_h > 0 else '🔴'}")
    st.write(f"**التعادل (X):** عادل `{res['fair_draw']:.2f}` | السوق `{mkt_d:.2f}` | الهامش: **{edge_d*100:+.1f}%** {'🟢' if edge_d > 0 else '🔴'}")
    st.write(f"**فوز الضيف (2):** عادل `{res['fair_away']:.2f}` | السوق `{mkt_a:.2f}` | الهامش: **{edge_a*100:+.1f}%** {'🟢' if edge_a > 0 else '🔴'}")
    
    st.markdown("---")
    if edge_h > 0.05 or edge_a > 0.05:
        st.success("🟢 **توصية المحرك: يوجد رهان قيمة (Value Bet)**")
    else:
        st.warning("⚠️ **القرار: NO BET - لا يوجد هامش ربح**")
