import pandas as pd
import numpy as np
import os
from collections import defaultdict
import re
from openpyxl import load_workbook
from openpyxl.styles import PatternFill

#print(os.getcwd())
data_dict = {}

class ExcelAnalyzer:
    def open_excel(self, file_path):
        """Open an Excel file and return a DataFrame."""
        try:
            df = pd.read_excel(file_path)
            #print(df)
            df['Target'] = (
                df['Target']
                .astype(str)
                .str.strip()
                .str.upper()
            )
            df['Source_File'] = os.path.basename(file_path)
            return df
        except Exception as e:
            print(f"Error opening file: {e}")
            return None

    def analyze_data(self, df):
        """Perform basic analysis on the DataFrame."""
        print("Data Head:")
        #print(df.head())  # Print first few rows
        print("\nData Summary:")
        #print(df.describe())  # Print summary statistics
        print("\nMissing Values:")
        #print(df.isnull().sum())  # Print count of missing values
        print("\nData Columns:")
        #print(df.columns)  # Print column names
        print("\nSample description lengths:")
        #print(df['Sample description 1'].str.len().mean())
        return df

    def duplicate_internal_controls(self, df):
        """Duplica os controlos internos FGFR3-IC para associar aos MUTs 248 e 249."""
        df = df.copy()
        # Seleciona apenas o controlo interno FGFR3-IC
        fgfr3_ic = df[df['Target'] == 'FGFR3-IC']
        # Cria cópias com novos nomes
        fgfr3_ic_248 = fgfr3_ic.copy()
        fgfr3_ic_248['Target'] = 'FGFR3-248-IC'
        fgfr3_ic_249 = fgfr3_ic.copy()
        fgfr3_ic_249['Target'] = 'FGFR3-249-IC'
        # Junta tudo num único DataFrame
        df_updated = pd.concat([df, fgfr3_ic_248, fgfr3_ic_249], ignore_index=True)
        df = df_updated
        print("Controlos internos duplicados:")
        print(df)
        #print(df[df['Target'].str.contains('FGFR3')][['Target', 'Accepted Droplets']])
        return df

    def accepted_droplets(self, df):
        """Perform specific calculations on the DataFrame."""
        # Cria coluna booleana por linha
        df['Accepted_Droplets_10000'] = df['Accepted Droplets'] >= 10000
        df['Invalid_Droplets'] = df['Accepted Droplets'] <= 5000
        # Adiciona essa coluna ao dicionário (como lista)
        keys = zip(df['Sample description 1'], df['Target'])
        values = zip(df['Sample description 1'], df['Conc(copies/µL)'], df['Accepted Droplets'], df['Positives'],
                     df['Fractional Abundance'], df['Accepted_Droplets_10000'], df['Invalid_Droplets'])
        data_dict = dict(zip(keys, values))
        print("Accepted Droplets Check:")
        #print(data_dict)
        return data_dict, df


    def positive_droplets(self, df, normalize=True):
        """Classify positive droplets based on Target type.

        Parameters
        ----------
        df : DataFrame
        normalize : bool, default True
            Se True, subtrai a média de 'Positives' dos controlos NTC/NC (por Target)
            a todas as amostras (background subtraction). Se False, mantém os
            valores de 'Positives' tal como estão, sem qualquer normalização.
        """
        # Definição da condição para controlos internos (targets que terminam em '-IC')
        #print(df.columns)
        print("Original Positives:", df['Positives'])
        df = df.copy()
        if normalize:
            # Considera como background as amostras identificadas como NTC ou NC
            # (palavra inteira, case-insensitive)
            background_pattern = r'\b(NTC|NC)\b'
            background = df[
                df['Sample description 1'].astype(str).str.contains(
                    background_pattern, case=False, na=False, regex=True
                )
            ]
            background_mean = background.groupby('Target')['Positives'].mean()

            # IMPORTANTE: o controlo interno (IC) é um "spike-in" adicionado a TODOS
            # os poços, incluindo o NTC — por isso o NTC normalmente já mostra sinal
            # de IC. Subtrair esse background ao próprio IC zera (ou quase) o sinal
            # de IC em todas as amostras, levando a resultados "Inconclusive" em
            # massa. A normalização deve aplicar-se apenas aos targets MUT.
            is_ic_target = df['Target'].str.upper().str.endswith('-IC')
            background_to_subtract = df['Target'].map(background_mean).fillna(0)
            background_to_subtract = background_to_subtract.where(~is_ic_target, 0)

            positives = df['Positives'] - background_to_subtract
            df['Positives'] = positives.clip(lower=0)
            print("Adjusted Positives (NTC/NC subtracted apenas dos targets MUT):", df['Positives'])
        else:
            print("Normalização pelo NTC/NC desativada — a usar valores de Positives originais.")
        is_ic = df['Target'].str.endswith('-IC')
        # Cria uma nova coluna booleana
        df['Positive_Droplets_OK'] = (
            (is_ic & (df['Positives'] >= 10)) |       # Controlos internos ≥ 10
            (~is_ic & (df['Positives'] >= 5))         # Mutados ≥ 5
        )
        keys = zip(df['Sample description 1'], df['Target'])
        values = zip(df['Conc(copies/µL)'], df['Accepted Droplets'], df['Positives'], 
                     df['Fractional Abundance'], df['Accepted_Droplets_10000'], df['Invalid_Droplets'], 
                     df['Positive_Droplets_OK'])
        data_dict = dict(zip(keys, values))
        print("Positive Droplets classification:")
        #print(data_dict)
        return data_dict, df
    
    def fractional_abundance(self, df):
        """Calcula a Fractional Abundance (FA) para cada par MUT/IC."""
        # Cria uma cópia para evitar modificar o df original
        df = df.copy()
        # Extrai o "gene base" do Target (por exemplo, FGFR3 de FGFR3-IC ou FGFR3-MUT)
        df['Gene'] = df['Target'].str.replace(r'-(MUT|IC)$', '', regex=True)
        # Garante que 'Positives' é numérico
        df['Positives'] = pd.to_numeric(df['Positives'], errors='coerce')
        # Separa MUT e IC
        mut_df = df[df['Target'].str.contains('MUT', case=False)][['Sample description 1', 'Gene', 'Positives']].rename(columns={'Positives': 'Pos_Mut'})
        ic_df = df[df['Target'].str.contains('IC', case=False)][['Sample description 1', 'Gene', 'Positives']].rename(columns={'Positives': 'Pos_IC'})
        # Junta as duas tabelas lado a lado (por Gene)
        merged = pd.merge(mut_df, ic_df, on=['Sample description 1', 'Gene'], how='left')
        #print("Antes do merge mut:")
        #print(mut_df)
        #print("Antes do merge ic:")
        #print(ic_df)
        #print("Depois do merge:")
        #print(merged)
        # Calcula a Fractional Abundance
        merged['Fractional_Abundance'] = np.where(
                (merged['Pos_Mut'] + merged['Pos_IC']) > 0,
                (merged['Pos_Mut'] / (merged['Pos_Mut'] + merged['Pos_IC'])) * 100,
                0
                )
        #print(merged)
        merged['Fractional_Abundance_OK'] = merged['Fractional_Abundance'] >= 0.5
        df = df.merge(
        merged[['Sample description 1', 'Gene', 'Fractional_Abundance', 'Fractional_Abundance_OK']],
                on=['Sample description 1', 'Gene'],
                how='left'
            )
        # Para as linhas IC, deixa FA em branco
        df.loc[df['Target'].str.endswith('IC'), 'Fractional_Abundance'] == 0
        #print(df[['Sample description 1', 'Target', 'Positives', 'Fractional_Abundance']])
        print("Fractional Abundance calculation:")
        keys = zip(df['Sample description 1'].astype(str), df['Target'].astype(str))
        values = zip(
            df['Conc(copies/µL)'],
            df['Accepted Droplets'],
            df['Positives'],
            df['Fractional Abundance'],
            df['Accepted_Droplets_10000'],
            df['Positive_Droplets_OK'],
            df['Fractional_Abundance'],
            df['Fractional_Abundance_OK']
        )
        data_dict = dict(zip(keys, values))
        #df[['Sample description 1', 'Target', 'Positives', 'Fractional_Abundance']].to_csv("output_fractional_abundance.txt",
        #                           sep="\t",    # separador por tabulação
        #                           index=False)
        #print("✅ Ficheiro de texto criado: output_fractional_abundance.txt")
        #print("✅ Fractional Abundance calculada e atribuída corretamente.")
        return data_dict, df

    def final_result_from_tuple_dict(self, data_dict):
        grouped = defaultdict(dict)
        updated_dict = {}
        # Agrupa por sample e gene
        for (sample, target), values in data_dict.items():
            gene = re.sub(r'-(MUT|IC)$', '', target, flags=re.IGNORECASE)
            grouped[(sample, gene)][target] = values
        # Avalia cada MUT
        for (sample, gene), targets in grouped.items():
            for target, values in targets.items():
                try:
                    accepted_10000 = values[4]
                except Exception:
                    accepted_10000 = False
                try:
                    positive_ok = values[5]
                except Exception:
                    positive_ok = False
                try:
                    frac_ok = values[7]
                except Exception:
                    frac_ok = False
                if "MUT" in target.upper():
                # procurar IC correspondente
                    ic_target = f"{gene}-IC"
                    #print(ic_target)
                    ic_values = targets.get(ic_target)
                    print(ic_target, ic_values)
                    if ic_values is not None:
                        try:
                            ic_positive = ic_values[5]  # Positive_Droplets_OK
                        except Exception:
                            ic_positive = None
                    else:
                        ic_positive = None
                    # lógica: se IC Accepted_Droplets_1000 == False -> Inconclusivo
                    #print(f"DEBUG IC {sample} - {gene}: ic_accepted_1000 = {ic_accepted_1000} ({type(ic_accepted_1000)})")
                    if not ic_positive:
                        result = "Inconclusive"
                    elif not accepted_10000 and ic_positive and not positive_ok and not frac_ok:
                        result = "Negative (<10k droplets)"
                    elif not accepted_10000 and ic_positive and not positive_ok and frac_ok:
                        result = "Negative (<10k droplets)"
                    elif positive_ok and frac_ok and accepted_10000:
                        result = "Positive"
                        #print(ic_accepted_1000)
                    elif not accepted_10000 and (positive_ok and frac_ok):
                        result = "Positive (<10k droplets)"
                    else:
                        result = "Negative"

                    # acrescenta o resultado ao fim da tupla
                    updated_dict[(sample, target)] = tuple(list(values) + [result])

                elif "IC" in target.upper():
                    # acrescenta valor em branco nas tuplas dos IC
                    updated_dict[(sample, target)] = tuple(list(values) + [""])

                else:
                    # targets que não são MUT nem IC — mantem igual
                    updated_dict[(sample, target)] = values

        # Se quiseres manter entradas que por alguma razão não apareceram no grouped (raro),
        # adiciona-as sem alteração:
        for key, val in data_dict.items():
            if key not in updated_dict:
                updated_dict[key] = val if ("IC" in key[1].upper() or "MUT" in key[1].upper()) else val

        # Substitui o data_dict original pelo actualizado
        return updated_dict


    def save_dictionary_in_excel(self, data_dict, filename, source_file):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        print(data_dict)
        """retirar invalid_droplets do data_dict"""
        df2 = pd.DataFrame(
            [(*key, *value) for key, value in data_dict.items()],
            columns=[
                'Sample description 1',
                'Target',
                'Conc (copies/µL)',
                'Accepted Droplets',
                'Positives',
                'Fractional Abundance',
                'Accepted_Droplets_10000',
                'Positive_Droplets_OK',
                'Merged Fractional Abundance',
                'Fractional_Abundance_OK',
                'Result'
            ]
        )
        df2.insert(0, 'Source_File', source_file)
        df2.to_excel(filename, index=False)
        return df2
        df2.to_excel(filename, index=False)
        return df2
 
