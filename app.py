import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import os
import re
import streamlit.components.v1 as components

from utils.sheets import load_data, tambah_baris, hapus_baris
from utils.format import rupiah
from openpyxl import load_workbook


# ==================================================
# KONFIGURASI
# ==================================================

editable_table = components.declare_component(
    "editable_table",
    path="components/editable_table"
)


st.set_page_config(
    page_title="Dashboard Pengeluaran",
    layout="wide"
)


# ==================================================
# CSS
# ==================================================

with open("assets/style.css") as f:
    st.markdown(
        f"<style>{f.read()}</style>",
        unsafe_allow_html=True
    )


# ==================================================
# LOAD DATA
# ==================================================

df, errors = load_data()

if errors:
    st.warning("\n".join(errors) )

# ==================================================
# BERSIHKAN DATA
# ==================================================

df = df[
    df["Tanggal"].astype(str).str.strip() != "Tanggal"
].reset_index(drop=True)
df = df[
    ~df.apply(
        lambda row: row.astype(str).str.upper().str.contains("TOTAL").any(),
        axis=1
    )
].reset_index(drop=True)

# Pastikan kolom angka benar-benar numerik
df["Harga"] = pd.to_numeric(
    df["Harga"],
    errors="coerce"
)

df["Jumlah"] = pd.to_numeric(
    df["Jumlah"],
    errors="coerce"
)

df["Subtotal"] = pd.to_numeric(
    df["Subtotal"],
    errors="coerce"
).fillna(0)

# ==================================================
# HITUNG DISKON
# Harga = harga asli per unit
# Subtotal = harga akhir x jumlah
# Diskon = harga asli total - subtotal
# ==================================================


df["Subtotal"] = pd.to_numeric(
    df["Subtotal"],
    errors="coerce"
)

df["Subtotal"] = df["Subtotal"].fillna(0)

df["Diskon"] = (
    (df["Harga"] * df["Jumlah"])
    - df["Subtotal"]
).clip(lower=0)

# ==================================================
# URUTAN BULAN
# ==================================================

urutan_bulan = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]

# ==================================================
# JUDUL
# ==================================================

with st.expander("+ Tambah Pengeluaran"):
    with st.form("form_tambah_pengeluaran"):

        bulan_input = st.selectbox("Bulan", urutan_bulan)
        tanggal_input = st.number_input("Tanggal", min_value=1, max_value=31, step=1)
        kategori_input = st.text_input("Kategori")
        barang_input = st.text_input("Nama Barang")
        harga_input = st.number_input("Harga", min_value=0, step=500)
        jumlah_input = st.number_input("Jumlah", min_value=1, step=1)
        subtotal_input = st.number_input("Subtotal (setelah diskon)", min_value=0, step=500)

        submit = st.form_submit_button("Simpan")

        if submit:
            tambah_baris(
                bulan_input,
                tanggal_input,
                kategori_input,
                barang_input,
                harga_input,
                jumlah_input,
                subtotal_input
            )
            st.success("Data berhasil ditambahkan!")
            st.rerun()


# ==================================================
# FILTER BULAN
# ==================================================

bulan_list = ["Semua"] + [
    bulan
    for bulan in urutan_bulan
    if bulan in df["Bulan"].unique()
]

pilih_bulan = st.sidebar.selectbox(
    "Bulan",
    bulan_list
)


if pilih_bulan == "Semua":
    hasil_bulan = df.copy()

else:
    hasil_bulan = df[
        df["Bulan"] == pilih_bulan
    ].copy()


# ==================================================
# FILTER KATEGORI
# ==================================================

kategori_list = ["Semua"] + sorted(
    hasil_bulan["Kategori"]
    .dropna()
    .astype(str)
    .unique()
)

pilih_kategori = st.sidebar.selectbox(
    "Kategori",
    kategori_list
)


if pilih_kategori == "Semua":
    hasil = hasil_bulan.copy()

else:
    hasil = hasil_bulan[
        hasil_bulan["Kategori"] == pilih_kategori
    ].copy()


# ==================================================
# JUDUL FILTER
# ==================================================

judul = []

if pilih_bulan != "Semua":
    judul.append(pilih_bulan)

if pilih_kategori != "Semua":
    judul.append(pilih_kategori)


if judul:
    st.subheader(" - ".join(judul))

else:
    st.subheader("Semua Pengeluaran")

# ==================================================
# TOTAL
# ==================================================

c1, c2, c3 = st.columns(3)


c1.metric(
    "Jumlah Transaksi",
    len(hasil)
)


c2.metric(
    "Total Pengeluaran",
    rupiah(
        hasil["Subtotal"].sum()
    )
)


c3.metric(
    "Total Diskon",
    rupiah(
        hasil["Diskon"].sum()
    )
)

# ==================================================
# TABEL UTAMA
# ==================================================

kolom_tabel = [
    "Tanggal",
    "Kategori",
    "Barang",
    "Harga",
    "Jumlah",
    "Subtotal",
    "Diskon"
]

if pilih_bulan == "Semua":
    kolom_tabel = [
        "Bulan"
    ] + kolom_tabel

data_tabel = hasil[
    kolom_tabel + ["_sheet", "_excel_row"]
].copy()

# Ubah NaN menjadi string kosong
data_tabel = data_tabel.fillna("")

# Data yang dikirim ke component
records = data_tabel.to_dict("records")

table_version = st.session_state.get(
    "table_version",
    0
)

edited = editable_table(
    data=records,
    key=f"editable_table_{table_version}"
)

if edited and edited.get("action") == "delete":

    hapus_baris(edited["data"])

    st.success("Data berhasil dihapus.")

    st.session_state.table_version = (
        table_version + 1
    )

    st.rerun()

    wb = load_workbook(
        "data/pengeluaran_2026.xlsx"
    )

    for row in data_edit:

        sheet_name = row["_sheet"]
        excel_row = int(row["_excel_row"])

        ws = wb[sheet_name]

        # ------------------------------
        # Tanggal
        # ------------------------------

        tanggal = str(
            row.get("Tanggal", "")
        ).strip()

        if tanggal == "":
            ws.cell(
                excel_row,
                1
            ).value = None
        else:
            try:
                ws.cell(
                    excel_row,
                    1
                ).value = int(float(tanggal))
            except:
                ws.cell(
                    excel_row,
                    1
                ).value = tanggal

        # ------------------------------
        # Kategori
        # ------------------------------

        ws.cell(
            excel_row,
            2
        ).value = row.get(
            "Kategori",
            ""
        )

        # ------------------------------
        # Barang
        # ------------------------------

        ws.cell(
            excel_row,
            3
        ).value = row.get(
            "Barang",
            ""
        )

        # ------------------------------
        # Harga
        # ------------------------------

        harga_text = str(
            row.get("Harga", "")
        )

        harga_text = (
            harga_text
            .replace(".", "")
            .replace(",", "")
            .strip()
        )

        if harga_text == "":
            harga = None
        else:
            harga = float(harga_text)

        ws.cell(
            excel_row,
            4
        ).value = harga

        # ------------------------------
        # Jumlah
        # ------------------------------

        jumlah_text = str(
            row.get("Jumlah", "")
        ).strip()

        if jumlah_text == "":
            jumlah = None
        else:
            jumlah = float(
                jumlah_text.replace(",", ".")
            )

        ws.cell(
            excel_row,
            5
        ).value = jumlah

        # ------------------------------
        # Subtotal
        # ------------------------------

        subtotal_text = str(
            row.get("Subtotal", "")
        )

        subtotal_text = (
            subtotal_text
            .replace(".", "")
            .replace(",", "")
            .strip()
        )

        if subtotal_text == "":
            subtotal = None
        else:
            subtotal = float(subtotal_text)

        ws.cell(
            excel_row,
            6
        ).value = subtotal

        # ------------------------------
        # Diskon
        # ------------------------------

        if (
            harga is not None
            and jumlah is not None
            and subtotal is not None
        ):

            diskon = (
                harga * jumlah
            ) - subtotal

            diskon = max(
                diskon,
                0
            )

        else:
            diskon = None

        ws.cell(
            excel_row,
            7
        ).value = diskon

    wb.save(
        "data/pengeluaran_2026.xlsx"
    )

    st.success(
        "Perubahan berhasil disimpan ke Excel."
    )

    st.session_state.table_version = (
        table_version + 1
    )

    st.rerun()
    
# ===== =============================================
# TABEL UTAMA
# ==================================================

kolom_tabel = [
    "Tanggal",
    "Kategori",
    "Barang",
    "Harga",
    "Jumlah",
    "Subtotal",
    "Diskon"
]

# Tampilkan Bulan jika semua bulan dipilih
if pilih_bulan == "Semua":
    kolom_tabel = [
        "Bulan"
    ] + kolom_tabel





