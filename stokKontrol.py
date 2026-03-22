import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import os
import re


def fiyati_hesapla(fiyat_str):
    """ Fiyatı temizler, +50 ekler ve iki fiyatı da döndürür """
    sayilar = re.findall(r'[0-9]+[.,]?[0-9]*', str(fiyat_str))
    if sayilar:
        temiz_fiyat = sayilar[0].replace(',', '.')
        try:
            orijinal = float(temiz_fiyat)
            return f"{orijinal + 50.0:.2f}", f"{orijinal:.2f}"
        except:
            pass
    return "0.00", "0.00"


async def stok_kontrol_baslat(girdi_excel, cikti_excel):
    if not os.path.exists(girdi_excel):
        print(f"❌ HATA: {girdi_excel} bulunamadı!")
        return

    df = pd.read_excel(girdi_excel)
    print(f"🚀 Toplam {len(df)} satır kontrol edilecek. (TARAYICI EKRANDA AÇILIYOR...)")
    sonuclar = []

    async with async_playwright() as p:

        # 🔥 TARAYICI ÇÖKMESİN DİYE BİLGİSAYARDAKİ CHROME VEYA EDGE KULLANILIR
        try:
            browser = await p.chromium.launch(channel="chrome", headless=False)
        except Exception:
            browser = await p.chromium.launch(channel="msedge", headless=False)

        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()

        onceki_url = ""
        stoktaki_bedenler = []

        for index, row in df.iterrows():
            barkod = str(row.get('Barkod', ''))
            url = str(row.get('Ürün URL', ''))

            # Excel'deki hedef bedeni alıyoruz
            hedef_beden = str(row.get('Beden', '')).strip()

            fiyat_arti_50, orijinal_fiyat = fiyati_hesapla(row.get('Fiyat', '0'))

            stok_durumu = 0  # Başlangıçta 0 (Stokta yok) kabul ediyoruz

            if "http" in url and hedef_beden != "":
                try:
                    # Hız için aynı linkte isek sayfayı tekrar yenileme
                    if url != onceki_url:
                        await page.goto(url, wait_until="domcontentloaded")
                        await asyncio.sleep(1)  # Sayfanın oturmasını bekle

                        # Senin DOĞRU ÇALIŞAN eski mantığın!
                        stoktaki_bedenler = await page.evaluate("""() => {
                            let aktif_bedenler = [];
                            let container = document.querySelector('.option-size-boxes');

                            if (container) {
                                let boxes = container.querySelectorAll('a, .option-size-box');

                                boxes.forEach(box => {
                                    let classIsmi = (box.className || '').toLowerCase();

                                    if (!classIsmi.includes('out-of-stock') && !classIsmi.includes('disabled')) {
                                        let tamMetin = box.innerText.trim();
                                        let ilkSatir = tamMetin.split('\\n')[0].trim();
                                        aktif_bedenler.push(ilkSatir);
                                    }
                                });
                            }
                            return aktif_bedenler;
                        }""")
                        onceki_url = url

                    # KESİN VE BİREBİR EŞLEŞME KONTROLÜ
                    stoktaki_bedenler_kucuk_harf = [b.lower() for b in stoktaki_bedenler]

                    if hedef_beden.lower() in stoktaki_bedenler_kucuk_harf:
                        stok_durumu = 2  # Birebir aynı, stokta var!

                except Exception as e:
                    # Sayfa açılmazsa veya hata verirse stok yok sayılır
                    stok_durumu = 0

            # Çıktı listesine ekle
            sonuclar.append({
                "Barkod": barkod,
                "Satış Fiyatı (+50)": fiyat_arti_50,
                "Orijinal Fiyat": orijinal_fiyat,
                "Stok": stok_durumu
            })

            durum_ikonu = "✅" if stok_durumu == 2 else "❌"
            print(f"🔄 Satır {index + 1} | Beden: '{hedef_beden}' -> {durum_ikonu} STOK: {stok_durumu}")

        await browser.close()

    # Çıktı dosyasını oluştur
    df_sonuc = pd.DataFrame(sonuclar)
    df_sonuc.to_excel(cikti_excel, index=False)

    print("\n" + "=" * 50)
    print(f"🎉 STOK KONTROLÜ TAMAMLANDI!")
    print(f"📁 Sonuçlar '{cikti_excel}' dosyasına başarıyla kaydedildi.")