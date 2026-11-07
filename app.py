import streamlit as st
import numpy as np
import pandas as pd
from scipy.stats import poisson

# إعدادات الصفحة لهواتف المحمول
st.set_page_config(
    page_title="PRO QUANT ENGINE",
    page_icon="⚽",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- NATIVE MATH ENGINE ---
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

def calculate_match_engine(att_home, def_away, att_away, def_home, avg_home, avg_away, rho=-0.13, max_goals=6):
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
        "xG_Home": lambda_x,
        "xG_Away": mu_y,
        "prob_home": prob_home,
        "prob_draw": prob_draw,
        "prob_away": prob_away,
        "fair_home": 1 / prob_home if prob_home > 0 else 0,
        "fair_draw": 1 / prob_draw if prob_draw > 0 else 0,
        "fair_away": 1 / prob_away if prob_away > 0 else 0
    }

# --- STREAMLIT UI ---
st.title("🛡️ PRO QUANT ENGINE")
st.caption("محرك تحليل الاحتمالات واكتشاف القيمة (Mobile Version)")

tab1, tab2 = st.tabs(["📊 تحليل مباراة واحدة", "📁 جدول تتبع الأسواق (CSV)"])

with tab1:
    st.subheader("بيانات قوى الفرق")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**الفريق المستضيف (Home)**")
        att_h = st.number_input("قوة الهجوم (Home)", value=1.35, step=0.05)
        def_h = st.number_input("قوة الدفاع (Home)", value=0.85, step=0.05)
    with col2:
        st.markdown("**الفريق الضيف (Away)**")
        att_a = st.number_input("قوة الهجوم (Away)", value=0.90, step=0.05)
        def_a = st.number_input("قوة الدفاع (Away)", value=1.20, step=0.05)
        
    st.markdown("---")
    st.subheader("أسعار السوق الحالية (Market Odds)")
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        mkt_home = st.number_input("سوق (1)", value=1.55, step=0.05)
    with col_m2:
        mkt_draw = st.number_input("سوق (X)", value=4.80, step=0.05)
    with col_m3:
        mkt_away = st.number_input("سوق (2)", value=8.50, step=0.05)

    if st.button("🚀 تشغيل التحليل", use_container_width=True):
        res = calculate_match_engine(att_h, def_a, att_a, def_h, 1.50, 1.10)
        
        st.markdown("### 📈 النتيجة المتوقعة (xG)")
        st.info(f"xG Home: **{res['xG_Home']:.2f}** | xG Away: **{res['xG_Away']:.2f}**")

        st.markdown("### ⚖️ السعر العادل مقابل السوق (Edge Analysis)")
        
        edge_h = (res['prob_home'] * mkt_home) - 1
        edge_d = (res['prob_draw'] * mkt_draw) - 1
        edge_a = (res['prob_away'] * mkt_away) - 1
        
        st.write(f"**فوز الأرض (1):** عادل `{res['fair_home']:.2f}` | السوق `{mkt_home:.2f}` | الهامش: **{edge_h*100:+.1f}%** {'🟢' if edge_h > 0 else '🔴'}")
        st.write(f"**التعادل (X):** عادل `{res['fair_draw']:.2f}` | السوق `{mkt_draw:.2f}` | الهامش: **{edge_d*100:+.1f}%** {'🟢' if edge_d > 0 else '🔴'}")
        st.write(f"**فوز الضيف (2):** عادل `{res['fair_away']:.2f}` | السوق `{mkt_away:.2f}` | الهامش: **{edge_a*100:+.1f}%** {'🟢' if edge_a > 0 else '🔴'}")

        st.markdown("---")
        if edge_h > 0.05:
            st.success("🟢 **توصية المحرك:** فرصة قوية على فوز المستضيف (Home Win Value Bet)")
        elif edge_a > 0.05:
            st.success("🟢 **توصية المحرك:** فرصة قوية على فوز الضيف (Away Win Value Bet)")
        else:
            st.warning("⚠️ **القرار: NO BET** - لا يوجد هامش ربح كافٍ يبرر المخاطرة.")

with tab2:
    st.subheader("رفع جدول المباريات والأسعار")
    uploaded_file = st.file_uploader("قم برفع ملف CSV للمباريات", type=["csv"])
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.dataframe(df)
