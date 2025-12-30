import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO

# ========================= CONFIG =========================
st.set_page_config(
    page_title="CDOE Feedback Analytics Dashboard",
    layout="wide"
)

# ========================= HELPERS =========================
def to_excel(sheet_dict):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, df in sheet_dict.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)
    return output.getvalue()

def safe_num(s):
    return pd.to_numeric(s, errors="coerce")

# ========================= TITLE =========================
st.title("📊 CDOE Feedback Analytics Dashboard")
st.caption("Distance | DTL | Online — Management, IQAC & NAAC Ready")

# ========================= UPLOAD =========================
files = st.file_uploader(
    "Upload ALL Feedback Files (CSV / Excel)",
    type=["csv", "xlsx"],
    accept_multiple_files=True
)

if not files:
    st.stop()

# ========================= LOAD DATA =========================
dfs = []
for f in files:
    if f.name.endswith(".csv"):
        df = pd.read_csv(f)
    else:
        df = pd.read_excel(f)

    df.columns = df.columns.astype(str).str.strip().str.lower()
    df["source_file"] = f.name
    dfs.append(df)

data = pd.concat(dfs, ignore_index=True)

# ========================= SIDEBAR FILTERS =========================
st.sidebar.header("🔍 Filters")

# Mode (derived from filename)
def detect_mode(x):
    x = x.lower()
    if "distance" in x:
        return "Distance"
    if "dtl" in x:
        return "DTL"
    if "online" in x:
        return "Online"
    return "Unknown"

data["mode"] = data["source_file"].apply(detect_mode)

modes = st.sidebar.multiselect(
    "Mode",
    sorted(data["mode"].unique()),
    default=sorted(data["mode"].unique())
)

filtered = data[data["mode"].isin(modes)]

files_sel = st.sidebar.multiselect(
    "Programme / File",
    sorted(filtered["source_file"].unique()),
    default=sorted(filtered["source_file"].unique())
)

filtered = filtered[filtered["source_file"].isin(files_sel)]

# ========================= TABS =========================
tabs = st.tabs([
    "Overview",
    "Delivery of Lecture",
    "Learner Support Centre (Distance)",
    "Master Dashboard",
    "Subject-wise Detailed Comparison"
])

# ========================================================
# TAB 1 — OVERVIEW
# ========================================================
with tabs[0]:
    st.subheader("Overview")

    rating_cols = [c for c in filtered.columns if "rate" in c or "rating" in c]

    overall_avg = (
        filtered[rating_cols]
        .apply(safe_num)
        .stack()
        .mean()
    )

    c1, c2 = st.columns(2)
    c1.metric("Total Responses", len(filtered))
    c2.metric("Overall Average Rating", round(overall_avg, 2))

# ========================================================
# TAB 2 — DELIVERY OF LECTURE
# ========================================================
with tabs[1]:
    st.subheader("Delivery of Lecture — File-wise")

    col = next((c for c in filtered.columns if "delivery of lecture" in c), None)

    if not col:
        st.error("Delivery of Lecture column not found.")
    else:
        df = (
            filtered[[col, "source_file"]]
            .assign(val=lambda x: safe_num(x[col]))
            .groupby("source_file", as_index=False)["val"]
            .mean()
            .rename(columns={"val": "Average Rating"})
        )

        st.dataframe(df)
        st.bar_chart(df.set_index("source_file"))

        st.download_button(
            "⬇️ Download Excel",
            to_excel({"Delivery of Lecture": df}),
            "delivery_of_lecture.xlsx"
        )

# ========================================================
# TAB 3 — LEARNER SUPPORT CENTRE (FIXED)
# ========================================================
with tabs[2]:
    st.subheader("Learner Support Centre — Distance Only")

    if "learner support centre" not in filtered.columns:
        st.error("Learner Support Centre column not present.")
    else:
        lsc = (
            filtered[filtered["mode"] == "Distance"]["learner support centre"]
            .dropna()
            .astype(str)
            .str.strip()
        )

        if lsc.empty:
            st.warning("Learner Support Centre values exist but are empty after filters.")
        else:
            lsc_df = lsc.value_counts().reset_index()
            lsc_df.columns = ["Learner Support Centre", "Responses"]

            st.dataframe(lsc_df)
            st.bar_chart(lsc_df.set_index("Learner Support Centre"))

            st.download_button(
                "⬇️ Download Excel",
                to_excel({"Learner Support Centre": lsc_df}),
                "learner_support_centre.xlsx"
            )

# ========================================================
# TAB 4 — MASTER DASHBOARD (NO NONE VALUES)
# ========================================================
with tabs[3]:
    st.subheader("Master Feedback Dashboard")

    params = []
    for c in filtered.columns:
        if any(k in c for k in [
            "ease", "admission", "support", "syllabus",
            "curriculum", "self-learning", "quality"
        ]):
            num = safe_num(filtered[c])
            if num.notna().sum() > 0:
                params.append({
                    "Parameter": c,
                    "Average Rating": round(num.mean(), 2)
                })

    master = pd.DataFrame(params)

    st.dataframe(master)

    st.download_button(
        "⬇️ Download Excel",
        to_excel({"Master Dashboard": master}),
        "master_dashboard.xlsx"
    )

# ========================================================
# TAB 5 — SUBJECT-WISE (REAL FIX)
# ========================================================
with tabs[4]:
    st.subheader("Subject-wise Detailed Comparison (Delivery of Lecture)")

    section = next((c for c in filtered.columns if "delivery of lecture" in c), None)

    if not section:
        st.error("Delivery of Lecture section not found.")
        st.stop()

    start_idx = filtered.columns.get_loc(section) + 1
    tail = filtered.columns[start_idx:]

    subject_cols = []
    for c in tail:
        if safe_num(filtered[c]).notna().sum() > 0:
            subject_cols.append(c)
        else:
            break

    if not subject_cols:
        st.error("Subject numeric columns not detected.")
        st.stop()

    rows = []
    for c in subject_cols:
        name = (
            filtered[c]
            .dropna()
            .astype(str)
            .iloc[0]
        )
        avg = safe_num(filtered[c]).mean()
        rows.append({
            "Subject": name,
            "Average Rating": round(avg, 2)
        })

    subj_df = pd.DataFrame(rows)

    st.dataframe(subj_df)
    st.bar_chart(subj_df.set_index("Subject"))

    st.download_button(
        "⬇️ Download Excel",
        to_excel({"Subject-wise Comparison": subj_df}),
        "subject_wise_comparison.xlsx"
    )
