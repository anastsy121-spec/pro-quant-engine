import streamlit as st
import numpy as np
import math

st.set_page_config(page_title="PRO QUANT ENGINE V1.5.4-PRO", layout="wide")
st.title("⚽ PRO QUANT ENGINE V1.5.4-PRO — Quantitative Betting Engine")
st.markdown("---")

# --- CORE MATHEMATICAL ENGINE (PYTHON PORT) ---
def log_factorial(n):
    if not isinstance(n, int) or n < 0:
        raise ValueError("Invalid factorial input")
    if n == 0:
        return 0.0
    x = n + 1
    z = x - 1
    c = [676.5203681218851, -1259.1392167224028, 771.3234287776531, -176.6150291621406, 12.507343278686905, -0.13857109526572012, 9.984369578019572e-6, 1.5056327351493116e-7]
    y = 0.99999999999980993
    for i, val in enumerate(c):
        y += val / (z + i + 1)
    t = z + len(c) - 0.5
    return 0.5 * math.log(2 * math.pi) + (z + 0.5) * math.log(t) - t + math.log(y)

def dixon_coles_tau(h, a, lh, la, rho):
    t = 1.0
    if h == 0 and a == 0:
        t = 1.0 - lh * la * rho
    elif h == 0 and a == 1:
        t = 1.0 + lh * rho
    elif h == 1 and a == 0:
        t = 1.0 + la * rho
    elif h == 1 and a == 1:
        t = 1.0 - rho
    if not (t > 0) or not math.isfinite(t):
        raise ValueError("Non-positive Dixon-Coles tau")
    return t

def predict_markets(lh, la, rho, tail_tolerance=1e-10, max_goals=100):
    if lh <= 0 or la <= 0:
        raise ValueError("Lambdas must be > 0")
    if not (-0.15 <= rho <= 0.15):
        raise ValueError("rho outside [-0.15, 0.15]")
    
    n = max(10, int(math.ceil(max(lh, la) + 10 * math.sqrt(max(lh, la) + 1) + 10)))
    n = min(n, max_goals)
    
    while True:
        ph = [math.exp(-lh) * (lh ** k) / math.exp(log_factorial(k)) for k in range(n + 1)]
        pa = [math.exp(-la) * (la ** k) / math.exp(log_factorial(k)) for k in range(n + 1)]
        base = sum(ph) * sum(pa)
        tail = max(0.0, 1.0 - base)
        if tail <= tail_tolerance:
            break
        if n >= max_goals:
            raise ValueError(f"CRITICAL_TAIL_MASS_ERROR: tail {tail} exceeds tolerance")
        n = min(max_goals, max(n + 10, int(n * 1.5)))
        
    sums = {"home": 0.0, "draw": 0.0, "away": 0.0, "over25": 0.0, "under25": 0.0, "bttsYes": 0.0, "bttsNo": 0.0}
    total = 0.0
    
    for h in range(n + 1):
        for a in range(n + 1):
            q = ph[h] * pa[a] * dixon_coles_tau(h, a, lh, la, rho)
            total += q
            if h > a:
                sums["home"] += q
            elif h == a:
                sums["draw"] += q
            else:
                sums["away"] += q
            if h + a > 2:
                sums["over25"] += q
            else:
                sums["under25"] += q
            if h > 0 and a > 0:
                sums["bttsYes"] += q
            else:
                sums["bttsNo"] += q
                
    p = {k: v / total for k, v in sums.items()}
    return p, rho, lh, la

def remove_overround(odds):
    raw = [1.0 / o for o in odds]
    total = sum(raw)
    return total - 1.0, [x / total for x in raw]

def calculate_ev(p, o):
    return p * o - 1.0

def kelly(p, o, fraction=0.25, bankroll=100, cap=0.02):
    ev = calculate_ev(p, o)
    full = ev / (o - 1.0)
    if ev <= 0 or full <= 0:
        return {"has_edge": False, "ev": ev, "stake": 0.0}
    f = min(full * fraction, cap)
    return {"has_edge": True, "ev": ev, "stake": bankroll * f}

# --- STREAMLIT UI ---
st.sidebar.header("⚙️ إعدادات المحرك الكمي")
home_team = st.sidebar.text_input("الفريق المضيف", "Alianza Valledupar")
away_team = st.sidebar.text_input("الفريق الضيف", "Llaneros FC")
home_lambda = st.sidebar.slider("القوة الهجومية المتوقعة (مضيف - Lambda)", 0.5, 3.0, 1.35, 0.05)
away_lambda = st.sidebar.slider("القوة الهجومية المتوقعة (ضيف - Lambda)", 0.5, 3.0, 1.15, 0.05)
rho_val = st.sidebar.slider("معامل الارتباط (Dixon-Coles Rho)", -0.15, 0.15, 0.0, 0.01)

st.subheader("📊 أسعار السوق (Decimal Odds)")
col1, col2, col3 = st.columns(3)
with col1:
    odd_home = st.number_input("فوز المضيف (1)", min_value=1.01, value=2.10, step=0.01)
with col2:
    odd_draw = st.number_input("التعادل (X)", min_value=1.01, value=3.10, step=0.01)
with col3:
    odd_away = st.number_input("فوز الضيف (2)", min_value=1.01, value=3.20, step=0.01)

col4, col5 = st.columns(2)
with col4:
    odd_over25 = st.number_input("أكثر من 2.5 أهداف (+)", min_value=1.01, value=2.00, step=0.01)
with col5:
    odd_under25 = st.number_input("أقل من 2.5 أهداف (-)", min_value=1.01, value=1.67, step=0.01)

if st.button("تشغيل التحليل الكمي المتكامل"):
    try:
        # حساب الاحتمالات عبر نموذج بواسن وديكسون-كولز
        probs, rho, lh, la = predict_markets(home_lambda, away_lambda, rho_val)
        
        st.markdown("---")
        st.subheader("📈 النتائج الاحتمالية للمحرك:")
        
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.metric(label=f"فوز {home_team}", value=f"{probs['home']*100:.1f}%", delta=f"سعر عادل: {1/probs['home']:.2f}")
        with m_col2:
            st.metric(label="التعادل", value=f"{probs['draw']*100:.1f}%", delta=f"سعر عادل: {1/probs['draw']:.2f}")
        with m_col3:
            st.metric(label=f"فوز {away_team}", value=f"{probs['away']*100:.1f}%", delta=f"سعر عادل: {1/probs['away']:.2f}")
            
        st.markdown("---")
        st.subheader("🎯 فحص القيمة والقرار الصارم (Pipeline Decision):")
        
        overround_1x2, fair_1x2 = remove_overround([odd_home, odd_draw, odd_away])
        st.write(f"**نسبة هامش صانع الدفعات (Overround):** {overround_1x2 * 100:.2f}%")
        
        # تقييم الرهان عبر معيار كيلي
        k_home = kelly(probs['home'], odd_home)
        k_away = kelly(probs['away'], odd_away)
        
        if k_home['has_edge'] and k_home['ev'] > 0.03:
            st.success(f"✅ رهان مؤهل (QUALIFIED_BET): فوز {home_team} بقيمة متوقعة EV = {k_home['ev']*100:.2f}%")
        elif k_away['has_edge'] and k_away['ev'] > 0.03:
            st.success(f"✅ رهان مؤهل (QUALIFIED_BET): فوز {away_team} بقيمة متوقعة EV = {k_away['ev']*100:.2f}%")
        else:
            st.warning("⚠️ الحالة الحالية تصنف كـ **NO_BET** أو **LEAN** لعدم تجاوز عتبة الحافة الربحية المطلوبة بدقة.")
            
    except Exception as e:
        st.error(f"خطأ في الحسابات الرياضية: {str(e)}")
