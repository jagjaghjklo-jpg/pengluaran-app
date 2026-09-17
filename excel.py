import pandas as pd

FILE = "data/pengeluaran_2026.xlsx"

BULAN = [
    "Januari",
    "Februari",
    "Maret",
    "April",
    "Mei",
    "Juni",
    "Juli",
    "Agustus",
    "September",
    "Oktober",
    "November",
    "Desember"
]


def load_data():
    semua = []
    gagal = []

    for bulan in BULAN:
        try:
            df = pd.read_excel(FILE, sheet_name=bulan)

            # Ambil maksimal 6 kolom pertama
            df = df.iloc[:, :6]

            df.columns = [
                "Tanggal",
                "Kategori",
                "Barang",
                "Harga",
                "Jumlah",
                "Subtotal"
            ]

            df["Bulan"] = bulan

            semua.append(df)

        except Exception as e:
            gagal.append(f"{bulan} gagal dibaca: {e}")

    if len(semua) == 0:
        return pd.DataFrame(), gagal

    hasil = pd.concat(semua, ignore_index=True)

    hasil = hasil.dropna(subset=["Kategori"])

    hasil["Kategori"] = hasil["Kategori"].astype(str).str.strip().str.title()

    hasil["Harga"] = pd.to_numeric(
        hasil["Harga"],
        errors="coerce"
    )

    hasil["Subtotal"] = pd.to_numeric(
        hasil["Subtotal"],
        errors="coerce"
    )

    return hasil, gagal