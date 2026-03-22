import asyncio
from playwright.async_api import async_playwright
from google import genai
from google.genai import types
import json
import pandas as pd
import os
import re
import time

# Küresel değişkenler (Başlangıçta boş bırakıyoruz, arayüzden gelecek)
client = None
VERI_AKTARICI_CALISIYOR = True

def veri_aktariciyi_durdur():
    global VERI_AKTARICI_CALISIYOR
    VERI_AKTARICI_CALISIYOR = False

async def sayfa_verilerini_al(url):
    try:
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(
                    channel="chrome",
                    headless=False,
                    args=["--disable-notifications", "--disable-popup-blocking", "--disable-gpu"]
                )
            except Exception:
                browser = await p.chromium.launch(
                    channel="msedge",
                    headless=False,
                    args=["--disable-notifications", "--disable-popup-blocking", "--disable-gpu"]
                )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 800}
            )
            page = await context.new_page()

            print(f"\n🌍 Sayfa açılıyor: {url}")

            # 🔥 YENİ KALKAN: Eğer sayfa 30 saniyede açılmazsa program çökmesin!
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(0.5)
            except Exception as e:
                print("⚠️ Sayfa 30 saniyede yüklenemedi! Bu ürün atlanıyor...")
                await browser.close()
                return None, None

            print("🧹 Reklam, çerez ve pop-up bildirimleri temizleniyor...")
            try:
                await page.evaluate("""() => {
                    const garbageSelectors = [
                        '[class*="cookie"]', '[id*="cookie"]', 
                        '[class*="popup"]', '[id*="popup"]', 
                        '[class*="modal"]', '[id*="modal"]', 
                        '[class*="banner"]', '[id*="banner"]', 
                        '[class*="overlay"]', '[class*="kampanya"]',
                        '.ins-web-opt-in', 'iframe' 
                    ];
                    document.querySelectorAll(garbageSelectors.join(', ')).forEach(el => el.remove());
                    document.body.style.overflow = 'auto';
                }""")
            except:
                pass

            try:
                await page.wait_for_selector("h1", timeout=8000)
            except Exception:
                pass

            for _ in range(2):
                await page.evaluate("window.scrollBy(0, 500)")
                await asyncio.sleep(0.2)

            print("📖 Açıklama panelleri zorla açılıyor...")

            # 1. BALYOZ: Daha zeki bir tıklama yöntemi (Tam eşleşme aramadan, içinde geçeni bulur ve tıklar)
            buton_metinleri = ["Ürün Açıklaması", "Ürün Özellikleri", "Tüm Özellikler", "Ürün İçeriği"]
            for metin in buton_metinleri:
                try:
                    # locator yerine get_by_text kullandık. Bu yöntem gizli butonları bulmada 10 kat daha iyidir.
                    await page.get_by_text(metin, exact=False).first.click(force=True, timeout=1500)
                    await asyncio.sleep(0.5)
                except:
                    pass

            # 2. BALYOZ: CSS kurallarını ezen (!important) JavaScript müdahalesi
            await page.evaluate("""() => {
                // Sitedeki açıklama barındıran tüm olası gizli kutuları bul
                const panels = document.querySelectorAll('.panel-body, .product-description, [class*="description"], [class*="detail"], [class*="özellik"], [class*="ozellik"]');

                panels.forEach(p => {
                    // Sitenin kendi gizleme ayarlarını ZORLA ezerek yazıları görünür yap
                    p.style.setProperty('display', 'block', 'important');
                    p.style.setProperty('visibility', 'visible', 'important');
                    p.style.setProperty('height', 'auto', 'important');
                    p.style.setProperty('opacity', '1', 'important');
                    p.classList.remove('hidden', 'collapse', 'd-none'); // Gizleyen class'ları sil
                });
            }""")

            await page.evaluate("""() => {
                const panels = document.querySelectorAll('.panel-body, .product-description, [class*="description"], [class*="detail"], div[style*="display: none"]');
                panels.forEach(p => {
                    p.style.display = 'block';
                    p.style.visibility = 'visible';
                    p.style.height = 'auto';
                    p.style.opacity = '1';
                });
            }""")

            print("🔍 Stok durumları analiz ediliyor...")
            await page.evaluate("""() => {
                const elements = document.querySelectorAll('a, button, div, span, label, li, p');
                elements.forEach(el => {
                    if (window.getComputedStyle(el).display === 'none') { el.style.display = 'block'; }
                    const className = (el.className || '').toString().toLowerCase();
                    const isDisabled = el.hasAttribute('disabled') || el.getAttribute('aria-disabled') === 'true' ||
                                       className.includes('disabled') || className.includes('out-of-stock') || 
                                       className.includes('passive') || className.includes('tukendi');
                    if (isDisabled && el.innerText.trim() !== '') { el.innerText = el.innerText + " [STOKTA_YOK]"; }
                });
            }""")

            print("✂️ Sayfa metni qısaldılır (Süper Tasarruf Modu)...")
            sayfa_metni = await page.evaluate("""() => {
                const gereksizler = document.querySelectorAll(`
                    header, footer, nav, aside, 
                    [class*="header"], [class*="footer"], [class*="menu"], 
                    [class*="similar"], [class*="recommend"], [class*="review"], 
                    [class*="comment"], [class*="newsletter"], [id*="footer"],
                    [class*="installments"], [class*="cargo"], [class*="delivery"],
                    [class*="breadcrumb"], [class*="return-policy"]
                `);
                gereksizler.forEach(el => el.remove());

                let temizMetin = document.body.innerText;
                return temizMetin.replace(/\\s+/g, ' ').trim();
            }""")

            gorsel_linkleri = await page.evaluate("""() => {
                return Array.from(document.querySelectorAll('img'))
                            .map(img => img.src || img.getAttribute('data-src'))
                            .filter(src => src && src.startsWith('http'));
            }""")

            await browser.close()
            return sayfa_metni, gorsel_linkleri

    # Tüm sistemi koruyan Genel Hata Kalkanı
    except Exception as e:
        print(f"❌ SİSTEM HATASI (Ürün Atlanıyor): Tarayıcı başlatılamadı veya kilitlendi.")
        return None, None

def fiyati_iki_katina_cikar(fiyat_str):
    sayilar = re.findall(r'[0-9]+[.,]?[0-9]*', str(fiyat_str))
    if sayilar:
        temiz_fiyat = sayilar[0].replace(',', '.')
        try:
            float_fiyat = float(temiz_fiyat)
            return f"{float_fiyat * 2:.2f}"
        except: pass
    return fiyat_str


# 🔥 YENİ: BEDEN İÇİNDEKİ PARANTEZLERİ TEMİZLEYEN VE "9-12" İSTİSNASINI UYGULAYAN FONKSİYON
def beden_temizle(beden_str):
    if not beden_str:
        return ""
    # Regex ile ( ) içindeki her şeyi siler
    temiz = re.sub(r'\(.*?\)', '', str(beden_str))
    # Enterları ve fazla boşlukları silip tek boşluğa düşürür
    temiz = ' '.join(temiz.split())

    # 🔥 İSTİSNA KURALI: Eğer beden tam olarak "9-12 Ay" ise sadece "9-12" yap
    if temiz.lower() == "9-12 ay":
        temiz = "9-12"

    return temiz


def ai_ile_veri_cikar(sayfa_metni):
    print("🤖 Yapay Zeka verileri analiz edip ayıklıyor...")

    prompt = f"""
    Sen gelişmiş bir e-ticaret veri kazıma asistanısın. 
    1. STOK DURUMU: Yanında "[STOKTA_YOK]" yazan beden/renkleri ALMA.
    2. FİYAT KURALI: Sadece rakamı yaz. İki fiyat varsa yüksek (ilk) olanı al.
    3. DETAYLI AÇIKLAMA (ÇOK KRİTİK): Ürün kodunun (Model Kodu) hemen altında veya çevresinde yazan ürünü tanıtan cümleyi, kumaş bilgisini ve materyal özelliklerini KESİNLİKLE BUL ve eksiksiz bir şekilde uzun bir metin yap. Asla boş bırakma!
    4. MODEL KODU: Sitede yazdığı gibi al, içindeki tireyi (-) silme. BÜYÜK HARF yaz.

    {{
        "model_kodu": "string", "marka": "string", "kategori": "string", "urun_adi": "string",
        "urun_aciklamasi": "string", "fiyat": "string (sadece rakam)", "para_birimi": "string",
        "stoktaki_varyasyonlar": [ {{"beden": "string", "renk": "string"}} ]
    }}

    --- SAYFA METNİ ---
    {sayfa_metni[:15000]} 
    """

    max_deneme = 3
    for deneme in range(max_deneme):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.0)
            )
            return json.loads(response.text)
        except Exception as e:
            hata_mesaji = str(e)
            if "403" in hata_mesaji or "Forbidden" in hata_mesaji or "429" in hata_mesaji:
                print(f"⏳ Google Güvenlik Duvarı yavaşlattı. 15 sn bekleniyor... (Deneme {deneme + 1}/{max_deneme})")
                time.sleep(15)
            else:
                print("❌ Beklenmeyen API Hatası:", hata_mesaji[:100])
                return None

    print("❌ 3 denemeye rağmen API'ye bağlanılamadı. Bu ürün atlanıyor.")
    return None

# DİKKAT: 'ham_gorsel_linkleri' parametresi eklendi!
def excel_olustur(ai_verisi, islenen_url, excel_dosyasi, ham_gorsel_linkleri):
    if not ai_verisi or "stoktaki_varyasyonlar" not in ai_verisi or len(ai_verisi["stoktaki_varyasyonlar"]) == 0:
        print("⚠️ Stokta ürün bulunamadı. Excel satırı oluşturulmadı.")
        return

    # Görselleri AI'dan değil, bizim kendi bedava listemizden alıyoruz!
    gorseller = ham_gorsel_linkleri if isinstance(ham_gorsel_linkleri, list) else []

    varyasyonlar = ai_verisi.get("stoktaki_varyasyonlar", [])
    ikikat_fiyat = fiyati_iki_katina_cikar(ai_verisi.get("fiyat", ""))

    excel_satirlari = []

    for var in varyasyonlar:
        ham_beden = var.get("beden", "")
        temizlenmis_beden = beden_temizle(ham_beden)

        orijinal_model_kodu = str(ai_verisi.get("model_kodu", "")).strip().upper()

        satir = {
            "Barkod": "",
            "Ürün URL": islenen_url,
            "Model Kodu": orijinal_model_kodu,
            "Marka": ai_verisi.get("marka", ""),
            "Kategori": ai_verisi.get("kategori", ""),
            "Para birimi": ai_verisi.get("para_birimi", ""),
            "Ürün adı": ai_verisi.get("urun_adi", ""),
            "Ürün açıklaması": ai_verisi.get("urun_aciklamasi", ""),
            "Fiyat": ikikat_fiyat,
            # Gorselleri doğrudan listenden atıyoruz, hata payı sıfır!
            "Görsel 1 html": gorseller[0] if len(gorseller) > 0 else "",
            "Görsel 2 html": gorseller[1] if len(gorseller) > 1 else "",
            "Görsel 3 html": gorseller[2] if len(gorseller) > 2 else "",
            "Görsel 4 html": gorseller[3] if len(gorseller) > 3 else "",
            "Görsel 5 html": gorseller[4] if len(gorseller) > 4 else "",
            "Beden": temizlenmis_beden,
            "Renk": var.get("renk", "")
        }
        excel_satirlari.append(satir)

    df_yeni = pd.DataFrame(excel_satirlari)
    if os.path.exists(excel_dosyasi):
        df_eski = pd.read_excel(excel_dosyasi)
        df_birlesik = pd.concat([df_eski, df_yeni], ignore_index=True)
        df_birlesik.to_excel(excel_dosyasi, index=False)
        print(f"✅ EKLENDİ -> '{excel_dosyasi}' (Toplam Satır: {len(df_birlesik)})")
    else:
        df_yeni.to_excel(excel_dosyasi, index=False)
        print(f"✅ YENİ OLUŞTURULDU -> '{excel_dosyasi}' (Toplam Satır: {len(excel_satirlari)})")


async def baslat(txt_dosyasi, excel_dosyasi, gemini_api_key):
    global VERI_AKTARICI_CALISIYOR, client
    VERI_AKTARICI_CALISIYOR = True

    # Kullanıcının arayüzden girdiği API ile Yapay Zeka oturumunu başlatıyoruz
    try:
        client = genai.Client(api_key=gemini_api_key)
    except Exception as e:
        print(f"❌ API Hatası: Lütfen geçerli bir Gemini API Anahtarı girin! Detay: {e}")
        return

    if not os.path.exists(txt_dosyasi):
        print(f"❌ HATA: {txt_dosyasi} bulunamadı!")
        return

    with open(txt_dosyasi, "r", encoding="utf-8") as f:
        urls = [line.strip() for line in f if line.strip()]

    print(f"Toplam {len(urls)} adet link '{txt_dosyasi}' dosyasından okundu. İşlem başlıyor...\n")

    for index, url in enumerate(urls, 1):
        if not VERI_AKTARICI_CALISIYOR:
            print("🛑 Veri Aktarıcı kullanıcı tarafından durduruldu.")
            break

        print(f"\n======================================")
        print(f"🔄 İŞLEM: {index}/{len(urls)}")
        print(f"======================================")
        sayfa_metni, gorsel_linkleri = await sayfa_verilerini_al(url)
        if sayfa_metni:
            sonuc_json = ai_ile_veri_cikar(sayfa_metni)
            if sonuc_json:
                excel_olustur(sonuc_json, url, excel_dosyasi, gorsel_linkleri)
            else:
                print("❌ Yapay zeka veriyi ayrıştıramadı.")
        else:
            print("❌ Sayfadan veri alınamadı.")

    print("\n🎉 VERİ AKTARIMI TAMAMLANDI!")