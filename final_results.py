import pandas as pd
import numpy as np
import os
print("FICHEIRO A SER EXECUTADO:", os.path.abspath(__file__))
from collections import defaultdict
import re
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
import glob

class Resultados:
    print(">>> DEBUG: versão correta da função está a ser usada")
    def results_together(self, file_path_pattern):
        # Encontra todos os ficheiros Excel com base no padrão dado
        ficheiros = glob.glob(file_path_pattern)
        if not ficheiros:
            print("⚠️ Nenhum ficheiro encontrado com esse padrão.")
            return None
        # Lê todos os ficheiros Excel encontrados
        dfs = [pd.read_excel(f) for f in ficheiros]
        # Junta todos num único DataFrame
        df_final = pd.concat(dfs, ignore_index=True)
        os.makedirs("Final_Results", exist_ok=True)
        #print(df_final)

        return df_final
    
    def select_information(self, df):
        """Agrupa dados por 'Sample description 1' e mostra Target e Result.

        Exclui linhas onde `Target` contém 'IC' e onde `Sample description 1`
        contém 'PC', 'NC' ou 'NTC' (case-insensitive).
        """
        selected_columns = [
            'Source_File',
            'Sample description 1',
            'Target',
            'Result'
        ]
        # Trabalha sobre uma cópia para não modificar o df exterior
        df_selected = df[selected_columns].copy()

        # Excluir targets que contenham 'IC' (ex.: 'FGFR3-IC', 'FGFR3-248-IC')
        df_selected = df_selected[~df_selected['Target'].astype(str).str.contains(r'IC', case=False, na=False)]

        # Excluir amostras que contenham controles: PC, NC, NTC (palavra inteira, case-insensitive)
        exclude_pattern = r"\b(PC|NC|NTC)\b|\+"
        df_selected = df_selected[~df_selected['Sample description 1'].astype(str).str.contains(exclude_pattern, case=False, na=False)]

        # Agrupa por "Sample description 1"
        grouped = df_selected.groupby('Sample description 1')

        print("Informação agrupada (controles excluídos) por Sample description 1:")
        print("=" * 80)

        for sample_name, group in grouped:
            print(f"\n📋 Sample: {sample_name}")
            print("-" * 80)
            # Mostra Target e Result para cada grupo
            for idx, row in group.iterrows():
                print(f"  Target: {row['Target']:<30} | Result: {row['Result']}")
            print("-" * 80)

        return df_selected

    def add_overall_result(self, df):
        """
        Adds:
        - Overall Result: Positive if any target is positive; Inconclusive if any target is inconclusive 
        and none are positive; Inconclusive and Positive if any target is inconclusive and any is positive; 
        Inconclusive and Negative if any target is inconclusive and none are positive; otherwise Negative.
        - Positive Targets: comma-separated list of positive targets
        """
        def is_positive(val):
            if isinstance(val, str):
                val = val.strip().lower()
                return val == "positive" or val == "positive (<10k droplets)"
            return False

        def is_inconclusive(val):
            if isinstance(val, str):
                val = val.strip().lower()
                return val == "inconclusive"
            return False

        def is_negative(val):
            if isinstance(val, str):
                val = val.strip().lower()
                return val == "negative" or val == "negative (<10k droplets)"
            return False
        
        grouped = df.groupby("Sample description 1")

        overall = []
        pos_targets = []

        for sample, group in grouped:
            positives = group[group["Result"].apply(is_positive)]["Target"].tolist()
            inconclusives = group[group["Result"].apply(is_inconclusive)]["Target"].tolist()
            negatives = group[group["Result"].apply(is_negative)]["Target"].tolist()

            overall.append({
                "Sample description 1": sample,
                "Overall Result": "Positive" if positives 
                else "Inconclusive" if inconclusives and negatives 
                else "Inconclusive" if inconclusives and negatives and positives
                else "Inconclusive" if inconclusives 
                else "Negative",
                "Positive Targets": ", ".join(positives) if positives else ""
            })

        return pd.DataFrame(overall)

    def save_selected_information(self, df, filename="Selected_Results.xlsx"):

        # Ensure DataFrame has the required columns
        required = ['Sample description 1', 'Target', 'Result']
        for col in required:
            if col not in df.columns:
                raise ValueError(f"DataFrame is missing required column: {col}")

        # Ensure output directory exists
        os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)

    def save_selected_information(self, df, filename="Final_Results/Selected_Results.xlsx",
                                      desired_order=None):
        """Save selected results in wide format (one row per sample).

        Parameters
        - df: DataFrame with columns ['Sample description 1', 'Target', 'Result']
        - filename: output Excel path
        - desired_order: list of Target names in the exact order to appear as columns

        Behavior: pivot the data so each Target becomes a column containing its Result.
        If a target from `desired_order` is missing in the data, an empty column is created.
        Only the columns in `desired_order` (plus 'Sample description 1') are included in output.
        The function applies cell coloring: 'Positivo' -> green, 'Negativo' -> red,
        'Inconclusivo' -> yellow (case-insensitive).
        """
            # Validate input
        required = ['Sample description 1', 'Target', 'Result']
        for col in required:
            if col not in df.columns:
                raise ValueError(f"DataFrame is missing required column: {col}")

            # Default desired order (Option A requested)
        if desired_order is None:
            desired_order = [
                "TERT-124-MUT",
                "TERT-146-MUT",
                "FGFR3-248-MUT",
                "FGFR3-249-MUT",
                "FGFR3-372-MUT",
                "FGFR3-375-MUT",
            ]

            # Pivot to wide format
            # If duplicates exist for (sample, target), take the first occurrence
        if df.duplicated(subset=['Sample description 1', 'Target']).any():
            df = df.groupby(['Sample description 1', 'Target'], as_index=False).first()

        # Pivot to wide format
        wide_df = df.pivot(index='Sample description 1', columns='Target', values='Result').reset_index()

        # Add overall result + positive targets
        summary_df = self.add_overall_result(df)

        wide_df = wide_df.merge(summary_df, on="Sample description 1", how="left")

        # Reorder columns
        # Ensure all desired target columns exist BEFORE reordering
        for t in desired_order:
            if t not in wide_df.columns:
                wide_df[t] = np.nan

        # Ensure summary columns exist
        for col in ['Overall Result', 'Positive Targets']:
            if col not in wide_df.columns:
                wide_df[col] = ""

        # Now reorder safely
        final_cols = (
            ['Sample description 1', 'Overall Result', 'Positive Targets'] +
            desired_order
        )
        wide_df = wide_df[final_cols]

        # Write wide DataFrame to Excel
        os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            wide_df.to_excel(writer, index=False, sheet_name='Results')

        # Open workbook and color result cells (all columns except the first)
        wb = load_workbook(filename)
        ws = wb['Results']

            # Define fills
        green_fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
        red_fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
        yellow_fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")

            # Apply fills across all target columns (column 2..max_col)
        for row in range(2, ws.max_row + 1):
            for col in range(2, ws.max_column + 1):
                cell = ws.cell(row=row, column=col)
                if cell.value is None:
                    continue
                val = str(cell.value).strip().lower()
                if val == 'positive':
                    cell.fill = green_fill
                elif val == 'positive (<10k droplets)':
                    cell.fill = green_fill
                elif val == 'negative':
                    cell.fill = red_fill
                elif val == 'negative (<10k droplets)':
                    cell.fill = red_fill
                elif val == 'inconclusive':
                    cell.fill = yellow_fill

        wb.save(filename)
        print(f"\n✅ Informações selecionadas exportadas com sucesso para: {filename}")
        return filename

    def save_full_information(self, df, filename="Final_Results/Results_full_information.xlsx"):
        extra_cols = [
            'Source_File',
            'Sample description 1',
            'Target',
            'Result',
            'Accepted Droplets',
            'Positives',
            'Merged Fractional Abundance'
        ]

        missing = [c for c in extra_cols if c not in df.columns]
        if missing:
            raise ValueError(f"Missing columns in DataFrame: {missing}")

        full_df = df[extra_cols].copy()

        summary_df = self.add_overall_result(df)
        full_df = full_df.merge(summary_df, on="Sample description 1", how="left")

        os.makedirs(os.path.dirname(filename), exist_ok=True)
        full_df = full_df[[
            'Source_File',
            'Sample description 1',
            'Target',
            'Result',
            'Accepted Droplets',
            'Positives',
            'Merged Fractional Abundance'
        ]]
        full_df = full_df[full_df['Merged Fractional Abundance'].notna()]
        full_df = full_df.drop_duplicates()
        full_df.to_excel(filename, index=False)

        print(f"✅ Ficheiro completo exportado para: {filename}")
        return filename
    
#df_final = Resultados().results_together("Final_Results/Results_*.xlsx")
#df_selected = Resultados().select_information(df_final)
#Resultados().save_selected_information(df_selected)
#Resultados().save_full_information(df_final)