import re

import gspread
import pandas as pd
import streamlit as st

from google.oauth2.service_account import Credentials


# ==================================================
# KONFIGURASI
# ==================================================

SPREADSHEET_ID = "1qxk8yNdkG7l_Zez6PUHWDzj_M4aj2HvSUtM0GRP2nXA"

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
    "Desember",
]

KOLOM_LENGKAP = [
    "Tanggal",
    "Kategori",
    "Barang",
    "Harga",
    "Jumlah",
    "Subtotal",
    "Diskon",
]


# ==================================================
# GOOGLE SHEETS CLIENT
# ==================================================

@st.cache_resource
def get_client():

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets"
        ],
    )

    return gspread.authorize(creds)


# ==================================================
# NORMALISASI NAMA KOLOM
# ==================================================

def normalisasi(teks):

    return re.sub(
        r"[^a-z0-9]",
        "",
        str(teks).lower(),
    )


# ==================================================
# PROSES 1 SHEET
# ==================================================

def proses_sheet(
    raw,
    bulan,
    tahun,
):

    semua = []

    # --------------------------------------------------
    # Sheet kosong
    # --------------------------------------------------

    if not raw:
        return None

    raw = pd.DataFrame(raw)

    if raw.empty or raw.dropna(
        how="all"
    ).empty:
        return None


    # --------------------------------------------------
    # Cari header
    # --------------------------------------------------

    baris_header = None

    for i in range(len(raw)):

        nilai_baris = (
            raw.iloc[i]
            .astype(str)
            .str.strip()
            .tolist()
        )

        if "Tanggal" in nilai_baris:

            baris_header = i
            break


    if baris_header is None:
        return None


    # --------------------------------------------------
    # Ambil header
    # --------------------------------------------------

    header_asli = (
        raw.iloc[baris_header]
        .astype(str)
        .str.strip()
        .tolist()
    )


    # --------------------------------------------------
    # Ambil data setelah header
    # --------------------------------------------------

    df = raw.iloc[
        baris_header + 1:
    ].copy()


    if df.empty:
        return None


    df.columns = header_asli[
        :df.shape[1]
    ]


    df = df.replace(
        "",
        None,
    )


    # --------------------------------------------------
    # Normalisasi nama kolom
    # --------------------------------------------------

    mapping = {}

    for kolom_asli in df.columns:

        asli_bersih = normalisasi(
            kolom_asli
        )

        for kolom_standar in KOLOM_LENGKAP:

            standar_bersih = normalisasi(
                kolom_standar
            )

            if standar_bersih in asli_bersih:

                mapping[
                    kolom_asli
                ] = kolom_standar

                break


    df = df.rename(
        columns=mapping
    )


    # --------------------------------------------------
    # Pastikan semua kolom tersedia
    # --------------------------------------------------

    for kolom in KOLOM_LENGKAP:

        if kolom not in df.columns:

            df[kolom] = None


    df = df[
        KOLOM_LENGKAP
    ]


    # --------------------------------------------------
    # Simpan posisi baris Google Sheets
    # --------------------------------------------------

    df["_excel_row"] = (
        df.index
        + baris_header
        + 2
    )

    df["_sheet"] = bulan


    # --------------------------------------------------
    # Hapus baris kosong
    # --------------------------------------------------

    kolom_cek = [
        "Kategori",
        "Barang",
        "Harga",
        "Jumlah",
        "Subtotal",
    ]

    df = df[
        df[kolom_cek]
        .notna()
        .any(axis=1)
    ].copy()


    if df.empty:
        return None


    # --------------------------------------------------
    # Isi tanggal ke bawah
    # --------------------------------------------------

    df["Tanggal"] = (
        df["Tanggal"]
        .ffill()
    )


    df = df[
        df[kolom_cek]
        .notna()
        .any(axis=1)
    ].copy()


    if df.empty:
        return None


    # --------------------------------------------------
    # Tambah bulan dan tahun
    # --------------------------------------------------

    df["Bulan"] = bulan
    df["Tahun"] = tahun


    return df


# ==================================================
# LOAD DATA
# ==================================================

@st.cache_data(ttl=60)
def load_data():

    client = get_client()

    sh = client.open_by_key(
        SPREADSHEET_ID
    )

    semua = []
    gagal = []


    # ==================================================
    # AMBIL TAHUN DARI NAMA SPREADSHEET
    # ==================================================

    tahun_match = re.search(
        r"(20\d{2})",
        sh.title,
    )

    tahun = (
        int(tahun_match.group(1))
        if tahun_match
        else None
    )


    # ==================================================
    # BACA 12 SHEET SEKALIGUS
    # ==================================================

    ranges = [
        f"{bulan}!A:Z"
        for bulan in BULAN
    ]


    try:

        response = sh.values_batch_get(
            ranges,
            params={
                "valueRenderOption": "UNFORMATTED_VALUE"
            },
        )

    except Exception as e:

        return (
            pd.DataFrame(),
            [
                f"Gagal membaca Google Sheets: {e}"
            ],
        )


    # ==================================================
    # PROSES HASIL BATCH
    # ==================================================

    value_ranges = response.get(
        "valueRanges",
        [],
    )


    for bulan, result in zip(
        BULAN,
        value_ranges,
    ):

        try:

            raw = result.get(
                "values",
                [],
            )


            df = proses_sheet(
                raw,
                bulan,
                tahun,
            )


            if df is not None:
                semua.append(df)

            else:

                # Jangan dianggap error kalau
                # sheet memang kosong.
                continue


        except Exception as e:

            gagal.append(
                f"{bulan} gagal dibaca: {e}"
            )


    # ==================================================
    # JIKA TIDAK ADA DATA
    # ==================================================

    if len(semua) == 0:

        return (
            pd.DataFrame(),
            gagal,
        )


    # ==================================================
    # GABUNG SEMUA BULAN
    # ==================================================

    hasil = pd.concat(
        semua,
        ignore_index=True,
    )


    # ==================================================
    # KONVERSI ANGKA
    # ==================================================

    hasil["Harga"] = pd.to_numeric(
        hasil["Harga"],
        errors="coerce",
    )

    hasil["Jumlah"] = pd.to_numeric(
        hasil["Jumlah"],
        errors="coerce",
    )

    hasil["Subtotal"] = pd.to_numeric(
        hasil["Subtotal"],
        errors="coerce",
    )

    hasil["Diskon"] = pd.to_numeric(
        hasil["Diskon"],
        errors="coerce",
    )


    # ==================================================
    # BERSIHKAN TEXT
    # ==================================================

    hasil["Kategori"] = (
        hasil["Kategori"]
        .astype(str)
        .str.strip()
        .str.title()
    )

    hasil["Barang"] = (
        hasil["Barang"]
        .astype(str)
        .str.strip()
    )

    hasil["Tanggal"] = (
        hasil["Tanggal"]
        .astype(str)
        .str.strip()
    )


    hasil["Kategori"] = (
        hasil["Kategori"]
        .replace("Nan", "")
    )

    hasil["Barang"] = (
        hasil["Barang"]
        .replace("nan", "")
    )


    # ==================================================
    # HAPUS BARIS TOTAL
    # ==================================================

    hasil = hasil[
        ~hasil.apply(
            lambda row:
                row.astype(str)
                .str.upper()
                .str.contains("TOTAL")
                .any(),
            axis=1,
        )
    ].reset_index(drop=True)


    # ==================================================
    # URUTAN KOLOM
    # ==================================================

    hasil = hasil[
        [
            "Tahun",
            "Bulan",
            "Tanggal",
            "Kategori",
            "Barang",
            "Harga",
            "Jumlah",
            "Subtotal",
            "Diskon",
            "_sheet",
            "_excel_row",
        ]
    ]


    return hasil, gagal


# ==================================================
# TAMBAH BARIS
# ==================================================

def tambah_baris(
    bulan,
    tanggal,
    kategori,
    barang,
    harga,
    jumlah,
    subtotal,
):

    client = get_client()

    ws = (
        client
        .open_by_key(SPREADSHEET_ID)
        .worksheet(bulan)
    )


    # Hitung diskon
    diskon = max(
        (harga * jumlah) - subtotal,
        0,
    )


    ws.append_row(
        [
            tanggal,
            kategori,
            barang,
            harga,
            jumlah,
            subtotal,
            diskon,
        ]
    )


# ==================================================
# HAPUS BARIS
# ==================================================


def hapus_baris(daftar_hapus):

    if not daftar_hapus:
        return 0

    client = get_client()

    sh = client.open_by_key(
        SPREADSHEET_ID
    )

    # Kelompokkan baris berdasarkan nama sheet
    per_sheet = {}

    for item in daftar_hapus:

        sheet_name = str(
            item.get("_sheet", "")
        ).strip()

        row_number = item.get("_excel_row")

        if not sheet_name:
            raise ValueError(
                "Nama sheet (_sheet) tidak ditemukan."
            )

        if row_number in (None, ""):
            raise ValueError(
                "Nomor baris (_excel_row) tidak ditemukan."
            )

        row_number = int(float(row_number))

        if row_number < 1:
            raise ValueError(
                f"Nomor baris tidak valid: {row_number}"
            )

        per_sheet.setdefault(
            sheet_name,
            []
        ).append(row_number)

    total_dihapus = 0

    # Proses setiap sheet
    for sheet_name, rows in per_sheet.items():

        ws = sh.worksheet(sheet_name)

        # Hilangkan duplikat dan urutkan dari bawah
        # supaya nomor baris tidak berubah sebelum
        # baris berikutnya dihapus.
        rows = sorted(
            set(rows),
            reverse=True
        )

        requests = []

        for row_number in rows:

            requests.append({
                "deleteDimension": {
                    "range": {
                        "sheetId": ws.id,
                        "dimension": "ROWS",
                        "startIndex": row_number - 1,
                        "endIndex": row_number
                    }
                }
            })

        if requests:

            sh.batch_update({
                "requests": requests
            })

            total_dihapus += len(requests)

    return total_dihapus

# ==================================================
# UPDATE / SIMPAN EDIT
# ==================================================

def update_baris(
    data_edit,
):

    client = get_client()

    sh = client.open_by_key(
        SPREADSHEET_ID
    )


    # ==================================================
    # KELOMPOKKAN BERDASARKAN SHEET
    # ==================================================

    per_sheet = {}

    for row in data_edit:

        sheet_name = row["_sheet"]

        per_sheet.setdefault(
            sheet_name,
            [],
        ).append(row)


    # ==================================================
    # UPDATE SETIAP SHEET
    # ==================================================

    for sheet_name, rows in per_sheet.items():

        ws = sh.worksheet(
            sheet_name
        )


        for row in rows:

            excel_row = int(
                row["_excel_row"]
            )


            # --------------------------------------------------
            # TANGGAL
            # --------------------------------------------------

            tanggal = str(
                row.get(
                    "Tanggal",
                    "",
                )
            ).strip()


            # --------------------------------------------------
            # KATEGORI
            # --------------------------------------------------

            kategori = row.get(
                "Kategori",
                "",
            )


            # --------------------------------------------------
            # BARANG
            # --------------------------------------------------

            barang = row.get(
                "Barang",
                "",
            )


            # --------------------------------------------------
            # HARGA
            # --------------------------------------------------

            try:

                harga = float(
                    str(
                        row.get(
                            "Harga",
                            "0",
                        )
                    )
                    .replace(
                        ".",
                        "",
                    )
                    .replace(
                        ",",
                        "",
                    )
                    .strip()
                )

            except (
                ValueError,
                TypeError,
            ):

                harga = 0


            # --------------------------------------------------
            # JUMLAH
            # --------------------------------------------------

            try:

                jumlah = float(
                    str(
                        row.get(
                            "Jumlah",
                            "1",
                        )
                    )
                    .replace(
                        ",",
                        ".",
                    )
                    .strip()
                )

            except (
                ValueError,
                TypeError,
            ):

                jumlah = 1


            # --------------------------------------------------
            # SUBTOTAL
            # --------------------------------------------------

            try:

                subtotal = float(
                    str(
                        row.get(
                            "Subtotal",
                            "0",
                        )
                    )
                    .replace(
                        ".",
                        "",
                    )
                    .replace(
                        ",",
                        "",
                    )
                    .strip()
                )

            except (
                ValueError,
                TypeError,
            ):

                subtotal = 0


            # --------------------------------------------------
            # HITUNG DISKON
            # --------------------------------------------------

            diskon = max(
                (harga * jumlah) - subtotal,
                0,
            )


            # --------------------------------------------------
            # UPDATE A:G
            # --------------------------------------------------

            ws.update(
                f"A{excel_row}:G{excel_row}",
                [[
                    tanggal,
                    kategori,
                    barang,
                    harga,
                    jumlah,
                    subtotal,
                    diskon,
                ]],
            )