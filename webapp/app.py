import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

st.set_page_config(page_title="Stock ML", layout="wide")
pages = [
    st.Page("backtest_page.py", title="Backtest", icon=":material/show_chart:", default=True),
    st.Page("paper_page.py", title="Paper trading", icon=":material/account_balance:"),
]
st.navigation(pages).run()
