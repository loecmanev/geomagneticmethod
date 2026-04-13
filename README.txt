GeomagApp - Web Praktikum Metode Geomagnetik 2026
GeomagApp adalah platform berbasis web yang dirancang khusus untuk membantu praktikan dalam melakukan pengolahan data geomagnetik.

Backend (Server-side) 
Bahasa Pemrograman: Python 3.11. 
Framework: FastAPI. 
Library Utama: NumPy, SciPy, Pandas, dan IGRF-Utils. 
Database: SQLite3 untuk manajemen persistensi data sesi. 
Deployment: Hugging Face Spaces dengan infrastruktur Container Docker. 

Frontend (Client-side) Teknologi: HTML5, CSS3, dan JavaScript (Vanilla JS). 
Komunikasi Data: Asynchronous JavaScript and XML (AJAX) menggunakan Fetch API ke endpoint RESTful backend. 
Deployment: GitHub Pages.

#1 KOREKSI IGRF

├── IGRF/                 # Modul utama pemodelan sferis harmonik
│   ├── SHC_files/        # File koefisien model IGRF-14 (.SHC)
│   └── igrf_utils.py     # Fungsi matematis pengolahan koordinat
├── main.py               # Logika server utama dan definisi API Endpoint
├── Dockerfile            # Instruksi konfigurasi lingkungan server
├── requirements.txt      # Daftar dependensi library Python
├── praktikum_geomagnet.db # Basis data lokal untuk identitas praktikan
├── index.html            # Antarmuka beranda aplikasi
├── login.html            # Antarmuka gerbang masuk pengguna
├── igrf.html             # Antarmuka komputasi data magnetik
└── processing.html       # Antarmuka pengolahan data massal

Instruksi Operasional Akses halaman utama melalui URL GitHub Pages yang telah disediakan. 
1. Lakukan login dengan memasukkan Nama dan NIM. 
2. Pilih metode input: Single Point: Masukkan koordinat (Lat, Lon), elevasi, dan tanggal pengukuran secara manual. Massal: Unggah file Excel sesuai template kolom yang ditentukan (Lat, Lon, Elevasi). 
3. Tunggu hingga server Hugging Face memuat API. 
4. Periksa hasil pada tabel yang muncul dan gunakan fitur unduh untuk menyimpan data.

Aplikasi ini dikembangkan untuk kebutuhan internal:
Laboratorium Geofisika Eksplorasi
Jurusan Teknik Geofisika
Fakultas Teknologi Mineral
UPN "Veteran" Yogyakarta

Pengembang: Muhammad Luqman Rahmatullah - @luqmanrhmt
