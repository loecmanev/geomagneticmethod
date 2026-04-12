import sqlite3

def inisialisasi_db():
    # Membuat atau menghubungkan ke file database
    conn = sqlite3.connect('praktikum_geomagnet.db')
    cursor = conn.cursor()

    # Tabel 1: Untuk menyimpan data praktikan yang login
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pengguna (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT NOT NULL,
            nim TEXT NOT NULL,
            waktu_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
    print("Sistem Database: Siap digunakan.")

if __name__ == "__main__":
    inisialisasi_db()