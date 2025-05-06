# Tarım Koçum

**Akıllı Tarım Asistanı**  
Çiftçilerin yaprak, bitki ve tarla sorunlarını hızlıca teşhis etmelerine yardımcı olan, yapay zekâ destekli bir web uygulamasıdır.

## Özellikler
- **Kullanıcı Yönetimi**: Kayıt olma ve giriş yapma  
- **Görsel Teşhis**: Yaprak fotoğrafı yükleyerek hastalık tahmini  
- **Gemini Entegrasyonu**: Google Gemini API ile Türkçe, anlaşılır hastalık açıklamaları  
- **Veritabanı**: SQLite + SQLAlchemy destekli kayıt ve geçmiş yönetimi  
- **Kolay Kullanım**: Streamlit tabanlı kullanıcı dostu arayüz

## Proje Dizin Yapısı
```
tarimkocum/
├── app.py                  # Streamlit uygulaması
├── database.py             # SQLite bağlantısı
├── models.py               # SQLAlchemy modelleri
├── routers/
│    └── init.py
│    └── plant.py           # API endpoint + gemini + model entegrasyonu
│    └── auth.py            # Kullanıcı kayıt endpointi
├── media/                  # Yüklenen görseller
├── tarimkocum.db           # SQLite veritabanı dosyası
├── requirements.txt        # Python bağımlılıkları
└── README.md               # Proje tanıtımı
```

## Kurulum
1. Depoyu klonlayın:
   ```bash
   git clone https://github.com/ch4uTR/tarimkocum.git
   cd tarimkocum
   ```
2. Sanal ortam oluşturun ve aktif edin:
   ```bash
   python -m venv venv
   source venv/bin/activate    # Windows: venv\Scripts\activate
   ```
3. Gerekli paketleri yükleyin:
   ```bash
   pip install -r requirements.txt
   ```
4. Ortam değişkenlerini ayarlayın (`.env` dosyası):
   ```env
   GEMINI_API_KEY=YOUR_API_KEY_HERE
   ```
5. Veritabanını oluşturun:
   ```bash
   python
   >>> from database import engine, Base
   >>> from models import User, Plant
   >>> Base.metadata.create_all(bind=engine)
   >>> exit()
   ```

## Çalıştırma
```bash
streamlit run app.py
```
Tarayıcınızda açılan uygulama üzerinden kayıt olma, giriş yapma, fotoğraf yükleme ve teşhis işlemlerini gerçekleştirebilirsiniz.

## Kullanım
1. **Kayıt Ol**: Yeni kullanıcı oluşturun.  
2. **Giriş Yap**: Oluşturduğunuz bilgilerle sisteme giriş yapın.  
3. **Fotoğraf Yükle**: Sağlıklı veya sorunlu yaprak fotoğrafını yükleyin.  
4. **Teşhis Et**: Uygulama size hastalık adı ve Türkçe açıklamasını sunar.  
5. **Geçmiş**: `tarimkocum.db` dosyasında tüm kayıtlar saklanır.

## Teknolojiler
- **Python 3.8+**  
- **Streamlit**  
- **FastAPI** (opsiyonel API modülü)  
- **SQLAlchemy** + **SQLite**  
- **Transformers** (AutoImageProcessor + MobileNet)  
- **httpx**  
- **Google Gemini API**

## Lisans
Bu proje MIT lisansı ile lisanslanmıştır.
