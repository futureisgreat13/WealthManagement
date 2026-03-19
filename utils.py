import json
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

DATA_DIR = Path(__file__).parent / "data"
USERS_DIR = DATA_DIR / "users"
TEMPLATE_DIR = DATA_DIR / "_template"

ASSET_CLASSES = [
    "Equity", "REITs", "Real Estate",
    "Private Equity", "Funds", "Business", "Bonds",
    "Precious Metals", "Cash", "Debt"
]

LIQUID = {"Equity", "REITs", "Bonds", "Precious Metals", "Cash"}
ILLIQUID = {"Private Equity", "Real Estate", "Funds", "Business", "Debt"}

SCENARIOS = ["Super Bear", "Bear", "Base", "Bull"]
SCENARIO_KEYS = {
    "Super Bear": "super_bear",
    "Bear": "bear",
    "Base": "base",
    "Bull": "bull"
}

CURRENCIES = ["EUR", "USD", "GBP", "INR", "HKD", "JPY", "CAD", "AUD", "CHF"]

CURRENT_YEAR = datetime.now().year


def fmt_eur(value: float) -> str:
    """Format EUR values: <1K exact, <1M as K, >=1M as M."""
    abs_val = abs(value)
    sign = "-" if value < 0 else ""
    if abs_val >= 1_000_000:
        return f"{sign}\u20ac{abs_val / 1_000_000:,.1f}M"
    elif abs_val >= 1_000:
        return f"{sign}\u20ac{abs_val / 1_000:,.0f}K"
    return f"{sign}\u20ac{abs_val:,.0f}"


def fmt_eur_short(value) -> str:
    """Format for dataframe columns - K/M notation."""
    if value is None or (isinstance(value, float) and value != value):  # NaN check
        return ""
    value = float(value)
    abs_val = abs(value)
    sign = "-" if value < 0 else ""
    if abs_val >= 1_000_000:
        return f"{sign}€{abs_val / 1_000_000:,.1f}M"
    elif abs_val >= 1_000:
        return f"{sign}€{abs_val / 1_000:,.0f}K"
    elif abs_val > 0:
        return f"{sign}€{abs_val:,.0f}"
    return "€0"


def fmt_pct(value: float) -> str:
    return f"{value:.1f}%"


def color_negative(value: float, formatted: str) -> str:
    if value < 0:
        return f"<span style='color:#FF4444'>{formatted}</span>"
    return formatted


# ---------------------------------------------------------------------------
# Bloomberg Theme
# ---------------------------------------------------------------------------

# Color constants
BG_BLACK = "#000000"
BG_PANEL = "#0a0a0a"
BG_HEADER = "#0d0d0d"
BG_HOVER = "#111111"
BORDER = "#1a1a1a"
GRID_LINE = "#111111"
C_ORANGE = "#FF8C00"     # Bloomberg orange (headers, accents)
C_GREEN = "#00FF88"      # Positive numbers
C_RED = "#FF4444"        # Negative numbers
C_NEUTRAL = "#D4D4D4"    # Neutral numbers
C_LABEL = "#AAAAAA"      # Labels, secondary text
C_AMBER = "#FF6600"      # Dark orange accent/hover
C_GOLD = "#FFD700"       # Manual input highlight
BG_INPUT = "#3d3200"     # Yellow-tinted bg for user-input cells
BG_IBKR = "#1a2744"      # Blue-tinted bg for IBKR-imported cells
C_IBKR = "#60a5fa"       # Light blue text for IBKR cells


def inject_bloomberg_css():
    """Inject global Bloomberg terminal CSS. Call once per page."""
    st.markdown(f"""<style>
    /* ── Global background ── */
    .stApp, [data-testid="stAppViewContainer"],
    [data-testid="stHeader"], header,
    [data-testid="stSidebar"], [data-testid="stSidebarContent"],
    section[data-testid="stSidebar"] > div {{
        background-color: {BG_BLACK} !important;
    }}
    [data-testid="stSidebar"] {{
        border-right: 1px solid {BORDER} !important;
    }}
    /* ── Sidebar nav ── */
    [data-testid="stSidebarNavLink"] {{
        padding: 2px 8px !important;
        font-size: 0.85rem !important;
    }}
    [data-testid="stSidebarNavLink"]:hover {{
        background-color: {BG_HOVER} !important;
    }}
    [data-testid="stSidebarNavSeparator"] {{
        margin: 2px 0 !important;
    }}
    /* ── Metrics compact ── */
    div[data-testid="stMetric"] {{
        padding: 4px 0 !important;
    }}
    div[data-testid="stMetric"] label {{
        color: {C_LABEL} !important;
        font-size: 0.75rem !important;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }}
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
        color: {C_ORANGE} !important;
        font-size: 1.3rem !important;
        font-weight: 600 !important;
    }}
    div[data-testid="stMetric"] [data-testid="stMetricDelta"] {{
        font-size: 0.7rem !important;
    }}
    /* ── DataFrames & DataEditors ── */
    div.stDataFrame, div[data-testid="stDataEditor"],
    div[data-testid="stDataFrame"] {{
        background: {BG_BLACK} !important;
        border: 1px solid {BORDER} !important;
        border-radius: 2px !important;
        padding: 0 !important;
    }}
    /* ── Expanders ── */
    div[data-testid="stExpander"] summary {{
        padding: 2px 0 !important;
        font-size: 0.85rem !important;
        color: {C_LABEL} !important;
    }}
    /* ── Headings ── */
    h1, h2, h3 {{
        color: {C_ORANGE} !important;
        font-weight: 600 !important;
    }}
    h1 {{ font-size: 1.5rem !important; margin-bottom: 0.3rem !important; }}
    h2 {{ font-size: 1.15rem !important; margin-top: 0.5rem !important; margin-bottom: 0.2rem !important; }}
    h3 {{ font-size: 0.95rem !important; }}
    /* ── Tabs ── */
    button[data-baseweb="tab"] {{
        color: {C_LABEL} !important;
        font-size: 0.8rem !important;
        padding: 4px 12px !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: {C_ORANGE} !important;
    }}
    /* ── Buttons ── */
    button[data-testid="stBaseButton-primary"] {{
        background-color: {C_ORANGE} !important;
        color: {BG_BLACK} !important;
        border: none !important;
        font-weight: 600 !important;
        font-size: 0.8rem !important;
        padding: 4px 16px !important;
    }}
    /* ── Dividers ── */
    hr {{
        border-color: {BORDER} !important;
        margin: 4px 0 !important;
    }}
    /* ── Reduce overall padding/margins ── */
    .block-container {{
        padding-top: 1rem !important;
        padding-bottom: 0 !important;
    }}
    [data-testid="stVerticalBlock"] > div {{
        gap: 0.3rem !important;
    }}
    /* ── Selectbox / multiselect compact ── */
    div[data-baseweb="select"] {{
        font-size: 0.8rem !important;
    }}
    /* ── Captions ── */
    .stCaption, [data-testid="stCaptionContainer"] {{
        font-size: 0.7rem !important;
        color: #666 !important;
    }}
    </style>""", unsafe_allow_html=True)


def bloomberg_chart_layout(**overrides):
    """Return a Plotly layout dict with Bloomberg terminal styling."""
    layout = dict(
        template="plotly_dark",
        paper_bgcolor=BG_BLACK,
        plot_bgcolor=BG_BLACK,
        font=dict(family="Consolas, monospace", size=11, color=C_LABEL),
        title="",
        title_font=dict(color=C_ORANGE, size=13),
        xaxis=dict(
            gridcolor=GRID_LINE, zerolinecolor=BORDER,
            tickfont=dict(size=10, color=C_LABEL),
        ),
        yaxis=dict(
            gridcolor=GRID_LINE, zerolinecolor=BORDER,
            tickfont=dict(size=10, color=C_LABEL), tickformat=",.0f",
        ),
        legend=dict(
            font=dict(size=10, color=C_LABEL),
            bgcolor="rgba(0,0,0,0)", borderwidth=0,
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
        ),
        margin=dict(l=50, r=10, t=30, b=30),
        hovermode="x unified",
    )
    layout.update(overrides)
    return layout


# ---------------------------------------------------------------------------
# AG-Grid display helper
# ---------------------------------------------------------------------------

def _eur_formatter_js():
    """JS valueFormatter that formats numbers as €1.2K / €3.4M / €5.6B etc."""
    return JsCode("""
        function(params) {
            if (params.value == null || params.value === '' || isNaN(params.value)) return params.value || '';
            var v = Number(params.value);
            if (v === 0) return '';
            var neg = v < 0;
            var abs = Math.abs(v);
            var formatted;
            if (abs >= 1e9) formatted = '€' + (abs / 1e9).toFixed(1) + 'B';
            else if (abs >= 1e6) formatted = '€' + (abs / 1e6).toFixed(1) + 'M';
            else if (abs >= 1e3) formatted = '€' + (abs / 1e3).toFixed(0) + 'K';
            else formatted = '€' + abs.toFixed(0);
            return neg ? '-' + formatted : formatted;
        }
    """)


def _pct_formatter_js():
    """JS valueFormatter that formats numbers as percentages (e.g. 12.2%)."""
    return JsCode("""
        function(params) {
            if (params.value == null || params.value === '' || isNaN(params.value)) return params.value || '';
            var v = Number(params.value);
            if (v === 0) return '\u2014';
            return v.toFixed(1) + '%';
        }
    """)


def render_aggrid_table(df, key: str, height: int = 400, cell_style_map: dict = None,
                        numeric_cols: list = None, highlight_total_row: bool = False,
                        bg_style_map: dict = None, formula_map: dict = None, **kwargs):
    """Render a DataFrame using AG-Grid with cell range selection and status bar.

    Features:
    - Cell range selection (select cells across columns)
    - Status bar showing sum, average, count of selected cells
    - Dark theme matching the app
    - Sortable/filterable columns
    - Optional cell_style_map for formula vs input color coding
    - Optional numeric_cols: columns to treat as numeric (enables SUM in status bar)
    - Optional bg_style_map for background colors: {col: {row_idx: "#hex_color" or None}}
    - Optional formula_map for hover tooltips: {col: {row_idx: "=formula"}}

    Args:
        cell_style_map: Maps column names to dicts of {row_index: cell_type}.
            cell_type can be "formula" (default text color) or "input" (gold/yellow).
        numeric_cols: List of column names that contain numeric data.
            These columns will display with € formatting and support SUM aggregation.
        bg_style_map: Maps column names to dicts of {row_index: hex_color_string}.
            Sets background color for specific cells. Merged with cell_style_map if both exist.
        formula_map: Maps column names to dicts of {row_index: formula_string}.
            Shows formula as tooltip on hover for cells with stored formulas.
    """
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(
        sortable=True,
        filterable=True,
        resizable=True,
        minWidth=65,
    )
    # Pin and widen the first column if it's a label column
    first_col = df.columns[0] if len(df.columns) > 0 else None
    if first_col and df[first_col].dtype == object:
        gb.configure_column(first_col, pinned="left", minWidth=130, maxWidth=200)

    # Build combined cell style JS for each column
    def _build_cell_style_js(col):
        """Build a JsCode cellStyle function combining text color (cell_style_map) and bg color (bg_style_map)."""
        parts = []
        # Text color from cell_style_map (yellow for "input" rows)
        if cell_style_map and col in cell_style_map:
            input_rows = [f'"{idx}"' for idx, stype in cell_style_map[col].items() if stype == "input"]
            if input_rows:
                parts.append(f"var inputRows = new Set([{','.join(input_rows)}]);")
                parts.append("if (inputRows.has(String(params.node.rowIndex))) { style['color'] = '#FFD700'; }")
        # Background color from bg_style_map
        if bg_style_map and col in bg_style_map:
            bg_entries = [(f'"{idx}"', color) for idx, color in bg_style_map[col].items() if color]
            if bg_entries:
                bg_map_str = ",".join(f'{idx}: "{color}"' for idx, color in bg_entries)
                parts.append(f"var bgMap = {{{bg_map_str}}};")
                parts.append("var bg = bgMap[String(params.node.rowIndex)]; if (bg) { style['backgroundColor'] = bg; }")
        if not parts:
            return None
        js_body = "var style = {};\n" + "\n".join(parts) + "\nreturn Object.keys(style).length > 0 ? style : null;"
        return JsCode(f"function(params) {{ {js_body} }}")

    # Build tooltip JS for columns with formula_map
    def _build_tooltip_js(col):
        """Build a JsCode tooltipValueGetter that shows stored formula on hover."""
        if not formula_map or col not in formula_map:
            return None
        entries = formula_map[col]
        if not entries:
            return None
        map_str = ",".join(f'"{idx}": "{formula}"' for idx, formula in entries.items())
        return JsCode(f"""function(params) {{
            var fmap = {{{map_str}}};
            var f = fmap[String(params.node.rowIndex)];
            return f ? f : null;
        }}""")

    # Configure numeric columns with EUR formatter for proper SUM support
    eur_fmt = _eur_formatter_js()
    if numeric_cols:
        for col in numeric_cols:
            if col in df.columns:
                col_config = {"valueFormatter": eur_fmt, "type": ["numericColumn"]}
                cell_style_js = _build_cell_style_js(col)
                if cell_style_js:
                    col_config["cellStyle"] = cell_style_js
                tooltip_js = _build_tooltip_js(col)
                if tooltip_js:
                    col_config["tooltipValueGetter"] = tooltip_js
                gb.configure_column(col, **col_config)

    # Apply cell styles for non-numeric columns
    all_styled_cols = set()
    if cell_style_map:
        all_styled_cols.update(cell_style_map.keys())
    if bg_style_map:
        all_styled_cols.update(bg_style_map.keys())
    if formula_map:
        all_styled_cols.update(formula_map.keys())
    for col in all_styled_cols:
        if col in df.columns and (not numeric_cols or col not in numeric_cols):
            col_config = {}
            cell_style_js = _build_cell_style_js(col)
            if cell_style_js:
                col_config["cellStyle"] = cell_style_js
            tooltip_js = _build_tooltip_js(col)
            if tooltip_js:
                col_config["tooltipValueGetter"] = tooltip_js
            if col_config:
                gb.configure_column(col, **col_config)

    grid_opts = {
        "enableRangeSelection": True,
        "tooltipShowDelay": 300,
        "statusBar": {
            "statusPanels": [
                {"statusPanel": "agTotalAndFilteredRowCountComponent", "align": "left"},
                {"statusPanel": "agAggregationComponent", "align": "right"},
            ]
        },
    }
    if highlight_total_row:
        grid_opts["getRowStyle"] = JsCode(f"""
            function(params) {{
                if (params.data && (params.data['Asset Class'] === 'TOTAL' || params.data['Name'] === 'TOTAL')) {{
                    return {{'fontWeight': 'bold', 'backgroundColor': '{BG_HEADER}', 'borderTop': '1px solid {C_ORANGE}', 'color': '{C_ORANGE}'}};
                }}
                return null;
            }}
        """)
    gb.configure_grid_options(**grid_opts)

    grid_options = gb.build()

    custom_css = {
        ".ag-root-wrapper": {
            "background-color": f"{BG_BLACK} !important",
            "border": f"1px solid {BORDER} !important",
            "border-radius": "0 !important",
            "font-size": "12px !important",
        },
        ".ag-header": {
            "background-color": f"{BG_HEADER} !important",
            "border-bottom": f"1px solid {C_ORANGE}33 !important",
            "min-height": "28px !important",
            "height": "28px !important",
        },
        ".ag-header-cell": {
            "padding": "0 6px !important",
        },
        ".ag-header-cell-label": {
            "color": f"{C_ORANGE} !important",
            "font-size": "11px !important",
            "font-weight": "600 !important",
            "letter-spacing": "0.3px !important",
        },
        ".ag-row": {
            "background-color": f"{BG_BLACK} !important",
            "color": f"{C_NEUTRAL} !important",
            "border-bottom": f"1px solid {GRID_LINE} !important",
            "font-size": "12px !important",
            "height": "26px !important",
        },
        ".ag-row-hover": {
            "background-color": f"{BG_HOVER} !important",
        },
        ".ag-cell": {
            "padding": "0 6px !important",
            "line-height": "26px !important",
        },
        ".ag-range-selection": {
            "background-color": "rgba(255, 140, 0, 0.15) !important",
            "border": f"1px solid {C_ORANGE} !important",
        },
        ".ag-status-bar": {
            "background-color": f"{BG_HEADER} !important",
            "color": f"{C_LABEL} !important",
            "border-top": f"1px solid {BORDER} !important",
            "font-size": "11px !important",
            "min-height": "24px !important",
        },
        ".ag-status-bar-part": {
            "color": f"{C_LABEL} !important",
        },
        ".ag-pinned-left-cols-container .ag-cell": {
            "color": f"{C_LABEL} !important",
            "font-weight": "500 !important",
        },
    }

    return AgGrid(
        df,
        gridOptions=grid_options,
        height=height,
        theme="streamlit",
        custom_css=custom_css,
        update_mode=GridUpdateMode.NO_UPDATE,
        enable_enterprise_modules=True,
        allow_unsafe_jscode=True,
        key=key,
        **kwargs,
    )


def render_editable_aggrid_table(df, key: str, height: int = 400,
                                 editable_cols: list = None,
                                 cell_style_map: dict = None,
                                 numeric_cols: list = None,
                                 highlight_total_row: bool = False,
                                 bg_style_map: dict = None,
                                 formula_map: dict = None,
                                 editor_key: str = None,
                                 formatter_js=None,
                                 **kwargs):
    """Render an editable DataFrame using AG-Grid.

    Like render_aggrid_table but with editable columns and formula support.
    Editable columns accept formula strings (e.g., =500*2) — on save,
    process_math_in_df() evaluates them. Tooltips show stored formulas on hover.
    Double-click a cell to edit; if a formula exists it's shown in edit mode.

    Args:
        editable_cols: Column names that are editable. Others are read-only.
        editor_key: Key for formula persistence in formulas.json.
        (other args same as render_aggrid_table)

    Returns:
        AgGrid result object. Access .data for the edited DataFrame.
    """
    import pandas as pd
    editable_cols = editable_cols or []

    # Build a formula lookup for JS-side: {col: {row_idx: "=formula"}}
    # This drives both tooltips AND edit-mode formula display
    formulas_js = {}
    if editor_key:
        stored = load_json(DATA_DIR / "formulas.json", {})
        for col in editable_cols:
            col_formulas = {}
            for row_idx in range(len(df)):
                fkey = f"{editor_key}::{row_idx}::{col}"
                if fkey in stored:
                    col_formulas[str(row_idx)] = stored[fkey]
            if col_formulas:
                formulas_js[col] = col_formulas

    # Merge editor_key formulas into formula_map for tooltips
    if formula_map is None:
        formula_map = {}
    for col, fmap in formulas_js.items():
        if col not in formula_map:
            formula_map[col] = {}
        for idx, f in fmap.items():
            formula_map[col][int(idx)] = f

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(
        sortable=True, filterable=True, resizable=True, minWidth=65,
    )

    first_col = df.columns[0] if len(df.columns) > 0 else None
    if first_col and df[first_col].dtype == object:
        gb.configure_column(first_col, pinned="left", minWidth=130, maxWidth=200)

    # --- Cell style JS builder (same as render_aggrid_table) ---
    def _build_cell_style_js(col):
        parts = []
        if cell_style_map and col in cell_style_map:
            input_rows = [f'"{idx}"' for idx, stype in cell_style_map[col].items() if stype == "input"]
            ibkr_rows = [f'"{idx}"' for idx, stype in cell_style_map[col].items() if stype == "ibkr"]
            if input_rows:
                parts.append(f"var inputRows = new Set([{','.join(input_rows)}]);")
                parts.append(f"if (inputRows.has(String(params.node.rowIndex))) {{ style['color'] = '{C_GOLD}'; }}")
            if ibkr_rows:
                parts.append(f"var ibkrRows = new Set([{','.join(ibkr_rows)}]);")
                parts.append(f"if (ibkrRows.has(String(params.node.rowIndex))) {{ style['color'] = '{C_IBKR}'; }}")
        if bg_style_map and col in bg_style_map:
            bg_entries = [(f'"{idx}"', color) for idx, color in bg_style_map[col].items() if color]
            if bg_entries:
                bg_map_str = ",".join(f'{idx}: "{color}"' for idx, color in bg_entries)
                parts.append(f"var bgMap = {{{bg_map_str}}};")
                parts.append("var bg = bgMap[String(params.node.rowIndex)]; if (bg) { style['backgroundColor'] = bg; }")
        if not parts:
            return None
        js_body = "var style = {};\n" + "\n".join(parts) + "\nreturn Object.keys(style).length > 0 ? style : null;"
        return JsCode(f"function(params) {{ {js_body} }}")

    def _build_tooltip_js(col):
        if not formula_map or col not in formula_map:
            return None
        entries = formula_map[col]
        if not entries:
            return None
        map_str = ",".join(f'"{idx}": "{formula}"' for idx, formula in entries.items())
        return JsCode(f"""function(params) {{
            var fmap = {{{map_str}}};
            var f = fmap[String(params.node.rowIndex)];
            return f ? f : null;
        }}""")

    # --- Configure columns ---
    eur_fmt = formatter_js if formatter_js else _eur_formatter_js()

    for col in df.columns:
        col_config = {}
        is_editable = col in editable_cols
        is_numeric = numeric_cols and col in numeric_cols

        if is_editable:
            col_config["editable"] = True
            col_config["suppressMenu"] = True
            col_config["suppressHeaderMenuButton"] = True
            col_config["sortable"] = False

        if is_numeric:
            col_config["valueFormatter"] = eur_fmt
            # Don't set type=numericColumn for editable cols — allows formula string input
            if not is_editable:
                col_config["type"] = ["numericColumn"]

        cell_style_js = _build_cell_style_js(col)
        if cell_style_js:
            col_config["cellStyle"] = cell_style_js

        tooltip_js = _build_tooltip_js(col)
        if tooltip_js:
            col_config["tooltipValueGetter"] = tooltip_js

        # For editable columns with formulas: show formula on double-click
        if is_editable and col in formulas_js and formulas_js[col]:
            fmap_entries = formulas_js[col]
            fmap_str = ",".join(f'"{k}": "{v}"' for k, v in fmap_entries.items())
            col_config["valueGetter"] = JsCode(f"""function(params) {{
                return params.data['{col}'];
            }}""")
            col_config["valueSetter"] = JsCode(f"""function(params) {{
                params.data['{col}'] = params.newValue;
                return true;
            }}""")
            # Use valueFormatter that shows formula in edit mode
            col_config["valueFormatter"] = JsCode(f"""function(params) {{
                if (params.value == null || params.value === '') return '';
                var v = params.value;
                if (typeof v === 'string' && (v.indexOf('=') === 0 || isNaN(v))) return v;
                v = Number(v);
                if (isNaN(v) || v === 0) return v === 0 ? '' : String(params.value);
                var neg = v < 0;
                var abs = Math.abs(v);
                var formatted;
                if (abs >= 1e9) formatted = '\\u20AC' + (abs / 1e9).toFixed(1) + 'B';
                else if (abs >= 1e6) formatted = '\\u20AC' + (abs / 1e6).toFixed(1) + 'M';
                else if (abs >= 1e3) formatted = '\\u20AC' + (abs / 1e3).toFixed(0) + 'K';
                else formatted = '\\u20AC' + abs.toFixed(0);
                return neg ? '-' + formatted : formatted;
            }}""")
            # cellEditorParams to show formula when entering edit mode
            col_config["cellEditorSelector"] = JsCode(f"""function(params) {{
                var fmap = {{{fmap_str}}};
                var f = fmap[String(params.node.rowIndex)];
                if (f) {{
                    params.data['{col}'] = f;
                }}
                return undefined;
            }}""")

        if col_config:
            gb.configure_column(col, **col_config)

    # Build FX rates map for JS-side formula evaluation
    fx_rates = load_fx_rates()
    fx_js_pairs = []
    for pair, rate in fx_rates.items():
        fx_js_pairs.append(f'"{pair}": {rate}')
        # Add inverse pairs (e.g., USDEUR from EURUSD)
        if len(pair) == 6 and rate > 0:
            inv_pair = pair[3:] + pair[:3]
            fx_js_pairs.append(f'"{inv_pair}": {round(1/rate, 6)}')
    fx_js_map = ", ".join(fx_js_pairs)

    grid_opts = {
        "enableRangeSelection": True,
        "enableFillHandle": True,
        "fillHandleDirection": "xy",
        "tooltipShowDelay": 300,
        "statusBar": {
            "statusPanels": [
                {"statusPanel": "agTotalAndFilteredRowCountComponent", "align": "left"},
                {"statusPanel": "agAggregationComponent", "align": "right"},
            ]
        },
        "singleClickEdit": False,
        "onCellValueChanged": JsCode(f"""function(params) {{
            var val = params.newValue;
            if (val == null || val === '') return;
            // Skip if already a plain number (prevents infinite loop from setDataValue)
            if (typeof val === 'number') return;
            var s = String(val).trim();
            // Skip if it's just a numeric string
            if (/^-?\\d+\\.?\\d*$/.test(s)) return;
            // Only process if starts with = or contains math operators (not just a negative number)
            var isFormula = (s.indexOf('=') === 0);
            var stripped = s.replace(/^-/, '');
            var hasMath = /[+\\-*/]/.test(stripped);
            if (!isFormula && !hasMath) return;
            if (s.indexOf('=') === 0) s = s.substring(1).trim();
            // Substitute FX variable names with rates
            var fxRates = {{{fx_js_map}}};
            for (var k in fxRates) {{
                if (fxRates.hasOwnProperty(k)) {{
                    s = s.replace(new RegExp(k, 'gi'), String(fxRates[k]));
                }}
            }}
            try {{
                var result = Function('"use strict"; return (' + s + ')')();
                if (typeof result === 'number' && isFinite(result)) {{
                    params.node.setDataValue(params.column.colId, Math.round(result));
                }}
            }} catch(e) {{
                // Invalid expression — leave as-is
            }}
        }}"""),
    }
    if highlight_total_row:
        grid_opts["getRowStyle"] = JsCode(f"""
            function(params) {{
                if (params.data && (params.data['Asset Class'] === 'TOTAL' || params.data['Name'] === 'TOTAL')) {{
                    return {{'fontWeight': 'bold', 'backgroundColor': '{BG_HEADER}', 'borderTop': '1px solid {C_ORANGE}', 'color': '{C_ORANGE}'}};
                }}
                return null;
            }}
        """)
    gb.configure_grid_options(**grid_opts)

    grid_options = gb.build()

    custom_css = {
        ".ag-root-wrapper": {
            "background-color": f"{BG_BLACK} !important",
            "border": f"1px solid {BORDER} !important",
            "border-radius": "0 !important",
            "font-size": "12px !important",
        },
        ".ag-header": {
            "background-color": f"{BG_HEADER} !important",
            "border-bottom": f"1px solid {C_ORANGE}33 !important",
            "min-height": "28px !important",
            "height": "28px !important",
        },
        ".ag-header-cell": {"padding": "0 6px !important"},
        ".ag-header-cell-label": {
            "color": f"{C_ORANGE} !important",
            "font-size": "11px !important",
            "font-weight": "600 !important",
            "letter-spacing": "0.3px !important",
        },
        ".ag-row": {
            "background-color": f"{BG_BLACK} !important",
            "color": f"{C_NEUTRAL} !important",
            "border-bottom": f"1px solid {GRID_LINE} !important",
            "font-size": "12px !important",
            "height": "26px !important",
        },
        ".ag-row-hover": {"background-color": f"{BG_HOVER} !important"},
        ".ag-cell": {"padding": "0 6px !important", "line-height": "26px !important"},
        ".ag-cell-edit-wrapper": {
            "background-color": f"{BG_PANEL} !important",
            "color": f"{C_GOLD} !important",
        },
        ".ag-range-selection": {
            "background-color": "rgba(255, 140, 0, 0.15) !important",
            "border": f"1px solid {C_ORANGE} !important",
        },
        ".ag-status-bar": {
            "background-color": f"{BG_HEADER} !important",
            "color": f"{C_LABEL} !important",
            "border-top": f"1px solid {BORDER} !important",
            "font-size": "11px !important",
            "min-height": "24px !important",
        },
        ".ag-status-bar-part": {"color": f"{C_LABEL} !important"},
        ".ag-pinned-left-cols-container .ag-cell": {
            "color": f"{C_LABEL} !important",
            "font-weight": "500 !important",
        },
    }

    return AgGrid(
        df,
        gridOptions=grid_options,
        height=height,
        theme="streamlit",
        custom_css=custom_css,
        update_mode=GridUpdateMode.VALUE_CHANGED,
        enable_enterprise_modules=True,
        allow_unsafe_jscode=True,
        reload_data=False,
        key=key,
        **kwargs,
    )


def track_unsaved_changes(editor_key: str, original_df, edited_df):
    """Track whether a table has unsaved changes. Call after each editor render."""
    import pandas as pd
    try:
        changed = not original_df.astype(str).reset_index(drop=True).equals(
            edited_df.astype(str).reset_index(drop=True)
        )
    except Exception:
        changed = False
    unsaved = st.session_state.setdefault("_unsaved_editors", set())
    if changed:
        unsaved.add(editor_key)
    else:
        unsaved.discard(editor_key)


def show_unsaved_warning():
    """Show warning if any editor has unsaved changes. Call at top of page."""
    unsaved = st.session_state.get("_unsaved_editors", set())
    if unsaved:
        # Build human-readable names from keys
        name_map = {
            "biz_pos": "Business Positions", "biz_val": "Business Valuation", "biz_inc": "Business Income",
            "fund_cc": "Fund Capital Calls", "fund_val": "Fund Valuations", "fund_edit": "Fund Positions",
            "pe_pos": "PE Positions", "pe_val": "PE Valuations",
            "re_pos": "RE Positions", "re_val": "RE Valuations",
            "bond_pos": "Bond Positions", "pm_pos": "Precious Metals",
            "reit_pos": "REIT Positions", "stock_val": "Equity Valuations",
            "cf_edit": "Cash Flow", "cash_pos": "Cash Positions",
            "opt_pos": "Optiver Positions", "opt_val": "Optiver Valuations", "opt_bonus": "Optiver Bonus",
            "inv_plan": "Investment Plan", "fx_liquid": "FX Liquid Returns", "fx_irr": "FX IRR Settings",
            "fx_div": "FX Dividends", "overview_hist": "Historical Values", "sym_class": "Symbol Classifications",
            "debt_positions": "Debt Positions", "debt_payments": "Debt Payments", "debt_valuations": "Debt Valuations",
        }
        names = [name_map.get(k, k) for k in sorted(unsaved)]
        cols = st.columns([5, 1])
        with cols[0]:
            st.error(f"⚠️ Unsaved changes: **{', '.join(names)}**. Save before switching pages!")
        with cols[1]:
            if st.button("Discard All", key="_discard_unsaved", type="secondary"):
                st.session_state["_unsaved_editors"] = set()
                st.rerun()


def clear_unsaved(editor_key: str):
    """Clear unsaved state after successful save."""
    st.session_state.setdefault("_unsaved_editors", set()).discard(editor_key)


def check_deleted_items(original_items: list, edited_df, name_col: str = "name") -> list:
    """Compare original items with edited DataFrame to find deleted item names.
    Returns list of deleted names."""
    original_names = {i.get(name_col, "") for i in original_items if i.get(name_col)}
    edited_names = set()
    if not edited_df.empty and name_col in edited_df.columns:
        edited_names = {str(n) for n in edited_df[name_col] if n and str(n).strip()}
    return sorted(original_names - edited_names)


def handle_save_with_delete_confirmation(key: str, deleted_names: list) -> str:
    """Handle save with delete confirmation flow.
    Returns: 'save' if ok to save, 'confirm_needed' if waiting for confirmation, 'cancelled' if user cancelled.

    Usage pattern — must be called OUTSIDE the save button block:
        # At top of save section:
        pending_key = f"_pending_save_{key}"
        confirm_key = f"_delete_confirm_{key}"

        if st.button("Save"):
            deleted = check_deleted_items(items, edited, "name")
            if not deleted:
                st.session_state[pending_key] = True  # no deletions, go ahead
            else:
                st.session_state[confirm_key] = deleted  # needs confirmation
            st.rerun()

        # Outside button block — handle pending states:
        result = handle_save_with_delete_confirmation(key, ...)
        if result == "save": ... do save ...
    """
    pending_key = f"_pending_save_{key}"
    confirm_key = f"_delete_confirm_{key}"

    # Case 1: Save was clicked with no deletions — proceed
    if st.session_state.get(pending_key):
        st.session_state.pop(pending_key, None)
        st.session_state.pop(confirm_key, None)
        return "save"

    # Case 2: No pending confirmation
    if confirm_key not in st.session_state:
        return "none"

    # Case 3: Confirmation needed — show warning and buttons
    names = st.session_state[confirm_key]
    st.warning(f"⚠️ The following items will be deleted: **{', '.join(names)}**")
    c1, c2 = st.columns(2)
    if c1.button("✅ Confirm Delete & Save", key=f"btn_confirm_{key}", type="primary"):
        st.session_state.pop(confirm_key, None)
        st.session_state[pending_key] = True
        st.rerun()
    if c2.button("❌ Cancel", key=f"btn_cancel_{key}"):
        st.session_state.pop(confirm_key, None)
        st.rerun()
    return "confirm_needed"


def build_valuation_style_maps(col_source_map):
    """Build bg_style_map and cell_style_map from a data-source map.

    Args:
        col_source_map: {col_name: {row_idx: "input"|"ibkr"|"formula"}}

    Returns:
        (bg_style_map, cell_style_map) for use with render_editable_aggrid_table.
    """
    bg_style_map = {}
    cell_style_map = {}
    for col, row_map in col_source_map.items():
        bg_col = {}
        style_col = {}
        for row_idx, source in row_map.items():
            if source == "input":
                bg_col[row_idx] = BG_INPUT
                style_col[row_idx] = "input"
            elif source == "ibkr":
                bg_col[row_idx] = BG_IBKR
                style_col[row_idx] = "ibkr"
            # "formula" gets no override (default dark bg, default text color)
        if bg_col:
            bg_style_map[col] = bg_col
        if style_col:
            cell_style_map[col] = style_col
    return bg_style_map, cell_style_map


def load_fx_rates() -> dict:
    return load_json(DATA_DIR / "fx_rates.json", {
        "EURUSD": 1.087, "EURINR": 90.5, "EURGBP": 0.855,
        "EURHKD": 8.49, "EURJPY": 161.5, "EURCAD": 1.48,
        "EURAUD": 1.66, "EURCHF": 0.935
    })


def save_fx_rates(rates: dict) -> None:
    save_json(DATA_DIR / "fx_rates.json", rates)


# ── Live Market Data (yfinance) ──────────────────────────────────────

BENCHMARK_TICKERS = {
    "S&P 500":       {"ticker": "^GSPC",     "currency": "USD"},
    "Nasdaq":        {"ticker": "^IXIC",     "currency": "USD"},
    "Gold":          {"ticker": "GC=F",      "currency": "USD"},
    "MSCI World":    {"ticker": "URTH",      "currency": "USD"},
    "Euro Stoxx 50": {"ticker": "^STOXX50E", "currency": "EUR"},
}

MARKET_TICKERS = {
    # Indices
    "S&P 500":       {"ticker": "^GSPC",     "currency": "USD"},
    "Nasdaq":        {"ticker": "^IXIC",     "currency": "USD"},
    "MSCI World":    {"ticker": "URTH",      "currency": "USD"},
    "Euro Stoxx 50": {"ticker": "^STOXX50E", "currency": "EUR"},
    "FTSE 100":      {"ticker": "^FTSE",     "currency": "GBP"},
    "DAX":           {"ticker": "^GDAXI",    "currency": "EUR"},
    "Nikkei 225":    {"ticker": "^N225",     "currency": "JPY"},
    "Sensex":        {"ticker": "^BSESN",    "currency": "INR"},
    # Commodities
    "Gold":          {"ticker": "GC=F",      "currency": "USD"},
    "Silver":        {"ticker": "SI=F",      "currency": "USD"},
    # Crypto
    "Bitcoin":       {"ticker": "BTC-USD",   "currency": "USD"},
}

FX_TICKER_MAP = {
    "EURUSD": "EURUSD=X",
    "EURGBP": "EURGBP=X",
    "EURINR": "EURINR=X",
    "EURHKD": "EURHKD=X",
    "EURJPY": "EURJPY=X",
    "EURCAD": "EURCAD=X",
    "EURAUD": "EURAUD=X",
    "EURCHF": "EURCHF=X",
}


@st.cache_data(ttl=300)
def fetch_live_fx_rates() -> dict:
    """Fetch live EUR/X rates via yfinance. Returns dict like {"EURUSD": 1.08, ...}.
    Returns empty dict on failure."""
    try:
        import yfinance as yf
        tickers = list(FX_TICKER_MAP.values())
        data = yf.download(tickers, period="1d", progress=False, threads=True)
        rates = {}
        for pair, ticker in FX_TICKER_MAP.items():
            try:
                if len(tickers) == 1:
                    close = data["Close"].iloc[-1]
                else:
                    close = data["Close"][ticker].iloc[-1]
                if close and close > 0:
                    rates[pair] = round(float(close), 4)
            except (KeyError, IndexError):
                continue
        return rates
    except Exception:
        return {}


@st.cache_data(ttl=900)
def fetch_benchmark_returns(ticker: str, currency: str = "USD") -> dict:
    """Fetch YTD, 1Y, 3Y, 5Y total returns for a benchmark.
    Returns dict like {"YTD": 12.5, "1Y": 18.2, "3Y": 45.0, "5Y": 80.1} (percentages).
    Returns in EUR terms if the benchmark is USD-denominated."""
    try:
        import yfinance as yf
        from datetime import datetime, timedelta

        now = datetime.now()
        start_5y = now - timedelta(days=5*365)

        # Fetch benchmark data
        bench = yf.download(ticker, start=start_5y.strftime("%Y-%m-%d"), progress=False)
        if bench.empty:
            return {}

        bench_close = bench["Close"].squeeze() if hasattr(bench["Close"], 'squeeze') else bench["Close"]

        # Define period start dates
        ytd_start = datetime(now.year, 1, 1)
        periods = {
            "YTD": ytd_start,
            "1Y": now - timedelta(days=365),
            "3Y": now - timedelta(days=3*365),
            "5Y": start_5y,
        }

        # Fetch EUR/USD for currency conversion if needed
        fx_start = None
        fx_data = None
        if currency != "EUR":
            fx_ticker = f"EUR{currency}=X"
            fx_start = start_5y
            fx_data = yf.download(fx_ticker, start=fx_start.strftime("%Y-%m-%d"), progress=False)
            if not fx_data.empty:
                fx_close = fx_data["Close"].squeeze() if hasattr(fx_data["Close"], 'squeeze') else fx_data["Close"]
            else:
                fx_close = None
        else:
            fx_close = None

        results = {}
        for label, start_date in periods.items():
            try:
                # Find closest available date
                mask = bench_close.index >= start_date.strftime("%Y-%m-%d")
                if not mask.any():
                    continue
                start_price = float(bench_close[mask].iloc[0])
                end_price = float(bench_close.iloc[-1])

                if start_price <= 0:
                    continue

                bench_return = (end_price / start_price) - 1  # as decimal

                # Convert to EUR if needed
                if fx_close is not None and currency != "EUR":
                    fx_mask = fx_close.index >= start_date.strftime("%Y-%m-%d")
                    if fx_mask.any():
                        fx_start_rate = float(fx_close[fx_mask].iloc[0])
                        fx_end_rate = float(fx_close.iloc[-1])
                        if fx_start_rate > 0 and fx_end_rate > 0:
                            # EUR return = (1 + USD_return) * (EUR/USD_start / EUR/USD_end) - 1
                            # If EUR/USD goes from 1.10 to 1.05, EUR appreciated, USD return worth less in EUR
                            bench_return = (1 + bench_return) * (fx_start_rate / fx_end_rate) - 1

                results[label] = round(bench_return * 100, 1)
            except (IndexError, KeyError, ZeroDivisionError):
                continue

        return results
    except Exception:
        return {}


@st.cache_data(ttl=900)
def fetch_benchmark_yearly(ticker: str, currency: str = "USD", start_year: int = 2018) -> dict:
    """Fetch year-end closing prices for a benchmark, converted to EUR.

    Returns {year: price_eur, ...} for each year from start_year to now.
    Used for overlaying benchmarks on the Performance chart.
    """
    try:
        import yfinance as yf
        from datetime import datetime

        now = datetime.now()
        data = yf.download(ticker, start=f"{start_year}-01-01", progress=False)
        if data.empty:
            return {}

        close = data["Close"].squeeze() if hasattr(data["Close"], "squeeze") else data["Close"]

        # Get EUR/X rates for conversion
        fx_close = None
        if currency != "EUR":
            fx_ticker = f"EUR{currency}=X"
            fx_data = yf.download(fx_ticker, start=f"{start_year}-01-01", progress=False)
            if not fx_data.empty:
                fx_close = fx_data["Close"].squeeze() if hasattr(fx_data["Close"], "squeeze") else fx_data["Close"]

        result = {}
        for yr in range(start_year, now.year + 1):
            # Pick last trading day of December (or latest available for current year)
            if yr == now.year:
                yr_data = close[close.index.year == yr]
            else:
                yr_data = close[(close.index.year == yr) & (close.index.month == 12)]
                if yr_data.empty:
                    yr_data = close[close.index.year == yr]
            if yr_data.empty:
                continue

            price = float(yr_data.iloc[-1])

            # Convert to EUR
            if fx_close is not None:
                if yr == now.year:
                    fx_yr = fx_close[fx_close.index.year == yr]
                else:
                    fx_yr = fx_close[(fx_close.index.year == yr) & (fx_close.index.month == 12)]
                    if fx_yr.empty:
                        fx_yr = fx_close[fx_close.index.year == yr]
                if not fx_yr.empty:
                    fx_rate = float(fx_yr.iloc[-1])
                    if fx_rate > 0:
                        price = price / fx_rate

            result[yr] = price
        return result
    except Exception:
        return {}


@st.cache_data(ttl=900)
def get_live_market_data() -> dict:
    """Fetch FX rates + market prices (indices, commodities, crypto) in one call.
    Cached for 15 minutes. Returns {"fx": {...}, "prices": {...}, "last_updated": str}."""
    from datetime import datetime
    fx = fetch_live_fx_rates()
    prices = {}
    try:
        import yfinance as yf
        tickers = list(set(v["ticker"] for v in MARKET_TICKERS.values()))
        data = yf.download(tickers, period="1d", progress=False, threads=True)
        if not data.empty:
            for name, info in MARKET_TICKERS.items():
                try:
                    t = info["ticker"]
                    if len(tickers) == 1:
                        price = float(data["Close"].iloc[-1])
                    else:
                        price = float(data["Close"][t].iloc[-1])
                    if price > 0:
                        prices[name] = {
                            "price": round(price, 2),
                            "currency": info["currency"],
                        }
                except (KeyError, IndexError, TypeError):
                    continue
    except Exception:
        pass
    return {
        "fx": fx,
        "prices": prices,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def to_eur(value: float, currency: str, fx_rates: dict) -> float:
    if currency == "EUR":
        return value
    key = f"EUR{currency}"
    rate = fx_rates.get(key, 1.0)
    if rate == 0:
        return value
    return value / rate


def auto_refresh_fx_rates():
    """Auto-fetch live FX rates on app load, throttled to every 15 minutes."""
    from datetime import datetime, timedelta
    now = datetime.now()
    last = st.session_state.get("_fx_last_refresh")
    if last and (now - last) < timedelta(minutes=15):
        return
    live = fetch_live_fx_rates()
    if live:
        existing = load_fx_rates()
        existing.update(live)
        save_fx_rates(existing)
        st.session_state["_fx_last_refresh"] = now


@st.cache_data(ttl=900)
def fetch_live_stock_prices() -> dict:
    """Fetch current prices for all tickers in public_stocks.json.

    Returns {ticker: {"price": float, "currency": str}, ...}.
    """
    try:
        import yfinance as yf
        positions = load_json(DATA_DIR / "public_stocks.json", [])
        ticker_currency = {}
        for p in positions:
            t = p.get("ticker", "").strip()
            if t:
                ticker_currency[t] = p.get("currency", "USD")
        if not ticker_currency:
            return {}
        tickers = list(ticker_currency.keys())
        data = yf.download(tickers, period="1d", progress=False, threads=True)
        if data.empty:
            return {}
        result = {}
        for t in tickers:
            try:
                if len(tickers) == 1:
                    price = float(data["Close"].iloc[-1])
                else:
                    price = float(data["Close"][t].iloc[-1])
                if price > 0:
                    result[t] = {"price": price, "currency": ticker_currency[t]}
            except (KeyError, IndexError, TypeError):
                continue
        return result
    except Exception:
        return {}


def auto_refresh_stock_prices():
    """Auto-update stock positions with live prices, throttled to every 15 minutes."""
    from datetime import datetime, timedelta
    now = datetime.now()
    last = st.session_state.get("_stocks_last_refresh")
    if last and (now - last) < timedelta(minutes=15):
        return
    prices = fetch_live_stock_prices()
    if not prices:
        return
    fx = load_fx_rates()
    positions = load_json(DATA_DIR / "public_stocks.json", [])
    changed = False
    for p in positions:
        t = p.get("ticker", "").strip()
        if t in prices:
            qty = p.get("quantity", 0)
            if qty > 0:
                live = prices[t]
                value_local = live["price"] * qty
                p["value_eur"] = round(to_eur(value_local, live["currency"], fx), 2)
                cost = p.get("cost_eur", 0)
                p["return_pct"] = round((p["value_eur"] - cost) / cost * 100, 2) if cost > 0 else 0
                p["last_updated"] = now.strftime("%Y-%m-%d %H:%M")
                changed = True
    if changed:
        save_json(DATA_DIR / "public_stocks.json", positions)
    st.session_state["_stocks_last_refresh"] = now


# Files shared across all users (not remapped to user directory)
SHARED_FILES = {"symbol_classifications.json", "fx_rates.json", "assumptions.json"}

def _get_effective_path(path: Path) -> Path:
    """Remap a DATA_DIR path to the logged-in user's isolated directory."""
    user_dir = st.session_state.get("user_data_dir")
    if user_dir is None:
        return path
    try:
        relative = path.relative_to(DATA_DIR)
    except ValueError:
        return path
    # Don't remap paths already inside users/ or _template/ or _backup
    if relative.parts and relative.parts[0] in ("users", "_template", "_backup_premigration"):
        return path
    # Don't remap shared files — they're global across all users
    if relative.name in SHARED_FILES:
        return path
    return Path(user_dir) / relative


# ── Supabase backend ──────────────────────────────────────────────────

def _get_supabase_client():
    """Return a cached Supabase client, or None if not configured."""
    if "_supabase_client" in st.session_state:
        return st.session_state["_supabase_client"]
    try:
        sb_secrets = st.secrets["supabase"]
        url = sb_secrets["url"]
        key = sb_secrets["key"]
        if url and key:
            from supabase import create_client
            client = create_client(url, key)
            st.session_state["_supabase_client"] = client
            return client
    except (KeyError, FileNotFoundError, Exception):
        pass
    st.session_state["_supabase_client"] = None
    return None


def _is_user_file(path: Path) -> bool:
    """Check if a path is a per-user data file (not shared)."""
    try:
        relative = path.relative_to(DATA_DIR)
    except ValueError:
        return False
    return relative.name not in SHARED_FILES


def _supabase_load_all_user_data(user_email: str) -> dict:
    """Load ALL data for a user from Supabase in one query. Cached in session state."""
    cache_key = f"_sb_cache_{user_email}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    client = _get_supabase_client()
    if client is None:
        return {}
    try:
        result = client.table("user_data").select("file_name,data").eq(
            "user_email", user_email).execute()
        cache = {row["file_name"]: row["data"] for row in result.data}
        st.session_state[cache_key] = cache
        return cache
    except Exception:
        return {}


def _supabase_invalidate_cache(user_email: str):
    """Clear the Supabase cache for a user (call after save)."""
    cache_key = f"_sb_cache_{user_email}"
    st.session_state.pop(cache_key, None)


def _supabase_load(file_name: str, user_email: str, default=None):
    """Load JSON data from Supabase for a specific user and file."""
    # Use cached bulk load
    cache = _supabase_load_all_user_data(user_email)
    if file_name in cache:
        data = cache[file_name]
        if default is not None and type(data) != type(default):
            return default
        return data
    return None  # Not found — fall through to filesystem


def _supabase_save(file_name: str, user_email: str, data) -> bool:
    """Save JSON data to Supabase for a specific user and file."""
    client = _get_supabase_client()
    if client is None:
        return False  # Supabase not configured
    try:
        client.table("user_data").upsert({
            "user_email": user_email,
            "file_name": file_name,
            "data": data,
            "updated_at": datetime.now().isoformat(),
        }, on_conflict="user_email,file_name").execute()
        # Update local cache
        cache_key = f"_sb_cache_{user_email}"
        if cache_key in st.session_state:
            st.session_state[cache_key][file_name] = data
        return True
    except Exception:
        return False


def load_json(path: Path, default=None):
    path = _get_effective_path(path)

    # Try Supabase for per-user files
    user_email = st.session_state.get("user_email")
    if user_email and _is_user_file(path):
        sb_data = _supabase_load(path.name, user_email, default)
        if sb_data is not None:
            return sb_data

    # Fallback to filesystem
    if path.exists():
        try:
            with open(path, "r") as f:
                data = json.load(f)
            # Type-safety: if caller expects a dict but file has a list (or vice versa), return default
            if default is not None and type(data) != type(default):
                return default
            return data
        except Exception:
            pass
    return default if default is not None else {}


def save_json(path: Path, data) -> None:
    path = _get_effective_path(path)

    # Save to Supabase for per-user files
    user_email = st.session_state.get("user_email")
    if user_email and _is_user_file(path):
        _supabase_save(path.name, user_email, data)

    # Always also save to filesystem (local dev + cache)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def setup_user_data_dir(email: str, name: str = "") -> Path:
    """Initialize user data directory and Supabase records for new users."""
    import shutil

    safe_email = email.lower().strip()
    if ".." in safe_email or "/" in safe_email or "\\" in safe_email:
        raise ValueError(f"Invalid email for directory name: {email}")

    # Store email in session state for Supabase queries
    st.session_state["user_email"] = safe_email

    user_dir = USERS_DIR / safe_email

    # Check if user exists in Supabase
    sb_client = _get_supabase_client()
    user_exists_in_sb = False
    if sb_client:
        try:
            result = sb_client.table("user_data").select("file_name").eq(
                "user_email", safe_email).limit(1).execute()
            user_exists_in_sb = bool(result.data)
        except Exception:
            pass

    if not user_dir.exists():
        user_dir.mkdir(parents=True, exist_ok=True)

        if user_exists_in_sb:
            # User has data in Supabase — load it to local cache
            try:
                result = sb_client.table("user_data").select("file_name,data").eq(
                    "user_email", safe_email).execute()
                for row in result.data:
                    fpath = user_dir / row["file_name"]
                    with open(fpath, "w") as f:
                        json.dump(row["data"], f, indent=2)
            except Exception:
                pass
        else:
            # New user — copy from templates
            if TEMPLATE_DIR.exists():
                for json_file in TEMPLATE_DIR.glob("*.json"):
                    shutil.copy2(json_file, user_dir / json_file.name)
            else:
                _create_blank_templates()
                for json_file in TEMPLATE_DIR.glob("*.json"):
                    shutil.copy2(json_file, user_dir / json_file.name)

            # Also seed Supabase with template data for new users
            if sb_client:
                for json_file in (user_dir).glob("*.json"):
                    if json_file.name.startswith("_"):
                        continue
                    try:
                        with open(json_file) as f:
                            data = json.load(f)
                        _supabase_save(json_file.name, safe_email, data)
                    except Exception:
                        pass

    # Write/update profile
    profile_path = user_dir / "_profile.json"
    profile = {}
    if profile_path.exists():
        try:
            with open(profile_path, "r") as f:
                profile = json.load(f)
        except Exception:
            pass

    profile["email"] = email
    profile["name"] = name
    profile["last_login"] = datetime.now().isoformat()
    if "created" not in profile:
        profile["created"] = datetime.now().isoformat()

    with open(profile_path, "w") as f:
        json.dump(profile, f, indent=2)

    st.session_state["user_data_dir"] = user_dir
    return user_dir


def _create_blank_templates():
    """Create blank/default JSON files for new users."""
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    # Files that should default to empty lists
    list_files = [
        "public_stocks.json", "real_estate.json", "private_equity.json",
        "funds.json", "business.json", "bonds.json", "precious_metals.json",
        "cash.json", "debt.json", "investment_plan.json",
    ]
    # Files that should default to empty dicts
    dict_files = [
        "assumptions.json", "fx_rates.json", "symbol_classifications.json",
        "dividend_config.json", "asset_value_history.json", "asset_history.json",
        "cashflow.json", "ibkr_capital_flows.json", "ibkr_database.json",
        "rules_notes.json", "todos.json",
        "historical_totals.json", "overview_settings.json",
    ]
    for fname in list_files:
        with open(TEMPLATE_DIR / fname, "w") as f:
            json.dump([], f)
    for fname in dict_files:
        with open(TEMPLATE_DIR / fname, "w") as f:
            json.dump({}, f)


def new_id() -> str:
    return str(uuid.uuid4())


def get_base_year() -> int | None:
    """Detect the most recent year < CURRENT_YEAR with any confirmed user data.

    Scans all data sources (asset_value_history, illiquid value_history,
    cashflow actual_cash, debt value_history) and returns the max year found.
    Returns None if no data exists at all.
    """
    all_years: set[int] = set()

    # Liquid assets: asset_value_history.json
    avh = load_json(DATA_DIR / "asset_value_history.json", {})
    for sub in avh.values():
        if isinstance(sub, dict):
            for y in sub.keys():
                try:
                    all_years.add(int(y))
                except ValueError:
                    pass

    # Illiquid assets: per-item value_history / income_history
    for fname, hist_key in [
        ("private_equity.json", "value_history"),
        ("real_estate.json", "value_history"),
        ("funds.json", "value_history"),
        ("business.json", "income_history"),
        ("debt.json", "value_history"),
    ]:
        items = load_json(DATA_DIR / fname, [])
        for item in items:
            vh = item.get(hist_key, {})
            for y in vh.keys():
                try:
                    all_years.add(int(y))
                except ValueError:
                    pass

    # Cash: actual_cash_by_year
    cf = load_json(DATA_DIR / "cashflow.json", {})
    actual_cash = cf.get("actual_cash_by_year", {})
    for y in actual_cash.keys():
        try:
            all_years.add(int(y))
        except ValueError:
            pass

    # Filter to years < CURRENT_YEAR and return the max
    past_years = [y for y in all_years if y < CURRENT_YEAR]
    if not past_years:
        return None
    return max(past_years)


YEAR_END_REASONS = {
    "Year-end valuation (IBKR)": "Net worth & projections",
    "Actual dividends received": "Cash flow & income tracking",
    "Net capital invested/withdrawn (IBKR)": "Return calculations & cash flow",
    "Year-end valuation": "Net worth & projections",
    "Year-end NAV": "Net worth & projections",
    "Annual income": "Cash flow & business valuation",
    "Actual cash balance": "Cash flow reconciliation",
    "Outstanding balance": "Net worth (reduces assets)",
}


def get_year_end_completeness(year: int = None) -> dict:
    """Return detailed completeness checklist for a year-end close.

    Returns:
        {
            "year": int,
            "missing_items": [{"asset_class": str, "name": str, "field": str}, ...],
            "complete_items": [{"asset_class": str, "name": str, "field": str}, ...],
            "complete_count": int,
            "total_count": int,
        }
    """
    if year is None:
        year = get_base_year()
    if year is None:
        return {"year": None, "missing_items": [], "complete_items": [],
                "complete_count": 0, "total_count": 0}

    yr_str = str(year)
    missing: list[dict] = []
    complete: list[dict] = []
    total = 0

    def _check(ok: bool, asset_class: str, name: str, field: str):
        nonlocal total
        total += 1
        entry = {"asset_class": asset_class, "name": name, "field": field}
        if ok:
            complete.append(entry)
        else:
            missing.append(entry)

    # ── Liquid assets (IBKR-driven) ──
    avh = load_json(DATA_DIR / "asset_value_history.json", {})
    div_cfg = load_json(DATA_DIR / "dividend_config.json", {})
    actual_divs = div_cfg.get("actual_dividends", {})
    cap_flows = load_json(DATA_DIR / "ibkr_capital_flows.json", {})

    # Values per liquid class
    liquid_classes = {"Equity": ["Equity", "ETF"], "REITs": ["REITs"],
                      "Precious Metals": ["Precious Metals"], "Bonds": ["Bonds"]}
    for display_name, avh_keys in liquid_classes.items():
        val = sum(avh.get(k, {}).get(yr_str, 0) for k in avh_keys)
        _check(bool(val), display_name, "Portfolio Value", "Year-end valuation (IBKR)")

    # Dividends (Equity, REITs)
    for div_class in ["Equity", "REITs"]:
        _check(bool(actual_divs.get(div_class, {}).get(yr_str)),
               div_class, "Dividends", "Actual dividends received")

    # Net capital flows per IBKR class
    for flow_class in ["Equity", "REIT"]:
        display = "REITs" if flow_class == "REIT" else flow_class
        _check(bool(cap_flows.get(flow_class, {}).get(yr_str)),
               display, "Net Capital", "Net capital invested/withdrawn (IBKR)")

    # ── Illiquid assets (per active item) ──
    # year_key: field that indicates when the item was acquired/started
    illiquid_checks = [
        ("private_equity.json", "Private Equity", "value_history", "Year-end valuation", "year_invested"),
        ("real_estate.json", "Real Estate", "value_history", "Year-end valuation", "year_invested"),
        ("funds.json", "Funds", "value_history", "Year-end NAV", "year_invested"),
        ("business.json", "Business", "income_history", "Annual income", "year_started"),
        ("business.json", "Business", "value_history", "Year-end valuation", "year_started"),
    ]
    for fname, ac, hist_key, field_label, yr_key in illiquid_checks:
        items = load_json(DATA_DIR / fname, [])
        active = [i for i in items if i.get("status", "Active") == "Active"]
        for item in active:
            # Skip items not yet invested/started in the target year
            item_start = item.get(yr_key, 0)
            if item_start and item_start > year:
                continue
            # For business income, skip the start year itself (income from year+1)
            if hist_key == "income_history" and item_start and year <= item_start:
                continue
            _check(bool(item.get(hist_key, {}).get(yr_str)),
                   ac, item.get("name", "Unknown"), field_label)

    # ── Cash ──
    cf = load_json(DATA_DIR / "cashflow.json", {})
    _check(bool(cf.get("actual_cash_by_year", {}).get(yr_str)),
           "Cash", "Year-End Cash", "Actual cash balance")

    # ── Debt (per item with any balance or recent activity) ──
    debt_items = load_json(DATA_DIR / "debt.json", [])
    active_debt = [d for d in debt_items
                   if d.get("outstanding_balance_eur", 0) > 0 or d.get("year_taken", 9999) >= year]
    for d in active_debt:
        _check(bool(d.get("value_history", {}).get(yr_str)),
               "Debt", d.get("name", "Unknown"), "Outstanding balance")

    # ── Cashflow manual items ──
    for expense_name in ["Wealth Tax", "Life Expenses"]:
        _check(bool(cf.get("expenses", {}).get(expense_name, {}).get(yr_str)),
               "Cashflow", expense_name, f"{expense_name} for {year}")

    return {
        "year": year,
        "missing_items": missing,
        "complete_items": complete,
        "complete_count": total - len(missing),
        "total_count": total,
    }


def render_year_end_alert(asset_class: str, year: int = None):
    """Show an expandable warning if the given asset class has missing year-end data."""
    import streamlit as st
    if year is None:
        year = CURRENT_YEAR - 1
    comp = get_year_end_completeness(year)
    ac_missing = [i for i in comp["missing_items"] if i["asset_class"] == asset_class]
    if ac_missing:
        with st.expander(f"⚠️ {len(ac_missing)} items missing {year} year-end data", expanded=False):
            for i in ac_missing:
                reason = YEAR_END_REASONS.get(i["field"], "")
                reason_text = f" — *{reason}*" if reason else ""
                st.markdown(f"❌ {i['name']}: {i['field']}{reason_text}")


def load_assumptions() -> dict:
    return load_json(DATA_DIR / "assumptions.json", {})


def save_assumptions(data: dict) -> None:
    save_json(DATA_DIR / "assumptions.json", data)


_DEFAULT_PE_MULT = {
    "Super Bear": {"irr": 0.5, "prob": 0.5},
    "Bear":       {"irr": 0.7, "prob": 0.75},
    "Base":       {"irr": 1.0, "prob": 1.0},
    "Bull":       {"irr": 1.3, "prob": 1.0},
}
_DEFAULT_RE_MULT = {
    "Super Bear": {"irr": 0.5, "prob": 1.0},
    "Bear":       {"irr": 0.7, "prob": 1.0},
    "Base":       {"irr": 1.0, "prob": 1.0},
    "Bull":       {"irr": 1.3, "prob": 1.0},
}


def get_scenario_multipliers(asset_type: str = "pe", scenario: str = "Base") -> dict:
    """Get IRR and probability multipliers for a scenario.

    asset_type: 'pe' for PE/Funds, 're' for Real Estate.
    Returns dict with 'irr' and 'prob' keys.
    """
    assumptions = load_assumptions()
    key = "pe_scenario_multipliers" if asset_type == "pe" else "re_scenario_multipliers"
    defaults = _DEFAULT_PE_MULT if asset_type == "pe" else _DEFAULT_RE_MULT
    stored = assumptions.get(key, defaults)
    return stored.get(scenario, defaults.get(scenario, {"irr": 1.0, "prob": 1.0}))


def get_all_scenario_multipliers(asset_type: str = "pe") -> dict:
    """Get all scenario multipliers for an asset type. Returns full dict."""
    assumptions = load_assumptions()
    key = "pe_scenario_multipliers" if asset_type == "pe" else "re_scenario_multipliers"
    defaults = _DEFAULT_PE_MULT if asset_type == "pe" else _DEFAULT_RE_MULT
    return assumptions.get(key, defaults)


def get_return_pct(asset_class: str, scenario: str, assumptions: dict) -> float:
    """Get return % for an asset class under a given scenario.

    Checks scenario-based assumptions first (assumptions[asset_class][scenario_key]),
    then falls back to flat liquid-return keys (equity_return_pct, etc.) with scenario multipliers.
    """
    key = SCENARIO_KEYS.get(scenario, "base")

    # 1) Try scenario-based: assumptions["Equity"]["base"]
    ac_data = assumptions.get(asset_class, {})
    if isinstance(ac_data, dict) and key in ac_data:
        import math
        val = ac_data.get(key, 0.0)
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return 0.0
        return val

    # 2) Fallback to flat liquid-return keys with scenario multiplier
    _FLAT_KEYS = {
        "Equity": "equity_return_pct",
        "REITs": "reit_return_pct",
        "Precious Metals": "metals_return_pct",
        "Bonds": "bond_return_pct",
    }
    _SCENARIO_MULT = {"Super Bear": 0.5, "Bear": 0.7, "Base": 1.0, "Bull": 1.5}
    flat_key = _FLAT_KEYS.get(asset_class)
    if flat_key and flat_key in assumptions:
        base = assumptions[flat_key]
        return base * _SCENARIO_MULT.get(scenario, 1.0)

    return 0.0


def project_value(current: float, return_pct: float, years: int = 10) -> list:
    values = [current]
    for _ in range(years):
        values.append(values[-1] * (1 + return_pct / 100))
    return values


def get_projection_years(n: int = 10) -> list:
    return list(range(CURRENT_YEAR, CURRENT_YEAR + n + 1))


def get_planned_investment(asset_class: str, year: int) -> float:
    """Get planned investment for a specific asset class and year.

    Priority:
    1. planned_investment_by_year[asset_class][year_str] — per-year override
    2. planned_investment_yr[asset_class] — default annual amount
    """
    plan = load_json(DATA_DIR / "investment_plan.json", {})
    if not isinstance(plan, dict): plan = {}
    # Check per-year override first
    by_year = plan.get("planned_investment_by_year", {})
    ac_years = by_year.get(asset_class, {})
    yr_str = str(year)
    if yr_str in ac_years:
        return float(ac_years[yr_str])
    # Fallback to default annual amount
    return float(plan.get("planned_investment_yr", {}).get(asset_class, 0))


def get_dividend_yield_pct(asset_class: str) -> float:
    """Get expected dividend yield % for an asset class from investment plan."""
    plan = load_json(DATA_DIR / "investment_plan.json", {})
    if not isinstance(plan, dict): plan = {}
    return float(plan.get("dividend_yield_pct", {}).get(asset_class, 0))


def get_public_stocks_total_eur(fx_rates: dict, type_filter=None) -> float:
    positions = load_json(DATA_DIR / "public_stocks.json", [])
    total = 0.0
    for p in positions:
        ptype = p.get("type", "Equity")
        if type_filter == "REIT" and ptype != "REIT":
            continue
        if type_filter == "non-REIT" and ptype in ("REIT", "Precious Metals"):
            continue
        if type_filter == "Precious Metals" and ptype != "Precious Metals":
            continue
        # Use pre-computed value_eur if available, fall back to qty × price
        val_eur = p.get("value_eur", 0)
        if val_eur:
            total += val_eur
        else:
            val = p.get("quantity", 0) * p.get("current_price", 0)
            total += to_eur(val, p.get("currency", "EUR"), fx_rates)
    return total


def get_real_estate_total_eur() -> float:
    """Sum current_value_eur for Active RE items from real_estate.json."""
    items = load_json(DATA_DIR / "real_estate.json", [])
    return sum(i.get("current_value_eur", 0) for i in items
               if i.get("status", "Active") == "Active")


def get_pe_total_eur() -> float:
    """Sum PE value for Active items (excludes Real Estate type).
    Uses latest year-end value_history entry, falling back to current_value_eur.
    This ensures consistency with overview projections and PE tab headline.
    """
    items = load_json(DATA_DIR / "private_equity.json", [])
    latest_yr = str(CURRENT_YEAR - 1)
    total = 0.0
    for i in items:
        if i.get("status") != "Active" or i.get("type") == "Real Estate":
            continue
        vh = i.get("value_history", {})
        val = vh.get(latest_yr, 0)
        if val <= 0:
            val = i.get("current_value_eur", 0)
        total += val
    return total


def get_funds_total_eur() -> float:
    items = load_json(DATA_DIR / "funds.json", [])
    return sum(i.get("current_nav_eur", 0) for i in items)


def compute_business_value_for_year(b: dict, year: int) -> float:
    """Compute a single business's valuation for a given year.

    Formula: (1 - bankruptcy_risk%) × (max(depreciated_investment, floor_value) + PE × income)
    Income starts from year_started+1. Returns 0 for years before year_started or closed businesses.
    """
    yr_start = b.get("year_started", 2020)
    if year < yr_start:
        return 0.0
    status = b.get("status", "Active")
    close_yr = b.get("close_year")
    if status == "Closed" and close_yr and year >= close_yr:
        return 0.0

    inv = b.get("initial_investment_eur", 0)
    dep_pct = b.get("depreciation_pct", 0) / 100
    dep = inv * (1 - dep_pct) ** (year - yr_start)
    floored = max(dep, b.get("floor_value_eur", 0))

    ih = b.get("income_history", {})
    expected = b.get("expected_annual_cashflow_eur", 0)
    actual = ih.get(str(year), 0)
    if actual > 0:
        # Conservative: use min(actual, expected) — never value above expected
        income = min(actual, expected)
    else:
        income = expected
    if year <= yr_start:
        income = 0  # No income until first full year

    risk = b.get("bankruptcy_risk_pct", 0) / 100
    return (1 - risk) * (floored + b.get("pe_multiple", 1) * income)


def get_business_total_eur() -> float:
    items = load_json(DATA_DIR / "business.json", [])
    yr = CURRENT_YEAR - 1
    total = 0.0
    for b in items:
        if b.get("status") == "Active":
            vh = b.get("value_history", {})
            override = vh.get(str(yr), 0)
            total += override if override > 0 else compute_business_value_for_year(b, yr)
    return total


def get_bonds_total_eur() -> float:
    items = load_json(DATA_DIR / "bonds.json", [])
    return sum(i.get("current_value_eur", 0) for i in items)


def get_precious_metals_total_eur() -> float:
    # Precious metals are now stored in public_stocks.json with type="Precious Metals"
    positions = load_json(DATA_DIR / "public_stocks.json", [])
    return sum(p.get("value_eur", 0) for p in positions if p.get("type") == "Precious Metals")


def get_cash_total_eur(fx_rates: dict) -> float:
    items = load_json(DATA_DIR / "cash.json", [])
    total = 0.0
    for c in items:
        total += to_eur(c.get("amount", 0), c.get("currency", "EUR"), fx_rates)
    return total


def get_debt_total_eur() -> float:
    items = load_json(DATA_DIR / "debt.json", [])
    return -sum(i.get("outstanding_balance_eur", 0) for i in items)


def get_all_totals_eur(fx_rates: dict) -> dict:
    return {
        "Equity": get_public_stocks_total_eur(fx_rates, type_filter="non-REIT"),
        "REITs": get_public_stocks_total_eur(fx_rates, type_filter="REIT"),
        "Real Estate": get_real_estate_total_eur(),
        "Private Equity": get_pe_total_eur(),
        "Funds": get_funds_total_eur(),
        "Business": get_business_total_eur(),
        "Bonds": get_bonds_total_eur(),
        "Precious Metals": get_precious_metals_total_eur(),
        "Cash": get_cash_total_eur(fx_rates),
        "Debt": get_debt_total_eur(),
    }


def get_net_worth_eur(fx_rates: dict) -> float:
    return sum(get_all_totals_eur(fx_rates).values())


def get_portfolio_projection(scenario: str, fx_rates: dict, assumptions: dict, years: int = 10) -> list:
    """Project portfolio value incorporating cash flow contributions.

    For liquid assets, uses planned investments from investment_plan.json.
    For all assets, applies scenario-based return rates.
    Also factors in net cash flow from cashflow.json for future years.
    """
    totals = get_all_totals_eur(fx_rates)
    plan = load_json(DATA_DIR / "investment_plan.json", {})
    if not isinstance(plan, dict): plan = {}
    planned_inv = plan.get("planned_investment_yr", {})
    cf = load_json(DATA_DIR / "cashflow.json", {})
    cf_years = [str(y) for y in cf.get("years", [])]
    cf_income = cf.get("income", {})
    cf_expenses = cf.get("expenses", {})

    result = [0.0] * (years + 1)
    for asset_class, current_val in totals.items():
        r = get_return_pct(asset_class, scenario, assumptions)
        annual_inv = planned_inv.get(asset_class, 0)
        if annual_inv > 0:
            proj = project_value_with_contributions(current_val, r, annual_inv, years)
        else:
            proj = project_value(current_val, r, years)
        for i, v in enumerate(proj):
            result[i] += v

    # Add net non-investment cash flow impact (life expenses, tax, debt reduce available capital)
    # This is already captured in the planned investments, but we add cash flow
    # projections for years that have data
    for i in range(1, years + 1):
        yr_str = str(CURRENT_YEAR + i)
        if yr_str in cf_years:
            # Non-investment expenses reduce portfolio
            non_inv_keys = {"Debt Payment", "Wealth Tax", "Life Expenses"}
            non_inv_exp = sum(v.get(yr_str, 0) for k, v in cf_expenses.items() if k in non_inv_keys)
            total_inc = sum(v.get(yr_str, 0) for v in cf_income.values())
            # Net available after non-investment costs (but planned investments already counted)
            total_planned = sum(planned_inv.values())
            net_surplus = total_inc - non_inv_exp - total_planned
            if net_surplus != 0:
                result[i] += net_surplus
    return result


def project_value_with_contributions(current: float, return_pct: float,
                                     annual_contribution: float, years: int = 10) -> list:
    """V(N) = V(N-1) * (1 + return) + new_capital_invested(N)."""
    values = [current]
    for _ in range(years):
        new_val = values[-1] * (1 + return_pct / 100) + annual_contribution
        values.append(new_val)
    return values


# ---------------------------------------------------------------------------
# Income / expense auto-pull helpers
# ---------------------------------------------------------------------------

def get_annual_dividend_income(fx_rates: dict) -> dict:
    """Return annual dividend income split by Equity vs REIT from public_stocks.json."""
    positions = load_json(DATA_DIR / "public_stocks.json", [])
    equity_div = 0.0
    reit_div = 0.0
    for p in positions:
        div = p.get("net_div_eur", 0) or 0
        if p.get("type") == "REIT":
            reit_div += div
        else:
            equity_div += div
    return {"Equity Dividends": equity_div, "REITs Dividends": reit_div}


def get_annual_bond_income() -> float:
    """Return total annual coupon income from bonds."""
    items = load_json(DATA_DIR / "bonds.json", [])
    return sum(i.get("face_value", 0) * i.get("coupon_rate_pct", 0) / 100 for i in items)


def get_annual_cash_interest(fx_rates: dict) -> float:
    """Return total annual interest from cash & savings accounts."""
    items = load_json(DATA_DIR / "cash.json", [])
    total = 0.0
    for c in items:
        amount_eur = to_eur(c.get("amount", 0), c.get("currency", "EUR"), fx_rates)
        total += amount_eur * c.get("interest_rate_pct", 0) / 100
    return total


def get_annual_debt_payments() -> float:
    """Return total annual debt payments from debt.json."""
    items = load_json(DATA_DIR / "debt.json", [])
    return sum(i.get("annual_payment_eur", 0) for i in items)


def get_annual_business_income() -> float:
    """Return total annual cash flow from active businesses."""
    items = load_json(DATA_DIR / "business.json", [])
    return sum(b.get("expected_annual_cashflow_eur", 0) for b in items if b.get("status") == "Active")


def get_annual_rental_income() -> float:
    """Return total annual rental income from real estate."""
    items = load_json(DATA_DIR / "real_estate.json", [])
    return sum(i.get("annual_rental_eur", 0) for i in items
               if i.get("status", "Active") == "Active")


def get_re_projection(years: int = 10, scenario: str = "Base") -> list:
    """Project RE portfolio using per-item IRR × probability.

    Similar to PE projection but for real estate items.
    """
    items = load_json(DATA_DIR / "real_estate.json", [])
    mult = get_scenario_multipliers("re", scenario)
    result = [0.0] * (years + 1)
    for item in items:
        if item.get("status") != "Active":
            continue
        current = item.get("current_value_eur", 0)
        irr = item.get("expected_irr_pct", 0) * mult["irr"]
        prob = min(100, item.get("success_probability_pct", 100) * mult["prob"])
        for yr in range(years + 1):
            if yr == 0:
                result[yr] += current
            else:
                result[yr] += current * (1 + irr / 100) ** yr * (prob / 100)
    return result


def get_pe_annual_dividends() -> float:
    """Return total annual dividends from PE holdings (e.g. Optiver shares)."""
    items = load_json(DATA_DIR / "private_equity.json", [])
    return sum(i.get("annual_dividend_eur", 0) for i in items if i.get("status") == "Active")


def get_pe_exits_by_year() -> dict:
    """Return dict of {year: total_exit_value} for exited PE investments."""
    items = load_json(DATA_DIR / "private_equity.json", [])
    exits = {}
    for i in items:
        if i.get("status") == "Exited":
            yr = i.get("expected_exit_year", 0)
            exit_val = i.get("exit_value_eur", i.get("current_value_eur", 0))
            exits[yr] = exits.get(yr, 0) + exit_val
    return exits


def get_pe_exit_value_for_year(year: int) -> float:
    """Return total exit cash received from PE in a given year."""
    exits = get_pe_exits_by_year()
    return exits.get(year, 0)


def get_re_exits_by_year() -> dict:
    """Return dict of {year: total_exit_value} for exited RE investments."""
    items = load_json(DATA_DIR / "real_estate.json", [])
    exits = {}
    for i in items:
        if i.get("status") == "Exited":
            yr = i.get("expected_exit_year", 0)
            exit_val = i.get("exit_value_eur", i.get("current_value_eur", 0))
            exits[yr] = exits.get(yr, 0) + exit_val
    return exits


def get_pe_investments_by_year() -> dict:
    """Return dict of {year: total_invested} for all PE investments."""
    items = load_json(DATA_DIR / "private_equity.json", [])
    inv = {}
    for i in items:
        yr = i.get("year_invested", 0)
        amt = i.get("amount_invested_eur", 0)
        if yr and amt:
            inv[yr] = inv.get(yr, 0) + amt
    return inv


def get_re_investments_by_year() -> dict:
    """Return dict of {year: total_invested} for all RE investments."""
    items = load_json(DATA_DIR / "real_estate.json", [])
    inv = {}
    for i in items:
        yr = i.get("year_invested", 0)
        amt = i.get("amount_invested_eur", 0)
        if yr and amt:
            inv[yr] = inv.get(yr, 0) + amt
    return inv


def estimate_wealth_tax(fx_rates: dict) -> float:
    """Estimate Dutch Box 3 wealth tax.

    Simplified: ~1.2% of net assets above €57,000 exemption (single).
    Uses current net worth minus primary residence and debt.
    """
    totals = get_all_totals_eur(fx_rates)
    # Taxable assets: everything except primary residence (first RE property)
    # and debt (already negative). Primary residence is excluded from Box 3.
    taxable = sum(totals.values())
    # Subtract primary residence value (approximate)
    re_items = load_json(DATA_DIR / "real_estate.json", [])
    primary_home_val = re_items[0].get("current_value_eur", 0) if re_items else 0
    taxable -= primary_home_val
    # Exemption ~57K for single, 114K for couple
    exemption = 114000
    taxable_base = max(0, taxable - exemption)
    # Effective rate ~1.2% (deemed return ~6.17% × 36% tax rate)
    return taxable_base * 0.012


def get_cashflow_auto_values(fx_rates: dict) -> dict:
    """Return auto-populated income and expense values for the current year."""
    divs = get_annual_dividend_income(fx_rates)
    pe_exits = get_pe_exit_value_for_year(CURRENT_YEAR)
    return {
        "auto_income": {
            "Equity Dividends": divs.get("Equity Dividends", 0),
            "REITs Dividends": divs.get("REITs Dividends", 0),
            "PE Dividends": get_pe_annual_dividends(),
            "Bond Coupon": get_annual_bond_income(),
            "Cash Interest": get_annual_cash_interest(fx_rates),
            "Business Income": get_annual_business_income(),
            "Rental Income": get_annual_rental_income(),
            "PE Exits": pe_exits,
        },
        "auto_expenses": {
            "Debt Payment": get_annual_debt_payments(),
            "Wealth Tax (est.)": estimate_wealth_tax(fx_rates),
        },
    }


def get_available_to_invest(fx_rates: dict) -> float:
    """Calculate available capital = current year net cash flow.

    Uses auto-pulled values for current year income, and loads manual cashflow
    data for expenses. Returns net = total_income - non_investment_expenses.
    Non-investment expenses: Life Expenses, Wealth Tax, Debt Payment.
    """
    cf = load_json(DATA_DIR / "cashflow.json", {})
    yr = str(CURRENT_YEAR)
    income = cf.get("income", {})
    expenses = cf.get("expenses", {})
    total_inc = sum(v.get(yr, 0) for v in income.values())
    non_invest_keys = {"Debt Payment", "Wealth Tax", "Life Expenses"}
    total_non_invest = sum(v.get(yr, 0) for k, v in expenses.items() if k in non_invest_keys)
    return total_inc - total_non_invest


def get_liquid_annual_income(fx_rates: dict) -> dict:
    """Return annual income per liquid asset class."""
    divs = get_annual_dividend_income(fx_rates)
    return {
        "Equity": divs.get("Equity Dividends", 0),
        "REITs": divs.get("REITs Dividends", 0),
        "Bonds": get_annual_bond_income(),
        "Precious Metals": 0.0,
        "Cash": get_annual_cash_interest(fx_rates),
    }


# ---------------------------------------------------------------------------
# Cash-flow auto-pull helpers (future years)
# ---------------------------------------------------------------------------

def get_funds_calls_by_year() -> dict:
    """Return dict {year_int: total_actual_eur} of fund capital calls by year."""
    funds = load_json(DATA_DIR / "funds.json", [])
    calls = {}
    for f in funds:
        for cs in f.get("capital_call_schedule", []):
            yr = cs.get("year", 0)
            amt = cs.get("actual_eur", 0)
            if yr and amt:
                calls[yr] = calls.get(yr, 0) + amt
    return calls


def get_funds_distributions_by_year() -> dict:
    """Return dict {year_int: total_distribution_eur} of fund distributions by year."""
    funds = load_json(DATA_DIR / "funds.json", [])
    dists = {}
    for f in funds:
        for yr_str, amt in f.get("distribution_history", {}).items():
            yr = int(yr_str)
            if amt:
                dists[yr] = dists.get(yr, 0) + amt
    return dists


def get_business_investments_by_year() -> dict:
    """Return dict {year_int: total_investment} from business.json year_started.

    Also includes exit sale proceeds (negative investment = cash inflow) when
    a business is closed with an exit_sale_value_eur.
    """
    items = load_json(DATA_DIR / "business.json", [])
    inv = {}
    for b in items:
        yr = b.get("year_started", 0)
        amt = b.get("initial_investment_eur", 0)
        if yr and amt:
            inv[yr] = inv.get(yr, 0) + amt
        # Exit sale: negative investment (cash inflow)
        close_yr = b.get("close_year")
        sale_val = b.get("exit_sale_value_eur", 0)
        if close_yr and sale_val > 0:
            inv[close_yr] = inv.get(close_yr, 0) - sale_val
    return inv


def get_business_income_by_year() -> dict:
    """Return dict {year_int: total_annual_cashflow} for active businesses.

    Uses income_history (actual) when available, otherwise expected_annual_cashflow_eur.
    Each business generates income from year_started+1 onward while Active.
    """
    items = load_json(DATA_DIR / "business.json", [])
    income = {}
    for b in items:
        if b.get("status") != "Active":
            continue
        yr_start = b.get("year_started", 9999)
        annual_cf = b.get("expected_annual_cashflow_eur", 0)
        close_yr = b.get("close_year") or 9999
        ih = b.get("income_history", {})
        # Generate income from yr_start+1 through close_yr (or far future)
        for yr in range(yr_start + 1, min(close_yr + 1, CURRENT_YEAR + 15)):
            # Use actual income if recorded, else expected
            actual = ih.get(str(yr), 0)
            val = actual if actual > 0 else annual_cf
            income[yr] = income.get(yr, 0) + val
    return income


def get_debt_payments_by_year() -> dict:
    """Return dict {year_int: total_payment} from debt.json.
    Uses payment_history for actual per-year payments, falls back to annual_payment_eur for future years."""
    items = load_json(DATA_DIR / "debt.json", [])
    payments = {}
    for d in items:
        annual = d.get("annual_payment_eur", 0)
        ph = d.get("payment_history", {})
        balance = d.get("outstanding_balance_eur", 0)
        if balance <= 0 and annual <= 0:
            continue
        # Use actual payment_history for past/present years
        for yr_str, amt in ph.items():
            yr = int(yr_str)
            payments[yr] = payments.get(yr, 0) + float(amt)
        # For future years without payment_history, use annual_payment_eur
        if annual > 0 and balance > 0:
            remaining_years = max(1, int(balance / annual) + 1) if annual > 0 else 0
            for yr in range(CURRENT_YEAR, CURRENT_YEAR + remaining_years + 1):
                yr_str = str(yr)
                if yr_str not in ph:
                    payments[yr] = payments.get(yr, 0) + annual
    return payments


def get_pe_dividends_total(year: int = 0) -> float:
    """Return total annual dividends from active PE items."""
    items = load_json(DATA_DIR / "private_equity.json", [])
    total = 0.0
    for i in items:
        if i.get("status") != "Active":
            continue
        div = i.get("annual_dividend_eur", 0)
        if not div:
            continue
        total += div
    return total


def get_investment_plan_by_year() -> dict:
    """Return dict {asset_class: annual_amount} from investment_plan.json."""
    plan = load_json(DATA_DIR / "investment_plan.json", {})
    if not isinstance(plan, dict): plan = {}
    return plan.get("planned_investment_yr", {})


def load_dividend_config() -> dict:
    """Load dividend configuration (yields and actuals)."""
    return load_json(DATA_DIR / "dividend_config.json", {
        "equity_yield_pct": 2.5, "reit_yield_pct": 5.0, "pe_yield_pct": 3.0,
        "actual_dividends": {"Equity": {}, "REITs": {}, "PE": {}}
    })


def get_projected_dividend(asset_class: str, year: int, current_value: float,
                           annual_investment: float, return_pct: float) -> float:
    """Project dividend for a given year based on growing capital + new investments.

    Dividend = (base_value * (1+return)^years_ahead + contributions) * yield_pct
    """
    div_config = load_dividend_config()
    actuals = div_config.get("actual_dividends", {}).get(asset_class, {})

    # If actual dividend recorded for this year, use it
    actual = actuals.get(str(year), 0)
    if actual > 0:
        return actual

    # Project: value grows, dividend = value * yield
    yield_map = {
        "Equity": div_config.get("equity_yield_pct", 2.5),
        "REITs": div_config.get("reit_yield_pct", 5.0),
        "PE": div_config.get("pe_yield_pct", 3.0),
    }
    yld = yield_map.get(asset_class, 2.5) / 100
    years_ahead = max(0, year - CURRENT_YEAR)
    # Simple FV: current grows + annual contributions compound
    fv = current_value * (1 + return_pct / 100) ** years_ahead
    if years_ahead > 0 and return_pct > 0:
        r = return_pct / 100
        fv += annual_investment * ((1 + r) ** years_ahead - 1) / r
    return fv * yld


def get_valuation_new_capital(asset_class: str, ibkr_key: str, year: int) -> float:
    """Get New Capital for a liquid asset from valuation tab data.

    This is the single source of truth used by both the valuation tabs
    and the cashflow page. Priority:
    1. planned_investment_by_year (user overrides from valuation tab)
    2. ibkr_capital_flows (IBKR import data)
    3. planned_investment_yr default (from Investment Plan page)
    Returns the value as-is (positive = invested, negative = sold).
    """
    plan = load_json(DATA_DIR / "investment_plan.json", {})
    if not isinstance(plan, dict): plan = {}
    planned_by_year = plan.get("planned_investment_by_year", {}).get(asset_class, {})

    # 1. Per-year override from valuation tab edits
    by_yr = planned_by_year.get(str(year))
    if by_yr is not None:
        return float(by_yr)

    # 2. IBKR actual data
    ibkr_val = get_ibkr_new_capital(ibkr_key, year)
    if ibkr_val is not None:
        return float(ibkr_val)

    # 3. Default from investment plan (for current/future years)
    if year >= CURRENT_YEAR:
        return float(plan.get("planned_investment_yr", {}).get(asset_class, 0))

    return 0


def compute_cashflow_line(category: str, year: int, stored_value, cashflow_data: dict) -> float:
    """Compute a single cash flow line for a given year.

    Tab-driven categories ALWAYS pull from their respective tab data
    (both historical and future). This ensures cashflow = single source of truth
    from each asset's tab.

    Manual-only categories (Optiver Bonus, Salary, etc.) always use stored values.

    Sign convention in the unified model:
    - Positive (+) = cash coming in (income, sale proceeds)
    - Negative (-) = cash going out (investments, expenses)
    """
    # ── LIQUID ASSET CATEGORIES ──
    # ALWAYS read from valuation tab's New Capital (historical + future).
    # Fall back to stored cashflow value for historical years with no tab data.
    _liquid_cf_map = {
        "Equity": ("Equity", "Equity"),       # (asset_class, ibkr_key)
        "REITS": ("REITs", "REIT"),
        "Precious Metals": ("Precious Metals", "Precious Metals"),
        "Bond": ("Bonds", "Bond"),
    }
    if category in _liquid_cf_map:
        ac, ibkr_key = _liquid_cf_map[category]
        tab_val = get_valuation_new_capital(ac, ibkr_key, year)
        if tab_val != 0:
            return tab_val
        # Fall back to stored cashflow value (for historical years not yet in valuation tab)
        return stored_value

    # ── ILLIQUID ASSET CATEGORIES (NET: investments − exits) ──
    # Positive = net cash out (more invested than exited)
    # Negative = net cash in (more exit proceeds than invested)
    if category == "Private Equity":
        inv = get_pe_investments_by_year()
        exits = get_pe_exits_by_year()
        return inv.get(year, 0) - exits.get(year, 0)

    if category == "Real Estate":
        inv = get_re_investments_by_year()
        exits = get_re_exits_by_year()
        return inv.get(year, 0) - exits.get(year, 0)

    if category == "Funds":
        calls = get_funds_calls_by_year()
        return calls.get(year, 0)

    if category == "Business":
        inv = get_business_investments_by_year()
        return inv.get(year, 0)

    if category == "Debt Payment":
        dp = get_debt_payments_by_year()
        return dp.get(year, stored_value)

    # ── INCOME CATEGORIES ──
    if category == "Equity Dividends":
        div_config = load_dividend_config()
        actual = div_config.get("actual_dividends", {}).get("Equity", {}).get(str(year), 0)
        if actual > 0:
            return actual
        positions = load_json(DATA_DIR / "public_stocks.json", [])
        return sum(p.get("net_div_eur", 0) for p in positions
                   if p.get("type") in ("Equity", "ETF"))

    if category == "REITs Dividends":
        div_config = load_dividend_config()
        actual = div_config.get("actual_dividends", {}).get("REITs", {}).get(str(year), 0)
        if actual > 0:
            return actual
        positions = load_json(DATA_DIR / "public_stocks.json", [])
        return sum(p.get("net_div_eur", 0) for p in positions
                   if p.get("type") == "REIT")

    if category == "PM Dividends":
        positions = load_json(DATA_DIR / "public_stocks.json", [])
        pm_div = sum(p.get("net_div_eur", 0) for p in positions
                     if p.get("type") == "Precious Metals")
        if pm_div > 0:
            return pm_div
        div_config = load_dividend_config()
        return div_config.get("actual_dividends", {}).get("Precious Metals", {}).get(str(year), 0)

    if category == "PE Dividends":
        return get_pe_dividends_total(year=year)

    if category == "Funds Distributions":
        dists = get_funds_distributions_by_year()
        return dists.get(year, stored_value)

    if category == "Business Income":
        bi = get_business_income_by_year()
        return bi.get(year, stored_value)

    if category == "Debt Inflow":
        return stored_value  # debt taken is a one-time event, keep manual

    # ── MANUAL-ONLY CATEGORIES ──
    # These have no tab to pull from — always use stored cashflow.json values
    return stored_value


def _nan_to_zero(v):
    """Convert NaN/None/non-numeric to 0."""
    if v is None:
        return 0
    try:
        v = float(v)
        return 0 if (v != v) else v  # NaN check: NaN != NaN
    except (ValueError, TypeError):
        return 0

def compute_full_cashflow(cashflow_data: dict) -> dict:
    """Compute complete cashflow with auto-pull for future years.

    Returns dict keyed by year_str with per-year breakdown.
    """
    years = [str(y) for y in cashflow_data.get("years", [])]
    income = cashflow_data.get("income", {})
    expenses = cashflow_data.get("expenses", {})
    actuals = cashflow_data.get("actual_cash_by_year", {})

    # Build computed income and expense dicts
    computed_income = {}
    for cat, vals in income.items():
        computed_income[cat] = {}
        for y in years:
            stored = vals.get(y, 0)
            computed_income[cat][y] = _nan_to_zero(compute_cashflow_line(cat, int(y), stored, cashflow_data))

    computed_expenses = {}
    for cat, vals in expenses.items():
        computed_expenses[cat] = {}
        for y in years:
            stored = vals.get(y, 0)
            computed_expenses[cat][y] = _nan_to_zero(compute_cashflow_line(cat, int(y), stored, cashflow_data))

    # Now compute cash flow with carry-forward
    results = {}
    prev_cash = actuals.get(str(int(years[0]) - 1), 0) if years else 0

    for y in years:
        yi = int(y)
        prev_yr = str(yi - 1)
        if prev_yr in actuals and actuals[prev_yr] > 0:
            old_cash = actuals[prev_yr]
        else:
            old_cash = prev_cash

        total_inc = sum(_nan_to_zero(computed_income[cat].get(y, 0)) for cat in computed_income)
        total_exp = sum(_nan_to_zero(computed_expenses[cat].get(y, 0)) for cat in computed_expenses)
        cash_left = old_cash + total_inc - total_exp

        results[y] = {
            "old_cash": old_cash,
            "total_income": total_inc,
            "total_expenses": total_exp,
            "net_cf": total_inc - total_exp,
            "cash_left": cash_left,
            "actual": actuals.get(y, 0),
            "computed_income": {cat: computed_income[cat].get(y, 0) for cat in computed_income},
            "computed_expenses": {cat: computed_expenses[cat].get(y, 0) for cat in computed_expenses},
        }

        if actuals.get(y, 0) > 0:
            prev_cash = actuals[y]
        else:
            prev_cash = cash_left

    return results


# ---------------------------------------------------------------------------
# Historical totals (auto-computed where possible)
# ---------------------------------------------------------------------------

def get_pe_value_by_year(year: int) -> float:
    """Sum PE value for a given year from value_history or best estimate.

    Items WITH value_history: use that year's recorded value.
    Items WITHOUT value_history: use amount_invested_eur if year >= year_invested
    and item was active in that year.
    """
    items = load_json(DATA_DIR / "private_equity.json", [])
    total = 0.0
    yr_str = str(year)
    for item in items:
        # Exclude Real Estate type items (those are counted in get_re_value_by_year)
        if item.get("type") == "Real Estate":
            continue
        vh = item.get("value_history", {})
        if yr_str in vh:
            total += vh[yr_str]
        else:
            # Estimate: was this item active in this year?
            invested_yr = item.get("year_invested", 9999)
            status = item.get("status", "")
            exit_yr = item.get("expected_exit_year", 9999)
            if year < invested_yr:
                continue
            if status == "Written Off":
                wo_yr = exit_yr if exit_yr < 9000 else invested_yr + 2
                if year < wo_yr:
                    total += item.get("amount_invested_eur", 0)
            elif status == "Exited":
                if year < exit_yr:
                    total += item.get("amount_invested_eur", 0)
            elif status == "Active":
                # Use current_value for base year and beyond, invested amount for older years
                if year >= (get_base_year() or CURRENT_YEAR - 2):
                    total += item.get("current_value_eur", 0)
                else:
                    total += item.get("amount_invested_eur", 0)
    return total


def _get_pe_valuation_items() -> list:
    """Return PE items relevant for valuations.

    Includes: Active, Exited (shown until exit year), Written Off (with value_history).
    Used by both PE tab Valuations grid and compute_pe_timeline.
    """
    pe_items = load_json(DATA_DIR / "private_equity.json", [])
    result = []
    for item in pe_items:
        status = item.get("status", "Active")
        if status == "Written Off" and not item.get("value_history"):
            continue
        if status not in ("Active", "Exited", "Written Off"):
            continue
        result.append(item)
    return result


def compute_pe_timeline(years_list: list, scenario: str = "Base") -> list:
    """Compute PE portfolio value for each year in years_list.

    This is THE single source of truth for PE valuations, used by:
    - PE tab Valuations (TOTAL row)
    - Overview projection

    Uses IDENTICAL logic to the PE tab's per-item display, so TOTAL always
    equals the sum of individual item rows in the grid.
    """
    items = _get_pe_valuation_items()
    mult = get_scenario_multipliers("pe", scenario)

    totals = [0.0] * len(years_list)

    for item in items:
        status = item.get("status", "Active")
        exit_yr = item.get("expected_exit_year", 9999)
        current = item.get("current_value_eur", 0)
        year_invested = item.get("year_invested", 2000)
        irr = item.get("expected_irr_pct", 0) * mult["irr"]
        prob = min(100, item.get("success_probability_pct", 0) * mult["prob"])
        vh = item.get("value_history", {})
        prev_val = current

        for i, yr in enumerate(years_list):
            if yr < year_invested:
                continue
            if status == "Exited" and yr >= exit_yr:
                continue  # Exit year = sold during that year, no position at year-end
            if status == "Written Off":
                override = vh.get(str(yr))
                if override is not None and override > 0:
                    totals[i] += override
                continue

            override = vh.get(str(yr))
            has_override = override is not None and override > 0

            if has_override:
                val = override
            elif yr == year_invested and not vh:
                val = item.get("amount_invested_eur", 0)
            elif i == 0 or prev_val == 0:
                # Backtrack: find most recent actual and project one year forward
                val = 0
                for prev_yr in range(yr - 1, year_invested - 1, -1):
                    prev_override = vh.get(str(prev_yr))
                    if prev_override is not None and prev_override > 0:
                        val = prev_override * (1 + irr / 100) * (prob / 100)
                        break
                if val == 0 and yr >= year_invested:
                    val = current if current > 0 else item.get("amount_invested_eur", 0)
            else:
                if status == "Exited":
                    val = prev_val  # Hold last known value until exit
                else:
                    val = prev_val * (1 + irr / 100) * (prob / 100) if prob > 0 else 0

            prev_val = val
            totals[i] += val

    return totals


def _get_re_valuation_items() -> list:
    """Return RE items relevant for valuations.

    Includes: Active, Exited (shown until exit year).
    Used by both RE tab Valuations grid and compute_re_timeline.
    """
    re_items = load_json(DATA_DIR / "real_estate.json", [])
    result = []
    for item in re_items:
        status = item.get("status", "Active")
        if status not in ("Active", "Exited"):
            continue
        result.append(item)
    return result


def compute_re_timeline(years_list: list, scenario: str = "Base") -> list:
    """Compute Real Estate portfolio value for each year in years_list.

    This is THE single source of truth for RE valuations, used by:
    - RE tab Valuations
    - Overview projection
    """
    re_items = _get_re_valuation_items()
    mult = get_scenario_multipliers("re", scenario)
    totals = [0.0] * len(years_list)

    for item in re_items:
        status = item.get("status", "Active")
        exit_yr = item.get("expected_exit_year", 9999)
        current = item.get("current_value_eur", 0)
        year_invested = item.get("year_invested", 2000)
        irr = item.get("expected_irr_pct", 0) * mult["irr"]
        prob = min(100, item.get("success_probability_pct", 100) * mult["prob"])
        vh = item.get("value_history", {})
        prev_val = 0

        for i, yr in enumerate(years_list):
            if yr < year_invested:
                continue
            if status == "Exited" and yr >= exit_yr:
                continue  # Exit year = sold during that year, no position at year-end
            override = vh.get(str(yr))
            has_override = override is not None and override > 0

            if has_override:
                val = override
            elif prev_val == 0:
                val = vh.get(str(yr), 0)
                if val <= 0:
                    val = current if current > 0 else 0
            else:
                if status == "Exited":
                    val = prev_val
                else:
                    val = prev_val * (1 + irr / 100) * (prob / 100) if prob > 0 else 0

            prev_val = val
            totals[i] += val

    return totals


def compute_funds_timeline(years_list: list, scenario: str = "Base") -> list:
    """Compute Funds portfolio value for each year in years_list.

    This is THE single source of truth for Funds valuations, used by:
    - Funds tab Valuations
    - Overview projection
    """
    funds = load_json(DATA_DIR / "funds.json", [])
    mult = get_scenario_multipliers("pe", scenario)
    irr_mult = mult["irr"]

    plan = load_json(DATA_DIR / "investment_plan.json", {})
    if not isinstance(plan, dict): plan = {}
    planned_inv = plan.get("planned_investment_yr", {}).get("Funds", 0)

    totals = [0.0] * len(years_list)

    for f in funds:
        if f.get("status") not in ("Active", None):
            continue
        current = f.get("current_nav_eur", 0)
        year_invested = f.get("year_invested", 2020)
        exit_yr = f.get("expected_exit_year")
        irr = f.get("expected_irr_pct", 0) * irr_mult / 100
        vh = f.get("value_history", {})
        committed = f.get("committed_eur", 0) or 0
        # Use actual EUR if available, otherwise fall back to planned % × committed
        schedule = {}
        for cs in f.get("capital_call_schedule", []):
            yr_cs = cs.get("year", 0)
            actual = cs.get("actual_eur", 0) or 0
            planned_pct = cs.get("planned_pct", 0) or 0
            schedule[yr_cs] = actual if actual > 0 else (planned_pct * committed / 100)
        prev_val = 0

        for i, yr in enumerate(years_list):
            if yr < year_invested:
                continue
            if exit_yr and yr > exit_yr:
                continue

            override = vh.get(str(yr))
            has_override = override is not None and override > 0

            if has_override:
                val = override
            elif prev_val == 0:
                val = vh.get(str(yr), 0)
                if val <= 0:
                    val = current if current > 0 else 0
            else:
                new_call = schedule.get(yr, 0)
                val = prev_val * (1 + irr) + new_call
                if yr > CURRENT_YEAR and not new_call:
                    val = prev_val * (1 + irr) + planned_inv

            prev_val = val
            totals[i] += val

    return totals


def compute_liquid_timeline(asset_class: str, years_list: list, scenario: str = "Base") -> list:
    """Compute liquid asset class value for each year in years_list.

    This is THE single source of truth for liquid asset valuations, used by:
    - Individual tabs (Public Stocks, REITs, Precious Metals, Bonds)
    - Overview projection

    asset_class: one of "Equity", "REITs", "Precious Metals", "Bonds"
    """
    assumptions = load_assumptions()
    adj_return = get_return_pct(asset_class, scenario, assumptions)

    # Map asset class to asset_value_history.json keys
    _avh_keys = {
        "Equity": ["Equity", "ETF"],
        "REITs": ["REITs"],
        "Precious Metals": ["Precious Metals"],
        "Bonds": ["Bonds"],
    }
    # Map asset class to IBKR capital flow keys
    _ibkr_keys = {
        "Equity": "Equity",
        "REITs": "REIT",
        "Precious Metals": "Precious Metals",
        "Bonds": "Bond",
    }

    avh = load_json(DATA_DIR / "asset_value_history.json", {})
    # Build combined year-end history from avh keys
    combined_history = {}
    for avh_key in _avh_keys.get(asset_class, []):
        hist = avh.get(avh_key, {})
        for yr_str, val in hist.items():
            combined_history[yr_str] = combined_history.get(yr_str, 0) + val

    # For Bonds, also merge asset_history.json as fallback
    if asset_class == "Bonds":
        ah = load_json(DATA_DIR / "asset_history.json", {})
        ah_bonds = ah.get("Bonds", {})
        for yr, val in ah_bonds.items():
            if yr not in combined_history and val > 0:
                combined_history[yr] = val

    ibkr_key = _ibkr_keys.get(asset_class, asset_class)

    def _get_new_capital(yr):
        return get_valuation_new_capital(asset_class, ibkr_key, yr)

    totals = [0.0] * len(years_list)
    prev_val = 0

    for i, yr in enumerate(years_list):
        yr_str = str(yr)
        actual = combined_history.get(yr_str)
        has_actual = actual is not None and actual > 0

        if has_actual:
            val = actual
            prev_val = val
        elif prev_val > 0:
            new_capital = _get_new_capital(yr)
            val = prev_val * (1 + adj_return / 100) + new_capital
            prev_val = val
        else:
            val = 0
        totals[i] = val

    return totals


def compute_business_timeline(years_list: list, scenario: str = "Base") -> list:
    """Compute Business portfolio value for each year in years_list.

    Uses compute_business_value_for_year() formula with value_history overrides.
    This is THE single source of truth for Business valuations, used by:
    - Overview projection
    """
    biz_items = load_json(DATA_DIR / "business.json", [])
    totals = [0.0] * len(years_list)

    for b in biz_items:
        status = b.get("status", "Active")
        close_yr = b.get("close_year")
        vh = b.get("value_history", {})

        for i, yr in enumerate(years_list):
            if status == "Closed" and close_yr and yr >= close_yr:
                continue
            override = vh.get(str(yr))
            if override is not None and override > 0:
                totals[i] += override
            else:
                totals[i] += compute_business_value_for_year(b, yr)

    return totals


def compute_cash_timeline(years_list: list) -> list:
    """Compute Cash value for each year in years_list.

    This is THE single source of truth for Cash valuations, used by:
    - Overview projection
    """
    cf_data = load_json(DATA_DIR / "cashflow.json", {})
    cf_results = compute_full_cashflow(cf_data)
    cf_actuals = cf_data.get("actual_cash_by_year", {})
    totals = [0.0] * len(years_list)

    for i, yr in enumerate(years_list):
        yr_str = str(yr)
        actual = cf_actuals.get(yr_str, 0)
        if actual > 0 and yr <= CURRENT_YEAR:
            totals[i] = actual
        elif yr_str in cf_results:
            totals[i] = cf_results[yr_str].get("cash_left", 0)
        elif i > 0:
            totals[i] = totals[i - 1]

    return totals


def compute_debt_timeline(years_list: list) -> list:
    """Compute Debt (negative) value for each year in years_list.

    Uses value_history for confirmed years, then projects forward from the
    latest confirmed year using annual_payment_eur.

    This is THE single source of truth for Debt valuations, used by:
    - Overview projection
    """
    debt_items = load_json(DATA_DIR / "debt.json", [])
    totals = [0.0] * len(years_list)

    for i, yr in enumerate(years_list):
        yr_str = str(yr)
        # Check if we have confirmed value_history data for this year
        hist_total = 0.0
        has_history = False
        for d in debt_items:
            vh = d.get("value_history", {})
            if yr_str in vh:
                hist_total += vh[yr_str]
                has_history = True
            elif has_history:
                # Some items have history, others don't — use outstanding_balance for those
                hist_total += d.get("outstanding_balance_eur", 0)

        if has_history:
            totals[i] = -hist_total
        else:
            # No history for this year — project from last known values
            if i == 0:
                # Use outstanding_balance as starting point
                remaining = sum(d.get("outstanding_balance_eur", 0) for d in debt_items)
            else:
                remaining = -totals[i - 1]  # Previous year's balance (stored as negative)
            total_annual = sum(d.get("annual_payment_eur", 0) for d in debt_items)
            totals[i] = -max(0, remaining - total_annual)

    return totals


def get_re_value_by_year(year: int) -> float:
    """Sum Real Estate value for a given year from real_estate.json."""
    items = load_json(DATA_DIR / "real_estate.json", [])
    total = 0.0
    yr_str = str(year)
    for item in items:
        vh = item.get("value_history", {})
        if yr_str in vh:
            total += vh[yr_str]
        else:
            invested_yr = item.get("year_invested", 9999)
            status = item.get("status", "")
            exit_yr = item.get("expected_exit_year", 9999)
            if year < invested_yr:
                continue
            if status == "Exited":
                if year < exit_yr:
                    total += item.get("amount_invested_eur", 0)
                elif year == exit_yr:
                    total += item.get("exit_value_eur", 0)
            elif status == "Active":
                if year >= CURRENT_YEAR:
                    total += item.get("current_value_eur", 0)
                else:
                    total += item.get("amount_invested_eur", 0)
    return total


def get_pe_projection(years: int = 10, scenario: str = "Base") -> list:
    """Project PE portfolio using per-item IRR × probability.

    Expected value = current_value × (1 + IRR/100)^yr × probability/100
    Failure → 0, so expected value is probability-weighted.

    Scenario adjustments:
      Super Bear: IRR×0.5, probability×0.5
      Bear:       IRR×0.7, probability×0.75
      Base:       as-is
      Bull:       IRR×1.3, probability capped at 100
    """
    items = load_json(DATA_DIR / "private_equity.json", [])
    mult = get_scenario_multipliers("pe", scenario)

    result = [0.0] * (years + 1)
    for item in items:
        if item.get("status") != "Active":
            continue
        current = item.get("current_value_eur", 0)
        irr = item.get("expected_irr_pct", 0) * mult["irr"]
        prob = min(100, item.get("success_probability_pct", 0) * mult["prob"])
        for yr in range(years + 1):
            if yr == 0:
                result[yr] += current
            else:
                result[yr] += current * (1 + irr / 100) ** yr * (prob / 100)
    return result


def get_historical_totals_by_asset(fx_rates: dict) -> dict:
    """Return per-year totals combining auto-computed PE/RE + manual asset_history.

    Returns dict: {year_str: {"PE": X, "RE": Y, "Stocks": Z, ...}, ...}
    PE and RE are auto-computed from value_history.
    Other asset classes come from asset_history.json (manually entered).
    """
    asset_hist = load_json(DATA_DIR / "asset_history.json", {})
    avh = load_json(DATA_DIR / "asset_value_history.json", {})

    # Map overview asset classes to asset_value_history sub-keys
    _avh_keys = {
        "Equity": ["Equity", "ETF"],
        "REITs": ["REITs"],
        "Precious Metals": ["Precious Metals"],
        "Bonds": ["Bonds"],
    }

    # Load actual cash values
    cf_data = load_json(DATA_DIR / "cashflow.json", {})
    actual_cash = cf_data.get("actual_cash_by_year", {})

    # Determine year range from asset_history keys + PE items + avh + cash
    all_years = set()
    for ac_data in asset_hist.values():
        if isinstance(ac_data, dict):
            all_years.update(ac_data.keys())
    for avh_data in avh.values():
        if isinstance(avh_data, dict):
            all_years.update(avh_data.keys())
    all_years.update(actual_cash.keys())

    # Also get years from PE/Funds/Business value_history and income_history
    for fname in ["private_equity.json", "funds.json", "business.json"]:
        for item in load_json(DATA_DIR / fname, []):
            for key in ("value_history", "income_history"):
                all_years.update(item.get(key, {}).keys())
    for item in load_json(DATA_DIR / "debt.json", []):
        all_years.update(item.get("value_history", {}).keys())

    # Compute per-asset timelines using shared compute functions (same as projection)
    sorted_years = sorted(all_years)
    hist_years_int = [int(y) for y in sorted_years]
    computed = {
        "Private Equity": compute_pe_timeline(hist_years_int, "Base") if hist_years_int else [],
        "Real Estate": compute_re_timeline(hist_years_int, "Base") if hist_years_int else [],
        "Funds": compute_funds_timeline(hist_years_int, "Base") if hist_years_int else [],
        "Business": compute_business_timeline(hist_years_int, "Base") if hist_years_int else [],
        "Cash": compute_cash_timeline(hist_years_int) if hist_years_int else [],
        "Debt": compute_debt_timeline(hist_years_int) if hist_years_int else [],
    }
    computed_by_year = {}
    for ac, vals in computed.items():
        computed_by_year[ac] = {str(y): v for y, v in zip(hist_years_int, vals)}

    result = {}
    for yr_str in sorted_years:
        entry = {}
        # Use compute functions for PE, RE, Funds, Business, Cash, Debt
        for ac in ("Private Equity", "Real Estate", "Funds", "Business", "Cash", "Debt"):
            entry[ac] = computed_by_year.get(ac, {}).get(yr_str, 0)
        # For liquid asset classes: prefer asset_value_history, fall back to asset_history
        for ac in ASSET_CLASSES:
            if ac in entry:
                continue
            avh_sum = 0
            for avh_key in _avh_keys.get(ac, []):
                avh_sum += avh.get(avh_key, {}).get(yr_str, 0)
            if avh_sum > 0:
                entry[ac] = avh_sum
            else:
                entry[ac] = asset_hist.get(ac, {}).get(yr_str, 0)
        result[yr_str] = entry
    return result


def get_historical_net_worth() -> dict:
    """Return dict of {year_str: total_net_worth} auto-computed from all sources.

    Uses get_historical_totals_by_asset for the breakdown, sums per year.
    """
    fx = load_fx_rates()
    by_asset = get_historical_totals_by_asset(fx)
    return {yr: sum(assets.values()) for yr, assets in by_asset.items()}


def get_portfolio_projection_v2(scenario: str, fx_rates: dict, assumptions: dict,
                                 years: int = 10, base_year: int = 0) -> dict:
    """Project portfolio per asset class starting from base_year.

    Delegates to per-asset compute_*_timeline() functions — each tab page's
    Valuations section uses the SAME function, so Overview always matches tabs.

    Returns: {"years": [base..base+years], "total": [...], "by_asset": {ac: [...], ...}}
    """
    base_yr = base_year or get_base_year() or (CURRENT_YEAR - 2)
    n_years = years + (CURRENT_YEAR - base_yr)
    proj_years = list(range(base_yr, base_yr + n_years + 1))

    by_asset = {}
    total = [0.0] * len(proj_years)

    # Each asset class uses its shared compute function
    asset_timelines = {
        "Private Equity": compute_pe_timeline(proj_years, scenario),
        "Real Estate": compute_re_timeline(proj_years, scenario),
        "Funds": compute_funds_timeline(proj_years, scenario),
        "Equity": compute_liquid_timeline("Equity", proj_years, scenario),
        "REITs": compute_liquid_timeline("REITs", proj_years, scenario),
        "Precious Metals": compute_liquid_timeline("Precious Metals", proj_years, scenario),
        "Bonds": compute_liquid_timeline("Bonds", proj_years, scenario),
        "Business": compute_business_timeline(proj_years, scenario),
        "Cash": compute_cash_timeline(proj_years),
        "Debt": compute_debt_timeline(proj_years),
    }

    import math as _math
    for ac, vals in asset_timelines.items():
        # Sanitize NaN values to 0
        clean_vals = [0.0 if (isinstance(v, float) and _math.isnan(v)) else v for v in vals]
        by_asset[ac] = clean_vals
        for i, v in enumerate(clean_vals):
            total[i] += v

    return {"years": proj_years, "total": total, "by_asset": by_asset}


# ---------------------------------------------------------------------------
# IB CSV parsing
# ---------------------------------------------------------------------------

def parse_ib_csv(csv_text: str) -> list:
    """Parse Interactive Brokers Activity Statement CSV (legacy - returns flat stock list)."""
    result = parse_ib_activity_statement(csv_text)
    return result.get("stocks", [])


def parse_ib_trades(csv_text: str) -> dict:
    """Parse IBKR Activity Statement for Trades section to compute net capital flows.

    Returns dict: {asset_class: {year_str: net_amount_eur}}.
    Positive = net bought (cash out), Negative = net sold (cash in).
    Asset classes: "Equity", "REIT", "Precious Metals", "Bond"
    """
    fx = load_fx_rates()
    existing = load_json(DATA_DIR / "public_stocks.json", [])
    reit_tickers = {p.get("ticker", "").upper() for p in existing if p.get("type") == "REIT"}
    metals_tickers = {p.get("ticker", "").upper() for p in existing if p.get("type") == "Precious Metals"}
    metal_keywords = {"GLD", "SLV", "IAU", "PPLT", "PALL", "GDX", "GDXJ", "SIL", "SILJ",
                      "SAFE", "GOLD", "PHYS", "PSLV", "SGOL", "AAAU"}

    flows = {}  # {asset_class: {year_str: total_eur}}
    lines = csv_text.strip().split("\n")
    header = None

    for line in lines:
        parts = [p.strip().strip('"') for p in line.split(",")]
        if len(parts) < 3:
            continue
        # Look for Trades section
        if parts[0] == "Trades" and parts[1] == "Header":
            header = parts
            continue
        if parts[0] == "Trades" and parts[1] == "Data":
            if not header or parts[2] in ("Total", "SubTotal", ""):
                continue
            row = dict(zip(header[2:], parts[2:]))
            try:
                symbol = row.get("Symbol", "")
                asset_cat = row.get("Asset Category", "").upper()
                currency = row.get("Currency", "USD")
                # Net proceeds: negative = buy, positive = sell
                proceeds = float(row.get("Proceeds", 0) or 0)
                # Commission
                comm = float(row.get("Comm/Fee", row.get("Commission", 0)) or 0)
                # Date
                date_str = row.get("Date/Time", row.get("Trade Date", ""))
                if not date_str:
                    continue
                # Extract year from date
                year_str = date_str[:4] if len(date_str) >= 4 else ""
                if not year_str.isdigit():
                    continue

                # Net cost: for buys proceeds is negative (money out), sells positive (money in)
                # We want net capital flow: positive = bought, negative = sold
                net_eur = -to_eur(proceeds + comm, currency, fx)

                # Classify
                if asset_cat == "BOND":
                    ac = "Bond"
                elif asset_cat == "CMDTY" or symbol.upper() in metal_keywords or symbol.upper() in metals_tickers:
                    ac = "Precious Metals"
                elif symbol.upper() in reit_tickers:
                    ac = "REIT"
                else:
                    ac = "Equity"

                flows.setdefault(ac, {})
                flows[ac][year_str] = flows[ac].get(year_str, 0) + net_eur
            except (ValueError, KeyError):
                continue

    # Round all values
    for ac in flows:
        for yr in flows[ac]:
            flows[ac][yr] = round(flows[ac][yr])
    return flows


def parse_ib_dividends(csv_text: str) -> dict:
    """Parse IBKR Dividend Detail CSV to extract per-stock dividend income.

    Reads DividendDetail,Data,Summary rows.
    Returns dict:
        by_symbol: {symbol: {gross_eur, withhold_eur, net_eur}}
        by_type:   {Equity: float, REITs: float}
        year:      int
    """
    existing = load_json(DATA_DIR / "public_stocks.json", [])
    reit_tickers = {p.get("ticker", "").upper() for p in existing if p.get("type") == "REIT"}
    ticker_map = {}
    for p in existing:
        t = p.get("ticker", "")
        ticker_map[t.upper()] = t
        ticker_map[t.upper().rstrip("dlDL")] = t

    by_symbol = {}
    year = None
    lines = csv_text.strip().split("\n")
    header = None

    for line in lines:
        parts = [p.strip().strip('"') for p in line.split(",")]
        if len(parts) < 3:
            continue
        if parts[0] == "DividendDetail" and parts[1] == "Header":
            header = parts[2:]
            continue
        if parts[0] == "DividendDetail" and parts[1] == "Data" and len(parts) > 2 and parts[2] == "Summary":
            if not header:
                continue
            row = dict(zip(header, parts[2:]))
            try:
                ib_symbol = row.get("Symbol", "").strip()
                gross_base = float(row.get("GrossInBase", 0) or 0)
                withhold_base = float(row.get("WithholdInBase", 0) or 0)
                net = gross_base + withhold_base

                report_date = row.get("ReportDate", "")
                if report_date and len(report_date) >= 4 and year is None:
                    year = int(report_date[:4])

                sym_upper = ib_symbol.upper()
                our_ticker = (ticker_map.get(sym_upper) or
                              ticker_map.get(sym_upper.rstrip("dlDL")) or
                              ticker_map.get(sym_upper.split(".")[0]) or
                              ib_symbol)

                if our_ticker not in by_symbol:
                    by_symbol[our_ticker] = {"gross_eur": 0, "withhold_eur": 0, "net_eur": 0}
                by_symbol[our_ticker]["gross_eur"] += gross_base
                by_symbol[our_ticker]["withhold_eur"] += withhold_base
                by_symbol[our_ticker]["net_eur"] += net
            except (ValueError, KeyError):
                continue

    by_type = {"Equity": 0.0, "REITs": 0.0}
    for ticker, vals in by_symbol.items():
        if ticker.upper() in reit_tickers:
            by_type["REITs"] += vals["net_eur"]
        else:
            by_type["Equity"] += vals["net_eur"]

    for t in by_symbol:
        for k in by_symbol[t]:
            by_symbol[t][k] = round(by_symbol[t][k], 2)
    for t in by_type:
        by_type[t] = round(by_type[t], 2)

    return {"by_symbol": by_symbol, "by_type": by_type, "year": year or CURRENT_YEAR}


def apply_ib_dividends(parsed: dict) -> dict:
    """Apply parsed IBKR dividend data to stocks, dividend_config, and asset_value_history."""
    year_str = str(parsed["year"])
    by_symbol = parsed["by_symbol"]
    by_type = parsed["by_type"]

    # 1. Update per-stock dividends
    stocks = load_json(DATA_DIR / "public_stocks.json", [])
    updated_count = 0
    for pos in stocks:
        ticker = pos.get("ticker", "")
        if ticker in by_symbol:
            pos["net_div_eur"] = by_symbol[ticker]["net_eur"]
            updated_count += 1
    save_json(DATA_DIR / "public_stocks.json", stocks)

    # 2. Update dividend_config actual_dividends
    div_config = load_json(DATA_DIR / "dividend_config.json", {})
    actuals = div_config.setdefault("actual_dividends", {})
    if by_type.get("Equity", 0) > 0:
        actuals.setdefault("Equity", {})[year_str] = round(by_type["Equity"])
    if by_type.get("REITs", 0) > 0:
        actuals.setdefault("REITs", {})[year_str] = round(by_type["REITs"])
    save_json(DATA_DIR / "dividend_config.json", div_config)

    # 3. Update asset_value_history with year-end valuations from current positions
    fx = load_fx_rates()
    avh = load_json(DATA_DIR / "asset_value_history.json", {})
    equity_total = etf_total = reit_total = metals_total = 0.0

    for pos in stocks:
        qty = pos.get("quantity", 0)
        price = pos.get("current_price", 0)
        ccy = pos.get("currency", "EUR")
        val_eur = to_eur(qty * price, ccy, fx)
        ptype = pos.get("type", "Equity")
        if ptype == "REIT":
            reit_total += val_eur
        elif ptype == "ETF":
            etf_total += val_eur
        elif ptype == "Precious Metals":
            metals_total += val_eur
        else:
            equity_total += val_eur

    metals_list = load_json(DATA_DIR / "precious_metals.json", [])
    for m in metals_list:
        metals_total += m.get("quantity_oz", 0) * m.get("current_price_eur", 0)

    avh.setdefault("Equity", {})[year_str] = round(equity_total)
    avh.setdefault("ETF", {})[year_str] = round(etf_total)
    avh.setdefault("REITs", {})[year_str] = round(reit_total)
    if metals_total > 0:
        avh.setdefault("Precious Metals", {})[year_str] = round(metals_total)
    save_json(DATA_DIR / "asset_value_history.json", avh)

    return {
        "stocks_updated": updated_count,
        "equity_dividends": by_type.get("Equity", 0),
        "reit_dividends": by_type.get("REITs", 0),
        "equity_valuation": round(equity_total),
        "etf_valuation": round(etf_total),
        "reit_valuation": round(reit_total),
        "metals_valuation": round(metals_total),
        "year": parsed["year"],
    }


def load_ibkr_capital_flows() -> dict:
    """Load stored IBKR capital flows: {asset_class: {year_str: net_eur}}."""
    return load_json(DATA_DIR / "ibkr_capital_flows.json", {})


def save_ibkr_capital_flows(flows: dict) -> None:
    """Save IBKR capital flows."""
    save_json(DATA_DIR / "ibkr_capital_flows.json", flows)


# ---------------------------------------------------------------------------
# NEW IBKR import functions (multi-section CSV format)
# ---------------------------------------------------------------------------

def load_symbol_classifications() -> dict:
    """Load symbol classification database: {symbol: category}.
    Categories: ETF, REIT, Precious Metal, Bond.
    Symbols not in this dict are treated as Public Stock (Equity).
    """
    return load_json(DATA_DIR / "symbol_classifications.json", {})


def save_symbol_classification(symbol: str, category: str):
    """Save a single symbol classification to the shared database."""
    path = DATA_DIR / "symbol_classifications.json"
    data = load_json(path, {})
    data[symbol] = category
    data = dict(sorted(data.items()))
    save_json(path, data)


@st.cache_data(ttl=3600, show_spinner=False)
def verify_symbol_classification(symbol: str) -> dict:
    """Use yfinance to auto-detect a symbol's likely classification.
    Returns {"suggested": str, "confidence": str, "reason": str}.
    """
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
    except Exception:
        return {"suggested": "Public Stock", "confidence": "low", "reason": "Failed to fetch data"}

    quote_type = info.get("quoteType", "").upper()
    long_name = (info.get("longName") or info.get("shortName") or "").lower()
    category = (info.get("category") or "").lower()
    sector = (info.get("sector") or "").lower()
    industry = (info.get("industry") or "").lower()
    combined = f"{long_name} {category} {sector} {industry}"

    # REITs - check quoteType first
    if quote_type == "REIT" or "reit" in quote_type:
        return {"suggested": "REIT", "confidence": "high", "reason": f"quoteType={quote_type}"}

    if quote_type == "ETF":
        # Bond ETFs
        bond_kw = ["bond", "treasury", "fixed income", "aggregate bond", "debt", "income fund",
                    "govt", "government bond", "corporate bond", "high yield", "municipal", "tips"]
        if any(kw in combined for kw in bond_kw):
            return {"suggested": "Bond", "confidence": "high", "reason": f"ETF, name/category contains bond keywords"}
        # REIT ETFs
        reit_kw = ["real estate", "reit", "property", "mortgage"]
        if any(kw in combined for kw in reit_kw):
            return {"suggested": "REIT", "confidence": "high", "reason": f"ETF, name/category contains real estate keywords"}
        # Precious Metal ETFs (specific metals only, NOT generic mining)
        pm_kw = ["gold", "silver", "platinum", "palladium", "precious metal", "bullion"]
        if any(kw in combined for kw in pm_kw):
            return {"suggested": "Precious Metal", "confidence": "high", "reason": f"ETF, name/category contains precious metal keywords"}
        # Generic equity ETF
        return {"suggested": "ETF", "confidence": "high", "reason": f"quoteType=ETF"}

    if quote_type == "EQUITY":
        # REIT stocks
        if "reit" in industry or "real estate" in industry:
            return {"suggested": "REIT", "confidence": "high", "reason": f"EQUITY, industry={industry}"}
        # Regular equity
        return {"suggested": "Public Stock", "confidence": "medium", "reason": f"EQUITY, sector={sector}"}

    # Fallback
    return {"suggested": "Public Stock", "confidence": "low", "reason": f"quoteType={quote_type or 'unknown'}"}


def classify_symbol(symbol: str, classifications: dict) -> str:
    """Classify a symbol into an asset class using the classification database.
    Returns one of: ETF, REIT, Precious Metal, Bond, Public Stock.
    """
    sym = symbol.strip()
    # Direct match
    cat = classifications.get(sym)
    if cat:
        return cat
    # Try uppercase
    for db_sym, db_cat in classifications.items():
        if db_sym.upper() == sym.upper():
            return db_cat
    # Try stripping common IBKR suffixes (d, l)
    stripped = sym.rstrip("dlDL")
    if stripped != sym:
        cat = classifications.get(stripped)
        if cat:
            return cat
        for db_sym, db_cat in classifications.items():
            if db_sym.upper() == stripped.upper():
                return db_cat
    # Try splitting on dots (e.g., PRX.DRTS -> PRX, ERUS.ESC -> ERUS)
    if "." in sym:
        base = sym.split(".")[0]
        cat = classifications.get(base)
        if cat:
            return cat
        for db_sym, db_cat in classifications.items():
            if db_sym.upper() == base.upper():
                return db_cat
    return "Public Stock"


def _asset_class_label(category: str) -> str:
    """Map classification category to overview asset class label."""
    return {
        "ETF": "Equity",
        "Public Stock": "Equity",
        "REIT": "REITs",
        "Precious Metal": "Precious Metals",
        "Bond": "Bonds",
    }.get(category, "Equity")


def _split_ibkr_activity_sections(csv_text: str) -> dict:
    """Split an IBKR standard Activity Statement CSV into sections.

    The CSV format has:
    - Column 1: section name (e.g., 'Open Positions', 'Trades', 'Dividends')
    - Column 2: 'Header' or 'Data'
    - Remaining columns: section-specific data

    Returns dict: {section_name: [list of row dicts keyed by header names]}
    """
    import csv as csv_mod
    import io
    sections = {}
    current_section = None
    current_headers = None

    for line in csv_mod.reader(io.StringIO(csv_text)):
        if len(line) < 3:
            continue
        section_name = line[0].strip()
        row_type = line[1].strip()

        if row_type == "Header":
            current_section = section_name
            current_headers = [h.strip() for h in line[2:]]
            if section_name not in sections:
                sections[section_name] = []
        elif row_type == "Data" and current_section == section_name and current_headers:
            row_data = {}
            for i, val in enumerate(line[2:]):
                if i < len(current_headers):
                    row_data[current_headers[i]] = val.strip()
            sections[section_name].append(row_data)

    return sections


def parse_ibkr_activity_statement(csv_text: str) -> dict:
    """Parse the standard IBKR Activity Statement CSV (single file).

    Any IBKR user can download this from:
    Performance & Reports → Statements → Activity → CSV

    Returns dict with same structure as parse_ibkr_positions_csv():
        positions: [{symbol, currency, quantity, mark_price, cost_basis_price,
                     position_value, cost_basis_money, unrealized_pnl, fx_rate}]
        dividends: [{symbol, currency, amount, fx_rate, amount_eur}]
        cash_summary: {currency: {dividends, deposits, withdrawals}}
    And transactions list with same structure as parse_ibkr_transactions_csv():
        transactions: [{symbol, quantity, trade_price, proceeds, cost_basis,
                       pnl, currency, fx_rate, trade_date, net_cash}]
    """
    import re

    sections = _split_ibkr_activity_sections(csv_text)

    # --- Extract FX rates: app rates PRIMARY, IBKR as fallback ---
    # Use app's year-end FX rates for consistency across all data sources
    fx_rates_map = {"EUR": 1.0}
    try:
        app_fx = load_fx_rates()
    except Exception:
        try:
            app_fx = load_json(DATA_DIR / "fx_rates.json", {})
        except Exception:
            app_fx = {}
    for pair, rate in app_fx.items():
        if pair.startswith("EUR") and len(pair) == 6:
            ccy = pair[3:]
            if rate > 0:
                fx_rates_map[ccy] = 1.0 / rate  # EUR/X rate → EUR per 1 unit of X

    # Fallback: use IBKR's Forex Balances for currencies not in app FX rates
    for row in sections.get("Forex Balances", []):
        ccy = row.get("Description", "").strip()
        close_str = row.get("Close Price", "")
        if ccy and close_str and ccy not in fx_rates_map:
            try:
                fx_rates_map[ccy] = float(close_str)
            except (ValueError, TypeError):
                pass

    # --- Extract Positions from Open Positions section ---
    positions = []
    for row in sections.get("Open Positions", []):
        # Only "Summary" rows are actual positions (skip subtotals/totals)
        if row.get("DataDiscriminator", "") != "Summary":
            continue
        symbol = row.get("Symbol", "").strip()
        currency = row.get("Currency", "EUR").strip()
        if not symbol:
            continue

        try:
            quantity = float(row.get("Quantity", 0) or 0)
            mark_price = float(row.get("Close Price", 0) or 0)
            cost_basis_price = float(row.get("Cost Price", 0) or 0)
            position_value = float(row.get("Value", 0) or 0)
            cost_basis_money = float(row.get("Cost Basis", 0) or 0)
            unrealized_pnl = float(row.get("Unrealized P/L", 0) or 0)
        except (ValueError, TypeError):
            continue

        fx_rate = fx_rates_map.get(currency, 1.0)

        positions.append({
            "symbol": symbol,
            "currency": currency,
            "quantity": quantity,
            "mark_price": mark_price,
            "cost_basis_price": cost_basis_price,
            "unrealized_pnl": unrealized_pnl,
            "position_value": position_value,
            "cost_basis_money": cost_basis_money,
            "fx_rate": fx_rate,
        })

    # --- Extract Dividends ---
    dividends = []
    for row in sections.get("Dividends", []):
        desc = row.get("Description", "")
        currency = row.get("Currency", "EUR").strip()
        try:
            amount = float(row.get("Amount", 0) or 0)
        except (ValueError, TypeError):
            continue

        # Extract symbol from description: "TTE(FR0000120271) Cash Dividend..."
        match = re.match(r'^(\S+?)\(', desc)
        symbol = match.group(1) if match else desc.split()[0] if desc else ""
        if not symbol:
            continue

        fx_rate = fx_rates_map.get(currency, 1.0)
        dividends.append({
            "symbol": symbol,
            "currency": currency,
            "amount": amount,
            "fx_rate": fx_rate,
            "amount_eur": round(amount * fx_rate, 2),
        })

    # --- Add Withholding Tax as negative dividends ---
    for row in sections.get("Withholding Tax", []):
        desc = row.get("Description", "")
        currency = row.get("Currency", "EUR").strip()
        try:
            amount = float(row.get("Amount", 0) or 0)
        except (ValueError, TypeError):
            continue

        match = re.match(r'^(\S+?)\(', desc)
        symbol = match.group(1) if match else desc.split()[0] if desc else ""
        if not symbol:
            continue

        fx_rate = fx_rates_map.get(currency, 1.0)
        dividends.append({
            "symbol": symbol,
            "currency": currency,
            "amount": amount,
            "fx_rate": fx_rate,
            "amount_eur": round(amount * fx_rate, 2),
        })

    # --- Extract Cash Summary from Deposits & Withdrawals ---
    cash_summary = {}
    for row in sections.get("Deposits & Withdrawals", []):
        currency = row.get("Currency", "EUR").strip()
        try:
            amount = float(row.get("Amount", 0) or 0)
        except (ValueError, TypeError):
            continue
        if currency not in cash_summary:
            cash_summary[currency] = {"dividends": 0, "deposits": 0, "withdrawals": 0}
        if amount > 0:
            cash_summary[currency]["deposits"] += amount
        else:
            cash_summary[currency]["withdrawals"] += abs(amount)

    # --- Extract Transactions from Trades section ---
    transactions = []
    for row in sections.get("Trades", []):
        if row.get("DataDiscriminator", "") != "Order":
            continue
        symbol = row.get("Symbol", "").strip()
        currency = row.get("Currency", "EUR").strip()
        if not symbol:
            continue

        try:
            quantity = float(row.get("Quantity", "0").replace(",", "") or 0)
            trade_price = float(row.get("T. Price", 0) or 0)
            proceeds = float(row.get("Proceeds", "0").replace(",", "") or 0)
            cost_basis = float(row.get("Basis", "0").replace(",", "") or 0)
            pnl = float(row.get("Realized P/L", "0").replace(",", "") or 0)
        except (ValueError, TypeError):
            continue

        fx_rate = fx_rates_map.get(currency, 1.0)
        # Trade date from "Date/Time" field: "2025-11-20, 03:00:08"
        trade_date_raw = row.get("Date/Time", "")
        trade_date = trade_date_raw.split(",")[0].replace("-", "") if trade_date_raw else ""

        # net_cash: positive = cash received (sell), negative = cash paid (buy)
        # In standard format, Proceeds captures this: positive for sells
        net_cash = proceeds

        transactions.append({
            "symbol": symbol,
            "quantity": quantity,
            "trade_price": trade_price,
            "proceeds": proceeds,
            "cost_basis": cost_basis,
            "pnl": pnl,
            "currency": currency,
            "fx_rate": fx_rate,
            "trade_date": trade_date,
            "net_cash": net_cash,
        })

    return {
        "positions": positions,
        "dividends": dividends,
        "cash_summary": cash_summary,
        "transactions": transactions,
    }


def parse_ibkr_positions_csv(csv_text: str) -> dict:
    """Parse the IBKR positions+dividends CSV (multi-section format).

    This CSV has 3 sections separated by different headers:
    Section 1: Cash summary (CurrencyPrimary, Dividends, Deposits, Withdrawals...)
    Section 2: Open positions (CurrencyPrimary, Symbol, MarkPrice, CostBasisPrice, ...)
    Section 3: Dividends per symbol (CurrencyPrimary, Symbol, Amount, FXRateToBase)

    Returns dict:
        positions: [{symbol, currency, quantity, mark_price, cost_basis_price,
                     unrealized_pnl, position_value, cost_basis_money, fx_rate}]
        dividends: [{symbol, currency, amount, fx_rate, amount_eur}]
        cash_summary: {currency: {dividends, deposits, withdrawals}}
    """
    import csv as csvmod
    import io

    lines = csv_text.strip().split("\n")
    positions = []
    dividends = []
    cash_summary = {}
    section = None  # "cash", "positions", "dividends"

    # Detect sections by header patterns
    for line in lines:
        reader = csvmod.reader(io.StringIO(line))
        try:
            parts = next(reader)
        except StopIteration:
            continue
        if not parts:
            continue

        # Detect section by header
        if parts[0] == "CurrencyPrimary":
            if "Dividends" in parts and "Deposits" in parts:
                section = "cash"
                continue
            elif "MarkPrice" in parts or "CostBasisPrice" in parts:
                section = "positions"
                pos_header = parts
                continue
            elif "Amount" in parts and len(parts) == 4:
                section = "dividends"
                continue
            else:
                continue

        if section == "cash":
            if parts[0] in ("BASE_SUMMARY", ""):
                continue
            try:
                ccy = parts[0]
                cash_summary[ccy] = {
                    "dividends": float(parts[1] or 0),
                    "deposits": float(parts[4] or 0),
                    "withdrawals": float(parts[7] or 0),
                }
            except (IndexError, ValueError):
                continue

        elif section == "positions":
            try:
                row = dict(zip(pos_header, parts))
                sym = row.get("Symbol", "").strip()
                if not sym:
                    continue
                positions.append({
                    "symbol": sym,
                    "currency": row.get("CurrencyPrimary", "USD"),
                    "quantity": float(row.get("Quantity", 0) or 0),
                    "mark_price": float(row.get("MarkPrice", 0) or 0),
                    "cost_basis_price": float(row.get("CostBasisPrice", 0) or 0),
                    "unrealized_pnl": float(row.get("FifoPnlUnrealized", 0) or 0),
                    "position_value": float(row.get("PositionValue", 0) or 0),
                    "cost_basis_money": float(row.get("CostBasisMoney", 0) or 0),
                    "fx_rate": float(row.get("FXRateToBase", 1) or 1),
                })
            except (ValueError, KeyError):
                continue

        elif section == "dividends":
            try:
                ccy = parts[0]
                sym = parts[1].strip()
                amount = float(parts[2] or 0)
                fx_rate = float(parts[3] or 1)
                if not sym:
                    continue
                dividends.append({
                    "symbol": sym,
                    "currency": ccy,
                    "amount": amount,
                    "fx_rate": fx_rate,
                    "amount_eur": round(amount * fx_rate, 2),
                })
            except (IndexError, ValueError):
                continue

    return {
        "positions": positions,
        "dividends": dividends,
        "cash_summary": cash_summary,
    }


def parse_ibkr_transactions_csv(csv_text: str) -> list:
    """Parse the IBKR transactions CSV.

    Format: Symbol, Quantity, TradePrice, Proceeds, CostBasis, FifoPnlRealized,
            CurrencyPrimary, FXRateToBase, TradeDate, NetCash

    Returns list of dicts: [{symbol, quantity, proceeds, cost_basis, pnl,
                             currency, fx_rate, trade_date, net_cash}]
    """
    import csv as csvmod
    import io

    reader = csvmod.DictReader(io.StringIO(csv_text))
    transactions = []
    for row in reader:
        try:
            sym = row.get("Symbol", "").strip()
            if not sym:
                continue
            transactions.append({
                "symbol": sym,
                "quantity": float(row.get("Quantity", 0) or 0),
                "trade_price": float(row.get("TradePrice", 0) or 0),
                "proceeds": float(row.get("Proceeds", 0) or 0),
                "cost_basis": float(row.get("CostBasis", 0) or 0),
                "pnl": float(row.get("FifoPnlRealized", 0) or 0),
                "currency": row.get("CurrencyPrimary", "USD"),
                "fx_rate": float(row.get("FXRateToBase", 1) or 1),
                "trade_date": row.get("TradeDate", ""),
                "net_cash": float(row.get("NetCash", 0) or 0),
            })
        except (ValueError, KeyError):
            continue
    return transactions


def is_fx_symbol(symbol: str) -> bool:
    """Check if a symbol is an FX pair (e.g., EUR.USD, GBP.USD)."""
    parts = symbol.split(".")
    if len(parts) == 2:
        ccys = {"EUR", "USD", "GBP", "HKD", "JPY", "CHF", "CAD", "AUD", "NZD", "MXN", "CNH", "CNY"}
        return parts[0].upper() in ccys and parts[1].upper() in ccys
    return False


def compute_ibkr_import(positions_csv: str, transactions_csv: str, year: int,
                        *, activity_statement: str = None) -> dict:
    """Main IBKR import function: parses CSVs and classifies everything.

    Accepts either:
    - Standard Activity Statement (single file): pass activity_statement=csv_text
    - Custom Report (two files): pass positions_csv + transactions_csv

    Returns dict:
        year: int
        positions_by_class: {asset_class: [{symbol, quantity, value_eur, cost_eur, ...}]}
        dividends_by_class: {asset_class: float}  (total EUR per class)
        dividends_by_symbol: {symbol: {amount_eur, category}}
        net_capital_by_class: {asset_class: float}  (net buys - sells in EUR)
        valuations_by_class: {asset_class: float}  (year-end market value EUR)
        unclassified: [symbols not in DB]
    """
    classifications = load_symbol_classifications()
    year_str = str(year)

    # Parse CSVs — either standard or custom format
    if activity_statement:
        parsed = parse_ibkr_activity_statement(activity_statement)
        pos_data = parsed  # has positions, dividends, cash_summary
        transactions = parsed["transactions"]
    else:
        pos_data = parse_ibkr_positions_csv(positions_csv)
        transactions = parse_ibkr_transactions_csv(transactions_csv)

    # --- Positions: classify and compute valuations ---
    positions_by_class = {}
    valuations_by_class = {}
    unclassified = set()

    for pos in pos_data["positions"]:
        sym = pos["symbol"]
        cat = classify_symbol(sym, classifications)
        ac = _asset_class_label(cat)
        value_eur = round(pos["position_value"] * pos["fx_rate"], 2)
        cost_eur = round(pos["cost_basis_money"] * pos["fx_rate"], 2)

        entry = {
            "symbol": sym,
            "category": cat,
            "asset_class": ac,
            "currency": pos["currency"],
            "quantity": pos["quantity"],
            "mark_price": pos["mark_price"],
            "cost_basis_price": pos["cost_basis_price"],
            "value_eur": value_eur,
            "cost_eur": cost_eur,
            "fx_rate": pos["fx_rate"],
        }
        positions_by_class.setdefault(ac, []).append(entry)
        valuations_by_class[ac] = valuations_by_class.get(ac, 0) + value_eur

        if cat == "Public Stock" and sym not in classifications:
            unclassified.add(sym)

    # --- Dividends: classify and aggregate ---
    dividends_by_class = {}
    dividends_by_symbol = {}

    for div in pos_data["dividends"]:
        sym = div["symbol"]
        # Strip .DRTS suffix for dividend rights
        clean_sym = sym.split(".")[0] if ".DRTS" in sym else sym
        cat = classify_symbol(clean_sym, classifications)
        ac = _asset_class_label(cat)

        amt_eur = div["amount_eur"]
        dividends_by_class[ac] = dividends_by_class.get(ac, 0) + amt_eur
        if clean_sym not in dividends_by_symbol:
            dividends_by_symbol[clean_sym] = {"amount_eur": 0, "category": cat, "asset_class": ac}
        dividends_by_symbol[clean_sym]["amount_eur"] += amt_eur

    # Round dividend totals
    for ac in dividends_by_class:
        dividends_by_class[ac] = round(dividends_by_class[ac], 2)
    for sym in dividends_by_symbol:
        dividends_by_symbol[sym]["amount_eur"] = round(dividends_by_symbol[sym]["amount_eur"], 2)

    # --- Transactions: compute net capital per asset class ---
    net_capital_by_class = {}

    for tx in transactions:
        sym = tx["symbol"]
        # Skip FX pairs
        if is_fx_symbol(sym):
            continue
        cat = classify_symbol(sym, classifications)
        ac = _asset_class_label(cat)

        # NetCash: positive for sells (cash in), 0 for buys (they show as cost basis rows)
        # Proceeds: positive for sells, empty/0 for buys
        # For net capital: we want buys (cash out) - sells (cash in)
        # net_cash is the actual cash impact: positive = cash received, negative = cash paid
        net_cash_eur = tx["net_cash"] * tx["fx_rate"]

        net_capital_by_class[ac] = net_capital_by_class.get(ac, 0) - net_cash_eur

    # Round
    for ac in net_capital_by_class:
        net_capital_by_class[ac] = round(net_capital_by_class[ac])

    # Round valuations
    for ac in valuations_by_class:
        valuations_by_class[ac] = round(valuations_by_class[ac])

    # --- Sold positions: symbols traded during period but not in Open Positions ---
    sold_positions = []
    # Aggregate trades by symbol
    trades_by_sym = {}
    for tx in transactions:
        sym = tx["symbol"]
        if is_fx_symbol(sym):
            continue
        if sym not in trades_by_sym:
            trades_by_sym[sym] = {"qty": 0, "proceeds_eur": 0, "realized_pnl_eur": 0}
        trades_by_sym[sym]["qty"] += tx["quantity"]
        trades_by_sym[sym]["proceeds_eur"] += tx["net_cash"] * tx["fx_rate"]
        trades_by_sym[sym]["realized_pnl_eur"] += tx.get("pnl", 0) * tx["fx_rate"]

    # Symbols in trades but NOT in open positions = sold during period
    open_syms = {p["symbol"] for p in pos_data["positions"]}
    for sym, data in trades_by_sym.items():
        if sym not in open_syms:
            cat = classify_symbol(sym, classifications)
            ac = _asset_class_label(cat)
            sold_positions.append({
                "symbol": sym,
                "asset_class": ac,
                "proceeds_eur": round(data["proceeds_eur"]),
                "realized_pnl_eur": round(data["realized_pnl_eur"]),
            })

    return {
        "year": year,
        "positions_by_class": positions_by_class,
        "dividends_by_class": dividends_by_class,
        "dividends_by_symbol": dividends_by_symbol,
        "net_capital_by_class": net_capital_by_class,
        "valuations_by_class": valuations_by_class,
        "sold_positions": sold_positions,
        "unclassified": sorted(unclassified),
    }


def apply_ibkr_import(result: dict) -> dict:
    """Apply the computed IBKR import results to the data files.

    Updates:
    - public_stocks.json: merged positions (Equity, ETF, REIT, Precious Metal)
    - asset_value_history.json: year-end valuations per sub-class
    - dividend_config.json: actual dividends per asset class
    - ibkr_capital_flows.json: net capital per asset class
    - cashflow.json: asset_sale_breakdown for net sales
    """
    year_str = str(result["year"])

    # 0. Update positions in public_stocks.json
    existing_positions = load_json(DATA_DIR / "public_stocks.json", [])
    existing_map = {}
    for p in existing_positions:
        key = p.get("ticker", "").upper()
        if key:
            existing_map[key] = p

    # Build new position list from IBKR data
    all_ibkr_positions = []
    for ac, positions in result["positions_by_class"].items():
        for pos in positions:
            all_ibkr_positions.append(pos)

    # Merge: update existing, add new
    seen_tickers = set()
    for pos in all_ibkr_positions:
        sym = pos["symbol"]
        sym_upper = sym.upper()
        seen_tickers.add(sym_upper)

        # Map category to type field
        type_map = {
            "ETF": "ETF",
            "REIT": "REIT",
            "Precious Metal": "Precious Metals",
            "Bond": "Bond",
            "Public Stock": "Equity",
        }
        pos_type = type_map.get(pos["category"], "Equity")

        if sym_upper in existing_map:
            # Update existing position
            p = existing_map[sym_upper]
            p["quantity"] = pos["quantity"]
            p["value_eur"] = round(pos["value_eur"], 2)
            p["cost_eur"] = round(pos["cost_eur"], 2)
            p["value_local"] = round(pos["quantity"] * pos["mark_price"], 2)
            p["cost_local"] = round(pos["cost_basis_price"] * pos["quantity"], 2)
            p["currency"] = pos["currency"]
            p["type"] = pos_type
            p["return_pct"] = round((pos["value_eur"] / pos["cost_eur"] - 1) * 100, 1) if pos["cost_eur"] > 0 else 0
            p["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        else:
            # New position
            new_pos = {
                "id": new_id(),
                "ticker": sym,
                "name": sym,
                "type": pos_type,
                "currency": pos["currency"],
                "quantity": pos["quantity"],
                "cost_eur": round(pos["cost_eur"], 2),
                "value_eur": round(pos["value_eur"], 2),
                "cost_local": round(pos["cost_basis_price"] * pos["quantity"], 2),
                "value_local": round(pos["quantity"] * pos["mark_price"], 2),
                "net_div_eur": 0.0,
                "return_pct": round((pos["value_eur"] / pos["cost_eur"] - 1) * 100, 1) if pos["cost_eur"] > 0 else 0,
                "last_updated": datetime.now().strftime("%Y-%m-%d"),
            }
            existing_positions.append(new_pos)

    # Update dividends per position
    for sym, div_info in result.get("dividends_by_symbol", {}).items():
        sym_upper = sym.upper()
        for p in existing_positions:
            if p.get("ticker", "").upper() == sym_upper:
                p["net_div_eur"] = round(div_info["amount_eur"], 2)
                break

    save_json(DATA_DIR / "public_stocks.json", existing_positions)

    # 1. Update asset_value_history with year-end valuations
    avh = load_json(DATA_DIR / "asset_value_history.json", {})

    # Split Equity into Equity vs ETF sub-categories
    classifications = load_symbol_classifications()
    equity_val = 0
    etf_val = 0
    reit_val = 0
    metals_val = 0
    bonds_val = 0

    for ac, positions in result["positions_by_class"].items():
        for pos in positions:
            val = pos["value_eur"]
            cat = pos["category"]
            if cat == "ETF":
                etf_val += val
            elif cat == "REIT":
                reit_val += val
            elif cat == "Precious Metal":
                metals_val += val
            elif cat == "Bond":
                bonds_val += val
            else:
                equity_val += val

    avh.setdefault("Equity", {})[year_str] = round(equity_val)
    avh.setdefault("ETF", {})[year_str] = round(etf_val)
    avh.setdefault("REITs", {})[year_str] = round(reit_val)
    if metals_val > 0:
        avh.setdefault("Precious Metals", {})[year_str] = round(metals_val)
    if bonds_val > 0:
        avh.setdefault("Bonds", {})[year_str] = round(bonds_val)
    save_json(DATA_DIR / "asset_value_history.json", avh)

    # 2. Update dividend_config actual_dividends
    div_config = load_json(DATA_DIR / "dividend_config.json", {})
    actuals = div_config.setdefault("actual_dividends", {})

    # Aggregate dividends by sub-category
    div_equity = 0
    div_reit = 0
    div_metals = 0
    div_bond = 0
    for sym, info in result["dividends_by_symbol"].items():
        cat = info["category"]
        amt = info["amount_eur"]
        if cat in ("ETF", "Public Stock"):
            div_equity += amt
        elif cat == "REIT":
            div_reit += amt
        elif cat == "Precious Metal":
            div_metals += amt
        elif cat == "Bond":
            div_bond += amt

    if div_equity > 0:
        actuals.setdefault("Equity", {})[year_str] = round(div_equity)
    if div_reit > 0:
        actuals.setdefault("REITs", {})[year_str] = round(div_reit)
    if div_metals > 0:
        actuals.setdefault("Precious Metals", {})[year_str] = round(div_metals)
    save_json(DATA_DIR / "dividend_config.json", div_config)

    # 3. Save net capital flows to ibkr_capital_flows.json
    existing_flows = load_ibkr_capital_flows()
    flow_key_map = {
        "Equity": "Equity",
        "REITs": "REIT",
        "Precious Metals": "Precious Metals",
        "Bonds": "Bond",
    }
    # IBKR sign convention: negative net_cash = bought, positive = sold
    # Our convention: positive New Capital = invested, negative = sold
    # So we negate the IBKR value
    plan = load_json(DATA_DIR / "investment_plan.json", {})
    if not isinstance(plan, dict): plan = {}
    by_year = plan.get("planned_investment_by_year", {})
    plan_ac_map = {
        "Equity": "Equity",
        "REITs": "REITs",
        "Precious Metals": "Precious Metals",
        "Bonds": "Bonds",
    }
    for ac, net in result["net_capital_by_class"].items():
        flow_key = flow_key_map.get(ac, ac)
        existing_flows.setdefault(flow_key, {})[year_str] = net
        # Also write to planned_investment_by_year so it shows in valuation tab
        plan_key = plan_ac_map.get(ac, ac)
        by_year.setdefault(plan_key, {})[year_str] = net
    save_ibkr_capital_flows(existing_flows)
    plan["planned_investment_by_year"] = by_year
    save_json(DATA_DIR / "investment_plan.json", plan)

    # 5. Save raw IBKR data centrally for future reference
    ibkr_db = load_json(DATA_DIR / "ibkr_database.json", {})
    ibkr_db[year_str] = {
        "imported_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "positions_by_class": {
            ac: [
                {
                    "symbol": p["symbol"], "category": p["category"],
                    "currency": p["currency"], "quantity": round(p["quantity"], 4),
                    "mark_price": round(p["mark_price"], 4),
                    "cost_basis_price": round(p.get("cost_basis_price", 0), 4),
                    "value_eur": round(p["value_eur"], 2),
                    "cost_eur": round(p["cost_eur"], 2),
                } for p in positions
            ]
            for ac, positions in result["positions_by_class"].items()
        },
        "dividends_by_symbol": {
            sym: {"amount_eur": round(info["amount_eur"], 2), "category": info["category"],
                  "asset_class": info["asset_class"]}
            for sym, info in result.get("dividends_by_symbol", {}).items()
        },
        "dividends_by_class": result["dividends_by_class"],
        "net_capital_by_class": result["net_capital_by_class"],
        "valuations_by_class": result["valuations_by_class"],
        "summary": {
            "equity_val": round(equity_val),
            "etf_val": round(etf_val),
            "reit_val": round(reit_val),
            "metals_val": round(metals_val),
            "bonds_val": round(bonds_val),
        },
    }
    save_json(DATA_DIR / "ibkr_database.json", ibkr_db)

    return {
        "year": result["year"],
        "equity_val": round(equity_val),
        "etf_val": round(etf_val),
        "reit_val": round(reit_val),
        "metals_val": round(metals_val),
        "bonds_val": round(bonds_val),
        "dividends": result["dividends_by_class"],
        "net_capital": result["net_capital_by_class"],
    }


def load_ibkr_database() -> dict:
    """Load the central IBKR database with all imported raw+summary data per year."""
    return load_json(DATA_DIR / "ibkr_database.json", {})


def get_ibkr_new_capital(asset_class: str, year: int) -> float | None:
    """Get IBKR-sourced net capital for an asset class/year. Returns None if no IBKR data."""
    flows = load_ibkr_capital_flows()
    ac_flows = flows.get(asset_class)
    if ac_flows is None:
        return None
    val = ac_flows.get(str(year))
    return val  # None if not present, else the amount


def parse_ib_activity_statement(csv_text: str) -> dict:
    """Parse IB Activity Statement CSV and classify positions.

    Returns dict with keys: stocks, bonds, metals.
    Uses the Asset Category column (STK, BOND, CMDTY) when available,
    otherwise falls back to heuristics.
    """
    # Load existing REIT tickers for classification
    existing = load_json(DATA_DIR / "public_stocks.json", [])
    reit_tickers = {p.get("ticker", "").upper() for p in existing if p.get("type") == "REIT"}

    stocks = []
    bonds = []
    metals = []

    lines = csv_text.strip().split("\n")
    header = None

    # Known metal tickers/keywords
    metal_keywords = {"GLD", "SLV", "IAU", "PPLT", "PALL", "GDX", "GDXJ", "SIL", "SILJ",
                      "SAFE", "GOLD", "PHYS", "PSLV", "SGOL", "AAAU"}

    for line in lines:
        parts = [p.strip().strip('"') for p in line.split(",")]
        if len(parts) < 3:
            continue
        if parts[0] == "Open Positions" and parts[1] == "Header":
            header = parts
            continue
        if parts[0] == "Open Positions" and parts[1] == "Data":
            if parts[2] in ("Total", "SubTotal", ""):
                continue
            if header is None:
                continue
            row = dict(zip(header[2:], parts[2:]))
            try:
                symbol = row.get("Symbol", "")
                asset_cat = row.get("Asset Category", row.get("Asset Class", "")).upper()
                currency = row.get("Currency", "USD")
                quantity = float(row.get("Quantity", 0) or 0)
                cost = float(row.get("Cost Price", row.get("Average Cost", 0)) or 0)
                price = float(row.get("Close Price", row.get("Mark Price", 0)) or 0)
                desc = row.get("Description", symbol)

                if asset_cat == "BOND":
                    bonds.append({
                        "id": new_id(),
                        "name": desc,
                        "currency": currency,
                        "face_value": abs(quantity),
                        "purchase_price": cost,
                        "coupon_rate_pct": 0.0,  # needs manual entry
                        "maturity_date": "",       # needs manual entry
                        "current_value_eur": abs(quantity) * price / 100,  # bonds quoted as % of face
                    })
                elif asset_cat == "CMDTY" or symbol.upper() in metal_keywords:
                    metals.append({
                        "id": new_id(),
                        "metal": "Gold" if "GOLD" in desc.upper() or "GLD" in symbol.upper() or "GDX" in symbol.upper() else "Silver" if "SILV" in desc.upper() or "SLV" in symbol.upper() or "SIL" in symbol.upper() else "Other",
                        "form": "ETF",
                        "ticker": symbol,
                        "quantity_oz": quantity,
                        "purchase_price_eur": cost,
                        "current_price_eur": price,
                        "notes": f"Imported from IB: {desc}",
                    })
                else:
                    # Stock/ETF/REIT
                    pos_type = "REIT" if symbol.upper() in reit_tickers else "Equity"
                    stocks.append({
                        "id": new_id(),
                        "ticker": symbol,
                        "name": desc,
                        "type": pos_type,
                        "currency": currency,
                        "quantity": quantity,
                        "cost_basis": cost,
                        "current_price": price,
                        "net_div_eur": 0.0,
                        "last_updated": datetime.now().isoformat(),
                    })
            except (ValueError, KeyError):
                continue
    return {"stocks": stocks, "bonds": bonds, "metals": metals}


def merge_ib_positions(existing: list, imported: list, match_key: str = "ticker") -> list:
    """Merge imported IB positions into existing, matching by match_key.

    - Matched: updates quantity, prices, last_updated; preserves manual fields (net_div_eur, type, etc.)
    - New: appends with new ID
    Returns merged list.
    """
    existing_map = {}
    for p in existing:
        key = p.get(match_key, "").upper()
        if key:
            existing_map[key] = p

    merged = list(existing)  # start with copy
    for imp in imported:
        key = imp.get(match_key, "").upper()
        if key and key in existing_map:
            # Update existing position
            pos = existing_map[key]
            pos["quantity"] = imp.get("quantity", pos.get("quantity", 0))
            pos["current_price"] = imp.get("current_price", pos.get("current_price", 0))
            pos["cost_basis"] = imp.get("cost_basis", pos.get("cost_basis", 0))
            pos["last_updated"] = datetime.now().isoformat()
            # Preserve: net_div_eur, type, name (manual fields)
        else:
            # New position
            imp["id"] = new_id()
            merged.append(imp)
    return merged


import ast
import operator

def _get_fx_variables() -> dict:
    """Get FX rate variables for use in formula evaluation.
    Returns dict like {'EURUSD': 1.15, 'EURINR': 103, 'USDEUR': 0.869...}.
    Supports both EURXXX and XXXEUR (inverse) lookups.
    """
    fx = load_fx_rates()
    variables = {}
    for pair, rate in fx.items():
        pair_upper = pair.upper()
        variables[pair_upper] = rate
        # Also create inverse: EURUSD -> USDEUR
        if len(pair_upper) == 6:
            base = pair_upper[:3]
            quote = pair_upper[3:]
            inverse_key = quote + base
            if inverse_key not in variables and rate > 0:
                variables[inverse_key] = round(1.0 / rate, 6)
    return variables


def safe_eval_math(expr_str, fx_vars: dict = None) -> float | None:
    """Safely evaluate simple math expressions like '500*2', '1000+500', '100/EURUSD'.
    Supports: +, -, *, /, parentheses, integers, floats, FX shortcuts (EURUSD, EURINR, etc).
    Expressions starting with '=' are treated as formulas (the '=' is stripped).
    Returns None if the expression is invalid or not a string.
    """
    if not isinstance(expr_str, str):
        try:
            return float(expr_str)
        except (TypeError, ValueError):
            return None
    expr_str = expr_str.strip()
    # Strip leading '=' for Excel-like formulas
    if expr_str.startswith('='):
        expr_str = expr_str[1:].strip()
    expr_str = expr_str.replace(',', '')  # Remove commas
    if not expr_str:
        return None
    try:
        return float(expr_str)
    except ValueError:
        pass

    # Substitute FX variables (EURUSD, EURINR, etc) with their values
    if fx_vars is None:
        # Only load FX vars if expression contains alpha chars (potential FX ref)
        import re
        if re.search(r'[A-Za-z]', expr_str):
            fx_vars = _get_fx_variables()
    if fx_vars:
        import re
        # Replace FX variable names with their numeric values (longest match first)
        for var_name in sorted(fx_vars.keys(), key=len, reverse=True):
            expr_str = re.sub(r'\b' + var_name + r'\b', str(fx_vars[var_name]), expr_str, flags=re.IGNORECASE)

    allowed_ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.USub: operator.neg,
    }
    def _eval(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        elif isinstance(node, ast.BinOp) and type(node.op) in allowed_ops:
            return allowed_ops[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp) and type(node.op) in allowed_ops:
            return allowed_ops[type(node.op)](_eval(node.operand))
        raise ValueError("Unsupported expression")
    try:
        tree = ast.parse(expr_str, mode='eval')
        return _eval(tree.body)
    except Exception:
        return None


def _is_formula(s: str) -> bool:
    """True if string is a formula (contains operators or FX vars), not just a plain number."""
    if not isinstance(s, str):
        return False
    s = s.strip().lstrip("=").replace(",", "")
    if not s:
        return False
    try:
        float(s)
        return False  # It's just a plain number
    except ValueError:
        return True  # Contains operators, FX vars, etc.


def _normalize_formula(s: str) -> str:
    """Ensure formula string starts with '=' prefix."""
    s = str(s).strip()
    if not s.startswith("="):
        s = "=" + s
    return s


def process_math_in_df(df, numeric_columns, editor_key=None):
    """Process math expressions in DataFrame columns from st.data_editor.
    For each specified column, evaluate string math expressions and replace with numeric result.
    Supports FX shortcuts like EURUSD, EURINR.

    If editor_key is provided, formulas are persisted to formulas.json so they can be
    shown again on re-edit (Excel-like: display value, edit shows formula).
    """
    import pandas as pd
    import re
    # Pre-load FX vars once if any column has alpha chars
    fx_vars = None
    for col in numeric_columns:
        if col in df.columns:
            for val in df[col]:
                if isinstance(val, str) and re.search(r'[A-Za-z]', val):
                    fx_vars = _get_fx_variables()
                    break
            if fx_vars:
                break

    # Load existing formulas for persistence
    formulas = {}
    if editor_key:
        formulas = load_json(DATA_DIR / "formulas.json", {})

    for col in numeric_columns:
        if col not in df.columns:
            continue
        for idx in df.index:
            val = df.at[idx, col]
            if pd.isna(val):
                continue
            str_val = str(val).strip()
            result = safe_eval_math(str_val, fx_vars=fx_vars)
            if result is not None:
                if editor_key and _is_formula(str_val):
                    # Store the formula (with = prefix)
                    formulas[f"{editor_key}::{idx}::{col}"] = _normalize_formula(str_val)
                elif editor_key:
                    # Plain number — remove any old formula
                    formulas.pop(f"{editor_key}::{idx}::{col}", None)
                df.at[idx, col] = result
            # If result is None, keep original value

    if editor_key:
        save_json(DATA_DIR / "formulas.json", formulas)
    return df


def inject_formulas_for_edit(df, editor_key, numeric_columns):
    """Replace computed values with stored formulas for editing.
    This gives Excel-like behavior: cells display numbers, but when user
    double-clicks to edit, they see the formula (e.g., =500*2).
    """
    formulas = load_json(DATA_DIR / "formulas.json", {})
    for col in numeric_columns:
        if col not in df.columns:
            continue
        for idx in df.index:
            fkey = f"{editor_key}::{idx}::{col}"
            if fkey in formulas:
                df.at[idx, col] = formulas[fkey]
    # Cast to string dtype so TextColumn is compatible with numeric data
    for col in numeric_columns:
        if col in df.columns:
            df[col] = df[col].astype(str)
    return df


def get_formula_map(editor_key, num_rows, columns):
    """Build a formula_map for AgGrid tooltips: {col: {row_idx: "=formula"}}.
    Used by render_aggrid_table to show formula tooltips on hover.
    """
    formulas = load_json(DATA_DIR / "formulas.json", {})
    formula_map = {}
    for col in columns:
        col_formulas = {}
        for row_idx in range(num_rows):
            fkey = f"{editor_key}::{row_idx}::{col}"
            if fkey in formulas:
                col_formulas[row_idx] = formulas[fkey]
        if col_formulas:
            formula_map[col] = col_formulas
    return formula_map
