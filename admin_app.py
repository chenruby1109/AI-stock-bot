"""
admin_app.py — 管理員專屬頁面
只有管理員能建立/刪除帳號，完全獨立運行
執行：streamlit run admin_app.py --server.port 8502
"""
import streamlit as st
import gist_db as db

st.set_page_config(page_title="AI Stock Bot 管理後台", page_icon="👑", layout="centered")

st.markdown("""
<style>
body,[class*="css"]{background:#0a0e1a;color:#e2e8f0;font-family:'Segoe UI',sans-serif;}
.stApp{background:#0a0e1a;}
.stTextInput>div>div>input{background:#131929!important;border:1px solid #2d3a52!important;
    border-radius:8px!important;color:#e2e8f0!important;}
.stSelectbox>div>div{background:#131929!important;border:1px solid #2d3a52!important;
    border-radius:8px!important;color:#e2e8f0!important;}
.card{background:#131929;border:1px solid #1e2a3a;border-radius:14px;padding:20px;margin-bottom:12px;}
.badge-admin{background:#1e3a5f;color:#38bdf8;font-size:11px;padding:2px 8px;border-radius:5px;font-weight:700;}
.badge-user{background:#1e1640;color:#a78bfa;font-size:11px;padding:2px 8px;border-radius:5px;font-weight:700;}
.stButton>button[kind="primary"]{background:linear-gradient(135deg,#0ea5e9,#6366f1)!important;
    color:#fff!important;border:none!important;border-radius:8px!important;font-weight:600!important;}
</style>
""", unsafe_allow_html=True)

# Session
if "admin_user" not in st.session_state:
    st.session_state.admin_user = None

# ── 登入 ──
if st.session_state.admin_user is None:
    st.markdown("## 👑 AI Stock Bot 管理後台")
    st.caption("僅限管理員登入")
    st.markdown("---")
    u = st.text_input("管理員帳號")
    p = st.text_input("密碼", type="password")
    if st.button("🔐 登入", type="primary"):
        user = db.login(u, p)
        if user and user.get("role") == "admin":
            st.session_state.admin_user = user
            st.rerun()
        elif user:
            st.error("❌ 非管理員帳號")
        else:
            st.error("❌ 帳號或密碼錯誤")
    st.stop()

admin = st.session_state.admin_user
st.markdown(f"## 👑 管理後台")
st.caption(f"登入身份：{admin['display_name']} (@{admin['username']})")

if st.button("登出"):
    st.session_state.admin_user = None
    st.rerun()

st.markdown("---")
tab1, tab2 = st.tabs(["➕ 建立帳號", "👥 用戶列表"])

# ════════════════════════════════════════
# TAB 1：建立帳號
# ════════════════════════════════════════
with tab1:
    st.markdown("### ➕ 建立新用戶帳號")
    st.caption("所有帳號由管理員手動建立，用戶無法自行註冊")

    with st.container(border=True):
        nu  = st.text_input("帳號（英文小寫）", placeholder="如：john")
        npw = st.text_input("初始密碼", type="password", placeholder="至少 4 碼")
        npw2= st.text_input("確認密碼", type="password", placeholder="再輸一次")
        nd  = st.text_input("顯示名稱", placeholder="如：小明")
        nr  = st.selectbox("角色", ["user", "admin"])
        tg  = st.text_input("Telegram Chat ID（選填）", placeholder="-5235921327")

        if st.button("✅ 建立帳號", type="primary", use_container_width=True):
            if not nu or not npw:
                st.error("❌ 帳號與密碼為必填")
            elif npw != npw2:
                st.error("❌ 兩次密碼不一致")
            else:
                ok, msg = db.create_user(nu, npw, nd or nu, nr)
                if ok:
                    if tg:
                        db.update_telegram(nu.strip().lower(), tg)
                    st.success(f"✅ 帳號 **{nu}** 建立成功！")
                    st.info(f"帳號：`{nu.strip().lower()}` ｜ 初始密碼：`{npw}`\n\n請將帳密傳給用戶，並提醒他們登入後修改密碼。")
                else:
                    st.error(f"❌ {msg}")

# ════════════════════════════════════════
# TAB 2：用戶列表
# ════════════════════════════════════════
with tab2:
    st.markdown("### 👥 所有用戶")
    all_users = db.get_all_users()
    st.caption(f"共 {len(all_users)} 位用戶")

    for uname, uinfo in all_users.items():
        role   = uinfo.get("role", "user")
        badge  = f"<span class='badge-admin'>👑 管理員</span>" if role=="admin" else f"<span class='badge-user'>👤 用戶</span>"
        tg_s   = "✅ " + uinfo.get("telegram_chat_id","") if uinfo.get("telegram_chat_id") else "❌ 未設定"
        wl_n   = len(uinfo.get("watchlist",[]))

        st.markdown(f"""
        <div class='card'>
            <div style='display:flex;justify-content:space-between;align-items:center'>
                <div>
                    <span style='font-size:16px;font-weight:700;color:#f8fafc'>{uinfo.get('display_name',uname)}</span>
                    <span style='color:#64748b;margin:0 8px'>@{uname}</span>
                    {badge}
                </div>
                <div style='font-size:12px;color:#64748b'>建立：{uinfo.get('created_at','—')}</div>
            </div>
            <div style='margin-top:8px;font-size:13px;color:#64748b'>
                TG：{tg_s} ｜ 觀察名單：{wl_n} 支
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander(f"⚙️ 管理 {uname}"):
            c1, c2 = st.columns(2)
            with c1:
                new_tg = st.text_input("更新 Telegram ID", key=f"tg_{uname}",
                                        value=uinfo.get("telegram_chat_id",""))
                if st.button("💾 更新 TG", key=f"utg_{uname}"):
                    db.update_telegram(uname, new_tg)
                    st.success("✅ 已更新"); st.rerun()
            with c2:
                new_pw = st.text_input("重設密碼", type="password", key=f"rpw_{uname}")
                if st.button("🔑 重設密碼", key=f"rp_{uname}"):
                    ok, msg = db.admin_reset_password(uname, new_pw)
                    st.success(msg) if ok else st.error(msg)

            if uname != admin["username"]:
                st.markdown("---")
                if st.button(f"🗑️ 刪除帳號 {uname}", key=f"del_{uname}", type="secondary"):
                    ok, msg = db.delete_user(uname)
                    st.success(msg) if ok else st.error(msg)
                    st.rerun()
            else:
                st.caption("（不能刪除自己）")
