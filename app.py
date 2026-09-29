import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import os
import re

from utils.sheets import (
    load_data,
    tambah_baris,
    hapus_baris,
    update_baris
)

from utils.format import rupiah


# ==================================================
# KONFIGURASI COMPONENT
# ==================================================

editable_table = components.declare_component(
    "editable_table",
    path="components/editable_table"
)


# ==================================================
# KONFIGURASI STREAMLIT
# ==================================================

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
    st.warning("\n".join(errors))


# ==================================================
# BERSIHKAN DATA
# ==================================================

df = df[
    df["Tanggal"].astype(str).str.strip() != "Tanggal"
].reset_index(drop=True)

df = df[
    ~df.apply(
        lambda row: row.astype(str)
        .str.upper()
        .str.contains("TOTAL")
        .any(),
        axis=1
    )
].reset_index(drop=True)


# ==================================================
# PASTIKAN KOLOM ANGKA NUMERIK
# ==================================================

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
# ==================================================

df["Diskon"] = (
    (df["Harga"] * df["Jumlah"])
    - df["Subtotal"]
).clip(lower=0)


# ==================================================
# URUTAN BULAN
# ==================================================

urutan_bulan = [
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


# ==================================================
# TAMBAH PENGELUARAN
# ==================================================

with st.expander("+ Tambah Pengeluaran"):

    with st.form("form_tambah_pengeluaran"):

        bulan_input = st.selectbox(
            "Bulan",
            urutan_bulan
        )

        tanggal_input = st.number_input(
            "Tanggal",
            min_value=1,
            max_value=31,
            step=1
        )

        kategori_input = st.text_input(
            "Kategori"
        )

        barang_input = st.text_input(
            "Nama Barang"
        )

        harga_input = st.number_input(
            "Harga",
            min_value=0,
            step=500
        )

        jumlah_input = st.number_input(
            "Jumlah",
            min_value=1,
            step=1
        )

        subtotal_input = st.number_input(
            "Subtotal (setelah diskon)",
            min_value=0,
            step=500
        )

        submit = st.form_submit_button(
            "Simpan"
        )

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

            st.success(
                "Data berhasil ditambahkan!"
            )

            # Bersihkan cache supaya data terbaru
            # langsung diambil dari Google Sheets
            st.cache_data.clear()

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

    st.subheader(
        " - ".join(judul)
    )

else:

    st.subheader(
        "Semua Pengeluaran"
    )


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


# Tampilkan Bulan jika memilih Semua
if pilih_bulan == "Semua":

    kolom_tabel = [
        "Bulan"
    ] + kolom_tabel


data_tabel = hasil[
    kolom_tabel + [
        "_sheet",
        "_excel_row"
    ]
].copy()


# ==================================================
# BERSIHKAN NILAI KOSONG
# ==================================================

data_tabel = data_tabel.fillna("")


# ==================================================
# UBAH DATA MENJADI RECORD
# ==================================================

records = data_tabel.to_dict(
    "records"
)


# ==================================================
# VERSI TABLE
# ==================================================

table_version = st.session_state.get(
    "table_version",
    0
)


# ==================================================
# EDITABLE TABLE
# ==================================================

edited = editable_table(
    data=records,
    key=f"editable_table_{table_version}"
)


# ==================================================
# HAPUS BARIS
# ==================================================
if edited and edited.get("action") == "delete":

    data_hapus = edited.get("data", [])

    if not data_hapus:
        st.error("Data hapus kosong.")
        st.stop()

    try:

        hasil_hapus = hapus_baris(data_hapus)

        for pesan in hasil_hapus:
            st.write(pesan)

        st.success("Perintah DELETE berhasil dikirim ke Google Sheets.")


        st.session_state.table_version = (
            table_version + 1
        )

        st.rerun()

    except Exception as e:

        st.error(
            f"GAGAL HAPUS: {type(e).__name__}: {e}"
        )
# ==================================================
# SIMPAN HASIL EDIT
# ==================================================

if edited and edited.get("action") == "save":

    update_baris(
        edited["data"]
    )

    st.success(
        "Perubahan berhasil disimpan."
    )

    # Bersihkan cache Google Sheets
    st.cache_data.clear()

    # Ganti key table supaya component
    # mengambil data terbaru
    st.session_state.table_version = (
        table_version + 1
    )

    st.rerun()