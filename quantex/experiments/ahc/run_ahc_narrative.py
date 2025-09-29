import os
import sys
from datetime import datetime, timedelta

import pandas as pd
from dotenv import load_dotenv

from quantex.experiments.ahc.run_ahc_mvp import fetch_ohlcv, CUTOFF_DATE_STR
from quantex.core.llm_manager import generate_completion, MODEL_CONFIG


# =============== Agente Historiador Compuesto (AHC) ===============
PROMPT_PATH = os.path.join(os.path.dirname(__file__), 'prompt_ahc.md')


def load_system_prompt() -> str:
    try:
        with open(PROMPT_PATH, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return (
            "Rol: Agente Historiador Compuesto (AHC). Explica puntos de inflexión hasta 2025-01-01. "
            "No proyectes ni uses información posterior al cutoff. Formato: lista Markdown cronológica."
        )


def _compute_abs_window_return(close: pd.Series, lookback_days: int) -> pd.Series:
    s = close.astype(float)
    s_lag = s.shift(lookback_days)
    pct = (s / s_lag - 1.0).abs()
    return pct.dropna()


def _safe_direction(df: pd.DataFrame, date: pd.Timestamp, lookback_days: int) -> tuple[float | None, str]:
    try:
        prev_dt = date - pd.Timedelta(days=lookback_days)
        if prev_dt in df.index and date in df.index:
            move = float(df['close'].loc[date] / df['close'].loc[prev_dt] - 1.0)
            direction = 'sube' if move >= 0 else 'baja'
            return move, direction
    except Exception:
        pass
    return None, 'desconocido'


def find_major_inflections(df: pd.DataFrame, top_n: int = 50, lookback_days: int = 60, cutoff_date: pd.Timestamp | None = None) -> list:
    if 'close' not in df.columns or df.empty:
        return []

    pct = _compute_abs_window_return(df['close'], lookback_days)
    if pct.empty:
        return []

    pct_df = pct.to_frame(name='abs_return')
    pct_df['date'] = pct_df.index
    pct_df['year'] = pct_df['date'].dt.year

    # 1) Máximo por año
    yearly_candidates = (
        pct_df.loc[pct_df.groupby('year')['abs_return'].idxmax()].copy()
        if not pct_df.empty else pd.DataFrame(columns=['date', 'abs_return'])
    )

    selected = []
    if not yearly_candidates.empty:
        selected.extend(list(yearly_candidates.itertuples(index=False)))

    # 2) Cobertura reciente (últimos 5 años antes del cutoff)
    if cutoff_date is None:
        cutoff_date = pd.to_datetime('2025-01-01')
    recent_start = cutoff_date - pd.Timedelta(days=5*365)
    recent = pct_df[pct_df['date'] >= recent_start]
    if not recent.empty:
        recent_top = recent.nlargest(3, 'abs_return')
        selected.extend(list(recent_top.itertuples(index=False)))

    # 2b) Forzar al menos 1 punto en los últimos 12 meses antes del cutoff
    last12_start = cutoff_date - pd.Timedelta(days=365)
    last12 = pct_df[(pct_df['date'] >= last12_start) & (pct_df['date'] < cutoff_date)]
    if not last12.empty:
        last12_top = last12.nlargest(1, 'abs_return')
        selected.extend(list(last12_top.itertuples(index=False)))

    # 2c) Forzar el último día disponible antes del cutoff
    last_day = df.index[df.index < cutoff_date].max()
    if pd.notna(last_day):
        move, _ = _safe_direction(df, last_day, lookback_days)
        if move is not None:
            selected.append(type('Row', (), {'date': last_day, 'abs_return': abs(move)}))

    # 3) Completar con top global si faltan
    if len(selected) < top_n:
        remaining = pct_df[~pct_df['date'].isin([r.date for r in selected])]
        if not remaining.empty:
            extra = remaining.nlargest(top_n * 2, 'abs_return')
            selected.extend(list(extra.itertuples(index=False)))

    # 4) Thinning y recorte a top_n por magnitud
    selected_sorted = sorted(selected, key=lambda r: r.abs_return, reverse=True)
    unique = []
    used_dates = []
    for r in selected_sorted:
        dt = r.date
        if all(abs((dt - u).days) >= 14 for u in used_dates):
            unique.append(r)
            used_dates.append(dt)
        if len(unique) >= top_n:
            break

    unique_sorted = sorted(unique, key=lambda r: r.date)
    out = []
    for r in unique_sorted:
        move, direction = _safe_direction(df, r.date, lookback_days)
        out.append({
            'date': r.date.strftime('%Y-%m-%d'),
            'window_days': lookback_days,
            'abs_return': float(r.abs_return),
            'direction': direction
        })
    return out


def calculate_monthly_data(df: pd.DataFrame, cutoff_date: pd.Timestamp) -> list:
    """Calcula datos mensuales para el análisis continuo."""
    if df.empty or 'close' not in df.columns:
        return []
    
    # Filtrar datos hasta el cutoff
    df_filtered = df[df.index < cutoff_date]
    if df_filtered.empty:
        return []
    
    monthly_data = []
    
    # Agrupar por mes
    df_monthly = df_filtered.resample('M').agg({
        'close': ['first', 'last', 'min', 'max']
    }).dropna()
    
    for month_end in df_monthly.index:
        month_start = month_end.replace(day=1)
        
        # Obtener datos del mes
        month_data = df_filtered[(df_filtered.index >= month_start) & (df_filtered.index <= month_end)]
        if month_data.empty:
            continue
            
        first_close = month_data['close'].iloc[0]
        last_close = month_data['close'].iloc[-1]
        monthly_return = (last_close / first_close - 1.0) * 100
        
        # Calcular volatilidad aproximada (desviación estándar de retornos diarios)
        daily_returns = month_data['close'].pct_change().dropna()
        volatility = daily_returns.std() * 100 if len(daily_returns) > 1 else 0.0
        
        # Determinar dirección del movimiento
        if monthly_return > 2.0:
            direction = "subió"
        elif monthly_return < -2.0:
            direction = "bajó"
        else:
            direction = "lateral"
        
        monthly_data.append({
            'period': month_end.strftime('%Y-%m'),
            'return_pct': round(monthly_return, 1),
            'direction': direction,
            'volatility': round(volatility, 1),
            'days_traded': len(month_data)
        })
    
    return monthly_data


def build_user_prompt(instrument_name: str, inflections: list, monthly_data: list, start_date_str: str | None = None, cutoff_date_str: str | None = None) -> str:
    lines = [
        f"Instrumento: {instrument_name}.",
    ]
    if start_date_str and cutoff_date_str:
        lines.append(f"Analiza solo el período desde {start_date_str} hasta {cutoff_date_str}.")
    else:
        lines.append("Analiza solo hasta 2025-01-01.")
    
    lines.append(f"Fechas candidatas a PUNTOS DE INFLEXIÓN (cobertura por año y magnitud, incluye 2024) - {len(inflections)} puntos:")
    for it in inflections:
        lines.append(f"- {it['date']} (mov.{it['direction']}, |ret|~{round(100*it['abs_return'],1)}%, ventana {it['window_days']}d)")
    
    lines.append(f"\nAnálisis mensual - {len(monthly_data)} meses:")
    for month in monthly_data:
        lines.append(f"- {month['period']}: {month['direction']} {month['return_pct']:+.1f}% (volatilidad {month['volatility']:.1f}%, {month['days_traded']} días)")
    
    return "\n".join(lines)


def run_ahc_narrative(identifier: str = 'SPIPSA.INDX', years: int = 20, cutoff_date_str: str = CUTOFF_DATE_STR, start_date_str: str | None = None) -> str | None:
    load_dotenv()
    if not cutoff_date_str:
        cutoff_date_str = '2025-01-01'

    days = int(years * 365 + 30)
    df = fetch_ohlcv(identifier, days)
    if df is None or df.empty or 'close' not in df.columns:
        print(f"No hay datos para {identifier}.")
        return None

    # Filtro por inicio si se entrega
    if start_date_str:
        start = pd.to_datetime(start_date_str)
        df = df[df.index >= start]
        if df.empty:
            print(f"Sin datos desde {start_date_str} para {identifier}.")
            return None

    cutoff = pd.to_datetime(cutoff_date_str)
    df = df[df.index < cutoff]
    if df.empty:
        print("Serie vacía antes del cutoff.")
        return None

    inflections = find_major_inflections(df, top_n=50, lookback_days=60, cutoff_date=cutoff)
    monthly_data = calculate_monthly_data(df, cutoff)
    
    if not inflections and not monthly_data:
        print("No se detectaron inflexiones ni datos mensuales.")
        return None

    system_prompt = load_system_prompt()
    user_prompt = build_user_prompt(identifier, inflections, monthly_data, start_date_str, cutoff_date_str)
    resp = generate_completion(
        task_complexity='complex',
        system_prompt=system_prompt,
        user_prompt=user_prompt
    )

    raw_text = resp.get('raw_text') if isinstance(resp, dict) else None
    if not raw_text:
        print("No se obtuvo texto de la IA.")
        return None

    out_path = os.path.join('quantex', 'experiments', 'ahc', f'ahc_{identifier}_narrative.md')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(raw_text)

    print(f"Narrativa guardada en: {out_path}")
    print("\n---\n")
    print(raw_text)
    return out_path


if __name__ == '__main__':
    ident = sys.argv[1] if len(sys.argv) > 1 else 'SPIPSA.INDX'
    years = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    cutoff = sys.argv[3] if len(sys.argv) > 3 else CUTOFF_DATE_STR
    start = sys.argv[4] if len(sys.argv) > 4 else None
    run_ahc_narrative(identifier=ident, years=years, cutoff_date_str=cutoff, start_date_str=start)
