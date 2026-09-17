import pandas as pd

excel = pd.ExcelFile("data/pengeluaran_2026.xlsx")

print(excel.sheet_names)
