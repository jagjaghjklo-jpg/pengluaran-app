import pandas as pd

def rupiah(x):
    if pd.isna(x):
        return ""

    try:
        return f"{int(float(x)):,}".replace(",", ".")
    except:
        return str(x)
