import streamlit as st
import pandas as pd
import plotly.express as px
from auto_fetch_future_data import *
from datetime import datetime

# Set page config
st.set_page_config(
    page_title="Options Data Visualizer",
    page_icon="📈",
    layout="wide"
)

# Title
st.title("科创50/创业板合成期货套利残差监控")
st.write("Interactive visualization of data with C-P+K-S calculation")

# Hardcoded credentials for testing (remove in production)
THS_USERNAME = "glzqgf076"  # Replace with actual username for testing
THS_PASSWORD = "SkTbcgR7"  # Replace with actual password for testing

# Sidebar for THS login credentials (hidden for now, using hardcoded values)
st.sidebar.header("同花顺登录")
ths_username = st.sidebar.text_input("同花顺账号", value=THS_USERNAME)
ths_password = st.sidebar.text_input("同花顺密码", type="password", value=THS_PASSWORD)
# ths_username = THS_USERNAME
# ths_password = THS_PASSWORD

# Strike prices input
strike_prices_input = st.sidebar.text_input(
    "行权价 (用逗号分隔，例如: 1850,1900,1950)",
    value="1850,1900,1950"
)

# Convert input to list of integers
try:
    strike_prices = [int(x.strip()) for x in strike_prices_input.split(',') if x.strip().isdigit()]
except:
    st.sidebar.error("请输入有效的行权价，例如: 1850,1900,1950")
    strike_prices = [1850, 1900, 1950]  # Default values

# Function to fetch data
@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_data(etf_name, maturity_month, username=None, password=None):
    # Login to THS if credentials are provided
    if username and password:
        try:
            THS_iFinDLogout()
            login_result = THS_iFinDLogin(username, password)
            if login_result != 0:
                st.error("同花顺登录失败，请检查账号密码")
                return pd.DataFrame()
        except Exception as e:
            st.error(f"登录出错: {e}")
            return pd.DataFrame()
    
    all_data = []
    
    for strike in strike_prices:
        try:
            df = download_future_data(
                ETFName=etf_name,
                strikePrice=strike,
                maturityMonth=maturity_month,
                csvOutput=False
            )
            if df is not None and not df.empty:
                df['display_name'] = f"{etf_name}_{maturity_month}_{strike}"
                all_data.append(df)
        except Exception as e:
            st.error(f"Error fetching data for strike {strike}: {e}")
    
    if not all_data:
        return pd.DataFrame()
    
    return pd.concat(all_data, ignore_index=True)

# Sidebar for controls
st.sidebar.header("Controls")

# ETF selection
etf_options = ['科创50', '科创板50', '创业板ETF']
etf_name = st.sidebar.selectbox(
    "选择ETF",
    etf_options,
    index=2  # Default to 创业板ETF
)

# Maturity month input
maturity_month = st.sidebar.number_input(
    "到期月份 (1-12)",
    min_value=1,
    max_value=12,
    value=6,  # Default to June
    step=1
)

# Function to generate a unique key for caching based on current parameters
def get_cache_key(etf_name, maturity_month, strike_prices):
    return f"{etf_name}_{maturity_month}_{'_'.join(map(str, sorted(strike_prices)))}"

# Add a button to fetch data
if st.sidebar.button("获取数据", type="primary"):
    with st.spinner('正在获取数据，请稍候...'):
        # Clear previous data
        st.session_state.df = pd.DataFrame()
        st.session_state.display_names = []
        st.session_state.selected_files = []
        
        # Fetch new data
        df = fetch_data(
            etf_name=etf_name, 
            maturity_month=maturity_month,
            username=ths_username,
            password=ths_password
        )
        
        if df is not None and not df.empty:
            # Store the data in session state
            st.session_state.df = df
            st.session_state.display_names = df['display_name'].unique().tolist()
            st.session_state.selected_files = st.session_state.display_names.copy()
        else:
            st.error("未能获取数据，请检查参数或稍后重试。")
            st.stop()

# Initialize session state if not exists
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()
if 'display_names' not in st.session_state:
    st.session_state.display_names = []
if 'selected_files' not in st.session_state:
    st.session_state.selected_files = []

# Initialize session state if not exists
if 'df' not in st.session_state:
    st.session_state.df = pd.DataFrame()
if 'display_names' not in st.session_state:
    st.session_state.display_names = []
if 'selected_files' not in st.session_state:
    st.session_state.selected_files = []

# Display file selection checkboxes
st.sidebar.subheader("选择显示的行权价")
for name in st.session_state.display_names:
    if st.sidebar.checkbox(
        name, 
        value=name in st.session_state.selected_files,
        key=f"file_{name}",
        on_change=lambda n=name: st.session_state.selected_files.append(n) 
                                if n not in st.session_state.selected_files 
                                else st.session_state.selected_files.remove(n)
    ):
        pass

# Filter data based on selection
filtered_df = st.session_state.df[st.session_state.df['display_name'].isin(st.session_state.selected_files)]

# Main plot
st.header(f"{etf_name} - C-P+K-S (到期月: {maturity_month}月)")

if filtered_df.empty:
    st.warning("没有可显示的数据。请点击'获取数据'按钮获取数据。")
else:
    # Create the plot
    fig = px.line(
        filtered_df, 
        x='time', 
        y='C-P+K-S', 
        color='display_name',
        labels={
            'time': '日期',
            'C-P+K-S': 'C - P + K - S',
            'display_name': '行权价'
        },
        title=f'{etf_name} 期权 C - P + K - S 值 (到期月: {maturity_month}月)',
        template='plotly_white'
    )
    
    # Customize the plot
    fig.update_layout(
        hovermode='x unified',
        xaxis_title='日期',
        yaxis_title='C - P + K - S 值',
        legend_title='行权价',
        height=600
    )
    
    # Show the plot
    st.plotly_chart(fig, use_container_width=True)

# Display raw data if needed
if st.sidebar.checkbox("显示原始数据"):
    st.subheader("原始数据")
    st.dataframe(filtered_df.sort_values(['time', 'display_name']), use_container_width=True)

# Add some instructions
with st.expander("ℹ️ 使用说明"):
    st.markdown("""
    1. 有时候更改了参数之后会没有重新拉取数据的响应，此时可以考虑刷新页面重新开始
    2. 使用左边栏中的选项，点击获取数据，稍等片刻即可自动生成
    2. 在图片上悬停鼠标，可看到数据细节
    3. 使用图片右上角工具栏可以：
       - 放大缩小
       - 下载png
       - 及其他功能
    4. 勾选左边栏原始数据，即可获取数据，数据内还包括合约未平仓量等数据。
    """)
