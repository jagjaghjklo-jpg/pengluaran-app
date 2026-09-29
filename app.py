import streamlit as st
import streamlit.components.v1 as components
import pandas as pd

from utils.sheets import (
    load_data,
    tambah_baris,
    hapus_baris,
    update_baris,
)
from utils.format import rupiah


st.set_page_config(
    page_title="Dashboard Pengeluaran",
    layout="wide",
)

editable_table = components.declare_component(
    "editable_table",
    path="components/editable_table",
)


with open("assets/style.css") as f:
    st.markdown(
        f"<style>{f.read()}</style>",
        unsafe_allow_html=True,
    )


# Baca data dari Google Sheets
df, errors = load_data()

if st.session_state.get("delete_notice"):
    st.success(st.session_state.pop("delete_notice"))

if errors:
    st.warning("\n".join(errors))


# Bersihkan data
df = df[
    df["Tanggal"].astype(str).str.strip() != "Tanggal"
].reset_index(drop=True)

df = df[
    ~df.apply(
        lambda row: row.astype(str)
        .str.upper()
        .str.contains("TOTAL")
        .any(),
        axis=1,
    )
].reset_index(drop=True)


# Pastikan nilai angka bertipe numerik
df["Harga"] = pd.to_numeric(df["Harga"], errors="coerce")
df["Jumlah"] = pd.to_numeric(df["Jumlah"], errors="coerce")
df["Subtotal"] = pd.to_numeric(
    df["Subtotal"],
    errors="coerce",
).fillna(0)

# Hitung diskon
df["Diskon"] = (
    (df["Harga"] * df["Jumlah"]) - df["Subtotal"]
).clip(lower=0)


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
    "Desember",
]


# Tambah pengeluaran
with st.expander("+ Tambah Pengeluaran"):
    with st.form("form_tambah_pengeluaran"):
        bulan_input = st.selectbox("Bulan", urutan_bulan)
        tanggal_input = st.number_input(
            "Tanggal",
            min_value=1,
            max_value=31,
            step=1,
        )
        kategori_input = st.text_input("Kategori")
        barang_input = st.text_input("Nama Barang")
        harga_input = st.number_input(
            "Harga",
            min_value=0,
            step=500,
        )
        jumlah_input = st.number_input(
            "Jumlah",
            min_value=1,
            step=1,
        )
        subtotal_input = st.number_input(
            "Subtotal (setelah diskon)",
            min_value=0,
            step=500,
        )

        submit = st.form_submit_button("Simpan")

        if submit:
            try:
                tambah_baris(
                    bulan_input,
                    tanggal_input,
                    kategori_input,
                    barang_input,
                    harga_input,
                    jumlah_input,
                    subtotal_input,
                )
                st.success("Data berhasil ditambahkan.")
                st.rerun()
            except Exception as e:
                st.error(f"GAGAL MENYIMPAN: {type(e).__name__}: {e}")


# Filter bulan
bulan_list = ["Semua"] + [
    bulan for bulan in urutan_bulan
    if bulan in df["Bulan"].unique()
]

pilih_bulan = st.sidebar.selectbox("Bulan", bulan_list)

if pilih_bulan == "Semua":
    hasil_bulan = df.copy()
else:
    hasil_bulan = df[df["Bulan"] == pilih_bulan].copy()


# Filter kategori
kategori_list = ["Semua"] + sorted(
    hasil_bulan["Kategori"]
    .dropna()
    .astype(str)
    .unique()
)

pilih_kategori = st.sidebar.selectbox("Kategori", kategori_list)

if pilih_kategori == "Semua":
    hasil = hasil_bulan.copy()
else:
    hasil = hasil_bulan[
        hasil_bulan["Kategori"] == pilih_kategori
    ].copy()


# Judul
judul = []

if pilih_bulan != "Semua":
    judul.append(pilih_bulan)

if pilih_kategori != "Semua":
    judul.append(pilih_kategori)

st.subheader(" - ".join(judul) if judul else "Semua Pengeluaran")


# Total
c1, c2, c3 = st.columns(3)

c1.metric("Jumlah Transaksi", len(hasil))
c2.metric("Total Pengeluaran", rupiah(hasil["Subtotal"].sum()))
c3.metric("Total Diskon", rupiah(hasil["Diskon"].sum()))


# Siapkan data tabel
kolom_tabel = [
    "Tanggal",
    "Kategori",
    "Barang",
    "Harga",
    "Jumlah",
    "Subtotal",
    "Diskon",
]

if pilih_bulan == "Semua":
    kolom_tabel = ["Bulan"] + kolom_tabel

data_tabel = hasil[
    kolom_tabel + ["_sheet", "_excel_row"]
].copy()

data_tabel = data_tabel.fillna("")
records = data_tabel.to_dict("records")


# Key baru membuat komponen tabel dibuat ulang setelah perubahan
table_version = st.session_state.get("table_version", 0)


# Tabel custom untuk edit/simpan
edited = editable_table(
    data=records,
    key=f"editable_table_{table_version}",
)


def hapus_dan_refresh(data_hapus):
    if not data_hapus:
        st.error("Belum ada transaksi yang dipilih.")
        return

    try:
        terhapus = hapus_baris(data_hapus)
        st.session_state["delete_notice"] = (
            f"Berhasil menghapus {len(terhapus)} baris dari Google Sheets."
        )
        st.session_state["table_version"] = table_version + 1
        st.rerun()
    except Exception as e:
        st.error(f"DELETE GAGAL: {type(e).__name__}: {e}")


# Jalur hapus dari tombol di dalam custom table
if edited and edited.get("action") == "delete":
    hapus_dan_refresh(edited.get("data", []))


# Simpan hasil edit dari custom table
if edited and edited.get("action") == "save":
    try:
        update_baris(edited["data"])
        st.session_state["table_version"] = table_version + 1
        st.success("Perubahan berhasil disimpan.")
        st.rerun()
    except Exception as e:
        st.error(f"GAGAL MENYIMPAN EDIT: {type(e).__name__}: {e}")
