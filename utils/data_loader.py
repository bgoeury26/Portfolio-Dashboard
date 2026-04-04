import pandas as pd
import streamlit as st


EXPECTED_IBKR_COLUMNS = [
    "CurrencyPrimary",
    "AssetClass",
    "SubCategory",
    "Symbol",
    "Description",
    "ISIN",
    "UnderlyingSymbol",
    "Quantity",
    "PositionValue",
    "PercentOfNAV",
    "OpenDateTime",
    "HoldingPeriodDateTime",
    "Weight",
    "MarkPrice",
    "CostBasisPrice",
    "CostBasisMoney",
    "FifoPnlUnrealized",
]


def load_ibkr_positions(file):
    df = pd.read_csv(file)

    missing_cols = [col for col in EXPECTED_IBKR_COLUMNS if col not in df.columns]
    if missing_cols:
        st.error("CSV missing required columns: " + ", ".join(missing_cols))
        st.stop()

    df = df.copy()

    numeric_cols = [
        "Quantity",
        "PositionValue",
        "PercentOfNAV",
        "Weight",
        "MarkPrice",
        "CostBasisPrice",
        "CostBasisMoney",
        "FifoPnlUnrealized",
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["sector"] = map_sector(df["Description"], df["SubCategory"], df["AssetClass"])
    df["PnLPercent"] = ((df["PositionValue"] - df["CostBasisMoney"]) / df["CostBasisMoney"]) * 100
    df["PnLPercent"] = df["PnLPercent"].replace([float("inf"), float("-inf")], pd.NA)

    df = df[df["PositionValue"].fillna(0) > 0].copy()
    df = df.sort_values("PositionValue", ascending=False)

    return df


def map_sector(description_series, subcategory_series, assetclass_series):
    desc = description_series.fillna("").str.lower()
    subcat = subcategory_series.fillna("").str.lower()
    asset = assetclass_series.fillna("").str.lower()

    sector = pd.Series("Other", index=description_series.index)

    sector = sector.mask(subcat.str.contains("etf", regex=True), "ETF")
    sector = sector.mask(asset.str.contains("cash", regex=True), "Cash")
    sector = sector.mask(desc.str.contains("software|semiconductor|tech|cloud|ai|comput"), "Technology")
    sector = sector.mask(desc.str.contains("bank|financial|insurance|capital|finserv"), "Financials")
    sector = sector.mask(desc.str.contains("energy|oil|gas|uranium|nuclear"), "Energy")
    sector = sector.mask(desc.str.contains("health|pharma|bio|therapeutics|medical|oncology"), "Healthcare")
    sector = sector.mask(desc.str.contains("silver|gold|mining|minerals"), "Materials")
    sector = sector.mask(desc.str.contains("reit|real estate|property"), "Real Estate")
    sector = sector.mask(desc.str.contains("aerospace|defense|defc"), "Industrials")
    sector = sector.mask(desc.str.contains("bitcoin|crypto"), "Digital Assets")

    return sector
