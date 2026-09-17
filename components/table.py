import streamlit as st
from utils.format import rupiah


def render_table(df):

    with open("assets/style.css") as f:
        css = f.read()

    kolom_kanan = {
        "Harga",
        "Subtotal",
        "Diskon"
    }

    kolom_tengah = {
        "Tanggal",
        "Jumlah"
    }

    editable = {
        "Tanggal",
        "Kategori",
        "Barang",
        "Harga",
        "Jumlah",
        "Subtotal"
    }

    html = f"""
    <style>
        {css}

        .edit-table {{
            width: 100%;
            border-collapse: collapse;
        }}

        .edit-table input {{
            width: 100%;
            box-sizing: border-box;
            background: transparent;
            color: white;
            border: none;
            outline: none;
            font-size: 15px;
        }}

        .edit-table input:focus {{
            background: #26364a;
        }}

        .save-button {{
            margin-top: 10px;
        }}
    </style>

    <table class="custom-table edit-table">
        <thead>
            <tr>
    """

    for kolom in df.columns:
        html += f"<th>{kolom}</th>"

    html += """
            </tr>
        </thead>
        <tbody>
    """

    tanggal_sebelumnya = None
    bulan_sebelumnya = None

    for index, row in df.iterrows():

        tanggal = str(row.get("Tanggal", "")).strip()

        if (
            tanggal_sebelumnya is not None
            and tanggal != tanggal_sebelumnya
        ):
            html += f"""
            <tr class="tanggal-divider">
                <td colspan="{len(df.columns)}"></td>
            </tr>
            """

        html += "<tr>"

        for kolom in df.columns:

            nilai = row[kolom]

            if kolom == "Bulan":

                if nilai == bulan_sebelumnya:
                    nilai = ""
                else:
                    bulan_sebelumnya = nilai

            if str(nilai) == "nan" or str(nilai) == "None":
                nilai = ""

            if kolom in kolom_kanan:

                if nilai != "":
                    nilai_tampil = rupiah(nilai)
                else:
                    nilai_tampil = ""

                align = "right"

            elif kolom in kolom_tengah:

                nilai_tampil = nilai
                align = "center"

            else:

                nilai_tampil = nilai
                align = "left"

            if kolom in editable:

                html += f"""
                <td class="{align}">
                    <input
                        type="text"
                        value="{nilai_tampil}"
                        data-row="{index}"
                        data-column="{kolom}">
                </td>
                """

            else:

                html += f"""
                <td class="{align}">
                    {nilai_tampil}
                </td>
                """

        html += "</tr>"

        tanggal_sebelumnya = tanggal

    html += """
        </tbody>
    </table>
    """

    return html