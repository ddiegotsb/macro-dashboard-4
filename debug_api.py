import requests
import json
import os
import sys

API_BASE = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"
USER = sys.argv[1]
PASS = sys.argv[2]

def fetch_raw(series_id, first="2025-01-01", last="2026-05-27"):
    url = (f"{API_BASE}?user={USER}&pass={PASS}"
           f"&firstdate={first}&lastdate={last}"
           f"&timeseries={series_id}&function=GetSeries")
    r = requests.get(url, timeout=30)
    data = r.json()
    print(f"\n=== {series_id} ===")
    print(json.dumps(data, indent=2, ensure_ascii=False)[:800])

# Probar variantes de TPM
for code in [
    "F022.BCO.TAB.D",
    "F022.BCO.TAB.M",
    "F022.BCO.TAB.D.D",
    "F022.BCO.TAB",
    "F074.IPC.VAR.Z.M",
    "F074.IPC.VAR.Z.M.Z.Z.6",
    "F032.IMC.IND.Z.M.Z.Z.BAS2018",
    "F032.IMC.IND.Z.M",
]:
    fetch_raw(code)
