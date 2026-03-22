import os
import sys
import customtkinter as ctk
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox
import threading
import asyncio
import multiprocessing

# Kendi yazdığımız scriptleri import ediyoruz
import urlFinder
import veriKaydedici
import stokKontrol
import otoStokKontrol

# YENİ EKLENEN KISIM ----------
from dotenv import load_dotenv

# .env dosyasındaki şifreleri programa yükler
load_dotenv('default_pass.env')

TRENDYOL_SATICI_ID = os.getenv("TRENDYOL_SATIC_ID")
TRENDYOL_API_KEY = os.getenv("TRENDYOL_API_KEY")
TRENDYOL_API_SECRET = os.getenv("TRENDYOL_API_SECRET")

class ConsoleRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        # 🔥 YENİ: METİN RENKLERİNİ TANIMLIYORUZ
        self.text_widget.tag_config("kirmizi", foreground="#ff4d4d")  # Çarpıcı Kırmızı
        self.text_widget.tag_config("yesil", foreground="#00e676")  # Fosforlu Yeşil
        self.text_widget.tag_config("sari", foreground="#ffca28")  # Uyarı Sarısı

    def write(self, text):
        # 🔥 YENİ: METNİN İÇİNDEKİ KELİMEYE GÖRE RENGİ BELİRLE
        if "STOK: 0" in text or "❌" in text or "HATA" in text.upper():
            self.text_widget.insert("end", text, "kirmizi")
        elif "STOK: 2" in text or "✅" in text or "⚡" in text:
            self.text_widget.insert("end", text, "yesil")
        elif "⚠️" in text or "⏳" in text:
            self.text_widget.insert("end", text, "sari")
        else:
            self.text_widget.insert("end", text)  # Normal beyaz/gri yazı

        self.text_widget.see("end")

    def flush(self):
        pass


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("DataFlex - E-Ticaret ve Trendyol Botu")
        self.geometry("1100x650")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        self.tab_aktarici = self.tabview.add("Veri Aktarıcı")
        self.tab_kaydedici = self.tabview.add("Url Kaydedici")
        self.tab_stok = self.tabview.add("Stok Kontrol")
        self.tab_oto = self.tabview.add("Trendyol Oto-Bot")

        self.setup_veri_aktarici_tab()
        self.setup_url_kaydedici_tab()
        self.setup_stok_kontrol_tab()
        self.setup_trendyol_oto_tab()

        self.log_frame = ctk.CTkFrame(self)
        self.log_frame.grid(row=0, column=1, padx=(0, 20), pady=20, sticky="nsew")
        self.log_label = ctk.CTkLabel(self.log_frame, text="Terminal Logları", font=ctk.CTkFont(weight="bold"))
        self.log_label.pack(pady=10)
        self.log_textbox = ctk.CTkTextbox(self.log_frame, font=("Consolas", 12))
        self.log_textbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        sys.stdout = ConsoleRedirector(self.log_textbox)
        sys.stderr = ConsoleRedirector(self.log_textbox)

    # --- SEKME 1: VERİ AKTARICI ---
    def setup_veri_aktarici_tab(self):
        ctk.CTkLabel(self.tab_aktarici, text="1. Linklerin Bulunduğu Dosya (.txt)").pack(pady=(20, 5), anchor="w", padx=20)
        txt_frame = ctk.CTkFrame(self.tab_aktarici, fg_color="transparent")
        txt_frame.pack(fill="x", padx=20)
        self.entry_txt_aktarici = ctk.CTkEntry(txt_frame, width=220, placeholder_text="Varsayılan: urun_linkleri.txt")
        self.entry_txt_aktarici.pack(side="left")
        ctk.CTkButton(txt_frame, text="Dosya Seç", width=70,
                      command=lambda: self.sec_dosya(self.entry_txt_aktarici, "*.txt")).pack(side="left", padx=10)

        ctk.CTkLabel(self.tab_aktarici, text="2. Kaydedilecek Excel Dosyası (.xlsx) [ZORUNLU]").pack(pady=(20, 5),
                                                                                                     anchor="w",
                                                                                                     padx=20)
        excel_frame = ctk.CTkFrame(self.tab_aktarici, fg_color="transparent")
        excel_frame.pack(fill="x", padx=20)
        self.entry_excel = ctk.CTkEntry(excel_frame, width=220)
        self.entry_excel.pack(side="left")
        self.btn_sec_excel = ctk.CTkButton(excel_frame, text="Dosya Seç", width=70,
                                           command=lambda: self.sec_dosya(self.entry_excel, "*.xlsx"))
        self.btn_sec_excel.pack(side="left", padx=10)

        btn_frame_aktarici = ctk.CTkFrame(self.tab_aktarici, fg_color="transparent")
        btn_frame_aktarici.pack(pady=50)

        self.btn_baslat_aktarici = ctk.CTkButton(btn_frame_aktarici, text="🚀 VERİ AKTARIMINI BAŞLAT", height=40,
                                                 font=ctk.CTkFont(weight="bold"), command=self.run_veri_aktarici)
        self.btn_baslat_aktarici.pack(side="left", padx=10)

        self.btn_durdur_aktarici = ctk.CTkButton(btn_frame_aktarici, text="⛔ DURDUR", fg_color="gray", state="disabled",
                                                 height=40, font=ctk.CTkFont(weight="bold"),
                                                 command=self.stop_veri_aktarici)
        self.btn_durdur_aktarici.pack(side="left", padx=10)

    # --- SEKME 2: URL KAYDEDİCİ ---
    # --- SEKME 2: URL KAYDEDİCİ ---
    def setup_url_kaydedici_tab(self):

        # 1. Kategori URL (Resimde kaybolan kısım geri geldi)
        ctk.CTkLabel(self.tab_kaydedici, text="1. Kategori URL [ZORUNLU]").pack(pady=(20, 5), anchor="w", padx=20)
        self.entry_kategori_url = ctk.CTkEntry(self.tab_kaydedici, width=350)
        self.entry_kategori_url.pack(pady=0, padx=20, anchor="w")

        # 2. Çekilecek Ürün Sayısı
        ctk.CTkLabel(self.tab_kaydedici, text="2. Çekilecek Ürün Sayısı [ZORUNLU]").pack(pady=(20, 5), anchor="w",
                                                                                         padx=20)
        self.entry_urun_sayisi = ctk.CTkEntry(self.tab_kaydedici, width=150)
        self.entry_urun_sayisi.pack(pady=0, padx=20, anchor="w")

        # 3. Kaydedilecek Dosya İsmi (Opsiyonel) + DOSYA SEÇ BUTONU EKLENDİ
        ctk.CTkLabel(self.tab_kaydedici, text="3. Kaydedilecek Dosya İsmi (.txt) [Opsiyonel]").pack(pady=(20, 5),
                                                                                                    anchor="w", padx=20)
        txt_kayit_frame = ctk.CTkFrame(self.tab_kaydedici, fg_color="transparent")
        txt_kayit_frame.pack(fill="x", padx=20)

        self.entry_txt_kaydedici = ctk.CTkEntry(txt_kayit_frame, width=220,
                                                placeholder_text="Varsayılan: urun_linkleri.txt")
        self.entry_txt_kaydedici.pack(side="left")

        ctk.CTkButton(txt_kayit_frame, text="Dosya Seç", width=70,
                      command=lambda: self.sec_dosya(self.entry_txt_kaydedici, "*.txt")).pack(side="left", padx=10)

        # Başlat Butonu
        self.btn_baslat_kaydedici = ctk.CTkButton(self.tab_kaydedici, text="🔗 URL TOPLAMAYI BAŞLAT", height=40,
                                                  font=ctk.CTkFont(weight="bold"), command=self.run_url_kaydedici)
        self.btn_baslat_kaydedici.pack(pady=50)
    # --- SEKME 3: STOK KONTROL ---
    def setup_stok_kontrol_tab(self):
        ctk.CTkLabel(self.tab_stok, text="1. Kontrol Edilecek (Kaynak) Excel [ZORUNLU]").pack(pady=(20, 5), anchor="w",
                                                                                              padx=20)
        frame1 = ctk.CTkFrame(self.tab_stok, fg_color="transparent")
        frame1.pack(fill="x", padx=20)
        self.entry_stok_girdi = ctk.CTkEntry(frame1, width=220)
        self.entry_stok_girdi.pack(side="left")
        ctk.CTkButton(frame1, text="Dosya Seç", width=70,
                      command=lambda: self.sec_dosya(self.entry_stok_girdi, "*.xlsx")).pack(side="left", padx=10)

        ctk.CTkLabel(self.tab_stok, text="2. Çıktının Yazılacağı Yeni Excel [ZORUNLU]").pack(pady=(20, 5), anchor="w",
                                                                                             padx=20)
        frame2 = ctk.CTkFrame(self.tab_stok, fg_color="transparent")
        frame2.pack(fill="x", padx=20)
        self.entry_stok_cikti = ctk.CTkEntry(frame2, width=220)
        self.entry_stok_cikti.pack(side="left")
        ctk.CTkButton(frame2, text="Dosya Seç", width=70,
                      command=lambda: self.sec_dosya(self.entry_stok_cikti, "*.xlsx")).pack(side="left", padx=10)

        self.btn_baslat_stok = ctk.CTkButton(self.tab_stok, text="⚡ STOK KONTROLÜ BAŞLAT", height=40,
                                             font=ctk.CTkFont(weight="bold"), fg_color="#28a745", hover_color="#218838",
                                             command=self.run_stok_kontrol)
        self.btn_baslat_stok.pack(pady=50)

    # --- SEKME 4: TRENDYOL OTO-BOT ---
    def setup_trendyol_oto_tab(self):
        ctk.CTkLabel(self.tab_oto, text="DİKKAT: Bu bot 7/24 çalışır ve Trendyol'u anında günceller!",
                     text_color="red").pack(pady=(5, 10))

        ctk.CTkLabel(self.tab_oto, text="1. Ana Veritabanı Excel'i (Barkod & Linkler)").pack(pady=(0, 5), anchor="w",
                                                                                             padx=20)
        frame = ctk.CTkFrame(self.tab_oto, fg_color="transparent")
        frame.pack(fill="x", padx=20)
        self.entry_oto_excel = ctk.CTkEntry(frame, width=220)
        self.entry_oto_excel.pack(side="left")
        ctk.CTkButton(frame, text="Dosya Seç", width=70,
                      command=lambda: self.sec_dosya(self.entry_oto_excel, "*.xlsx")).pack(side="left", padx=10)

        ctk.CTkLabel(self.tab_oto, text="2. Trendyol API Bilgileri (Değiştirebilirsiniz):").pack(pady=(15, 5),
                                                                                                 anchor="w", padx=20)
        api_frame = ctk.CTkFrame(self.tab_oto, fg_color="transparent")
        api_frame.pack(fill="x", padx=20)

        self.entry_api_id = ctk.CTkEntry(api_frame, width=80, placeholder_text="Satıcı ID", show="*")
        self.entry_api_id.insert(0, TRENDYOL_SATICI_ID)
        self.entry_api_id.pack(side="left", padx=(0, 5))

        self.entry_api_key = ctk.CTkEntry(api_frame, width=150, placeholder_text="API Key", show="*")
        self.entry_api_key.insert(0, TRENDYOL_API_KEY)
        self.entry_api_key.pack(side="left", padx=(0, 5))

        self.entry_api_secret = ctk.CTkEntry(api_frame, width=150, placeholder_text="API Secret", show="*")
        self.entry_api_secret.insert(0, TRENDYOL_API_SECRET)
        self.entry_api_secret.pack(side="left")

        ctk.CTkLabel(self.tab_oto, text="3. Tur Bekleme Süresi (Dakika)").pack(pady=(15, 5), anchor="w", padx=20)
        self.entry_bekleme = ctk.CTkEntry(self.tab_oto, width=100)
        self.entry_bekleme.insert(0, "15")
        self.entry_bekleme.pack(anchor="w", padx=20)

        btn_frame = ctk.CTkFrame(self.tab_oto, fg_color="transparent")
        btn_frame.pack(pady=15)

        self.btn_baslat_oto = ctk.CTkButton(btn_frame, text="🔥 OTO-BOTU BAŞLAT", fg_color="#d32f2f",
                                            hover_color="#b71c1c", height=40, font=ctk.CTkFont(weight="bold"),
                                            command=self.run_trendyol_bot)
        self.btn_baslat_oto.pack(side="left", padx=10)

        self.btn_durdur_oto = ctk.CTkButton(btn_frame, text="⛔ DURDUR", fg_color="gray", state="disabled", height=40,
                                            font=ctk.CTkFont(weight="bold"), command=self.stop_trendyol_bot)
        self.btn_durdur_oto.pack(side="left", padx=10)

    # --- YARDIMCI FONKSİYONLAR ---
    def sec_dosya(self, entry_widget, file_type):
        dosya = filedialog.askopenfilename(filetypes=[("Dosyalar", file_type)])
        if dosya:
            entry_widget.delete(0, "end")
            entry_widget.insert(0, dosya)

    # --- İŞLEMLER ---
    def run_veri_aktarici(self):
        excel_dosyasi = self.entry_excel.get().strip()
        txt_dosyasi = self.entry_txt_aktarici.get().strip() or "urun_linkleri.txt"
        if not excel_dosyasi:
            messagebox.showerror("Hata", "Lütfen bir Excel dosyası seçin!")
            return

        self.btn_baslat_aktarici.configure(state="disabled", text="ÇALIŞIYOR...")
        self.btn_durdur_aktarici.configure(state="normal", fg_color="#f57c00")
        print(f"\n--- VERİ AKTARICI BAŞLATILDI ---")

        def worker():
            try:
                asyncio.run(veriKaydedici.baslat(txt_dosyasi, excel_dosyasi))
            except Exception as e:
                import traceback
                print(f"\n❌ SİSTEM HATASI ÇIKTI:\n{traceback.format_exc()}")
            finally:
                self.btn_baslat_aktarici.configure(state="normal", text="🚀 VERİ AKTARIMINI BAŞLAT")
                self.btn_durdur_aktarici.configure(state="disabled", fg_color="gray")

        threading.Thread(target=worker, daemon=True).start()


    def run_url_kaydedici(self):
        kategori_url = self.entry_kategori_url.get().strip()
        urun_sayisi_str = self.entry_urun_sayisi.get().strip()
        txt_dosyasi = self.entry_txt_kaydedici.get().strip() or "urun_linkleri.txt"

        if not kategori_url or not urun_sayisi_str.isdigit():
            messagebox.showerror("Hata", "URL ve rakamla ürün sayısı zorunludur!")
            return

        self.btn_baslat_kaydedici.configure(state="disabled", text="ÇALIŞIYOR...")
        print(f"\n--- URL KAYDEDİCİ BAŞLATILDI ---")

        def worker():
            try:
                asyncio.run(urlFinder.baslat(kategori_url, int(urun_sayisi_str), txt_dosyasi))
            except Exception as e:
                import traceback
                print(f"\n❌ SİSTEM HATASI ÇIKTI:\n{traceback.format_exc()}")
            finally:
                self.btn_baslat_kaydedici.configure(state="normal", text="🔗 URL TOPLAMAYI BAŞLAT")

        threading.Thread(target=worker, daemon=True).start()

    def run_stok_kontrol(self):
        girdi_excel = self.entry_stok_girdi.get().strip()
        cikti_excel = self.entry_stok_cikti.get().strip()

        if not girdi_excel or not cikti_excel:
            messagebox.showerror("Hata", "Lütfen Girdi ve Çıktı Excel dosyalarını seçin!")
            return

        self.btn_baslat_stok.configure(state="disabled", text="ÇALIŞIYOR...")
        print(f"\n--- STOK KONTROL BAŞLATILDI ---")

        def worker():
            try:
                asyncio.run(stokKontrol.stok_kontrol_baslat(girdi_excel, cikti_excel))
            except Exception as e:
                import traceback
                print(f"\n❌ SİSTEM HATASI ÇIKTI:\n{traceback.format_exc()}")
            finally:
                self.btn_baslat_stok.configure(state="normal", text="⚡ STOK KONTROLÜ BAŞLAT")

        threading.Thread(target=worker, daemon=True).start()

    def run_trendyol_bot(self):
        excel_dosya = self.entry_oto_excel.get().strip()
        bekleme_dk = self.entry_bekleme.get().strip()

        satici_id = self.entry_api_id.get().strip()
        api_key = self.entry_api_key.get().strip()
        api_secret = self.entry_api_secret.get().strip()

        if not excel_dosya or not bekleme_dk.isdigit():
            messagebox.showerror("Hata", "Lütfen Excel dosyasını seçin ve bekleme süresini yazın!")
            return

        if not satici_id or not api_key or not api_secret:
            messagebox.showerror("Hata", "Lütfen Trendyol API Bilgilerini tam doldurun!")
            return

        self.btn_baslat_oto.configure(state="disabled", text="OTOMASYON ÇALIŞIYOR...")
        self.btn_durdur_oto.configure(state="normal", fg_color="#f57c00")

        def worker():
            try:
                asyncio.run(
                    otoStokKontrol.oto_bot_baslat(excel_dosya, int(bekleme_dk), satici_id, api_key, api_secret))
            except Exception as e:
                import traceback
                print(f"\n❌ SİSTEM HATASI ÇIKTI:\n{traceback.format_exc()}")
            finally:
                self.btn_baslat_oto.configure(state="normal", text="🔥 OTO-BOTU BAŞLAT")
                self.btn_durdur_oto.configure(state="disabled", fg_color="gray")

        threading.Thread(target=worker, daemon=True).start()

    def stop_trendyol_bot(self):
        print("\n⏳ Durdurma sinyali gönderildi, bot mevcut işlemi bitirince kapanacak...")
        self.btn_durdur_oto.configure(state="disabled", text="Durduruluyor...")
        otoStokKontrol.botu_durdur()

    def stop_veri_aktarici(self):
        print("\n⏳ Durdurma sinyali gönderildi, mevcut ürün bittikten sonra duracak...")
        self.btn_durdur_aktarici.configure(state="disabled", text="Durduruluyor...")
        veriKaydedici.veri_aktariciyi_durdur()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"
    app = App()
    app.mainloop()