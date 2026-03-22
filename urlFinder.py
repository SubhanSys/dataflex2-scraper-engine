import asyncio
from playwright.async_api import async_playwright

async def linkleri_topla(kategori_url, istenilen_adet):
    async with async_playwright() as p:
        # 1. HAMLE: Bildirimleri Kapat
        try:
            browser = await p.chromium.launch(
                channel="chrome",
                headless=False,
                args=["--disable-notifications", "--disable-popup-blocking"]
            )
        except Exception:
            browser = await p.chromium.launch(
                channel="msedge",
                headless=False,
                args=["--disable-notifications", "--disable-popup-blocking"]
            )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = await context.new_page()

        print(f"\n🌍 Sayfa açılıyor: {kategori_url}")
        await page.goto(kategori_url, wait_until="domcontentloaded")
        await asyncio.sleep(2)

        # 2. HAMLE: JAVASCRIPT POP-UP KATİLİ
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

        await asyncio.sleep(1)

        print("⬇️ Sayfa genişletiliyor ve gizli ürünler yükleniyor...")
        onceki_yukseklik = 0
        temiz_linkler = set()

        while True:
            # 🔥 YENİ VƏ QÜSURSUZ LİNK FİLTRİ
            su_anki_linkler = await page.evaluate("""() => {
                const anchors = Array.from(document.querySelectorAll('a'));
                const links = [];
                anchors.forEach(a => {
                    let href = a.getAttribute('href');
                    if (href && href.length > 20 && !href.includes('javascript')) {
                        // Linkin sonundaki parametreleri (?size=1) ve çapaları (#) təmizlə
                        let temiz_href = href.split('?')[0].split('#')[0];
                        let lowerHref = temiz_href.toLowerCase();

                        // 🛑 YASAQLI KƏLMƏLƏR: İçində bunlar varsa, KƏSİNLİKLƏ məhsul deyil!
                        const yasakli = [
                            '/kategori/', '/arama', '/etiket/', '/magazalar',
                            '/yardim', '/sepet', '/uyelik', '/giris', '/markalar',
                            '/outlet', '/kampanya', '/koleksiyon', '/favoriler'
                        ];

                        // Əgər link yasaqlı kəlmələrdən heç birini ehtiva ETMİRSƏ (isSafe = true)
                        const isSafe = !yasakli.some(kelime => lowerHref.includes(kelime));

                        // 🔍 LC WAIKIKI SPESİFİK KONTROL: 
                        // Məhsul linklərində hər zaman ən az 2 tire (-) olur (Örn: /mavi-kadin-elbise-o-1234)
                        const isProductFormat = (lowerHref.match(/-/g) || []).length >= 2;

                        if (isSafe && isProductFormat && a.closest('[class*="product"]')) {
                            let tam_link = temiz_href.startsWith('http') ? temiz_href : 'https://www.lcw.com' + temiz_href;
                            links.push(tam_link);
                        }
                    }
                });
                return links;
            }""")

            temiz_linkler.update(su_anki_linkler)
            guncel_sayi = len(temiz_linkler)

            print(f"🔄 Ekranda anlık bulunan TƏMİZ məhsul sayısı: {guncel_sayi} / {istenilen_adet}")

            if guncel_sayi >= istenilen_adet:
                print("✅ İstenilen ürün sayısına ulaşıldı! Sayfa genişletme işlemi durduruluyor.")
                break

            await page.evaluate("window.scrollTo(0, document.body.scrollHeight - 1000);")
            await asyncio.sleep(1)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            await asyncio.sleep(2)

            try:
                buton = page.locator("text='Daha Fazla Ürün Gör'").first
                if await buton.is_visible():
                    print("🔘 'Daha Fazla Ürün Gör' butonuna basıldı...")
                    await buton.click(force=True)
                    await asyncio.sleep(3)
            except:
                pass

            yeni_yukseklik = await page.evaluate("document.body.scrollHeight")
            if yeni_yukseklik == onceki_yukseklik:
                await asyncio.sleep(2)
                if yeni_yukseklik == await page.evaluate("document.body.scrollHeight"):
                    print("🛑 Sayfa sonuna ulaşıldı, daha fazla ürün yok.")
                    break
            onceki_yukseklik = yeni_yukseklik

        await browser.close()
        return list(temiz_linkler)[:istenilen_adet]

# Arayüzden tetiklenecek ana fonksiyon
async def baslat(kategori_url, istenilen_adet, kayit_dosyasi):
    final_linkler = await linkleri_topla(kategori_url, istenilen_adet)

    print("\n" + "=" * 50)
    if len(final_linkler) < istenilen_adet:
        print(f"⚠️ DİKKAT: İstenilen {istenilen_adet} ürüne ulaşılamadı!")
        print(f"Sitede maksimum {len(final_linkler)} adet eşsiz ürün bulundu.")
    else:
        print(f"🎉 BAŞARILI: Tam olarak {istenilen_adet} adet temiz ürün linki çekildi.")
    print("=" * 50 + "\n")

    with open(kayit_dosyasi, "w", encoding="utf-8") as dosya:
        for link in final_linkler:
            dosya.write(link + "\n")

    print(f"📁 Linkler '{kayit_dosyasi}' dosyasına kaydedildi.")