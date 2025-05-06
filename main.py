import streamlit as st
from PIL import Image
from database import SessionLocal
from models import User, Plant
from routers.plant import ImageProcessor, FileHandler, get_disease_description # get_disease_description'ı async yerine sync yapacağız
from passlib.context import CryptContext
import os
import asyncio

def predict_disease(img):
    processor = ImageProcessor()
    # Görseli geçici olarak kaydet
    temp_path = "temp_predict.jpg"
    img.save(temp_path)
    prediction = processor.predict(temp_path)
    try:
        label = processor.model.config.id2label[prediction]
    except Exception:
        label = "Unknown"
    os.remove(temp_path)
    return label

bcrypt = CryptContext(schemes=["bcrypt"], deprecated="auto")

st.title("Tarım Koçum")

if "login" not in st.session_state:
    st.session_state.login = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None

# ------------------------------------------------
# 1) Giriş/Kayıt modu
if not st.session_state.login:
    mode = st.radio("Mod seçin", ["Giriş Yap", "Üye Ol"], key="mode")

    db = SessionLocal()
    if mode == "Giriş Yap":
        st.subheader("Giriş Yap")
        user = st.text_input("Kullanıcı Adı", key="login_username")
        pwd  = st.text_input("Şifre", type="password", key="login_password")
        if st.button("Giriş Yap"):
            db_user = db.query(User).filter_by(username=user).first()
            if db_user and bcrypt.verify(pwd, db_user.hashed_password):
                st.session_state.login = True
                st.session_state.user_id = db_user.id
                st.success("Giriş başarılı!")
            else:
                st.error("Hatalı kullanıcı veya şifre.")
    else:
        st.subheader("Üye Ol")
        new_user = st.text_input("Kullanıcı Adı", key="reg_username")
        new_email= st.text_input("E-posta", key="reg_email")
        new_pwd  = st.text_input("Şifre", type="password", key="reg_password")
        conf_pwd = st.text_input("Şifre Tekrar", type="password", key="reg_confirm")
        if st.button("Üye Ol"):
            if new_pwd != conf_pwd:
                st.error("Şifreler eşleşmiyor!")
            else:
                exists = db.query(User).filter(
                    (User.username == new_user) | (User.email == new_email)
                ).first()
                if exists:
                    st.error("Zaten kayıtlı!")
                else:
                    u = User(
                        username=new_user,
                        email=new_email,
                        hashed_password=bcrypt.hash(new_pwd),
                        first_name="", last_name="", phone_number=""
                    )
                    db.add(u)
                    db.commit()
                    st.success("Kayıt başarılı. Giriş yapın.")
    db.close()

# ------------------------------------------------
# 2) Teşhis ekranı
if st.session_state.login:
    st.subheader("Teşhis İçin Görsel Yükleyin")
    uploaded = st.file_uploader(
        "Yaprak fotoğrafı yükleyin", 
        type=["jpg", "png", "jpeg"], 
        key="uploaded_file"
    )
    if uploaded and st.button("Teşhis Et"):
        img = Image.open(uploaded).convert("RGB")
        st.image(img, use_column_width=True)

        # predict_disease senkron çalışıyor
        label = predict_disease(img)

        # get_disease_description async → sync çalıştır
        desc = asyncio.run(get_disease_description(label))

        st.markdown(f"**Hastalık:** {label}")
        st.markdown(f"**Açıklama:** {desc}")

        # Kaydet ve DB’ye ekle
        os.makedirs("media", exist_ok=True)
        path = os.path.join("media", uploaded.name)
        img.save(path)
        db = SessionLocal()
        plant = Plant(
            file_path=path,
            predicted_disease=label,
            disease_description=desc,
            owner_id=st.session_state.user_id
        )
        db.add(plant)
        db.commit()
        db.close()
        st.success("Kaydedildi.")


