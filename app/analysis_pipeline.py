from QX200_Excel_Analyze import ExcelAnalyzer
import os
import datetime

def run_analysis(input_excel_path, output_dir, normalize=True):
    os.makedirs(output_dir, exist_ok=True)

    analyzer = ExcelAnalyzer()

    df = analyzer.open_excel(input_excel_path)
    if df is None:
        raise ValueError("Não foi possível abrir o ficheiro Excel")
    
    df = analyzer.duplicate_internal_controls(df)
    data_dict, df = analyzer.accepted_droplets(df)
    data_dict, df = analyzer.positive_droplets(df, normalize=normalize)
    data_dict, df = analyzer.fractional_abundance(df)
    data_dict = analyzer.final_result_from_tuple_dict(data_dict)

    # 🔑 NOME ÚNICO
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output_file = os.path.join(
        output_dir,
        f"Resultados_Analise_{timestamp}.xlsx"
    )

    source_file = os.path.splitext(os.path.basename(input_excel_path))[0]
    analyzer.save_dictionary_in_excel(data_dict, output_file, source_file)

    return output_file
