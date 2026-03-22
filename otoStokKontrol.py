import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import os
import re
import requests
import time

BOT_CALISIYOR = True


def fiyati_temizle(fiyat_str):
    """ Excel'deki fiyatı alır, içindeki 'TL' vs gibi yazıları atar, SADECE NET RAKAMI döndürür (Ekleme/Çıkarma yapmaz!) """
    sayilar = re.findall(r'[0-9]+[.,]?[0-9]*', str(fiyat_str))
    if sayilar:
        temiz_fiyat = sayilar[0].replace(',', '.')
        try:
            # Hiçbir ekleme yapmadan doğrudan Excel'deki sayıyı döndürüyoruz
            return round(float(temiz_fiyat), 2)
        except:
            pass
    return 0.0


def trendyol_api_guncelle(barkod, stok, fiyat, satici_id, api_key, api_secret):
    url = f"https://api.trendyol.com/sapigw/suppliers/{satici_id}/products/price-and-inventory"

    payload = {
        "items": [
            {
                "barcode": barkod,
                "quantity": stok,
                "salePrice": fiyat,  # Doğrudan Excel fiyatı
                "listPrice": fiyat  # Doğrudan Excel fiyatı
            }
        ]
    }

    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'DataFlexBot'
    }

    try:
        response = requests.post(url, json=payload, headers=headers, auth=(api_key, api_secret))
        if response.status_code == 200:
            return True, "Başarılı"
        elif response.status_code == 429:
            return False, "429 - Trendyol Hız Sınırı"
        elif response.status_code == 401 or response.status_code == 403:
            return False, "Şifre Reddedildi (Yetkilendirme Hatası)"
        else:
            return False, f"Bilinmeyen Hata: {response.text}"
    except Exception as e:
        return False, str(e)


async def oto_bot_baslat(girdi_excel, bekleme_suresi_dk, satici_id, api_key, api_secret):
    global BOT_CALISIYOR
    BOT_CALISIYOR = True

    if not os.path.exists(girdi_excel):
        print(f"❌ HATA: {girdi_excel} bulunamadı!")
        return

    df = pd.read_excel(girdi_excel)
    print(f"🚀 TRENDYOL OTO-BOT BAŞLADI! (Toplam {len(df)} Ürün İzleniyor)")
    print("👻 Bot arka planda (görünmez olarak) çalışıyor, bilgisayarınızı kullanabilirsiniz...\n")

    tur_sayisi = 1

    async with async_playwright() as p:
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

        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()

        while BOT_CALISIYOR:
            print(f"\n======================================")
            print(f"🔄 {tur_sayisi}. KONTROL TURU BAŞLIYOR")
            print(f"======================================")

            onceki_url = ""
            stoktaki_bedenler = []

            for index, row in df.iterrows():
                if not BOT_CALISIYOR:
                    break

                barkod = str(row.get('Barkod', ''))
                url = str(row.get('Ürün URL', ''))
                hedef_beden = str(row.get('Beden', '')).strip()

                # 🔥 YENİ: Excel'deki Fiyat sütununu okur ve hiçbir ekleme yapmadan net rakamı alır
                excel_fiyati = fiyati_temizle(row.get('Fiyat', '0'))

                stok_durumu = 0

                if "http" in url and hedef_beden != "":
                    try:
                        if url != onceki_url:
                            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                            await asyncio.sleep(1.5)

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

                        stoktaki_bedenler_kucuk_harf = [b.lower() for b in stoktaki_bedenler]
                        hedef = hedef_beden.lower()

                        # 🔥 YENİ: "9-12" İSTİSNASINI STOK KONTROLDE GERİ ÇEVİRİYORUZ
                        if hedef == "9-12":
                            # Eğer sitede "9-12 ay" varsa onu da kabul et
                            if "9-12 ay" in stoktaki_bedenler_kucuk_harf or "9-12" in stoktaki_bedenler_kucuk_harf:
                                stok_durumu = 2
                        else:
                            # Normal bedenler için standart kontrol
                            if hedef in stoktaki_bedenler_kucuk_harf:
                                stok_durumu = 2

                    except Exception as e:
                        stok_durumu = 0

                durum_ikonu = "✅" if stok_durumu == 2 else "❌"
                excel_satir_no = index + 2
                print(
                    f"LCW: Excel Satır {excel_satir_no} | Barkod: {barkod} | '{hedef_beden}' -> {durum_ikonu} STOK: {stok_durumu}")

                if len(barkod) > 3 and barkod.lower() != "nan":
                    # Trendyol API'ye doğrudan Excel'deki fiyatı (excel_fiyati) gönderiyoruz
                    api_basarili, api_mesaj = trendyol_api_guncelle(barkod, stok_durumu, excel_fiyati, satici_id,
                                                                    api_key, api_secret)

                    if api_basarili:
                        print(
                            f"   └─ ⚡ Trendyol Güncellendi! Barkod: {barkod} | Stok: {stok_durumu} | Fiyat: {excel_fiyati} TL")
                        print("----------------------------------------")
                        print()
                    else:
                        print(f"   └─ ⚠️ Trendyol Hata: {api_mesaj}")
                        print("----------------------------------------")
                        print()

                        if "429" in api_mesaj:
                            print("   └─ ⏳ Trendyol IP Engeli! 10 saniye bekleniyor...")
                            print("----------------------------------------")
                            print()
                            time.sleep(10)
                        elif "Yetkilendirme" in api_mesaj or "auth" in api_mesaj.lower():
                            print("   └─ 🛑 ŞİFRE HATASI! Bot durduruluyor, lütfen şifreleri kontrol et.")
                            print("----------------------------------------")
                            print()
                            break

                time.sleep(1)

            if not BOT_CALISIYOR:
                break

            print(f"\n✅ {tur_sayisi}. Tur Tamamlandı.")
            tur_sayisi += 1

            bekleme_saniyesi = bekleme_suresi_dk * 60
            print(f"💤 Bot {bekleme_suresi_dk} dakika uykuya geçiyor...")
            for _ in range(bekleme_saniyesi):
                if not BOT_CALISIYOR:
                    break
                await asyncio.sleep(1)

        await browser.close()
        print("🛑 OTO-BOT TAMAMEN DURDURULDU.")


def botu_durdur():
    global BOT_CALISIYOR
    BOT_CALISIYOR = False