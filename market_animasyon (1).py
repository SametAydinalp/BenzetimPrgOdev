import pygame
import simpy
import random
import sys

# --- SİMÜLASYON VE EKRAN AYARLARI ---
GELIS_ARALIGI = 2.0    # Simülasyonun hızlı akması için sıklaştırdık
SIM_HIZI = 3.0

pygame.init()
WIDTH, HEIGHT = 900, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Süpermarket Kasa Simülasyonu - Apdil Samet Aydınalp")
clock = pygame.time.Clock()

# Renkler
BG_COLOR = (240, 245, 250)
KASA_NORMAL_COLOR = (50, 150, 220)  # Mavi
KASA_SELF_COLOR = (220, 100, 200)   # Mor
MUSTERI_AZ_URUN = (50, 200, 100)    # Yeşil (Hızlı)
MUSTERI_COK_URUN = (220, 80, 80)    # Kırmızı (Yavaş)
TEXT_COLOR = (40, 40, 40)
font = pygame.font.SysFont("Arial", 16, bold=True)

# --- SINIFLAR VE MANTIK ---
class Kasa:
    def __init__(self, env, id, x, y, tip):
        self.id = id
        self.x = x
        self.y = y
        self.tip = tip # 'Normal' veya 'Self'
        self.res = simpy.Resource(env, capacity=1)
        self.gorsel_kuyruk = [] # Animasyon için sırada bekleyenler listesi
        self.aktif_musteri = None

    def draw(self, surface):
        renk = KASA_NORMAL_COLOR if self.tip == 'Normal' else KASA_SELF_COLOR
        pygame.draw.rect(surface, renk, (self.x, self.y, 80, 50), border_radius=8)
        
        # Kasa numarasını ve tipini yazdır
        isim = font.render(f"Kasa {self.id}", True, (255,255,255))
        tip_yazi = font.render(self.tip, True, (255,255,255))
        surface.blit(isim, (self.x + 10, self.y + 5))
        surface.blit(tip_yazi, (self.x + 10, self.y + 25))

class Musteri:
    def __init__(self, id, urun_sayisi):
        self.id = id
        self.urun_sayisi = urun_sayisi
        self.x = WIDTH // 2 - 20
        self.y = HEIGHT + 50 # Ekranın altından girer
        self.hiz = 200
        self.renk = MUSTERI_AZ_URUN if urun_sayisi <= 10 else MUSTERI_COK_URUN
        self.bitti_mi = False

    def draw(self, surface):
        pygame.draw.circle(surface, self.renk, (int(self.x), int(self.y)), 15)
        # İçine ürün sayısını yaz
        urun_yazi = font.render(str(self.urun_sayisi), True, (255,255,255))
        surface.blit(urun_yazi, (self.x - 8, self.y - 8))

    def hareket_et(self, dt, hedef_x, hedef_y):
        # Müşteriyi hedefine doğru yumuşakça hareket ettir
        if abs(self.x - hedef_x) > 2:
            self.x += (hedef_x - self.x) * dt * SIM_HIZI
        if abs(self.y - hedef_y) > 2:
            self.y += (hedef_y - self.y) * dt * SIM_HIZI

# --- SİMPY SÜREÇLERİ ---
def musteri_davranisi(env, musteri, kasalar):
    # AKILLI KASA SEÇİMİ (Yük Dengeleme)
    if musteri.urun_sayisi <= 10:
        uygun_kasalar = kasalar # Az ürünü olan her kasaya gidebilir
    else:
        uygun_kasalar = [k for k in kasalar if k.tip == 'Normal'] # Çok ürünü olan sadece Normal'e
        
    # En kısa kuyruğa sahip olanı seç (Resource.queue uzunluğu + işlemde olan)
    secilen_kasa = min(uygun_kasalar, key=lambda k: len(k.res.queue) + len(k.res.users))
    
    # Müşteriyi kasanın görsel kuyruğuna ekle
    secilen_kasa.gorsel_kuyruk.append(musteri)
    
    with secilen_kasa.res.request() as istek:
        yield istek # Sıramı bekliyorum...
        
        # Sıra bana geldi!
        secilen_kasa.aktif_musteri = musteri
        
        # İşlem süresi hesabı
        islem_hizi = 0.5 if secilen_kasa.tip == 'Normal' else 1.0
        bekleme = (musteri.urun_sayisi * islem_hizi) + 2.0
        
        yield env.timeout(bekleme) # Kasada işlem yapılıyor
        
        # İşim bitti, kasadan ayrıl
        secilen_kasa.gorsel_kuyruk.remove(musteri)
        secilen_kasa.aktif_musteri = None
        musteri.bitti_mi = True

def musteri_ureteci(env, kasalar):
    i = 0
    while True:
        yield env.timeout(random.expovariate(1.0 / GELIS_ARALIGI))
        i += 1
        urun_sayisi = random.randint(1, 25)
        yeni_musteri = Musteri(i, urun_sayisi)
        musteriler.append(yeni_musteri)
        env.process(musteri_davranisi(env, yeni_musteri, kasalar))

# --- MOTOR KURULUMU ---
env = simpy.Environment()
musteriler = []

# Senaryo 4'ü Kuruyoruz: 3 Normal, 2 Self-Checkout Kasa
kasalar = [
    Kasa(env, 1, 100, 50, 'Normal'),
    Kasa(env, 2, 250, 50, 'Normal'),
    Kasa(env, 3, 400, 50, 'Normal'),
    Kasa(env, 4, 600, 50, 'Self'),
    Kasa(env, 5, 750, 50, 'Self')
]

env.process(musteri_ureteci(env, kasalar))

# --- EKRAN ÇİZİM DÖNGÜSÜ ---
running = True
while running:
    dt = clock.tick(60) / 1000.0
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False

    env.run(until=env.now + (dt * SIM_HIZI))
    
    screen.fill(BG_COLOR)
    
    # Bilgi Panosu
    bilgi = font.render("Yeşil: Hızlı Müşteri (1-10 Ürün) | Kırmızı: Yavaş Müşteri (11+ Ürün)", True, TEXT_COLOR)
    screen.blit(bilgi, (10, 10))

    # Kasaları Çiz
    for kasa in kasalar:
        kasa.draw(screen)

    # Müşterilerin Fiziksel Hareketleri
    for musteri in musteriler:
        if musteri.bitti_mi:
            # İşi biten ekranın üstünden çıkar
            musteri.hareket_et(dt, musteri.x, -50)
        else:
            # Kasa hedefini bul
            hedef_kasa = next((k for k in kasalar if musteri in k.gorsel_kuyruk), None)
            
            if hedef_kasa:
                # Kuyruktaki sırasını bul
                sira_no = hedef_kasa.gorsel_kuyruk.index(musteri)
                hedef_x = hedef_kasa.x + 40
                # Kasadaki ilk kişiyse kasanın hemen önünde dursun, değilse arkaya dizilsin
                hedef_y = hedef_kasa.y + 80 + (sira_no * 40) 
                
                musteri.hareket_et(dt, hedef_x, hedef_y)
                
        musteri.draw(screen)

    # Ekrandan tamamen çıkanları RAM'den temizle
    musteriler = [m for m in musteriler if m.y > -40]

    pygame.display.flip()

pygame.quit()
sys.exit()