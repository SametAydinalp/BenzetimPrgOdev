import simpy
import random
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# --- SİMÜLASYON PARAMETRELERİ ---
SIM_SURESI = 3600  # 1 Saatlik yoğun saat simülasyonu (Saniye)
MUSTERI_GELIS_ARALIGI = 30  # Ortalama her 30 saniyede 1 müşteri gelir

# Kasa İşlem Hızları
NORMAL_KASA_HIZI = 2.0  # Kasiyer ürün başı 2 saniye harcar
SELF_CHECKOUT_HIZI = 4.0 # Müşteri ürün başı 4 saniye harcar (Daha yavaş)
ODEME_SURESI = 15.0      # Kart/Nakit ödeme süresi sabittir

tum_veriler = []

def musteri(env, isim, normal_kasalar, self_kasalar, senaryo_adi):
    gelis_zamani = env.now
    urun_sayisi = random.randint(1, 25) # Müşterinin sepetindeki ürün sayısı
    
    # KASA SEÇİM ALGORİTMASI
    # Eğer self-checkout varsa ve ürün sayısı azsa (hızlı kasa mantığı) orayı tercih et
    if self_kasalar and urun_sayisi <= 10:
        secilen_kasa = self_kasalar
        kasa_tipi = "Self-Checkout"
        islem_suresi = (urun_sayisi * SELF_CHECKOUT_HIZI) + ODEME_SURESI
    else:
        secilen_kasa = normal_kasalar
        kasa_tipi = "Normal Kasa"
        islem_suresi = (urun_sayisi * NORMAL_KASA_HIZI) + ODEME_SURESI

    # Müşteri seçtiği kasanın kuyruğuna girer
    with secilen_kasa.request() as istek:
        yield istek
        bekleme_suresi = env.now - gelis_zamani
        
        # Kasada işlemini halleder
        yield env.timeout(islem_suresi)
        
        # Verileri kaydet
        tum_veriler.append({
            'Senaryo': senaryo_adi,
            'Musteri': isim,
            'Urun_Sayisi': urun_sayisi,
            'Kasa_Tipi': kasa_tipi,
            'Bekleme_Suresi': bekleme_suresi / 60  # Dakika cinsinden kaydet
        })

def musteri_ureteci(env, normal_kasalar, self_kasalar, senaryo_adi):
    i = 0
    while True:
        yield env.timeout(random.expovariate(1.0 / MUSTERI_GELIS_ARALIGI))
        i += 1
        env.process(musteri(env, f"Müşteri-{i}", normal_kasalar, self_kasalar, senaryo_adi))

def senaryo_calistir(senaryo_adi, normal_kasa_sayisi, self_kasa_sayisi=0):
    print(f"{senaryo_adi} simüle ediliyor... (Normal: {normal_kasa_sayisi}, Self: {self_kasa_sayisi})")
    env = simpy.Environment()
    
    # Kaynakları (Kasaları) oluştur
    normal_kasalar = simpy.Resource(env, capacity=normal_kasa_sayisi)
    self_kasalar = simpy.Resource(env, capacity=self_kasa_sayisi) if self_kasa_sayisi > 0 else None
    
    env.process(musteri_ureteci(env, normal_kasalar, self_kasalar, senaryo_adi))
    env.run(until=SIM_SURESI)

# --- RAPORDAKİ 4 SENARYOYU SIRAYLA ÇALIŞTIR ---
senaryo_calistir("Senaryo 1 (2 Kasa)", normal_kasa_sayisi=2)
senaryo_calistir("Senaryo 2 (4 Kasa)", normal_kasa_sayisi=4)
senaryo_calistir("Senaryo 3 (6 Kasa)", normal_kasa_sayisi=6)
senaryo_calistir("Senaryo 4 (3 Normal + 2 Self)", normal_kasa_sayisi=3, self_kasa_sayisi=2)

# --- VERİ ANALİZİ VE GÖRSELLEŞTİRME ---
df = pd.DataFrame(tum_veriler)

# İstatistikleri Ekrana Yazdır
print("\n--- SİMÜLASYON SONUÇLARI (Ortalama Bekleme Süreleri) ---")
ozet = df.groupby('Senaryo')['Bekleme_Suresi'].agg(['mean', 'max', 'count']).round(2)
ozet.columns = ['Ortalama Bekleme (Dk)', 'Maksimum Bekleme (Dk)', 'Hizmet Alan Müşteri']
print(ozet)

# Grafikleri Çizdir
sns.set_theme(style="whitegrid")
plt.figure(figsize=(12, 6))

# Boxplot (Kutu Grafiği) ile Senaryoların Karşılaştırması
sns.boxplot(data=df, x='Senaryo', y='Bekleme_Suresi', palette='Set2')
plt.title('Farklı Kasa Senaryolarında Müşteri Bekleme Süreleri Karşılaştırması')
plt.ylabel('Bekleme Süresi (Dakika)')
plt.xlabel('Senaryolar')
plt.tight_layout()
plt.show()