from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import sys
import os

# --- 1. SETUP LOKASI FOLDER IGRF ---
# Memaksa Python untuk membaca folder 'IGRF' agar bisa import igrf_utils
folder_igrf = os.path.join(os.path.dirname(os.path.abspath(__file__)), "IGRF")
sys.path.append(folder_igrf)

import igrf_utils as iut
import numpy as np
import datetime
from scipy import interpolate

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 2. VARIABEL GLOBAL UNTUK MODEL IGRF ---
IGRF_MODEL_DATA = None

def muat_model_igrf():
    """Fungsi untuk memuat file koefisien .SHC hanya sekali saat server menyala"""
    global IGRF_MODEL_DATA
    # Path menyesuaikan folder IGRF/SHC_files/
    shc_path = os.path.join(folder_igrf, "SHC_files", "IGRF14.SHC")
    try:
        IGRF_MODEL_DATA = iut.load_shcfile(shc_path, None)
        print("Model IGRF-14 berhasil dimuat ke memori server!")
    except Exception as e:
        print(f"Gagal memuat model IGRF: {e}")

# Panggil fungsi ini saat server baru menyala
muat_model_igrf()


# --- 3. FUNGSI MATEMATIKA DARI SCRIPT ANDA ---
def date_to_decimal_year(date_obj):
    start_of_year = datetime.date(date_obj.year, 1, 1)
    days_in_year = 366 if (date_obj.year % 4 == 0 and (date_obj.year % 100 != 0 or date_obj.year % 400 == 0)) else 365
    day_of_year = (date_obj - start_of_year).days
    return date_obj.year + (day_of_year / days_in_year)

def geodetic_to_geocentric(lat, lon, alt_km):
    a = 6378.137
    f = 1/298.257223563
    b = a * (1 - f)
    e2 = 1 - (b/a)**2
    
    lat_rad = np.radians(lat)
    clat = np.cos(lat_rad)
    slat = np.sin(lat_rad)
    
    N = a / np.sqrt(1 - e2 * slat**2)
    X = (N + alt_km) * clat * np.cos(np.radians(lon))
    Y = (N + alt_km) * clat * np.sin(np.radians(lon))
    Z = (N * (1 - e2) + alt_km) * slat
    
    r = np.sqrt(X**2 + Y**2 + Z**2)
    lat_geocentric = np.arcsin(Z / r)
    colat_rad = (np.pi / 2) - lat_geocentric
    
    psi = lat_geocentric
    phi = lat_rad
    cd = np.cos(phi - psi)
    sd = np.sin(phi - psi)
    
    return r, colat_rad, sd, cd


# --- 4. FORMAT DATA KOMUNIKASI ---
class LoginData(BaseModel):
    nama: str
    nim: str

class IGRFInput(BaseModel):
    nama_praktikan: str
    lat: float
    lon: float
    alt: float  # dalam meter (Z)
    tanggal: str # Format: YYYY-MM-DD

# --- 5. RUTE API ---

@app.post("/api/login")
async def login(data: LoginData):
    try:
        conn = sqlite3.connect('praktikum_geomagnet.db')
        cursor = conn.cursor()
        cursor.execute("SELECT nama FROM pengguna WHERE nim = ?", (data.nim,))
        user_existing = cursor.fetchone()
        
        if user_existing:
            pesan = f"Selamat datang kembali, {user_existing[0]}!"
        else:
            cursor.execute("INSERT INTO pengguna (nama, nim) VALUES (?, ?)", (data.nama, data.nim))
            pesan = "Data sesi baru berhasil disiapkan."
            
        conn.commit()
        conn.close()
        return {"status": "success", "message": pesan}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/api/hitung_igrf")
async def hitung_igrf(data: IGRFInput):
    if IGRF_MODEL_DATA is None:
        return {"status": "error", "message": "Model IGRF belum dimuat di server."}

    try:
        # Konversi tanggal
        survey_date = datetime.datetime.strptime(data.tanggal, "%Y-%m-%d").date()
        decimal_year = date_to_decimal_year(survey_date)
        
        # Interpolasi koefisien
        f_interp = interpolate.interp1d(IGRF_MODEL_DATA.time, IGRF_MODEL_DATA.coeffs, fill_value='extrapolate')
        coeffs = f_interp(decimal_year)
        
        # Konversi elevasi
        alt_km = data.alt / 1000.0 
        
        # Hitung Geocentric
        r, colat_rad, sd, cd = geodetic_to_geocentric(data.lat, data.lon, alt_km)
        colat_deg = np.degrees(colat_rad)
        
        # Sintesis nilai (menggunakan fungsi iut dari script Anda)
        Br, Bt, Bp = iut.synth_values(coeffs.T, r, colat_deg, data.lon, IGRF_MODEL_DATA.parameters['nmax'])
        
        X = -Bt
        Y = Bp
        Z = -Br
        
        t = X
        X = X * cd + Z * sd
        Z = Z * cd - t * sd
        
        # Ekstrak nilai Deklinasi, Inklinasi, Total Field
        dec, hoz, inc, eff = iut.xyz2dhif(X, Y, Z)
        
        # Cetak di terminal untuk bukti jalan
        print(f"[{data.nama_praktikan}] menghitung koordinat ({data.lat}, {data.lon}) -> F: {round(eff, 2)} nT")

        return {
            "status": "success", 
            "data": {
                "deklinasi": round(dec, 4),
                "inklinasi": round(inc, 4),
                "total_field": round(eff, 2)
            }
        }
        
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
from fastapi import UploadFile, File, Form
import pandas as pd
import io

# ... (Kode main.py Anda yang sebelumnya tetap ada di atasnya) ...

@app.post("/api/hitung_igrf_massal")
async def hitung_igrf_massal(
    tanggal: str = Form(...),
    file: UploadFile = File(...)
):
    if IGRF_MODEL_DATA is None:
        return {"status": "error", "message": "Model IGRF belum dimuat di server."}

    try:
        # 1. Baca file Excel yang diunggah ke dalam memori
        isi_file = await file.read()
        
        # Baca menggunakan Pandas (header=None agar nama kolom tidak dipedulikan)
        # Asumsi: Kolom 0 = Lat, Kolom 1 = Lon, Kolom 2 = Alt
        df = pd.read_excel(io.BytesIO(isi_file), header=None)
        
        # Cek apakah minimal ada 3 kolom
        if len(df.columns) < 3:
            return {"status": "error", "message": "File Excel minimal harus memiliki 3 kolom (Latitude, Longitude, Elevasi)."}

        # Buang baris pertama jika itu adalah teks header (misal: "Lat", "Lon")
        # Kita cek apakah baris pertama kolom pertama adalah string
        if isinstance(df.iloc[0, 0], str):
            df = df.iloc[1:].reset_index(drop=True)

        # 2. Siapkan komputasi IGRF
        survey_date = datetime.datetime.strptime(tanggal, "%Y-%m-%d").date()
        decimal_year = date_to_decimal_year(survey_date)
        
        f_interp = interpolate.interp1d(IGRF_MODEL_DATA.time, IGRF_MODEL_DATA.coeffs, fill_value='extrapolate')
        coeffs = f_interp(decimal_year)

        # Siapkan tempat untuk menyimpan hasil
        hasil_komputasi = []

        # 3. Looping setiap baris di Excel
        for index, row in df.iterrows():
            try:
                lat = float(row[0])
                lon = float(row[1])
                alt_m = float(row[2])
                alt_km = alt_m / 1000.0
                
                # Proses Geocentric -> Synth -> DHIF
                r, colat_rad, sd, cd = geodetic_to_geocentric(lat, lon, alt_km)
                colat_deg = np.degrees(colat_rad)
                
                Br, Bt, Bp = iut.synth_values(coeffs.T, r, colat_deg, lon, IGRF_MODEL_DATA.parameters['nmax'])
                
                X = -Bt
                Y = Bp
                Z = -Br
                
                t = X
                X = X * cd + Z * sd
                Z = Z * cd - t * sd
                
                dec, hoz, inc, eff = iut.xyz2dhif(X, Y, Z)
                
                # Simpan hasil untuk baris ini
                hasil_komputasi.append({
                    "Titik": index + 1,
                    "Lat": round(lat, 6),
                    "Lon": round(lon, 6),
                    "Elevasi": alt_m,
                    "IGRF_Dec": round(dec, 4),
                    "IGRF_Inc": round(inc, 4),
                    "IGRF_Total": round(eff, 2)
                })
            except Exception as e:
                # Jika ada baris yang kosong atau error angkanya, lewati saja
                continue

        # 4. Kembalikan data hasil komputasi ke Frontend
        print(f"Berhasil memproses {len(hasil_komputasi)} titik data massal.")
        return {
            "status": "success",
            "total_data": len(hasil_komputasi),
            "data": hasil_komputasi
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)