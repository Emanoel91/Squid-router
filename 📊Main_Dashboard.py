import streamlit as st
import pandas as pd
import snowflake.connector
import plotly.graph_objects as go
import plotly.express as px
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

# --- Page Config ------------------------------------------------------------------------------------------------------
st.set_page_config(
    page_title="Squid router",
    page_icon="https://img.cryptorank.io/coins/squid1675241862798.png",
    layout="wide"
)

# --- Title with Logo -----------------------------------------------------------------------------------------------------
st.markdown(
    """
    <div style="display: flex; align-items: center; gap: 15px;">
        <img src="https://img.cryptorank.io/coins/squid1675241862798.png" alt="Squid Logo" style="width:60px; height:60px;">
        <h1 style="margin: 0;">Squid router</h1>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Builder Info ---------------------------------------------------------------------------------------------------------
st.markdown(
    """
    <div style="margin-top: 20px; margin-bottom: 20px; font-size: 16px;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="https://pbs.twimg.com/profile_images/1841479747332608000/bindDGZQ_400x400.jpg" style="width:25px; height:25px; border-radius: 50%;">
            <span>Built by: <a href="https://x.com/0xeman_raz" target="_blank">Eman Raz</a></span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div style="background-color:#e4d902; padding:1px; border-radius:10px;">
        <h2 style="color:#000000; text-align:center; font-family: 'Britannic Bold', sans-serif;">
            Squid | Make anything cross-chain
        </h2>
    </div>
    """,
    unsafe_allow_html=True
)
# ----------------------------------------------------------------------------------------------------------------------------------
st.info("📊Charts initially display data for a default time range. Select a custom range to view results for your desired period.")
st.info("⏳On-chain data retrieval may take a few moments. Please wait while the results load.")

# --- Snowflake Connection ----------------------------------------------------------------------------------------
snowflake_secrets = st.secrets["snowflake"]
user = snowflake_secrets["user"]
account = snowflake_secrets["account"]
private_key_str = snowflake_secrets["private_key"]
warehouse = snowflake_secrets.get("warehouse", "")
database = snowflake_secrets.get("database", "")
schema = snowflake_secrets.get("schema", "")

private_key_pem = f"-----BEGIN PRIVATE KEY-----\n{private_key_str}\n-----END PRIVATE KEY-----".encode("utf-8")
private_key = serialization.load_pem_private_key(
    private_key_pem,
    password=None,
    backend=default_backend()
)
private_key_bytes = private_key.private_bytes(
    encoding=serialization.Encoding.DER,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)

conn = snowflake.connector.connect(
    user=user,
    account=account,
    private_key=private_key_bytes,
    warehouse=warehouse,
    database=database,
    schema=schema
)

# --- Date Inputs ---------------------------------------------------------------------------------------------------
col1, col2, col3 = st.columns(3)

with col1:
    timeframe = st.selectbox("Select Time Frame", ["month", "week", "day"])

with col2:
    start_date = st.date_input("Start Date", value=pd.to_datetime("2023-01-01"))

with col3:
    end_date = st.date_input("End Date", value=pd.to_datetime("2025-09-30"))
# --- Query Function: Row 1, 2 --------------------------------------------------------------------------------------
@st.cache_data
def load_kpi_data(timeframe, start_date, end_date):
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    query = f"""
    WITH axelar_service AS (
        -- Token Transfers
        SELECT 
            created_at, 
            LOWER(data:send:original_source_chain) AS source_chain, 
            LOWER(data:send:original_destination_chain) AS destination_chain,
            recipient_address AS user, 
            CASE 
              WHEN IS_ARRAY(data:send:amount) THEN NULL
              WHEN IS_OBJECT(data:send:amount) THEN NULL
              WHEN TRY_TO_DOUBLE(data:send:amount::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:send:amount::STRING)
              ELSE NULL
            END AS amount,
            CASE 
              WHEN IS_ARRAY(data:send:amount) OR IS_ARRAY(data:link:price) THEN NULL
              WHEN IS_OBJECT(data:send:amount) OR IS_OBJECT(data:link:price) THEN NULL
              WHEN TRY_TO_DOUBLE(data:send:amount::STRING) IS NOT NULL AND TRY_TO_DOUBLE(data:link:price::STRING) IS NOT NULL 
                THEN TRY_TO_DOUBLE(data:send:amount::STRING) * TRY_TO_DOUBLE(data:link:price::STRING)
              ELSE NULL
            END AS amount_usd,
            CASE 
              WHEN IS_ARRAY(data:send:fee_value) THEN NULL
              WHEN IS_OBJECT(data:send:fee_value) THEN NULL
              WHEN TRY_TO_DOUBLE(data:send:fee_value::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:send:fee_value::STRING)
              ELSE NULL
            END AS fee,
            id, 
            'Token Transfers' AS Service, 
            data:link:asset::STRING AS raw_asset
        FROM axelar.axelscan.fact_transfers
        WHERE status = 'executed'
          AND simplified_status = 'received'
          AND (
            sender_address ilike '%0xce16F69375520ab01377ce7B88f5BA8C48F8D666%' 
            OR sender_address ilike '%0x492751eC3c57141deb205eC2da8bFcb410738630%'
            OR sender_address ilike '%0xDC3D8e1Abe590BCa428a8a2FC4CfDbD1AcF57Bd9%'
            OR sender_address ilike '%0xdf4fFDa22270c12d0b5b3788F1669D709476111E%'
            OR sender_address ilike '%0xe6B3949F9bBF168f4E3EFc82bc8FD849868CC6d8%'
          )

        UNION ALL

        -- GMP
        SELECT  
            created_at,
            data:call.chain::STRING AS source_chain,
            data:call.returnValues.destinationChain::STRING AS destination_chain,
            data:call.transaction.from::STRING AS user,
            CASE 
              WHEN IS_ARRAY(data:amount) OR IS_OBJECT(data:amount) THEN NULL
              WHEN TRY_TO_DOUBLE(data:amount::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:amount::STRING)
              ELSE NULL
            END AS amount,
            CASE 
              WHEN IS_ARRAY(data:value) OR IS_OBJECT(data:value) THEN NULL
              WHEN TRY_TO_DOUBLE(data:value::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:value::STRING)
              ELSE NULL
            END AS amount_usd,
            COALESCE(
              CASE 
                WHEN IS_ARRAY(data:gas:gas_used_amount) OR IS_OBJECT(data:gas:gas_used_amount) 
                  OR IS_ARRAY(data:gas_price_rate:source_token.token_price.usd) OR IS_OBJECT(data:gas_price_rate:source_token.token_price.usd) 
                THEN NULL
                WHEN TRY_TO_DOUBLE(data:gas:gas_used_amount::STRING) IS NOT NULL 
                  AND TRY_TO_DOUBLE(data:gas_price_rate:source_token.token_price.usd::STRING) IS NOT NULL 
                THEN TRY_TO_DOUBLE(data:gas:gas_used_amount::STRING) * TRY_TO_DOUBLE(data:gas_price_rate:source_token.token_price.usd::STRING)
                ELSE NULL
              END,
              CASE 
                WHEN IS_ARRAY(data:fees:express_fee_usd) OR IS_OBJECT(data:fees:express_fee_usd) THEN NULL
                WHEN TRY_TO_DOUBLE(data:fees:express_fee_usd::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:fees:express_fee_usd::STRING)
                ELSE NULL
              END
            ) AS fee,
            id, 
            'GMP' AS Service, 
            data:symbol::STRING AS raw_asset
        FROM axelar.axelscan.fact_gmp 
        WHERE status = 'executed'
          AND simplified_status = 'received'
          AND (
            data:approved:returnValues:contractAddress ilike '%0xce16F69375520ab01377ce7B88f5BA8C48F8D666%' 
            OR data:approved:returnValues:contractAddress ilike '%0x492751eC3c57141deb205eC2da8bFcb410738630%'
            OR data:approved:returnValues:contractAddress ilike '%0xDC3D8e1Abe590BCa428a8a2FC4CfDbD1AcF57Bd9%'
            OR data:approved:returnValues:contractAddress ilike '%0xdf4fFDa22270c12d0b5b3788F1669D709476111E%'
            OR data:approved:returnValues:contractAddress ilike '%0xe6B3949F9bBF168f4E3EFc82bc8FD849868CC6d8%'
          )
    )
    SELECT 
        COUNT(DISTINCT id) AS NUMBER_OF_SWAPS, 
        COUNT(DISTINCT user) AS NUMBER_OF_SWAPPERS, 
        ROUND(SUM(amount_usd)) AS VOLUME_OF_SWAPS,
        round(count(distinct id)/count(distinct created_at::date)) as AVG_DAILY_SWAPS,
        round(count(distinct user)/count(distinct created_at::date)) as AVG_DAILY_SWAPPERS,
        round(sum(amount_usd)/count(distinct created_at::date)) as AVG_DAILY_SWAP_VOLUME
    FROM axelar_service
    WHERE created_at::date >= '{start_str}' 
      AND created_at::date <= '{end_str}'
    """

    df = pd.read_sql(query, conn)
    return df

# --- Load Data ----------------------------------------------------------------------------------------------------
df_kpi = load_kpi_data(timeframe, start_date, end_date)

# --- KPI Row ------------------------------------------------------------------------------------------------------
card_style = """
    <div style="
        background-color: #f9f9f9;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
        ">
        <h4 style="margin: 0; font-size: 20px; color: #555;">{label}</h4>
        <p style="margin: 5px 0 0; font-size: 20px; font-weight: bold; color: #000;">{value}</p>
    </div>
"""

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(card_style.format(label="💸Volume of Swaps", value=f"${df_kpi['VOLUME_OF_SWAPS'][0]:,}"), unsafe_allow_html=True)
with col2:
    st.markdown(card_style.format(label="🔄Number of Swaps", value=f"{df_kpi['NUMBER_OF_SWAPS'][0]:,} Swaps"), unsafe_allow_html=True)
with col3:
    st.markdown(card_style.format(label="👥Number of Swappers", value=f"{df_kpi['NUMBER_OF_SWAPPERS'][0]:,} Wallets"), unsafe_allow_html=True)

col4, col5, col6 = st.columns(3)
with col4:
    st.markdown(card_style.format(label="📊Avg Daily Swap Volume", value=f"${df_kpi['AVG_DAILY_SWAP_VOLUME'][0]:,}"), unsafe_allow_html=True)
with col5:
    st.markdown(card_style.format(label="🔁Avg Daily Swaps", value=f"{df_kpi['AVG_DAILY_SWAPS'][0]:,} Swaps"), unsafe_allow_html=True)
with col6:
    st.markdown(card_style.format(label="👨‍💻Avg Daily Swappers", value=f"{df_kpi['AVG_DAILY_SWAPPERS'][0]:,} Wallets"), unsafe_allow_html=True)

# --- Row 3 ----------------------------------------------------------------------------------------------------------------------------------------------------
@st.cache_data
def load_time_series_data(timeframe, start_date, end_date):
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    query = f"""
    WITH axelar_service AS (
        -- Token Transfers
        SELECT 
            created_at, 
            LOWER(data:send:original_source_chain) AS source_chain, 
            LOWER(data:send:original_destination_chain) AS destination_chain,
            recipient_address AS user, 
            CASE 
              WHEN IS_ARRAY(data:send:amount) THEN NULL
              WHEN IS_OBJECT(data:send:amount) THEN NULL
              WHEN TRY_TO_DOUBLE(data:send:amount::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:send:amount::STRING)
              ELSE NULL
            END AS amount,
            CASE 
              WHEN IS_ARRAY(data:send:amount) OR IS_ARRAY(data:link:price) THEN NULL
              WHEN IS_OBJECT(data:send:amount) OR IS_OBJECT(data:link:price) THEN NULL
              WHEN TRY_TO_DOUBLE(data:send:amount::STRING) IS NOT NULL AND TRY_TO_DOUBLE(data:link:price::STRING) IS NOT NULL 
                THEN TRY_TO_DOUBLE(data:send:amount::STRING) * TRY_TO_DOUBLE(data:link:price::STRING)
              ELSE NULL
            END AS amount_usd,
            CASE 
              WHEN IS_ARRAY(data:send:fee_value) THEN NULL
              WHEN IS_OBJECT(data:send:fee_value) THEN NULL
              WHEN TRY_TO_DOUBLE(data:send:fee_value::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:send:fee_value::STRING)
              ELSE NULL
            END AS fee,
            id, 
            'Token Transfers' AS Service, 
            data:link:asset::STRING AS raw_asset
        FROM axelar.axelscan.fact_transfers
        WHERE status = 'executed'
          AND simplified_status = 'received'
          AND (
            sender_address ilike '%0xce16F69375520ab01377ce7B88f5BA8C48F8D666%' 
            OR sender_address ilike '%0x492751eC3c57141deb205eC2da8bFcb410738630%'
            OR sender_address ilike '%0xDC3D8e1Abe590BCa428a8a2FC4CfDbD1AcF57Bd9%'
            OR sender_address ilike '%0xdf4fFDa22270c12d0b5b3788F1669D709476111E%'
            OR sender_address ilike '%0xe6B3949F9bBF168f4E3EFc82bc8FD849868CC6d8%'
          )

        UNION ALL

        -- GMP
        SELECT  
            created_at,
            data:call.chain::STRING AS source_chain,
            data:call.returnValues.destinationChain::STRING AS destination_chain,
            data:call.transaction.from::STRING AS user,
            CASE 
              WHEN IS_ARRAY(data:amount) OR IS_OBJECT(data:amount) THEN NULL
              WHEN TRY_TO_DOUBLE(data:amount::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:amount::STRING)
              ELSE NULL
            END AS amount,
            CASE 
              WHEN IS_ARRAY(data:value) OR IS_OBJECT(data:value) THEN NULL
              WHEN TRY_TO_DOUBLE(data:value::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:value::STRING)
              ELSE NULL
            END AS amount_usd,
            COALESCE(
              CASE 
                WHEN IS_ARRAY(data:gas:gas_used_amount) OR IS_OBJECT(data:gas:gas_used_amount) 
                  OR IS_ARRAY(data:gas_price_rate:source_token.token_price.usd) OR IS_OBJECT(data:gas_price_rate:source_token.token_price.usd) 
                THEN NULL
                WHEN TRY_TO_DOUBLE(data:gas:gas_used_amount::STRING) IS NOT NULL 
                  AND TRY_TO_DOUBLE(data:gas_price_rate:source_token.token_price.usd::STRING) IS NOT NULL 
                THEN TRY_TO_DOUBLE(data:gas:gas_used_amount::STRING) * TRY_TO_DOUBLE(data:gas_price_rate:source_token.token_price.usd::STRING)
                ELSE NULL
              END,
              CASE 
                WHEN IS_ARRAY(data:fees:express_fee_usd) OR IS_OBJECT(data:fees:express_fee_usd) THEN NULL
                WHEN TRY_TO_DOUBLE(data:fees:express_fee_usd::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:fees:express_fee_usd::STRING)
                ELSE NULL
              END
            ) AS fee,
            id, 
            'GMP' AS Service, 
            data:symbol::STRING AS raw_asset
        FROM axelar.axelscan.fact_gmp 
        WHERE status = 'executed'
          AND simplified_status = 'received'
          AND (
            data:approved:returnValues:contractAddress ilike '%0xce16F69375520ab01377ce7B88f5BA8C48F8D666%' 
            OR data:approved:returnValues:contractAddress ilike '%0x492751eC3c57141deb205eC2da8bFcb410738630%'
            OR data:approved:returnValues:contractAddress ilike '%0xDC3D8e1Abe590BCa428a8a2FC4CfDbD1AcF57Bd9%'
            OR data:approved:returnValues:contractAddress ilike '%0xdf4fFDa22270c12d0b5b3788F1669D709476111E%'
            OR data:approved:returnValues:contractAddress ilike '%0xe6B3949F9bBF168f4E3EFc82bc8FD849868CC6d8%'
          )
    )
    SELECT 
        DATE_TRUNC('{timeframe}', created_at) AS Date,
        COUNT(DISTINCT id) AS Swap_Count, 
        COUNT(DISTINCT user) AS Swapper_Count, 
        ROUND(SUM(amount_usd)) AS Swap_Volume,
        round((count(distinct id)/count(distinct user)),1) as Swap_Count_per_Swapper
    FROM axelar_service
    WHERE created_at::date >= '{start_str}' 
      AND created_at::date <= '{end_str}'
    GROUP BY 1
    ORDER BY 1
    """

    return pd.read_sql(query, conn)

# --- Load Data ----------------------------------------------------------------------------------------------------
df_ts = load_time_series_data(timeframe, start_date, end_date)
# --- Row 3 --------------------------------------------------------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    fig1 = go.Figure()

    fig1.add_bar(
        x=df_ts["DATE"], 
        y=df_ts["SWAP_COUNT"], 
        name="Swap Count", 
        yaxis="y1",
        marker_color="violet"
    )

    fig1.add_trace(go.Scatter(
        x=df_ts["DATE"], 
        y=df_ts["SWAP_VOLUME"], 
        name="Swap Volume", 
        mode="lines", 
        yaxis="y2",
        line=dict(color="yellow")
    ))
    fig1.update_layout(
        title="Number of Transactions & Volume Over Time",
        yaxis=dict(title="Txns count"),
        yaxis2=dict(title="$USD", overlaying="y", side="right"),
        xaxis=dict(title=" "),
        barmode="group",
        legend=dict(
            orientation="h",   
            yanchor="bottom", 
            y=1.05,           
            xanchor="center",  
            x=0.5
        )
    )
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    fig2 = go.Figure()
 
    fig2.add_bar(
        x=df_ts["DATE"], 
        y=df_ts["SWAPPER_COUNT"], 
        name="Swapper Count", 
        yaxis="y1",
        marker_color="violet"
    )
  
    fig2.add_trace(go.Scatter(
        x=df_ts["DATE"], 
        y=df_ts["SWAP_COUNT_PER_SWAPPER"], 
        name="Swap Count per Swapper", 
        mode="lines", 
        yaxis="y2",
        line=dict(color="yellow")
    ))
    fig2.update_layout(
        title="Number of Users Over Time",
        yaxis=dict(title="Wallet count"),
        yaxis2=dict(title="$USD", overlaying="y", side="right"),
        xaxis=dict(title=" "),
        barmode="group",
        legend=dict(
            orientation="h",   
            yanchor="bottom", 
            y=1.05,           
            xanchor="center",  
            x=0.5
        )
    )
    st.plotly_chart(fig2, use_container_width=True)

# --- Row 4, 5 ----------------------------------------------------------------------------------------------------------------------------------------------------
@st.cache_data
def load_time_series_data_by_path(timeframe, start_date, end_date):
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    query = f"""
    WITH axelar_service AS (
        -- Token Transfers
        SELECT 
            created_at, 
            LOWER(data:send:original_source_chain) AS source_chain, 
            LOWER(data:send:original_destination_chain) AS destination_chain,
            recipient_address AS user, 
            CASE 
              WHEN IS_ARRAY(data:send:amount) THEN NULL
              WHEN IS_OBJECT(data:send:amount) THEN NULL
              WHEN TRY_TO_DOUBLE(data:send:amount::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:send:amount::STRING)
              ELSE NULL
            END AS amount,
            CASE 
              WHEN IS_ARRAY(data:send:amount) OR IS_ARRAY(data:link:price) THEN NULL
              WHEN IS_OBJECT(data:send:amount) OR IS_OBJECT(data:link:price) THEN NULL
              WHEN TRY_TO_DOUBLE(data:send:amount::STRING) IS NOT NULL AND TRY_TO_DOUBLE(data:link:price::STRING) IS NOT NULL 
                THEN TRY_TO_DOUBLE(data:send:amount::STRING) * TRY_TO_DOUBLE(data:link:price::STRING)
              ELSE NULL
            END AS amount_usd,
            CASE 
              WHEN IS_ARRAY(data:send:fee_value) THEN NULL
              WHEN IS_OBJECT(data:send:fee_value) THEN NULL
              WHEN TRY_TO_DOUBLE(data:send:fee_value::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:send:fee_value::STRING)
              ELSE NULL
            END AS fee,
            id, 
            'Token Transfers' AS Service, 
            data:link:asset::STRING AS raw_asset
        FROM axelar.axelscan.fact_transfers
        WHERE status = 'executed'
          AND simplified_status = 'received'
          AND (
            sender_address ilike '%0xce16F69375520ab01377ce7B88f5BA8C48F8D666%' 
            OR sender_address ilike '%0x492751eC3c57141deb205eC2da8bFcb410738630%'
            OR sender_address ilike '%0xDC3D8e1Abe590BCa428a8a2FC4CfDbD1AcF57Bd9%'
            OR sender_address ilike '%0xdf4fFDa22270c12d0b5b3788F1669D709476111E%'
            OR sender_address ilike '%0xe6B3949F9bBF168f4E3EFc82bc8FD849868CC6d8%'
          )

        UNION ALL

        -- GMP
        SELECT  
            created_at,
            data:call.chain::STRING AS source_chain,
            data:call.returnValues.destinationChain::STRING AS destination_chain,
            data:call.transaction.from::STRING AS user,
            CASE 
              WHEN IS_ARRAY(data:amount) OR IS_OBJECT(data:amount) THEN NULL
              WHEN TRY_TO_DOUBLE(data:amount::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:amount::STRING)
              ELSE NULL
            END AS amount,
            CASE 
              WHEN IS_ARRAY(data:value) OR IS_OBJECT(data:value) THEN NULL
              WHEN TRY_TO_DOUBLE(data:value::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:value::STRING)
              ELSE NULL
            END AS amount_usd,
            COALESCE(
              CASE 
                WHEN IS_ARRAY(data:gas:gas_used_amount) OR IS_OBJECT(data:gas:gas_used_amount) 
                  OR IS_ARRAY(data:gas_price_rate:source_token.token_price.usd) OR IS_OBJECT(data:gas_price_rate:source_token.token_price.usd) 
                THEN NULL
                WHEN TRY_TO_DOUBLE(data:gas:gas_used_amount::STRING) IS NOT NULL 
                  AND TRY_TO_DOUBLE(data:gas_price_rate:source_token.token_price.usd::STRING) IS NOT NULL 
                THEN TRY_TO_DOUBLE(data:gas:gas_used_amount::STRING) * TRY_TO_DOUBLE(data:gas_price_rate:source_token.token_price.usd::STRING)
                ELSE NULL
              END,
              CASE 
                WHEN IS_ARRAY(data:fees:express_fee_usd) OR IS_OBJECT(data:fees:express_fee_usd) THEN NULL
                WHEN TRY_TO_DOUBLE(data:fees:express_fee_usd::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:fees:express_fee_usd::STRING)
                ELSE NULL
              END
            ) AS fee,
            id, 
            'GMP' AS Service, 
            data:symbol::STRING AS raw_asset
        FROM axelar.axelscan.fact_gmp 
        WHERE status = 'executed'
          AND simplified_status = 'received'
          AND (
            data:approved:returnValues:contractAddress ilike '%0xce16F69375520ab01377ce7B88f5BA8C48F8D666%' 
            OR data:approved:returnValues:contractAddress ilike '%0x492751eC3c57141deb205eC2da8bFcb410738630%'
            OR data:approved:returnValues:contractAddress ilike '%0xDC3D8e1Abe590BCa428a8a2FC4CfDbD1AcF57Bd9%'
            OR data:approved:returnValues:contractAddress ilike '%0xdf4fFDa22270c12d0b5b3788F1669D709476111E%'
            OR data:approved:returnValues:contractAddress ilike '%0xe6B3949F9bBF168f4E3EFc82bc8FD849868CC6d8%'
          )
    )
    SELECT 
        DATE_TRUNC('{timeframe}', created_at) AS Date, (source_chain || '➡' || destination_chain) as Path,
        COUNT(DISTINCT id) AS Swap_Count,  
        ROUND(SUM(amount_usd)) AS Swap_Volume
    FROM axelar_service
    WHERE created_at::date >= '{start_str}' 
      AND created_at::date <= '{end_str}'
    GROUP BY 1, 2
    ORDER BY 1
    """

    return pd.read_sql(query, conn)

# --- Load Data ----------------------------------------------------------------------------------------------------
time_series_data_by_path = load_time_series_data_by_path(timeframe, start_date, end_date)
# --- Chart: Row 4, 5 --------------------------------------------------------------------------------------------------------

# split source & destination
time_series_data_by_path[["Source", "Destination"]] = time_series_data_by_path["PATH"].str.split("➡", expand=True)

# defult filters
col_filter1, col_filter2 = st.columns(2)

with col_filter1:
    selected_source = st.selectbox(
        "Select Source Chain",
        options=sorted(time_series_data_by_path["Source"].unique()),
        index=sorted(time_series_data_by_path["Source"].unique()).index("ethereum")
    )

with col_filter2:
    selected_destination = st.selectbox(
        "Select Destination Chain",
        options=sorted(time_series_data_by_path["Destination"].unique()),
        index=sorted(time_series_data_by_path["Destination"].unique()).index("base")
    )

# filters
filtered_df = time_series_data_by_path[
    (time_series_data_by_path["Source"] == selected_source) &
    (time_series_data_by_path["Destination"] == selected_destination)
]

# --- KPI ----------------------------------------------------------------
total_volume = filtered_df["SWAP_VOLUME"].sum()
total_txn = filtered_df["SWAP_COUNT"].sum()

kpi_col1, kpi_col2 = st.columns(2)
kpi_col1.metric("Total Volume ($USD)", f"${total_volume:,.0f}")
kpi_col2.metric("Total Transactions", f"{total_txn:,}")

# --- charts ---------------------------------------
col1, col2 = st.columns(2)

with col1:
    fig_stacked_volume = px.bar(
        filtered_df,
        x="DATE",
        y="SWAP_VOLUME",
        color="PATH",
        title=f"Volume by Route Over Time ({selected_source} ➡ {selected_destination})"
    )
    fig_stacked_volume.update_layout(barmode="stack", yaxis_title="$USD", xaxis_title="")
    st.plotly_chart(fig_stacked_volume, use_container_width=True)

with col2:
    fig_stacked_txn = px.bar(
        filtered_df,
        x="DATE",
        y="SWAP_COUNT",
        color="PATH",
        title=f"Transaction by Route Over Time ({selected_source} ➡ {selected_destination})"
    )
    fig_stacked_txn.update_layout(barmode="stack", yaxis_title="Txns count", xaxis_title="")
    st.plotly_chart(fig_stacked_txn, use_container_width=True)

# --- Row 6 ------------------------------------------------------------------------------------
@st.cache_data
def load_path_data(start_date, end_date):
    start_str = pd.to_datetime(start_date).strftime("%Y-%m-%d")
    end_str = pd.to_datetime(end_date).strftime("%Y-%m-%d")

    query = f"""
    WITH axelar_service AS (
      SELECT 
        created_at, 
        LOWER(data:send:original_source_chain) AS source_chain, 
        LOWER(data:send:original_destination_chain) AS destination_chain,
        recipient_address AS user, 
        CASE 
          WHEN IS_ARRAY(data:send:amount) THEN NULL
          WHEN IS_OBJECT(data:send:amount) THEN NULL
          WHEN TRY_TO_DOUBLE(data:send:amount::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:send:amount::STRING)
          ELSE NULL
        END AS amount,
        CASE 
          WHEN IS_ARRAY(data:send:amount) OR IS_ARRAY(data:link:price) THEN NULL
          WHEN IS_OBJECT(data:send:amount) OR IS_OBJECT(data:link:price) THEN NULL
          WHEN TRY_TO_DOUBLE(data:send:amount::STRING) IS NOT NULL AND TRY_TO_DOUBLE(data:link:price::STRING) IS NOT NULL 
            THEN TRY_TO_DOUBLE(data:send:amount::STRING) * TRY_TO_DOUBLE(data:link:price::STRING)
          ELSE NULL
        END AS amount_usd,
        CASE 
          WHEN IS_ARRAY(data:send:fee_value) THEN NULL
          WHEN IS_OBJECT(data:send:fee_value) THEN NULL
          WHEN TRY_TO_DOUBLE(data:send:fee_value::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:send:fee_value::STRING)
          ELSE NULL
        END AS fee,
        id, 
        'Token Transfers' AS "Service", 
        data:link:asset::STRING AS raw_asset
      FROM axelar.axelscan.fact_transfers
      WHERE status = 'executed'
        AND simplified_status = 'received'
        AND created_at::date >= '{start_str}'
        AND created_at::date <= '{end_str}'
        AND (
          sender_address ILIKE '%0xce16F69375520ab01377ce7B88f5BA8C48F8D666%'
          OR sender_address ILIKE '%0x492751eC3c57141deb205eC2da8bFcb410738630%'
          OR sender_address ILIKE '%0xDC3D8e1Abe590BCa428a8a2FC4CfDbD1AcF57Bd9%'
          OR sender_address ILIKE '%0xdf4fFDa22270c12d0b5b3788F1669D709476111E%'
          OR sender_address ILIKE '%0xe6B3949F9bBF168f4E3EFc82bc8FD849868CC6d8%'
        )
      UNION ALL
      SELECT  
        created_at,
        data:call.chain::STRING AS source_chain,
        data:call.returnValues.destinationChain::STRING AS destination_chain,
        data:call.transaction.from::STRING AS user,
        CASE 
          WHEN IS_ARRAY(data:amount) OR IS_OBJECT(data:amount) THEN NULL
          WHEN TRY_TO_DOUBLE(data:amount::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:amount::STRING)
          ELSE NULL
        END AS amount,
        CASE 
          WHEN IS_ARRAY(data:value) OR IS_OBJECT(data:value) THEN NULL
          WHEN TRY_TO_DOUBLE(data:value::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:value::STRING)
          ELSE NULL
        END AS amount_usd,
        COALESCE(
          CASE 
            WHEN IS_ARRAY(data:gas:gas_used_amount) OR IS_OBJECT(data:gas:gas_used_amount) 
              OR IS_ARRAY(data:gas_price_rate:source_token.token_price.usd) OR IS_OBJECT(data:gas_price_rate:source_token.token_price.usd) 
            THEN NULL
            WHEN TRY_TO_DOUBLE(data:gas:gas_used_amount::STRING) IS NOT NULL 
              AND TRY_TO_DOUBLE(data:gas_price_rate:source_token.token_price.usd::STRING) IS NOT NULL 
            THEN TRY_TO_DOUBLE(data:gas:gas_used_amount::STRING) * TRY_TO_DOUBLE(data:gas_price_rate:source_token.token_price.usd::STRING)
            ELSE NULL
          END,
          CASE 
            WHEN IS_ARRAY(data:fees:express_fee_usd) OR IS_OBJECT(data:fees:express_fee_usd) THEN NULL
            WHEN TRY_TO_DOUBLE(data:fees:express_fee_usd::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:fees:express_fee_usd::STRING)
            ELSE NULL
          END
        ) AS fee,
        id, 
        'GMP' AS "Service", 
        data:symbol::STRING AS raw_asset
      FROM axelar.axelscan.fact_gmp 
      WHERE status = 'executed'
        AND simplified_status = 'received'
        AND created_at::date >= '{start_str}'
        AND created_at::date <= '{end_str}'
        AND (
          data:approved:returnValues:contractAddress ILIKE '%0xce16F69375520ab01377ce7B88f5BA8C48F8D666%'
          OR data:approved:returnValues:contractAddress ILIKE '%0x492751eC3c57141deb205eC2da8bFcb410738630%'
          OR data:approved:returnValues:contractAddress ILIKE '%0xDC3D8e1Abe590BCa428a8a2FC4CfDbD1AcF57Bd9%'
          OR data:approved:returnValues:contractAddress ILIKE '%0xdf4fFDa22270c12d0b5b3788F1669D709476111E%'
          OR data:approved:returnValues:contractAddress ILIKE '%0xe6B3949F9bBF168f4E3EFc82bc8FD849868CC6d8%'
        )
    )
    SELECT 
      source_chain || '➡' || destination_chain AS "🔀Path", 
      COUNT(DISTINCT id) AS "🔗Transactions",
      round(COUNT(DISTINCT id)/COUNT(DISTINCT user)) as "📋Transaction per User",
      COUNT(DISTINCT user) AS "👥Users", 
      ROUND(SUM(amount_usd),1) AS "💰Volume ($)",
      round((SUM(AMOUNT_USD)/COUNT(DISTINCT USER)),1) as "💸Volume per User ($)",
      count(distinct raw_asset) as "💎Swapped Tokens",
      round(median(amount_usd),1) as "📊Median Volume of Txns ($)"
    FROM axelar_service
    GROUP BY 1
    ORDER BY 2 DESC
    """

    return pd.read_sql(query, conn)

# --- Load data ---
df_path = load_path_data(start_date, end_date)

# --- Show table ---
st.subheader("🔀Squid Activity by Path")
df_display = df_path.copy()
df_display.index = df_display.index + 1
df_display = df_display.applymap(lambda x: f"{x:,}" if isinstance(x, (int, float)) else x)
st.dataframe(df_display, use_container_width=True)

# --- Row 7, 8 --------------------------------------------------------------------------------------------------------------

@st.cache_data
def load_time_series_data_by_token(timeframe, start_date, end_date):
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    query = f"""
    WITH overview as (
    WITH axelar_service AS (
        -- Token Transfers
        SELECT 
            created_at, 
            LOWER(data:send:original_source_chain) AS source_chain, 
            LOWER(data:send:original_destination_chain) AS destination_chain,
            recipient_address AS user, 
            CASE 
              WHEN IS_ARRAY(data:send:amount) THEN NULL
              WHEN IS_OBJECT(data:send:amount) THEN NULL
              WHEN TRY_TO_DOUBLE(data:send:amount::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:send:amount::STRING)
              ELSE NULL
            END AS amount,
            CASE 
              WHEN IS_ARRAY(data:send:amount) OR IS_ARRAY(data:link:price) THEN NULL
              WHEN IS_OBJECT(data:send:amount) OR IS_OBJECT(data:link:price) THEN NULL
              WHEN TRY_TO_DOUBLE(data:send:amount::STRING) IS NOT NULL AND TRY_TO_DOUBLE(data:link:price::STRING) IS NOT NULL 
                THEN TRY_TO_DOUBLE(data:send:amount::STRING) * TRY_TO_DOUBLE(data:link:price::STRING)
              ELSE NULL
            END AS amount_usd,
            CASE 
              WHEN IS_ARRAY(data:send:fee_value) THEN NULL
              WHEN IS_OBJECT(data:send:fee_value) THEN NULL
              WHEN TRY_TO_DOUBLE(data:send:fee_value::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:send:fee_value::STRING)
              ELSE NULL
            END AS fee,
            id, 
            'Token Transfers' AS Service, 
            data:link:asset::STRING AS raw_asset
        FROM axelar.axelscan.fact_transfers
        WHERE status = 'executed'
          AND simplified_status = 'received'
          AND (
            sender_address ilike '%0xce16F69375520ab01377ce7B88f5BA8C48F8D666%' 
            OR sender_address ilike '%0x492751eC3c57141deb205eC2da8bFcb410738630%'
            OR sender_address ilike '%0xDC3D8e1Abe590BCa428a8a2FC4CfDbD1AcF57Bd9%'
            OR sender_address ilike '%0xdf4fFDa22270c12d0b5b3788F1669D709476111E%'
            OR sender_address ilike '%0xe6B3949F9bBF168f4E3EFc82bc8FD849868CC6d8%'
          )

        UNION ALL

        -- GMP
        SELECT  
            created_at,
            data:call.chain::STRING AS source_chain,
            data:call.returnValues.destinationChain::STRING AS destination_chain,
            data:call.transaction.from::STRING AS user,
            CASE 
              WHEN IS_ARRAY(data:amount) OR IS_OBJECT(data:amount) THEN NULL
              WHEN TRY_TO_DOUBLE(data:amount::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:amount::STRING)
              ELSE NULL
            END AS amount,
            CASE 
              WHEN IS_ARRAY(data:value) OR IS_OBJECT(data:value) THEN NULL
              WHEN TRY_TO_DOUBLE(data:value::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:value::STRING)
              ELSE NULL
            END AS amount_usd,
            COALESCE(
              CASE 
                WHEN IS_ARRAY(data:gas:gas_used_amount) OR IS_OBJECT(data:gas:gas_used_amount) 
                  OR IS_ARRAY(data:gas_price_rate:source_token.token_price.usd) OR IS_OBJECT(data:gas_price_rate:source_token.token_price.usd) 
                THEN NULL
                WHEN TRY_TO_DOUBLE(data:gas:gas_used_amount::STRING) IS NOT NULL 
                  AND TRY_TO_DOUBLE(data:gas_price_rate:source_token.token_price.usd::STRING) IS NOT NULL 
                THEN TRY_TO_DOUBLE(data:gas:gas_used_amount::STRING) * TRY_TO_DOUBLE(data:gas_price_rate:source_token.token_price.usd::STRING)
                ELSE NULL
              END,
              CASE 
                WHEN IS_ARRAY(data:fees:express_fee_usd) OR IS_OBJECT(data:fees:express_fee_usd) THEN NULL
                WHEN TRY_TO_DOUBLE(data:fees:express_fee_usd::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:fees:express_fee_usd::STRING)
                ELSE NULL
              END
            ) AS fee,
            id, 
            'GMP' AS Service, 
            data:symbol::STRING AS raw_asset
        FROM axelar.axelscan.fact_gmp 
        WHERE status = 'executed'
          AND simplified_status = 'received'
          AND (
            data:approved:returnValues:contractAddress ilike '%0xce16F69375520ab01377ce7B88f5BA8C48F8D666%' 
            OR data:approved:returnValues:contractAddress ilike '%0x492751eC3c57141deb205eC2da8bFcb410738630%'
            OR data:approved:returnValues:contractAddress ilike '%0xDC3D8e1Abe590BCa428a8a2FC4CfDbD1AcF57Bd9%'
            OR data:approved:returnValues:contractAddress ilike '%0xdf4fFDa22270c12d0b5b3788F1669D709476111E%'
            OR data:approved:returnValues:contractAddress ilike '%0xe6B3949F9bBF168f4E3EFc82bc8FD849868CC6d8%'
          )
    )
    SELECT 
        created_at, id, user, amount_usd, CASE 
      WHEN raw_asset='arb-wei' THEN 'ARB'
      WHEN raw_asset='avalanche-uusdc' THEN 'Avalanche USDC'
      WHEN raw_asset='avax-wei' THEN 'AVAX'
      WHEN raw_asset='bnb-wei' THEN 'BNB'
      WHEN raw_asset='busd-wei' THEN 'BUSD'
      WHEN raw_asset='cbeth-wei' THEN 'cbETH'
      WHEN raw_asset='cusd-wei' THEN 'cUSD'
      WHEN raw_asset='dai-wei' THEN 'DAI'
      WHEN raw_asset='dot-planck' THEN 'DOT'
      WHEN raw_asset='eeur' THEN 'EURC'
      WHEN raw_asset='ern-wei' THEN 'ERN'
      WHEN raw_asset='eth-wei' THEN 'ETH'
      WHEN raw_asset ILIKE 'factory/sei10hub%' THEN 'SEILOR'
      WHEN raw_asset='fil-wei' THEN 'FIL'
      WHEN raw_asset='frax-wei' THEN 'FRAX'
      WHEN raw_asset='ftm-wei' THEN 'FTM'
      WHEN raw_asset='glmr-wei' THEN 'GLMR'
      WHEN raw_asset='hzn-wei' THEN 'HZN'
      WHEN raw_asset='link-wei' THEN 'LINK'
      WHEN raw_asset='matic-wei' THEN 'MATIC'
      WHEN raw_asset='mkr-wei' THEN 'MKR'
      WHEN raw_asset='mpx-wei' THEN 'MPX'
      WHEN raw_asset='oath-wei' THEN 'OATH'
      WHEN raw_asset='op-wei' THEN 'OP'
      WHEN raw_asset='orbs-wei' THEN 'ORBS'
      WHEN raw_asset='factory/sei10hud5e5er4aul2l7sp2u9qp2lag5u4xf8mvyx38cnjvqhlgsrcls5qn5ke/seilor' THEN 'SEILOR'
      WHEN raw_asset='pepe-wei' THEN 'PEPE'
      WHEN raw_asset='polygon-uusdc' THEN 'Polygon USDC'
      WHEN raw_asset='reth-wei' THEN 'rETH'
      WHEN raw_asset='ring-wei' THEN 'RING'
      WHEN raw_asset='shib-wei' THEN 'SHIB'
      WHEN raw_asset='sonne-wei' THEN 'SONNE'
      WHEN raw_asset='stuatom' THEN 'stATOM'
      WHEN raw_asset='uatom' THEN 'ATOM'
      WHEN raw_asset='uaxl' THEN 'AXL'
      WHEN raw_asset='ukuji' THEN 'KUJI'
      WHEN raw_asset='ulava' THEN 'LAVA'
      WHEN raw_asset='uluna' THEN 'LUNA'
      WHEN raw_asset='ungm' THEN 'NGM'
      WHEN raw_asset='uni-wei' THEN 'UNI'
      WHEN raw_asset='uosmo' THEN 'OSMO'
      WHEN raw_asset='usomm' THEN 'SOMM'
      WHEN raw_asset='ustrd' THEN 'STRD'
      WHEN raw_asset='utia' THEN 'TIA'
      WHEN raw_asset='uumee' THEN 'UMEE'
      WHEN raw_asset='uusd' THEN 'USTC'
      WHEN raw_asset='uusdc' THEN 'USDC'
      WHEN raw_asset='uusdt' THEN 'USDT'
      WHEN raw_asset='vela-wei' THEN 'VELA'
      WHEN raw_asset='wavax-wei' THEN 'WAVAX'
      WHEN raw_asset='wbnb-wei' THEN 'WBNB'
      WHEN raw_asset='wbtc-satoshi' THEN 'WBTC'
      WHEN raw_asset='weth-wei' THEN 'WETH'
      WHEN raw_asset='wfil-wei' THEN 'WFIL'
      WHEN raw_asset='wftm-wei' THEN 'WFTM'
      WHEN raw_asset='wglmr-wei' THEN 'WGLMR'
      WHEN raw_asset='wmai-wei' THEN 'WMAI'
      WHEN raw_asset='wmatic-wei' THEN 'WMATIC'
      WHEN raw_asset='wsteth-wei' THEN 'wstETH'
      WHEN raw_asset='yield-eth-wei' THEN 'yieldETH' 
      else raw_asset end as Token 
    FROM axelar_service
    WHERE created_at::date >= '{start_str}' 
      AND created_at::date <= '{end_str}')

      select date_trunc('{timeframe}',created_at) as Date, Token, count(distinct id) as Swap_Count, sum(amount_usd) as Swap_Volume
      from overview
      group by 1, 2
      order by 1
    """

    return pd.read_sql(query, conn)

# --- Load Data ----------------------------------------------------------------------------------------------------
time_series_data_by_token = load_time_series_data_by_token(timeframe, start_date, end_date)

# --- Filters (single dropdown) ------------------------------------------------------------------------------------
# نکته مهم: columns(1) لیست برمی‌گرداند؛ با کاما آن‌پک می‌کنیم تا ستون تکی داشته باشیم
col_filter1, = st.columns(1)

with col_filter1:
    tokens = sorted(time_series_data_by_token["TOKEN"].dropna().unique().tolist())
    if not tokens:
        st.warning("No token data to display for the selected period.")
        st.stop()

    default_token = "USDC"
    try:
        default_idx = tokens.index(default_token)
    except ValueError:
        default_idx = 0  # اگر USDC وجود نداشت، اولین گزینه انتخاب شود

    selected_token = st.selectbox(
        "Select Token",
        options=tokens,
        index=default_idx
    )

# --- Filtering ----------------------------------------------------------------------------------------------------
filtered_df = time_series_data_by_token[
    (time_series_data_by_token["TOKEN"] == selected_token)
]

# --- KPI ----------------------------------------------------------------------------------------------------------
total_volume = float(filtered_df["SWAP_VOLUME"].sum() or 0)
total_txn = int(filtered_df["SWAP_COUNT"].sum() or 0)

kpi_col1, kpi_col2 = st.columns(2)
kpi_col1.metric("Total Volume ($USD)", f"${total_volume:,.0f}")
kpi_col2.metric("Total Transactions", f"{total_txn:,}")

# --- Charts (same stacked bar style) ------------------------------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    fig_stacked_volume = px.bar(
        filtered_df,
        x="DATE",
        y="SWAP_VOLUME",
        color="TOKEN",
        title=f"Swap Volume of ({selected_token}) Token Over Time ($USD)"
    )
    fig_stacked_volume.update_layout(barmode="stack", yaxis_title="$USD", xaxis_title="")
    st.plotly_chart(fig_stacked_volume, use_container_width=True)

with col2:
    fig_stacked_txn = px.bar(
        filtered_df,
        x="DATE",
        y="SWAP_COUNT",
        color="TOKEN",
        title=f"Swap Count of ({selected_token}) Token Over Time"
    )
    fig_stacked_txn.update_layout(barmode="stack", yaxis_title="Txns count", xaxis_title="")
    st.plotly_chart(fig_stacked_txn, use_container_width=True)

# --- Row 9 ----------------------------------------------------------------------------------------------------------------
@st.cache_data
def load_token_data(start_date, end_date):
    start_str = pd.to_datetime(start_date).strftime("%Y-%m-%d")
    end_str = pd.to_datetime(end_date).strftime("%Y-%m-%d")

    query = f"""
    with overview as (
    WITH axelar_service AS (
      SELECT 
        created_at, 
        LOWER(data:send:original_source_chain) AS source_chain, 
        LOWER(data:send:original_destination_chain) AS destination_chain,
        recipient_address AS user, 
        CASE 
          WHEN IS_ARRAY(data:send:amount) THEN NULL
          WHEN IS_OBJECT(data:send:amount) THEN NULL
          WHEN TRY_TO_DOUBLE(data:send:amount::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:send:amount::STRING)
          ELSE NULL
        END AS amount,
        CASE 
          WHEN IS_ARRAY(data:send:amount) OR IS_ARRAY(data:link:price) THEN NULL
          WHEN IS_OBJECT(data:send:amount) OR IS_OBJECT(data:link:price) THEN NULL
          WHEN TRY_TO_DOUBLE(data:send:amount::STRING) IS NOT NULL AND TRY_TO_DOUBLE(data:link:price::STRING) IS NOT NULL 
            THEN TRY_TO_DOUBLE(data:send:amount::STRING) * TRY_TO_DOUBLE(data:link:price::STRING)
          ELSE NULL
        END AS amount_usd,
        CASE 
          WHEN IS_ARRAY(data:send:fee_value) THEN NULL
          WHEN IS_OBJECT(data:send:fee_value) THEN NULL
          WHEN TRY_TO_DOUBLE(data:send:fee_value::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:send:fee_value::STRING)
          ELSE NULL
        END AS fee,
        id, 
        'Token Transfers' AS "Service", 
        data:link:asset::STRING AS raw_asset
      FROM axelar.axelscan.fact_transfers
      WHERE status = 'executed'
        AND simplified_status = 'received'
        AND created_at::date >= '{start_str}'
        AND created_at::date <= '{end_str}'
        AND (
          sender_address ILIKE '%0xce16F69375520ab01377ce7B88f5BA8C48F8D666%'
          OR sender_address ILIKE '%0x492751eC3c57141deb205eC2da8bFcb410738630%'
          OR sender_address ILIKE '%0xDC3D8e1Abe590BCa428a8a2FC4CfDbD1AcF57Bd9%'
          OR sender_address ILIKE '%0xdf4fFDa22270c12d0b5b3788F1669D709476111E%'
          OR sender_address ILIKE '%0xe6B3949F9bBF168f4E3EFc82bc8FD849868CC6d8%'
        )
      UNION ALL
      SELECT  
        created_at,
        data:call.chain::STRING AS source_chain,
        data:call.returnValues.destinationChain::STRING AS destination_chain,
        data:call.transaction.from::STRING AS user,
        CASE 
          WHEN IS_ARRAY(data:amount) OR IS_OBJECT(data:amount) THEN NULL
          WHEN TRY_TO_DOUBLE(data:amount::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:amount::STRING)
          ELSE NULL
        END AS amount,
        CASE 
          WHEN IS_ARRAY(data:value) OR IS_OBJECT(data:value) THEN NULL
          WHEN TRY_TO_DOUBLE(data:value::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:value::STRING)
          ELSE NULL
        END AS amount_usd,
        COALESCE(
          CASE 
            WHEN IS_ARRAY(data:gas:gas_used_amount) OR IS_OBJECT(data:gas:gas_used_amount) 
              OR IS_ARRAY(data:gas_price_rate:source_token.token_price.usd) OR IS_OBJECT(data:gas_price_rate:source_token.token_price.usd) 
            THEN NULL
            WHEN TRY_TO_DOUBLE(data:gas:gas_used_amount::STRING) IS NOT NULL 
              AND TRY_TO_DOUBLE(data:gas_price_rate:source_token.token_price.usd::STRING) IS NOT NULL 
            THEN TRY_TO_DOUBLE(data:gas:gas_used_amount::STRING) * TRY_TO_DOUBLE(data:gas_price_rate:source_token.token_price.usd::STRING)
            ELSE NULL
          END,
          CASE 
            WHEN IS_ARRAY(data:fees:express_fee_usd) OR IS_OBJECT(data:fees:express_fee_usd) THEN NULL
            WHEN TRY_TO_DOUBLE(data:fees:express_fee_usd::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:fees:express_fee_usd::STRING)
            ELSE NULL
          END
        ) AS fee,
        id, 
        'GMP' AS "Service", 
        data:symbol::STRING AS raw_asset
      FROM axelar.axelscan.fact_gmp 
      WHERE status = 'executed'
        AND simplified_status = 'received'
        AND created_at::date >= '{start_str}'
        AND created_at::date <= '{end_str}'
        AND (
          data:approved:returnValues:contractAddress ILIKE '%0xce16F69375520ab01377ce7B88f5BA8C48F8D666%'
          OR data:approved:returnValues:contractAddress ILIKE '%0x492751eC3c57141deb205eC2da8bFcb410738630%'
          OR data:approved:returnValues:contractAddress ILIKE '%0xDC3D8e1Abe590BCa428a8a2FC4CfDbD1AcF57Bd9%'
          OR data:approved:returnValues:contractAddress ILIKE '%0xdf4fFDa22270c12d0b5b3788F1669D709476111E%'
          OR data:approved:returnValues:contractAddress ILIKE '%0xe6B3949F9bBF168f4E3EFc82bc8FD849868CC6d8%'
        )
    )
    Select id, user, amount_usd, source_chain, destination_chain, created_at, CASE 
      WHEN raw_asset='arb-wei' THEN 'ARB'
      WHEN raw_asset='avalanche-uusdc' THEN 'Avalanche USDC'
      WHEN raw_asset='avax-wei' THEN 'AVAX'
      WHEN raw_asset='bnb-wei' THEN 'BNB'
      WHEN raw_asset='busd-wei' THEN 'BUSD'
      WHEN raw_asset='cbeth-wei' THEN 'cbETH'
      WHEN raw_asset='cusd-wei' THEN 'cUSD'
      WHEN raw_asset='dai-wei' THEN 'DAI'
      WHEN raw_asset='dot-planck' THEN 'DOT'
      WHEN raw_asset='eeur' THEN 'EURC'
      WHEN raw_asset='ern-wei' THEN 'ERN'
      WHEN raw_asset='eth-wei' THEN 'ETH'
      WHEN raw_asset ILIKE 'factory/sei10hub%' THEN 'SEILOR'
      WHEN raw_asset='fil-wei' THEN 'FIL'
      WHEN raw_asset='frax-wei' THEN 'FRAX'
      WHEN raw_asset='ftm-wei' THEN 'FTM'
      WHEN raw_asset='glmr-wei' THEN 'GLMR'
      WHEN raw_asset='hzn-wei' THEN 'HZN'
      WHEN raw_asset='link-wei' THEN 'LINK'
      WHEN raw_asset='matic-wei' THEN 'MATIC'
      WHEN raw_asset='mkr-wei' THEN 'MKR'
      WHEN raw_asset='mpx-wei' THEN 'MPX'
      WHEN raw_asset='oath-wei' THEN 'OATH'
      WHEN raw_asset='op-wei' THEN 'OP'
      WHEN raw_asset='orbs-wei' THEN 'ORBS'
      WHEN raw_asset='factory/sei10hud5e5er4aul2l7sp2u9qp2lag5u4xf8mvyx38cnjvqhlgsrcls5qn5ke/seilor' THEN 'SEILOR'
      WHEN raw_asset='pepe-wei' THEN 'PEPE'
      WHEN raw_asset='polygon-uusdc' THEN 'Polygon USDC'
      WHEN raw_asset='reth-wei' THEN 'rETH'
      WHEN raw_asset='ring-wei' THEN 'RING'
      WHEN raw_asset='shib-wei' THEN 'SHIB'
      WHEN raw_asset='sonne-wei' THEN 'SONNE'
      WHEN raw_asset='stuatom' THEN 'stATOM'
      WHEN raw_asset='uatom' THEN 'ATOM'
      WHEN raw_asset='uaxl' THEN 'AXL'
      WHEN raw_asset='ukuji' THEN 'KUJI'
      WHEN raw_asset='ulava' THEN 'LAVA'
      WHEN raw_asset='uluna' THEN 'LUNA'
      WHEN raw_asset='ungm' THEN 'NGM'
      WHEN raw_asset='uni-wei' THEN 'UNI'
      WHEN raw_asset='uosmo' THEN 'OSMO'
      WHEN raw_asset='usomm' THEN 'SOMM'
      WHEN raw_asset='ustrd' THEN 'STRD'
      WHEN raw_asset='utia' THEN 'TIA'
      WHEN raw_asset='uumee' THEN 'UMEE'
      WHEN raw_asset='uusd' THEN 'USTC'
      WHEN raw_asset='uusdc' THEN 'USDC'
      WHEN raw_asset='uusdt' THEN 'USDT'
      WHEN raw_asset='vela-wei' THEN 'VELA'
      WHEN raw_asset='wavax-wei' THEN 'WAVAX'
      WHEN raw_asset='wbnb-wei' THEN 'WBNB'
      WHEN raw_asset='wbtc-satoshi' THEN 'WBTC'
      WHEN raw_asset='weth-wei' THEN 'WETH'
      WHEN raw_asset='wfil-wei' THEN 'WFIL'
      WHEN raw_asset='wftm-wei' THEN 'WFTM'
      WHEN raw_asset='wglmr-wei' THEN 'WGLMR'
      WHEN raw_asset='wmai-wei' THEN 'WMAI'
      WHEN raw_asset='wmatic-wei' THEN 'WMATIC'
      WHEN raw_asset='wsteth-wei' THEN 'wstETH'
      WHEN raw_asset='yield-eth-wei' THEN 'yieldETH' 
      else raw_asset end as Token 
    FROM axelar_service)
    SELECT 
      Token AS "💎Token", 
      COUNT(DISTINCT id) AS "🔗Transactions",
      round(COUNT(DISTINCT id)/COUNT(DISTINCT user)) as "📋Transaction per User",
      COUNT(DISTINCT user) AS "👥Users", 
      ROUND(SUM(amount_usd),1) AS "💰Volume ($)",
      round((SUM(AMOUNT_USD)/COUNT(DISTINCT USER)),1) as "💸Volume per User ($)",
      count(distinct (source_chain || '➡' || destination_chain)) as "🔀Unique Routes",
      round(median(amount_usd),1) as "📊Median Volume of Txns ($)"
      from overview
      where token is not null
      group by 1
      order by 2 desc 
    """

    return pd.read_sql(query, conn)

# --- Load data ---
df_token = load_token_data(start_date, end_date)

# --- Show table ---
st.subheader("🔀Squid Activity by Token")
df_display = df_token.copy()
df_display.index = df_display.index + 1
df_display = df_display.applymap(lambda x: f"{x:,}" if isinstance(x, (int, float)) else x)
st.dataframe(df_display, use_container_width=True)

# --- Row 10 --------------------------------------------------------------------------------------------------------------------
@st.cache_data
def load_stablecoin_kpi(start_date, end_date):
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    query = f"""
    WITH overview as (
    WITH axelar_service AS (
        -- Token Transfers
        SELECT 
            created_at, 
            LOWER(data:send:original_source_chain) AS source_chain, 
            LOWER(data:send:original_destination_chain) AS destination_chain,
            recipient_address AS user, 
            CASE 
              WHEN IS_ARRAY(data:send:amount) THEN NULL
              WHEN IS_OBJECT(data:send:amount) THEN NULL
              WHEN TRY_TO_DOUBLE(data:send:amount::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:send:amount::STRING)
              ELSE NULL
            END AS amount,
            CASE 
              WHEN IS_ARRAY(data:send:amount) OR IS_ARRAY(data:link:price) THEN NULL
              WHEN IS_OBJECT(data:send:amount) OR IS_OBJECT(data:link:price) THEN NULL
              WHEN TRY_TO_DOUBLE(data:send:amount::STRING) IS NOT NULL AND TRY_TO_DOUBLE(data:link:price::STRING) IS NOT NULL 
                THEN TRY_TO_DOUBLE(data:send:amount::STRING) * TRY_TO_DOUBLE(data:link:price::STRING)
              ELSE NULL
            END AS amount_usd,
            CASE 
              WHEN IS_ARRAY(data:send:fee_value) THEN NULL
              WHEN IS_OBJECT(data:send:fee_value) THEN NULL
              WHEN TRY_TO_DOUBLE(data:send:fee_value::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:send:fee_value::STRING)
              ELSE NULL
            END AS fee,
            id, 
            'Token Transfers' AS Service, 
            data:link:asset::STRING AS raw_asset
        FROM axelar.axelscan.fact_transfers
        WHERE status = 'executed'
          AND simplified_status = 'received'
          AND (
            sender_address ilike '%0xce16F69375520ab01377ce7B88f5BA8C48F8D666%' 
            OR sender_address ilike '%0x492751eC3c57141deb205eC2da8bFcb410738630%'
            OR sender_address ilike '%0xDC3D8e1Abe590BCa428a8a2FC4CfDbD1AcF57Bd9%'
            OR sender_address ilike '%0xdf4fFDa22270c12d0b5b3788F1669D709476111E%'
            OR sender_address ilike '%0xe6B3949F9bBF168f4E3EFc82bc8FD849868CC6d8%'
          )

        UNION ALL

        -- GMP
        SELECT  
            created_at,
            data:call.chain::STRING AS source_chain,
            data:call.returnValues.destinationChain::STRING AS destination_chain,
            data:call.transaction.from::STRING AS user,
            CASE 
              WHEN IS_ARRAY(data:amount) OR IS_OBJECT(data:amount) THEN NULL
              WHEN TRY_TO_DOUBLE(data:amount::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:amount::STRING)
              ELSE NULL
            END AS amount,
            CASE 
              WHEN IS_ARRAY(data:value) OR IS_OBJECT(data:value) THEN NULL
              WHEN TRY_TO_DOUBLE(data:value::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:value::STRING)
              ELSE NULL
            END AS amount_usd,
            COALESCE(
              CASE 
                WHEN IS_ARRAY(data:gas:gas_used_amount) OR IS_OBJECT(data:gas:gas_used_amount) 
                  OR IS_ARRAY(data:gas_price_rate:source_token.token_price.usd) OR IS_OBJECT(data:gas_price_rate:source_token.token_price.usd) 
                THEN NULL
                WHEN TRY_TO_DOUBLE(data:gas:gas_used_amount::STRING) IS NOT NULL 
                  AND TRY_TO_DOUBLE(data:gas_price_rate:source_token.token_price.usd::STRING) IS NOT NULL 
                THEN TRY_TO_DOUBLE(data:gas:gas_used_amount::STRING) * TRY_TO_DOUBLE(data:gas_price_rate:source_token.token_price.usd::STRING)
                ELSE NULL
              END,
              CASE 
                WHEN IS_ARRAY(data:fees:express_fee_usd) OR IS_OBJECT(data:fees:express_fee_usd) THEN NULL
                WHEN TRY_TO_DOUBLE(data:fees:express_fee_usd::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:fees:express_fee_usd::STRING)
                ELSE NULL
              END
            ) AS fee,
            id, 
            'GMP' AS Service, 
            data:symbol::STRING AS raw_asset
        FROM axelar.axelscan.fact_gmp 
        WHERE status = 'executed'
          AND simplified_status = 'received'
          AND (
            data:approved:returnValues:contractAddress ilike '%0xce16F69375520ab01377ce7B88f5BA8C48F8D666%' 
            OR data:approved:returnValues:contractAddress ilike '%0x492751eC3c57141deb205eC2da8bFcb410738630%'
            OR data:approved:returnValues:contractAddress ilike '%0xDC3D8e1Abe590BCa428a8a2FC4CfDbD1AcF57Bd9%'
            OR data:approved:returnValues:contractAddress ilike '%0xdf4fFDa22270c12d0b5b3788F1669D709476111E%'
            OR data:approved:returnValues:contractAddress ilike '%0xe6B3949F9bBF168f4E3EFc82bc8FD849868CC6d8%'
          )
    )
    
    SELECT 
        source_chain, destination_chain, id, user, amount_usd, CASE 
      WHEN raw_asset='arb-wei' THEN 'ARB'
      WHEN raw_asset='avalanche-uusdc' THEN 'Avalanche USDC'
      WHEN raw_asset='avax-wei' THEN 'AVAX'
      WHEN raw_asset='bnb-wei' THEN 'BNB'
      WHEN raw_asset='busd-wei' THEN 'BUSD'
      WHEN raw_asset='cbeth-wei' THEN 'cbETH'
      WHEN raw_asset='cusd-wei' THEN 'cUSD'
      WHEN raw_asset='dai-wei' THEN 'DAI'
      WHEN raw_asset='dot-planck' THEN 'DOT'
      WHEN raw_asset='eeur' THEN 'EURC'
      WHEN raw_asset='ern-wei' THEN 'ERN'
      WHEN raw_asset='eth-wei' THEN 'ETH'
      WHEN raw_asset ILIKE 'factory/sei10hub%' THEN 'SEILOR'
      WHEN raw_asset='fil-wei' THEN 'FIL'
      WHEN raw_asset='frax-wei' THEN 'FRAX'
      WHEN raw_asset='ftm-wei' THEN 'FTM'
      WHEN raw_asset='glmr-wei' THEN 'GLMR'
      WHEN raw_asset='hzn-wei' THEN 'HZN'
      WHEN raw_asset='link-wei' THEN 'LINK'
      WHEN raw_asset='matic-wei' THEN 'MATIC'
      WHEN raw_asset='mkr-wei' THEN 'MKR'
      WHEN raw_asset='mpx-wei' THEN 'MPX'
      WHEN raw_asset='oath-wei' THEN 'OATH'
      WHEN raw_asset='op-wei' THEN 'OP'
      WHEN raw_asset='orbs-wei' THEN 'ORBS'
      WHEN raw_asset='factory/sei10hud5e5er4aul2l7sp2u9qp2lag5u4xf8mvyx38cnjvqhlgsrcls5qn5ke/seilor' THEN 'SEILOR'
      WHEN raw_asset='pepe-wei' THEN 'PEPE'
      WHEN raw_asset='polygon-uusdc' THEN 'Polygon USDC'
      WHEN raw_asset='reth-wei' THEN 'rETH'
      WHEN raw_asset='ring-wei' THEN 'RING'
      WHEN raw_asset='shib-wei' THEN 'SHIB'
      WHEN raw_asset='sonne-wei' THEN 'SONNE'
      WHEN raw_asset='stuatom' THEN 'stATOM'
      WHEN raw_asset='uatom' THEN 'ATOM'
      WHEN raw_asset='uaxl' THEN 'AXL'
      WHEN raw_asset='ukuji' THEN 'KUJI'
      WHEN raw_asset='ulava' THEN 'LAVA'
      WHEN raw_asset='uluna' THEN 'LUNA'
      WHEN raw_asset='ungm' THEN 'NGM'
      WHEN raw_asset='uni-wei' THEN 'UNI'
      WHEN raw_asset='uosmo' THEN 'OSMO'
      WHEN raw_asset='usomm' THEN 'SOMM'
      WHEN raw_asset='ustrd' THEN 'STRD'
      WHEN raw_asset='utia' THEN 'TIA'
      WHEN raw_asset='uumee' THEN 'UMEE'
      WHEN raw_asset='uusd' THEN 'USTC'
      WHEN raw_asset='uusdc' THEN 'USDC'
      WHEN raw_asset='uusdt' THEN 'USDT'
      WHEN raw_asset='vela-wei' THEN 'VELA'
      WHEN raw_asset='wavax-wei' THEN 'WAVAX'
      WHEN raw_asset='wbnb-wei' THEN 'WBNB'
      WHEN raw_asset='wbtc-satoshi' THEN 'WBTC'
      WHEN raw_asset='weth-wei' THEN 'WETH'
      WHEN raw_asset='wfil-wei' THEN 'WFIL'
      WHEN raw_asset='wftm-wei' THEN 'WFTM'
      WHEN raw_asset='wglmr-wei' THEN 'WGLMR'
      WHEN raw_asset='wmai-wei' THEN 'WMAI'
      WHEN raw_asset='wmatic-wei' THEN 'WMATIC'
      WHEN raw_asset='wsteth-wei' THEN 'wstETH'
      WHEN raw_asset='yield-eth-wei' THEN 'yieldETH' 
      else raw_asset end as Token
    FROM axelar_service
    WHERE created_at::date >= '{start_str}' 
      AND created_at::date <= '{end_str}')

      SELECT 
        COUNT(DISTINCT id) AS Number_of_Swaps, 
        COUNT(DISTINCT user) AS Number_of_Swappers, 
        ROUND(SUM(amount_usd)) AS Volume_of_Swaps
    FROM overview
    WHERE token in ('axlUSDC','USDC','axlUSDT','EUROC','AXLEUROC','USDT','DAI','axlDAI','PolygonUSDC','axlArbitrumUSDC',
      'AvalancheUSDC','sFRAX','FRAX','BUSD','axlBUSD','axlFRAX','axlOptimismUSDC','cUSD')

    """

    return pd.read_sql(query, conn)

# --- Load Data -----------------------------------------------------------------------------------------------------------------
stablecoin_kpi = load_stablecoin_kpi(start_date, end_date)
# --- Charts 10 -----------------------------------------------------------------------------------------------------------------
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(card_style.format(label="Volume of Swaps", value=f"${stablecoin_kpi['VOLUME_OF_SWAPS'][0]:,}"), unsafe_allow_html=True)
with col2:
    st.markdown(card_style.format(label="Number of Swaps", value=f"{stablecoin_kpi['NUMBER_OF_SWAPS'][0]:,} Swaps"), unsafe_allow_html=True)
with col3:
    st.markdown(card_style.format(label="Number of Swappers", value=f"{stablecoin_kpi['NUMBER_OF_SWAPPERS'][0]:,} Wallets"), unsafe_allow_html=True)

# --- Row 11, 12 ----------------------------------------------------------------------------------------------------------------
@st.cache_data
def load_stablecoin_data(timeframe, start_date, end_date):
    start_str = pd.to_datetime(start_date).strftime("%Y-%m-%d")
    end_str = pd.to_datetime(end_date).strftime("%Y-%m-%d")

    query = f"""
    with overview as (
    WITH axelar_service AS (
      SELECT 
        created_at, 
        LOWER(data:send:original_source_chain) AS source_chain, 
        LOWER(data:send:original_destination_chain) AS destination_chain,
        recipient_address AS user, 
        CASE 
          WHEN IS_ARRAY(data:send:amount) THEN NULL
          WHEN IS_OBJECT(data:send:amount) THEN NULL
          WHEN TRY_TO_DOUBLE(data:send:amount::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:send:amount::STRING)
          ELSE NULL
        END AS amount,
        CASE 
          WHEN IS_ARRAY(data:send:amount) OR IS_ARRAY(data:link:price) THEN NULL
          WHEN IS_OBJECT(data:send:amount) OR IS_OBJECT(data:link:price) THEN NULL
          WHEN TRY_TO_DOUBLE(data:send:amount::STRING) IS NOT NULL AND TRY_TO_DOUBLE(data:link:price::STRING) IS NOT NULL 
            THEN TRY_TO_DOUBLE(data:send:amount::STRING) * TRY_TO_DOUBLE(data:link:price::STRING)
          ELSE NULL
        END AS amount_usd,
        CASE 
          WHEN IS_ARRAY(data:send:fee_value) THEN NULL
          WHEN IS_OBJECT(data:send:fee_value) THEN NULL
          WHEN TRY_TO_DOUBLE(data:send:fee_value::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:send:fee_value::STRING)
          ELSE NULL
        END AS fee,
        id, 
        'Token Transfers' AS "Service", 
        data:link:asset::STRING AS raw_asset
      FROM axelar.axelscan.fact_transfers
      WHERE status = 'executed'
        AND simplified_status = 'received'
        AND created_at::date >= '{start_str}'
        AND created_at::date <= '{end_str}'
        AND (
          sender_address ILIKE '%0xce16F69375520ab01377ce7B88f5BA8C48F8D666%'
          OR sender_address ILIKE '%0x492751eC3c57141deb205eC2da8bFcb410738630%'
          OR sender_address ILIKE '%0xDC3D8e1Abe590BCa428a8a2FC4CfDbD1AcF57Bd9%'
          OR sender_address ILIKE '%0xdf4fFDa22270c12d0b5b3788F1669D709476111E%'
          OR sender_address ILIKE '%0xe6B3949F9bBF168f4E3EFc82bc8FD849868CC6d8%'
        )
      UNION ALL
      SELECT  
        created_at,
        data:call.chain::STRING AS source_chain,
        data:call.returnValues.destinationChain::STRING AS destination_chain,
        data:call.transaction.from::STRING AS user,
        CASE 
          WHEN IS_ARRAY(data:amount) OR IS_OBJECT(data:amount) THEN NULL
          WHEN TRY_TO_DOUBLE(data:amount::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:amount::STRING)
          ELSE NULL
        END AS amount,
        CASE 
          WHEN IS_ARRAY(data:value) OR IS_OBJECT(data:value) THEN NULL
          WHEN TRY_TO_DOUBLE(data:value::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:value::STRING)
          ELSE NULL
        END AS amount_usd,
        COALESCE(
          CASE 
            WHEN IS_ARRAY(data:gas:gas_used_amount) OR IS_OBJECT(data:gas:gas_used_amount) 
              OR IS_ARRAY(data:gas_price_rate:source_token.token_price.usd) OR IS_OBJECT(data:gas_price_rate:source_token.token_price.usd) 
            THEN NULL
            WHEN TRY_TO_DOUBLE(data:gas:gas_used_amount::STRING) IS NOT NULL 
              AND TRY_TO_DOUBLE(data:gas_price_rate:source_token.token_price.usd::STRING) IS NOT NULL 
            THEN TRY_TO_DOUBLE(data:gas:gas_used_amount::STRING) * TRY_TO_DOUBLE(data:gas_price_rate:source_token.token_price.usd::STRING)
            ELSE NULL
          END,
          CASE 
            WHEN IS_ARRAY(data:fees:express_fee_usd) OR IS_OBJECT(data:fees:express_fee_usd) THEN NULL
            WHEN TRY_TO_DOUBLE(data:fees:express_fee_usd::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:fees:express_fee_usd::STRING)
            ELSE NULL
          END
        ) AS fee,
        id, 
        'GMP' AS "Service", 
        data:symbol::STRING AS raw_asset
      FROM axelar.axelscan.fact_gmp 
      WHERE status = 'executed'
        AND simplified_status = 'received'
        AND created_at::date >= '{start_str}'
        AND created_at::date <= '{end_str}'
        AND (
          data:approved:returnValues:contractAddress ILIKE '%0xce16F69375520ab01377ce7B88f5BA8C48F8D666%'
          OR data:approved:returnValues:contractAddress ILIKE '%0x492751eC3c57141deb205eC2da8bFcb410738630%'
          OR data:approved:returnValues:contractAddress ILIKE '%0xDC3D8e1Abe590BCa428a8a2FC4CfDbD1AcF57Bd9%'
          OR data:approved:returnValues:contractAddress ILIKE '%0xdf4fFDa22270c12d0b5b3788F1669D709476111E%'
          OR data:approved:returnValues:contractAddress ILIKE '%0xe6B3949F9bBF168f4E3EFc82bc8FD849868CC6d8%'
        )
    )
    Select id, user, amount_usd, source_chain, destination_chain, created_at, CASE 
      WHEN raw_asset='arb-wei' THEN 'ARB'
      WHEN raw_asset='avalanche-uusdc' THEN 'Avalanche USDC'
      WHEN raw_asset='avax-wei' THEN 'AVAX'
      WHEN raw_asset='bnb-wei' THEN 'BNB'
      WHEN raw_asset='busd-wei' THEN 'BUSD'
      WHEN raw_asset='cbeth-wei' THEN 'cbETH'
      WHEN raw_asset='cusd-wei' THEN 'cUSD'
      WHEN raw_asset='dai-wei' THEN 'DAI'
      WHEN raw_asset='dot-planck' THEN 'DOT'
      WHEN raw_asset='eeur' THEN 'EURC'
      WHEN raw_asset='ern-wei' THEN 'ERN'
      WHEN raw_asset='eth-wei' THEN 'ETH'
      WHEN raw_asset ILIKE 'factory/sei10hub%' THEN 'SEILOR'
      WHEN raw_asset='fil-wei' THEN 'FIL'
      WHEN raw_asset='frax-wei' THEN 'FRAX'
      WHEN raw_asset='ftm-wei' THEN 'FTM'
      WHEN raw_asset='glmr-wei' THEN 'GLMR'
      WHEN raw_asset='hzn-wei' THEN 'HZN'
      WHEN raw_asset='link-wei' THEN 'LINK'
      WHEN raw_asset='matic-wei' THEN 'MATIC'
      WHEN raw_asset='mkr-wei' THEN 'MKR'
      WHEN raw_asset='mpx-wei' THEN 'MPX'
      WHEN raw_asset='oath-wei' THEN 'OATH'
      WHEN raw_asset='op-wei' THEN 'OP'
      WHEN raw_asset='orbs-wei' THEN 'ORBS'
      WHEN raw_asset='factory/sei10hud5e5er4aul2l7sp2u9qp2lag5u4xf8mvyx38cnjvqhlgsrcls5qn5ke/seilor' THEN 'SEILOR'
      WHEN raw_asset='pepe-wei' THEN 'PEPE'
      WHEN raw_asset='polygon-uusdc' THEN 'Polygon USDC'
      WHEN raw_asset='reth-wei' THEN 'rETH'
      WHEN raw_asset='ring-wei' THEN 'RING'
      WHEN raw_asset='shib-wei' THEN 'SHIB'
      WHEN raw_asset='sonne-wei' THEN 'SONNE'
      WHEN raw_asset='stuatom' THEN 'stATOM'
      WHEN raw_asset='uatom' THEN 'ATOM'
      WHEN raw_asset='uaxl' THEN 'AXL'
      WHEN raw_asset='ukuji' THEN 'KUJI'
      WHEN raw_asset='ulava' THEN 'LAVA'
      WHEN raw_asset='uluna' THEN 'LUNA'
      WHEN raw_asset='ungm' THEN 'NGM'
      WHEN raw_asset='uni-wei' THEN 'UNI'
      WHEN raw_asset='uosmo' THEN 'OSMO'
      WHEN raw_asset='usomm' THEN 'SOMM'
      WHEN raw_asset='ustrd' THEN 'STRD'
      WHEN raw_asset='utia' THEN 'TIA'
      WHEN raw_asset='uumee' THEN 'UMEE'
      WHEN raw_asset='uusd' THEN 'USTC'
      WHEN raw_asset='uusdc' THEN 'USDC'
      WHEN raw_asset='uusdt' THEN 'USDT'
      WHEN raw_asset='vela-wei' THEN 'VELA'
      WHEN raw_asset='wavax-wei' THEN 'WAVAX'
      WHEN raw_asset='wbnb-wei' THEN 'WBNB'
      WHEN raw_asset='wbtc-satoshi' THEN 'WBTC'
      WHEN raw_asset='weth-wei' THEN 'WETH'
      WHEN raw_asset='wfil-wei' THEN 'WFIL'
      WHEN raw_asset='wftm-wei' THEN 'WFTM'
      WHEN raw_asset='wglmr-wei' THEN 'WGLMR'
      WHEN raw_asset='wmai-wei' THEN 'WMAI'
      WHEN raw_asset='wmatic-wei' THEN 'WMATIC'
      WHEN raw_asset='wsteth-wei' THEN 'wstETH'
      WHEN raw_asset='yield-eth-wei' THEN 'yieldETH' 
      else raw_asset end as Token 
    FROM axelar_service)
    SELECT 
      date_trunc('{timeframe}', created_at) as Date, Token, COUNT(DISTINCT id) AS Number_of_Swaps,  ROUND(SUM(amount_usd),1) AS Volume_of_Swaps,
      COUNT(DISTINCT user) AS Number_of_Users, count(distinct (source_chain || '➡' || destination_chain)) as Number_of_Unique_Routes
      from overview
      where token in ('axlUSDC','USDC','axlUSDT','EUROC','AXLEUROC','USDT','DAI','axlDAI','PolygonUSDC','axlArbitrumUSDC',
      'AvalancheUSDC','sFRAX','FRAX','BUSD','axlBUSD','axlFRAX','axlOptimismUSDC','cUSD')
      group by 1, 2
      order by 1
    """

    return pd.read_sql(query, conn)

# --- Load data ----------------------------------------------
stablecoin_data = load_stablecoin_data(timeframe, start_date, end_date)
# ------------------------------------------------------------

col1, col2 = st.columns(2)

with col1:
    fig_stacked_volume = px.bar(
        stablecoin_data,
        x="DATE",
        y="VOLUME_OF_SWAPS",
        color="TOKEN",
        title="Volume of Swaps by Stablecoin Over Time"
    )
    fig_stacked_volume.update_layout(barmode="stack", yaxis_title="$USD", xaxis_title="")
    st.plotly_chart(fig_stacked_volume, use_container_width=True)

with col2:
    fig_stacked_txn = px.bar(
        stablecoin_data,
        x="DATE",
        y="NUMBER_OF_SWAPS",
        color="TOKEN",
        title="Number of Swaps by Stablecoin Over Time"
    )
    fig_stacked_txn.update_layout(barmode="stack", yaxis_title="Txns count", xaxis_title="")
    st.plotly_chart(fig_stacked_txn, use_container_width=True)

col3, col4 = st.columns(2)

with col3:
    fig_line_user = px.line(
        stablecoin_data,
        x="DATE",
        y="NUMBER_OF_USERS",
        color="TOKEN",
        title="Number of Swappers by Stablecoin Over Time"
    )
    fig_line_user.update_layout(yaxis_title="Wallet count", xaxis_title="")
    st.plotly_chart(fig_line_user, use_container_width=True)

with col4:
    fig_line_route = px.line(
        stablecoin_data,
        x="DATE",
        y="NUMBER_OF_UNIQUE_ROUTES",
        color="TOKEN",
        title="Number of Unique Routes by Stablecoin Over Time"
    )
    fig_line_route.update_layout(yaxis_title="Path count", xaxis_title="")
    st.plotly_chart(fig_line_route, use_container_width=True)

# --- Row 13 --------------------------------------------------------------------------------------------------------------------------------------------------------------

@st.cache_data
def load_pie_data(start_date, end_date):
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    query = f"""
    WITH overview as (
    WITH axelar_service AS (
        -- Token Transfers
        SELECT 
            created_at, 
            LOWER(data:send:original_source_chain) AS source_chain, 
            LOWER(data:send:original_destination_chain) AS destination_chain,
            recipient_address AS user, 
            CASE 
              WHEN IS_ARRAY(data:send:amount) THEN NULL
              WHEN IS_OBJECT(data:send:amount) THEN NULL
              WHEN TRY_TO_DOUBLE(data:send:amount::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:send:amount::STRING)
              ELSE NULL
            END AS amount,
            CASE 
              WHEN IS_ARRAY(data:send:amount) OR IS_ARRAY(data:link:price) THEN NULL
              WHEN IS_OBJECT(data:send:amount) OR IS_OBJECT(data:link:price) THEN NULL
              WHEN TRY_TO_DOUBLE(data:send:amount::STRING) IS NOT NULL AND TRY_TO_DOUBLE(data:link:price::STRING) IS NOT NULL 
                THEN TRY_TO_DOUBLE(data:send:amount::STRING) * TRY_TO_DOUBLE(data:link:price::STRING)
              ELSE NULL
            END AS amount_usd,
            CASE 
              WHEN IS_ARRAY(data:send:fee_value) THEN NULL
              WHEN IS_OBJECT(data:send:fee_value) THEN NULL
              WHEN TRY_TO_DOUBLE(data:send:fee_value::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:send:fee_value::STRING)
              ELSE NULL
            END AS fee,
            id, 
            'Token Transfers' AS Service, 
            data:link:asset::STRING AS raw_asset
        FROM axelar.axelscan.fact_transfers
        WHERE status = 'executed'
          AND simplified_status = 'received'
          AND (
            sender_address ilike '%0xce16F69375520ab01377ce7B88f5BA8C48F8D666%' 
            OR sender_address ilike '%0x492751eC3c57141deb205eC2da8bFcb410738630%'
            OR sender_address ilike '%0xDC3D8e1Abe590BCa428a8a2FC4CfDbD1AcF57Bd9%'
            OR sender_address ilike '%0xdf4fFDa22270c12d0b5b3788F1669D709476111E%'
            OR sender_address ilike '%0xe6B3949F9bBF168f4E3EFc82bc8FD849868CC6d8%'
          )

        UNION ALL

        -- GMP
        SELECT  
            created_at,
            data:call.chain::STRING AS source_chain,
            data:call.returnValues.destinationChain::STRING AS destination_chain,
            data:call.transaction.from::STRING AS user,
            CASE 
              WHEN IS_ARRAY(data:amount) OR IS_OBJECT(data:amount) THEN NULL
              WHEN TRY_TO_DOUBLE(data:amount::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:amount::STRING)
              ELSE NULL
            END AS amount,
            CASE 
              WHEN IS_ARRAY(data:value) OR IS_OBJECT(data:value) THEN NULL
              WHEN TRY_TO_DOUBLE(data:value::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:value::STRING)
              ELSE NULL
            END AS amount_usd,
            COALESCE(
              CASE 
                WHEN IS_ARRAY(data:gas:gas_used_amount) OR IS_OBJECT(data:gas:gas_used_amount) 
                  OR IS_ARRAY(data:gas_price_rate:source_token.token_price.usd) OR IS_OBJECT(data:gas_price_rate:source_token.token_price.usd) 
                THEN NULL
                WHEN TRY_TO_DOUBLE(data:gas:gas_used_amount::STRING) IS NOT NULL 
                  AND TRY_TO_DOUBLE(data:gas_price_rate:source_token.token_price.usd::STRING) IS NOT NULL 
                THEN TRY_TO_DOUBLE(data:gas:gas_used_amount::STRING) * TRY_TO_DOUBLE(data:gas_price_rate:source_token.token_price.usd::STRING)
                ELSE NULL
              END,
              CASE 
                WHEN IS_ARRAY(data:fees:express_fee_usd) OR IS_OBJECT(data:fees:express_fee_usd) THEN NULL
                WHEN TRY_TO_DOUBLE(data:fees:express_fee_usd::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:fees:express_fee_usd::STRING)
                ELSE NULL
              END
            ) AS fee,
            id, 
            'GMP' AS Service, 
            data:symbol::STRING AS raw_asset
        FROM axelar.axelscan.fact_gmp 
        WHERE status = 'executed'
          AND simplified_status = 'received'
          AND (
            data:approved:returnValues:contractAddress ilike '%0xce16F69375520ab01377ce7B88f5BA8C48F8D666%' 
            OR data:approved:returnValues:contractAddress ilike '%0x492751eC3c57141deb205eC2da8bFcb410738630%'
            OR data:approved:returnValues:contractAddress ilike '%0xDC3D8e1Abe590BCa428a8a2FC4CfDbD1AcF57Bd9%'
            OR data:approved:returnValues:contractAddress ilike '%0xdf4fFDa22270c12d0b5b3788F1669D709476111E%'
            OR data:approved:returnValues:contractAddress ilike '%0xe6B3949F9bBF168f4E3EFc82bc8FD849868CC6d8%'
          )
    )
    
    SELECT 
        source_chain, destination_chain, id, user, amount_usd, CASE 
      WHEN raw_asset='arb-wei' THEN 'ARB'
      WHEN raw_asset='avalanche-uusdc' THEN 'Avalanche USDC'
      WHEN raw_asset='avax-wei' THEN 'AVAX'
      WHEN raw_asset='bnb-wei' THEN 'BNB'
      WHEN raw_asset='busd-wei' THEN 'BUSD'
      WHEN raw_asset='cbeth-wei' THEN 'cbETH'
      WHEN raw_asset='cusd-wei' THEN 'cUSD'
      WHEN raw_asset='dai-wei' THEN 'DAI'
      WHEN raw_asset='dot-planck' THEN 'DOT'
      WHEN raw_asset='eeur' THEN 'EURC'
      WHEN raw_asset='ern-wei' THEN 'ERN'
      WHEN raw_asset='eth-wei' THEN 'ETH'
      WHEN raw_asset ILIKE 'factory/sei10hub%' THEN 'SEILOR'
      WHEN raw_asset='fil-wei' THEN 'FIL'
      WHEN raw_asset='frax-wei' THEN 'FRAX'
      WHEN raw_asset='ftm-wei' THEN 'FTM'
      WHEN raw_asset='glmr-wei' THEN 'GLMR'
      WHEN raw_asset='hzn-wei' THEN 'HZN'
      WHEN raw_asset='link-wei' THEN 'LINK'
      WHEN raw_asset='matic-wei' THEN 'MATIC'
      WHEN raw_asset='mkr-wei' THEN 'MKR'
      WHEN raw_asset='mpx-wei' THEN 'MPX'
      WHEN raw_asset='oath-wei' THEN 'OATH'
      WHEN raw_asset='op-wei' THEN 'OP'
      WHEN raw_asset='orbs-wei' THEN 'ORBS'
      WHEN raw_asset='factory/sei10hud5e5er4aul2l7sp2u9qp2lag5u4xf8mvyx38cnjvqhlgsrcls5qn5ke/seilor' THEN 'SEILOR'
      WHEN raw_asset='pepe-wei' THEN 'PEPE'
      WHEN raw_asset='polygon-uusdc' THEN 'Polygon USDC'
      WHEN raw_asset='reth-wei' THEN 'rETH'
      WHEN raw_asset='ring-wei' THEN 'RING'
      WHEN raw_asset='shib-wei' THEN 'SHIB'
      WHEN raw_asset='sonne-wei' THEN 'SONNE'
      WHEN raw_asset='stuatom' THEN 'stATOM'
      WHEN raw_asset='uatom' THEN 'ATOM'
      WHEN raw_asset='uaxl' THEN 'AXL'
      WHEN raw_asset='ukuji' THEN 'KUJI'
      WHEN raw_asset='ulava' THEN 'LAVA'
      WHEN raw_asset='uluna' THEN 'LUNA'
      WHEN raw_asset='ungm' THEN 'NGM'
      WHEN raw_asset='uni-wei' THEN 'UNI'
      WHEN raw_asset='uosmo' THEN 'OSMO'
      WHEN raw_asset='usomm' THEN 'SOMM'
      WHEN raw_asset='ustrd' THEN 'STRD'
      WHEN raw_asset='utia' THEN 'TIA'
      WHEN raw_asset='uumee' THEN 'UMEE'
      WHEN raw_asset='uusd' THEN 'USTC'
      WHEN raw_asset='uusdc' THEN 'USDC'
      WHEN raw_asset='uusdt' THEN 'USDT'
      WHEN raw_asset='vela-wei' THEN 'VELA'
      WHEN raw_asset='wavax-wei' THEN 'WAVAX'
      WHEN raw_asset='wbnb-wei' THEN 'WBNB'
      WHEN raw_asset='wbtc-satoshi' THEN 'WBTC'
      WHEN raw_asset='weth-wei' THEN 'WETH'
      WHEN raw_asset='wfil-wei' THEN 'WFIL'
      WHEN raw_asset='wftm-wei' THEN 'WFTM'
      WHEN raw_asset='wglmr-wei' THEN 'WGLMR'
      WHEN raw_asset='wmai-wei' THEN 'WMAI'
      WHEN raw_asset='wmatic-wei' THEN 'WMATIC'
      WHEN raw_asset='wsteth-wei' THEN 'wstETH'
      WHEN raw_asset='yield-eth-wei' THEN 'yieldETH' 
      else raw_asset end as Token
    FROM axelar_service
    WHERE created_at::date >= '{start_str}' 
      AND created_at::date <= '{end_str}')

      SELECT 
        source_chain as Source_Chain,
        COUNT(DISTINCT id) AS Swap_Count, 
        COUNT(DISTINCT user) AS Swapper_Count, 
        ROUND(SUM(amount_usd)) AS Swap_Volume
    FROM overview
    WHERE token in ('axlUSDC','USDC','axlUSDT','EUROC','AXLEUROC','USDT','DAI','axlDAI','PolygonUSDC','axlArbitrumUSDC',
      'AvalancheUSDC','sFRAX','FRAX','BUSD','axlBUSD','axlFRAX','axlOptimismUSDC','cUSD')
    GROUP BY 1
    ORDER BY 2 desc
    """

    return pd.read_sql(query, conn)

# --- Load Data ----------------------------------------------------------------------------------------------------

df_pie = load_pie_data(start_date, end_date)

# --- Layout -------------------------------------------------------------------------------------------------------
col1, col2 = st.columns(2)

# Pie Chart for Volume
fig1 = px.pie(
    df_pie, 
    values="SWAP_VOLUME",    
    names="SOURCE_CHAIN",    
    title="Swap Volume By Source Chain ($USD)"
)
fig1.update_traces(textinfo="percent+label", textposition="inside", automargin=True)

# Pie Chart for Bridges
fig2 = px.pie(
    df_pie, 
    values="SWAP_COUNT",     
    names="SOURCE_CHAIN",    
    title="Swap Count By Source Chain"
)
fig2.update_traces(textinfo="percent+label", textposition="inside", automargin=True)

# display charts
col1.plotly_chart(fig1, use_container_width=True)
col2.plotly_chart(fig2, use_container_width=True)

# --- Row 14 --------------------------------------------------------------------------------------------------------------------------------------------------------------
@st.cache_data
def load_pie_data_dest(start_date, end_date):
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")

    query = f"""
    WITH overview as (
    WITH axelar_service AS (
        -- Token Transfers
        SELECT 
            created_at, 
            LOWER(data:send:original_source_chain) AS source_chain, 
            LOWER(data:send:original_destination_chain) AS destination_chain,
            recipient_address AS user, 
            CASE 
              WHEN IS_ARRAY(data:send:amount) THEN NULL
              WHEN IS_OBJECT(data:send:amount) THEN NULL
              WHEN TRY_TO_DOUBLE(data:send:amount::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:send:amount::STRING)
              ELSE NULL
            END AS amount,
            CASE 
              WHEN IS_ARRAY(data:send:amount) OR IS_ARRAY(data:link:price) THEN NULL
              WHEN IS_OBJECT(data:send:amount) OR IS_OBJECT(data:link:price) THEN NULL
              WHEN TRY_TO_DOUBLE(data:send:amount::STRING) IS NOT NULL AND TRY_TO_DOUBLE(data:link:price::STRING) IS NOT NULL 
                THEN TRY_TO_DOUBLE(data:send:amount::STRING) * TRY_TO_DOUBLE(data:link:price::STRING)
              ELSE NULL
            END AS amount_usd,
            CASE 
              WHEN IS_ARRAY(data:send:fee_value) THEN NULL
              WHEN IS_OBJECT(data:send:fee_value) THEN NULL
              WHEN TRY_TO_DOUBLE(data:send:fee_value::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:send:fee_value::STRING)
              ELSE NULL
            END AS fee,
            id, 
            'Token Transfers' AS Service, 
            data:link:asset::STRING AS raw_asset
        FROM axelar.axelscan.fact_transfers
        WHERE status = 'executed'
          AND simplified_status = 'received'
          AND (
            sender_address ilike '%0xce16F69375520ab01377ce7B88f5BA8C48F8D666%' 
            OR sender_address ilike '%0x492751eC3c57141deb205eC2da8bFcb410738630%'
            OR sender_address ilike '%0xDC3D8e1Abe590BCa428a8a2FC4CfDbD1AcF57Bd9%'
            OR sender_address ilike '%0xdf4fFDa22270c12d0b5b3788F1669D709476111E%'
            OR sender_address ilike '%0xe6B3949F9bBF168f4E3EFc82bc8FD849868CC6d8%'
          )

        UNION ALL

        -- GMP
        SELECT  
            created_at,
            data:call.chain::STRING AS source_chain,
            data:call.returnValues.destinationChain::STRING AS destination_chain,
            data:call.transaction.from::STRING AS user,
            CASE 
              WHEN IS_ARRAY(data:amount) OR IS_OBJECT(data:amount) THEN NULL
              WHEN TRY_TO_DOUBLE(data:amount::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:amount::STRING)
              ELSE NULL
            END AS amount,
            CASE 
              WHEN IS_ARRAY(data:value) OR IS_OBJECT(data:value) THEN NULL
              WHEN TRY_TO_DOUBLE(data:value::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:value::STRING)
              ELSE NULL
            END AS amount_usd,
            COALESCE(
              CASE 
                WHEN IS_ARRAY(data:gas:gas_used_amount) OR IS_OBJECT(data:gas:gas_used_amount) 
                  OR IS_ARRAY(data:gas_price_rate:source_token.token_price.usd) OR IS_OBJECT(data:gas_price_rate:source_token.token_price.usd) 
                THEN NULL
                WHEN TRY_TO_DOUBLE(data:gas:gas_used_amount::STRING) IS NOT NULL 
                  AND TRY_TO_DOUBLE(data:gas_price_rate:source_token.token_price.usd::STRING) IS NOT NULL 
                THEN TRY_TO_DOUBLE(data:gas:gas_used_amount::STRING) * TRY_TO_DOUBLE(data:gas_price_rate:source_token.token_price.usd::STRING)
                ELSE NULL
              END,
              CASE 
                WHEN IS_ARRAY(data:fees:express_fee_usd) OR IS_OBJECT(data:fees:express_fee_usd) THEN NULL
                WHEN TRY_TO_DOUBLE(data:fees:express_fee_usd::STRING) IS NOT NULL THEN TRY_TO_DOUBLE(data:fees:express_fee_usd::STRING)
                ELSE NULL
              END
            ) AS fee,
            id, 
            'GMP' AS Service, 
            data:symbol::STRING AS raw_asset
        FROM axelar.axelscan.fact_gmp 
        WHERE status = 'executed'
          AND simplified_status = 'received'
          AND (
            data:approved:returnValues:contractAddress ilike '%0xce16F69375520ab01377ce7B88f5BA8C48F8D666%' 
            OR data:approved:returnValues:contractAddress ilike '%0x492751eC3c57141deb205eC2da8bFcb410738630%'
            OR data:approved:returnValues:contractAddress ilike '%0xDC3D8e1Abe590BCa428a8a2FC4CfDbD1AcF57Bd9%'
            OR data:approved:returnValues:contractAddress ilike '%0xdf4fFDa22270c12d0b5b3788F1669D709476111E%'
            OR data:approved:returnValues:contractAddress ilike '%0xe6B3949F9bBF168f4E3EFc82bc8FD849868CC6d8%'
          )
    )
    
    SELECT 
        source_chain, destination_chain, id, user, amount_usd, CASE 
      WHEN raw_asset='arb-wei' THEN 'ARB'
      WHEN raw_asset='avalanche-uusdc' THEN 'Avalanche USDC'
      WHEN raw_asset='avax-wei' THEN 'AVAX'
      WHEN raw_asset='bnb-wei' THEN 'BNB'
      WHEN raw_asset='busd-wei' THEN 'BUSD'
      WHEN raw_asset='cbeth-wei' THEN 'cbETH'
      WHEN raw_asset='cusd-wei' THEN 'cUSD'
      WHEN raw_asset='dai-wei' THEN 'DAI'
      WHEN raw_asset='dot-planck' THEN 'DOT'
      WHEN raw_asset='eeur' THEN 'EURC'
      WHEN raw_asset='ern-wei' THEN 'ERN'
      WHEN raw_asset='eth-wei' THEN 'ETH'
      WHEN raw_asset ILIKE 'factory/sei10hub%' THEN 'SEILOR'
      WHEN raw_asset='fil-wei' THEN 'FIL'
      WHEN raw_asset='frax-wei' THEN 'FRAX'
      WHEN raw_asset='ftm-wei' THEN 'FTM'
      WHEN raw_asset='glmr-wei' THEN 'GLMR'
      WHEN raw_asset='hzn-wei' THEN 'HZN'
      WHEN raw_asset='link-wei' THEN 'LINK'
      WHEN raw_asset='matic-wei' THEN 'MATIC'
      WHEN raw_asset='mkr-wei' THEN 'MKR'
      WHEN raw_asset='mpx-wei' THEN 'MPX'
      WHEN raw_asset='oath-wei' THEN 'OATH'
      WHEN raw_asset='op-wei' THEN 'OP'
      WHEN raw_asset='orbs-wei' THEN 'ORBS'
      WHEN raw_asset='factory/sei10hud5e5er4aul2l7sp2u9qp2lag5u4xf8mvyx38cnjvqhlgsrcls5qn5ke/seilor' THEN 'SEILOR'
      WHEN raw_asset='pepe-wei' THEN 'PEPE'
      WHEN raw_asset='polygon-uusdc' THEN 'Polygon USDC'
      WHEN raw_asset='reth-wei' THEN 'rETH'
      WHEN raw_asset='ring-wei' THEN 'RING'
      WHEN raw_asset='shib-wei' THEN 'SHIB'
      WHEN raw_asset='sonne-wei' THEN 'SONNE'
      WHEN raw_asset='stuatom' THEN 'stATOM'
      WHEN raw_asset='uatom' THEN 'ATOM'
      WHEN raw_asset='uaxl' THEN 'AXL'
      WHEN raw_asset='ukuji' THEN 'KUJI'
      WHEN raw_asset='ulava' THEN 'LAVA'
      WHEN raw_asset='uluna' THEN 'LUNA'
      WHEN raw_asset='ungm' THEN 'NGM'
      WHEN raw_asset='uni-wei' THEN 'UNI'
      WHEN raw_asset='uosmo' THEN 'OSMO'
      WHEN raw_asset='usomm' THEN 'SOMM'
      WHEN raw_asset='ustrd' THEN 'STRD'
      WHEN raw_asset='utia' THEN 'TIA'
      WHEN raw_asset='uumee' THEN 'UMEE'
      WHEN raw_asset='uusd' THEN 'USTC'
      WHEN raw_asset='uusdc' THEN 'USDC'
      WHEN raw_asset='uusdt' THEN 'USDT'
      WHEN raw_asset='vela-wei' THEN 'VELA'
      WHEN raw_asset='wavax-wei' THEN 'WAVAX'
      WHEN raw_asset='wbnb-wei' THEN 'WBNB'
      WHEN raw_asset='wbtc-satoshi' THEN 'WBTC'
      WHEN raw_asset='weth-wei' THEN 'WETH'
      WHEN raw_asset='wfil-wei' THEN 'WFIL'
      WHEN raw_asset='wftm-wei' THEN 'WFTM'
      WHEN raw_asset='wglmr-wei' THEN 'WGLMR'
      WHEN raw_asset='wmai-wei' THEN 'WMAI'
      WHEN raw_asset='wmatic-wei' THEN 'WMATIC'
      WHEN raw_asset='wsteth-wei' THEN 'wstETH'
      WHEN raw_asset='yield-eth-wei' THEN 'yieldETH' 
      else raw_asset end as Token
    FROM axelar_service
    WHERE created_at::date >= '{start_str}' 
      AND created_at::date <= '{end_str}')

      SELECT 
        destination_chain,
        COUNT(DISTINCT id) AS Swap_Count, 
        COUNT(DISTINCT user) AS Swapper_Count, 
        ROUND(SUM(amount_usd)) AS Swap_Volume
    FROM overview
    WHERE token in ('axlUSDC','USDC','axlUSDT','EUROC','AXLEUROC','USDT','DAI','axlDAI','PolygonUSDC','axlArbitrumUSDC',
      'AvalancheUSDC','sFRAX','FRAX','BUSD','axlBUSD','axlFRAX','axlOptimismUSDC','cUSD')
    GROUP BY 1
    ORDER BY 2 desc
    """

    return pd.read_sql(query, conn)

# --- Load Data ----------------------------------------------------------------------------------------------------

df_pie_dest = load_pie_data_dest(start_date, end_date)

# --- Layout -------------------------------------------------------------------------------------------------------
col1, col2 = st.columns(2)

# Pie Chart for Volume
fig1 = px.pie(
    df_pie_dest, 
    values="SWAP_VOLUME",    
    names="DESTINATION_CHAIN",    
    title="Swap Volume By Destination Chain ($USD)"
)
fig1.update_traces(textinfo="percent+label", textposition="inside", automargin=True)

# Pie Chart for Bridges
fig2 = px.pie(
    df_pie_dest, 
    values="SWAP_COUNT",     
    names="DESTINATION_CHAIN",    
    title="Swap Count By Destination Chain"
)
fig2.update_traces(textinfo="percent+label", textposition="inside", automargin=True)

# display charts
col1.plotly_chart(fig1, use_container_width=True)
col2.plotly_chart(fig2, use_container_width=True)

# --- Reference and Rebuild Info --------------------------------------------------------------------------------------
st.markdown(
    """
    <div style="margin-top: 20px; margin-bottom: 20px; font-size: 16px;">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
            <img src="https://cdn-icons-png.flaticon.com/512/3178/3178287.png" alt="Reference" style="width:20px; height:20px;">
            <span>Dashboard Reference (Some of the code and charts were modified and rewritten): <a href="https://flipsidecrypto.xyz/Saleh/squid-router-edCgEI" target="_blank">https://flipsidecrypto.xyz/Saleh/squid-router-edCgEI/</a></span>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="https://pbs.twimg.com/profile_images/1856738793325268992/OouKI10c_400x400.jpg" alt="Flipside" style="width:25px; height:25px; border-radius: 50%;">
            <span>Data Powered by: <a href="https://flipsidecrypto.xyz/home/" target="_blank">Flipside</a></span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Links with Logos ---------------------------------------------------------------------------------------
st.markdown(
    """
    <div style="font-size: 16px;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="https://axelarscan.io/logos/logo.png" alt="Axelar" style="width:20px; height:20px;">
            <a href="https://www.axelar.network/" target="_blank">Axelar Website</a>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="https://axelarscan.io/logos/logo.png" alt="X" style="width:20px; height:20px;">
            <a href="https://x.com/axelar" target="_blank">Axelar X Account</a>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="https://img.cryptorank.io/coins/squid1675241862798.png" alt="squid" style="width:20px; height:20px;">
            <a href="https://www.squidrouter.com/" target="_blank">Squid Website</a>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
            <img src="https://img.cryptorank.io/coins/squid1675241862798.png" alt="squid" style="width:20px; height:20px;">
            <a href="https://x.com/squidrouter" target="_blank">Squid X Account</a>
        </div>
        
    </div>
    """,
    unsafe_allow_html=True
)
