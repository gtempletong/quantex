import sys
from datetime import datetime
from quantex.experiments.ahc.run_ahc_narrative import run_ahc_narrative
from quantex.experiments.ahc.run_ahc_annotated_chart import generate_annotated_chart
from quantex.experiments.ahc.build_ahc_report import build_report


def run_all(identifier: str = 'SPIPSA.INDX', years: int = 1, start_date_str: str | None = None, cutoff_date_str: str | None = '2025-01-01') -> None:
    narrative_path = run_ahc_narrative(identifier=identifier, years=years, cutoff_date_str=cutoff_date_str, start_date_str=start_date_str)
    if not narrative_path:
        print("Narrativa no generada. Abortando.")
        return
    chart_path = generate_annotated_chart(identifier=identifier, years=years, start_date_str=start_date_str, cutoff_date_str=cutoff_date_str)
    if not chart_path:
        print("Gráfico no generado. Abortando.")
        return
    build_report(identifier=identifier)


def _prompt_with_default(prompt_text: str, default_value: str) -> str:
    try:
        entered = input(f"{prompt_text} [{default_value}]: ").strip()
        return entered or default_value
    except Exception:
        return default_value


def _validate_date(date_str: str, field_name: str) -> str:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        raise ValueError(f"{field_name} debe tener formato YYYY-MM-DD (recibido: {date_str})")


def _looks_like_date(s: str) -> bool:
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except Exception:
        return False


if __name__ == '__main__':
    if len(sys.argv) > 1:
        # CLI mode: python -m quantex.experiments.ahc.run_ahc_orchestrator TICKER YEARS START CUTOFF
        ident = sys.argv[1] if len(sys.argv) > 1 else 'SPIPSA.INDX'
        years = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        start = sys.argv[3] if len(sys.argv) > 3 else '2024-01-01'
        cutoff = sys.argv[4] if len(sys.argv) > 4 else '2025-01-01'
        run_all(identifier=ident, years=years, start_date_str=start, cutoff_date_str=cutoff)
    else:
        # Interactive mode (no args)
        print("AHC Orquestador - modo interactivo")
        ident_input = _prompt_with_default("Ticker", "SPIPSA.INDX")
        years_str = _prompt_with_default("Años de ventana (se ignora si das fechas)", "1")
        start_input = _prompt_with_default("Fecha inicio (YYYY-MM-DD)", "2024-01-01")
        cutoff_input = _prompt_with_default("Fecha cutoff/exclusiva (YYYY-MM-DD)", "2025-01-01")

        # Si el usuario escribió una fecha en el campo ticker, lo interpretamos como fecha inicio
        if _looks_like_date(ident_input) and not _looks_like_date(start_input):
            start_input = ident_input
            ident_input = 'SPIPSA.INDX'
            print(f"Detecté fecha en 'Ticker'. Usaré start={start_input} y ticker por defecto {ident_input}.")

        # Validaciones simples
        try:
            years = int(years_str)
        except Exception:
            years = 1
        start = _validate_date(start_input, "Fecha inicio")
        cutoff = _validate_date(cutoff_input, "Fecha cutoff")

        run_all(identifier=ident_input, years=years, start_date_str=start, cutoff_date_str=cutoff)
