import re
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
import streamlit as st


SPREADSHEET_ID = "1qxk8yNdkG7l_Zez6PUHWDzj_M4aj2HvSUtM0GRP2nXA"

BULAN = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]

KOLOM_LENGKAP = [
    "Tanggal", "Kategori", "Barang", "Harga", "Jumlah", "Subtotal", "Diskon"
]


def get_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return gspread.authorize(creds)


def load_data():

    client = get_client()
    sh = client.open_by_key(SPREADSHEET_ID)

    semua = []
    gagal = []

    tahun_match = re.search(r"(20\d{2})", sh.title)
    tahun = int(tahun_match.group(1)) if tahun_match else None

    for bulan in BULAN:

        try:
            ws = sh.worksheet(bulan)
            raw = pd.DataFrame(ws.get_all_values(value_render_option='UNFORMATTED_VALUE'))

            if raw.dropna(how="all").empty or raw.empty:
                continue

            baris_header = None

            for i in range(len(raw)):
                nilai_baris = raw.iloc[i].astype(str).str.strip().tolist()
                if "Tanggal" in nilai_baris:
                    baris_header = i
                    break

            if baris_header is None:
                gagal.append(f"{bulan} gagal dibaca: header 'Tanggal' tidak ditemukan")
                continue

            header_asli = (
                raw.iloc[baris_header]
                .astype(str)
                .str.strip()
                .tolist()
            )

            df = raw.iloc[baris_header + 1:].copy()
            df.columns = header_asli[:df.shape[1]]

            df = df.replace("", None)

            def normalisasi(teks):
                return re.sub(r"[^a-z0-9]", "", str(teks).lower())

            mapping = {}
            for kolom_asli in df.columns:
                asli_bersih = normalisasi(kolom_asli)
                for kolom_standar in KOLOM_LENGKAP:
                    standar_bersih = normalisasi(kolom_standar)
                    if standar_bersih in asli_bersih:
                        mapping[kolom_asli] = kolom_standar
                        break

            df = df.rename(columns=mapping)

            for kolom in KOLOM_LENGKAP:
                if kolom not in df.columns:
                    df[kolom] = None

            df = df[KOLOM_LENGKAP]

            df["_excel_row"] = df.index + baris_header + 2
            df["_sheet"] = bulan

            kolom_cek = ["Kategori", "Barang", "Harga", "Jumlah", "Subtotal"]
            df = df[df[kolom_cek].notna().any(axis=1)].copy()

            df["Tanggal"] = df["Tanggal"].ffill()
            df = df[df[kolom_cek].notna().any(axis=1)].copy()

            df["Bulan"] = bulan
            df["Tahun"] = tahun

            semua.append(df)

        except Exception as e:
            gagal.append(f"{bulan} gagal dibaca: {e}")

    if len(semua) == 0:
        return pd.DataFrame(), gagal

    hasil = pd.concat(semua, ignore_index=True)

    hasil["Harga"] = pd.to_numeric(hasil["Harga"], errors="coerce")
    hasil["Jumlah"] = pd.to_numeric(hasil["Jumlah"], errors="coerce")
    hasil["Subtotal"] = pd.to_numeric(hasil["Subtotal"], errors="coerce")
    hasil["Diskon"] = pd.to_numeric(hasil["Diskon"], errors="coerce")

    hasil["Kategori"] = hasil["Kategori"].astype(str).str.strip().str.title()
    hasil["Barang"] = hasil["Barang"].astype(str).str.strip()
    hasil["Tanggal"] = hasil["Tanggal"].astype(str).str.strip()

    hasil["Kategori"] = hasil["Kategori"].replace("Nan", "")
    hasil["Barang"] = hasil["Barang"].replace("nan", "")

    hasil = hasil[
        ~hasil.apply(
            lambda row: row.astype(str).str.upper().str.contains("TOTAL").any(),
            axis=1
        )
    ].reset_index(drop=True)

    hasil = hasil[[
        "Tahun", "Bulan", "Tanggal", "Kategori", "Barang",
        "Harga", "Jumlah", "Subtotal", "Diskon", "_sheet", "_excel_row"
    ]]

    return hasil, gagal


def tambah_baris(bulan, tanggal, kategori, barang, harga, jumlah, subtotal):

    client = get_client()
    ws = client.open_by_key(SPREADSHEET_ID).worksheet(bulan)

    diskon = max((harga * jumlah) - subtotal, 0)

    ws.append_row([tanggal, kategori, barang, harga, jumlah, subtotal, diskon])


def hapus_baris(daftar_hapus):

    client = get_client()
    sh = client.open_by_key(SPREADSHEET_ID)

    per_sheet = {}
    for item in daftar_hapus:
        sheet = item["_sheet"]
        baris = int(item["_excel_row"])
        per_sheet.setdefault(sheet, []).append(baris)

    for sheet_name, daftar_baris in per_sheet.items():
        ws = sh.worksheet(sheet_name)
        for baris in sorted(daftar_baris, reverse=True):
            ws.delete_rows(baris)