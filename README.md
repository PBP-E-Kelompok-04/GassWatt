# GassWatt

Proyek Tengah Semester Kelompok 4 — Pemrograman Berbasis Platform

## Deskripsi Aplikasi

GassWatt adalah aplikasi web yang membantu pengguna memahami dan mengevaluasi jejak karbon dari kebiasaan sehari-hari, khususnya penggunaan energi dan aktivitas rumah tangga maupun anak kos. Pengguna dapat mencatat penggunaan perangkat listrik, transportasi, dan barang guna ulang untuk memperoleh estimasi emisi karbon serta melihat riwayat dan grafik emisi.

Aplikasi ini juga menggunakan data cuaca berdasarkan lokasi pengguna untuk memberikan rekomendasi yang lebih relevan dengan kondisi lingkungan. GassWatt dibangun menggunakan Django dengan arsitektur **Model-Template-View (MTV)**.

## Penerapan Arsitektur MTV (Model-Template-View)

1. **Model (`main/models.py`)**
   - Mengelola struktur data dan interaksi dengan basis data, termasuk:
     - **TransportationSurvey**: moda dan jarak transportasi beserta estimasi emisinya.
     - **ElectricitySurvey**: perangkat, jumlah, daya, dan durasi penggunaan listrik beserta konsumsi energi dan estimasi emisinya.
     - **ReusableItemSurvey**: penggunaan barang guna ulang dan estimasi emisinya.
     - **DailyEmissionLog**: ringkasan emisi harian untuk riwayat dan grafik.
     - **SavedLocation**: lokasi tersimpan pengguna untuk informasi cuaca.
     - **FAQ**: pertanyaan dan jawaban yang ditampilkan pada aplikasi.
2. **Template (`templates/`)**
   - Menggunakan Django Template Language (DTL) untuk merender halaman, komponen, dan data yang dikirim dari view.
   - Template dikelompokkan berdasarkan bagian aplikasi, seperti dashboard, halaman utama, autentikasi, dan komponen.
3. **View (`main/views.py`, `authentication/views.py`, dan `GassWatt/view.py`)**
   - Memproses permintaan HTTP, menjalankan logika aplikasi, berinteraksi dengan model, dan memilih template untuk ditampilkan.
   - Menangani alur autentikasi serta fitur survei, dashboard, administrasi, cuaca, dan rekomendasi.

## Panduan Setup & Instalasi Lokal

### Prasyarat Sistem

- **Python** 3.10 atau lebih baru
- **pip**
- **Git**

### Langkah Instalasi

1. Klon repositori dan masuk ke direktori proyek:

   ```bash
   git clone https://github.com/PBP-E-Kelompok-04/GassWatt.git
   cd GassWatt
   ```

2. Buat dan aktifkan virtual environment:

   **Windows PowerShell**

   ```powershell
   python -m venv env
   .\env\Scripts\Activate.ps1
   ```

   **Linux/macOS**

   ```bash
   python3 -m venv env
   source env/bin/activate
   ```

3. Pasang dependensi:

   ```bash
   pip install -r requirements.txt
   ```

4. Terapkan migrasi basis data:

   ```bash
   python manage.py migrate
   ```

5. Jalankan server pengembangan:

   ```bash
   python manage.py runserver
   ```

   Buka <http://127.0.0.1:8000/> di browser.

Secara default, proyek menggunakan SQLite untuk pengembangan lokal. Konfigurasi produksi menggunakan PostgreSQL dan diaktifkan melalui variabel lingkungan `PRODUCTION`; kredensial basis data produksi tidak diperlukan untuk menjalankan aplikasi secara lokal.

## Pengelolaan Konten Aplikasi

Pengguna terautentikasi dapat mengisi survei kebiasaan sehari-hari dan mencatat aktivitas yang tersedia di aplikasi. Data tersebut digunakan untuk menghitung estimasi emisi, menampilkan riwayat, dan menyusun rekomendasi. FAQ dan administrasi pengguna dikelola melalui fitur portal admin sesuai hak aksesnya.

## Menjalankan Pengujian (Testing)

Proyek menggunakan kerangka pengujian bawaan Django. Jalankan seluruh pengujian dengan perintah:

```bash
python manage.py test
```

## Penjelasan Role Pengguna

1. **Pengunjung tanpa login**: dapat melihat halaman utama dan informasi umum tentang GassWatt; perlu login untuk fitur yang membutuhkan akun.
2. **Pengguna**: dapat melengkapi profil, mengisi survei kebiasaan, mencatat penggunaan perangkat dan aktivitas, serta melihat estimasi, riwayat, grafik, dan rekomendasi.
3. **Admin**: memiliki akses ke portal admin untuk mengelola pengguna dan FAQ serta melihat statistik dan tren website.

## Pembagian Tugas

| Anggota | NPM | Tanggung jawab |
|---|---:|---|
| Fernando Hazel | 2506587195 | Autentikasi dan profil pengguna |
| Sofie Daniella Ang | 2506619562 | Profil admin dan portal admin |
| Yohana Louisa Saragih | 2506584205 | Homepage, About Us, FAQ, dan survei inventaris |
| Arya Dwipa Wicaksana | 2506623111 | Fitur cuaca dan rekomendasi |
| Suruuri Isya Alfaruq | 2506548080 | Perhitungan Ringkasan emisi dan rekomendasi berdasarkan emisi, Pembuatan Survey Untuk Inventarisasi Transportasi, serta desain dan sebagian kartu pada Dashboard utama  |

## AI Disclosure

| No | Penggunaan | Alat | Keterangan |
|---|---|---|---|
| 1 | Penyusunan dan perapian README | AI assistant menggunakan Copilot SDK di VS Code | Membantu menyusun dokumentasi berdasarkan struktur dan informasi proyek yang tersedia. Penggunaan AI ini terbatas pada README dan tidak menyatakan bahwa implementasi aplikasi dibuat oleh AI. |
| 2 | Dasar Perhitungan Emisi | Gemini AI | Membantu membuat dasar perhitungan untuk emisi seperti untuk setiap moda transportasi memiliki rata-rata emisi yang dihasilkan per-km dan perhitungan eco-score.
| 3 | Cara Menggunakan Chart.js | Gemini AI | Membantu mengarahkan penggunaan chart.jas untuk perhitungan emisi seminggu dengan konteks terkait.
| 4 | Implementasi Pengambilan Data dari API dan Penerapan Cache | Gemini AI | Membantu dalam menerapkan pengambilan data cuaca melalui API Open-Meteo serta penerapan mekanisme caching untuk mengurangi permintaan data berulang.
| 5 | Implementasi Pencarian Lokasi | Gemini AI | Membantu dalam mengimplementasikan Geocoding Open-Meteo untuk pencarian lokasi dan pengambilan koordinat melalui GPS.

## Referensi

- Dokumentasi Public API Open-Meteo: <https://open-meteo.com/en/docs>
- Desain Figma GassWatt: <https://www.figma.com/design/smLsJmdd3R4Z5DMCoHq1xS/GassWatt?node-id=0-1&t=TZGIqgrjTskNhzp8-1>
- Website GassWatt: <https://arya-dwipa-gasswatt.pws.cs.ui.ac.id/>
