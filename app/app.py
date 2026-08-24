from shiny import App, ui, render, reactive
from shiny.ui import Progress
from analysis_pipeline import run_analysis
from summary_pipeline import run_summary
import tempfile
import shutil
import os
import datetime
import pandas as pd

# ---------------- UI ----------------
app_ui = ui.page_fluid(
    ui.h2("ddPCR Analyzer"),

    ui.h3("1️⃣ Individual Analysis"),
    ui.input_file(
        "file1",
        "Select Excel ddPCR file",
        accept=[".xlsx"],
        multiple=False
    ),
    ui.input_checkbox(
        "normalize_ntc",
        "Normalizar pelo NTC/NC (subtrair background dos controlos)",
        value=True
    ),
    ui.input_action_button("run_analysis", "Run individual analysis"),
    ui.download_button("download_analysis", "Download individual result"),

    ui.hr(),

    ui.h3("2️⃣ Final Summary"),
    ui.input_action_button("run_summary", "Run final summary"),
    ui.output_table("summary_table"),
    ui.download_button("download_summary", "Download final summary"),
    ui.download_button("download_full_summary", "Download full information summary")
)

# ---------------- SERVER ----------------
def server(input, output, session):

    # -------- Reactive values --------
    analysis_file = reactive.Value(None)
    summary_df = reactive.Value(None)
    summary_file = reactive.Value(None)
    full_summary_file = reactive.Value(None)

    # -------- Temporary directory --------
    tmpdir = tempfile.mkdtemp()
    print("📁 TMPDIR:", tmpdir)

    @session.on_ended
    def cleanup():
        shutil.rmtree(tmpdir, ignore_errors=True)
        print("🧹 TMPDIR cleaned")

    # =========================================================
    # PART 1 — INDIVIDUAL ANALYSIS (WITH PROGRESS BAR)
    # =========================================================
    @reactive.Effect
    @reactive.event(input.run_analysis)
    def _run_analysis():

        with Progress(min=0, max=3) as p:

            p.set(
                value=0,
                message="Individual analysis",
                detail="Validating input file..."
            )

            files = input.file1()
            if not files:
                ui.notification_show(
                    "❌ No file selected",
                    type="error"
                )
                analysis_file.set(None)
                return

            p.set(
                value=1,
                detail="Copying file to temporary directory..."
            )

            fileinfo = files[0]
            input_path = os.path.join(tmpdir, fileinfo["name"])
            shutil.copyfile(fileinfo["datapath"], input_path)

            try:
                p.set(
                    value=2,
                    detail="Running ddPCR analysis..."
                )

                output_path = run_analysis(
                    input_excel_path=input_path,
                    output_dir=tmpdir,
                    normalize=input.normalize_ntc()
                )

                analysis_file.set(output_path)

                p.set(
                    value=3,
                    detail="Analysis completed"
                )

            except Exception as e:
                ui.notification_show(
                    f"❌ Error in analysis: {e}",
                    type="error",
                    duration=10
                )
                analysis_file.set(None)
                return

        ui.notification_show(
            "✅ Individual analysis completed successfully!",
            type="message"
        )

    @output
    @render.download(
        filename=lambda: os.path.basename(
            analysis_file() or "Analysis_result.xlsx"
        )
    )
    def download_analysis():
        path = analysis_file()
        return path if path and os.path.exists(path) else None

    # =========================================================
    # PART 2 — FINAL SUMMARY (WITH PROGRESS BAR)
    # =========================================================
    @reactive.Effect
    @reactive.event(input.run_summary)
    def _run_summary():

        with Progress(min=0, max=3) as p:

            p.set(
                value=0,
                message="Final summary",
                detail="Scanning analysis results..."
            )

            try:
                p.set(
                    value=1,
                    detail="Running summary pipeline..."
                )

                selected_path, full_path = run_summary(
                    input_dir=tmpdir,
                    output_dir=tmpdir
                )

                p.set(
                    value=2,
                    detail="Loading summary table..."
                )

                summary_file.set(selected_path)
                summary_df.set(pd.read_excel(selected_path))
                full_summary_file.set(full_path)

                p.set(
                    value=3,
                    detail="Summary completed"
                )

            except Exception as e:
                ui.notification_show(
                    f"❌ Error creating summary: {e}",
                    type="error",
                    duration=10
                )
                summary_file.set(None)
                summary_df.set(None)
                full_summary_file.set(None)
                return

        ui.notification_show(
            "✅ Final summary created successfully!",
            type="message"
        )

    @output
    @render.table
    def summary_table():
        df = summary_df()
        return df if df is not None else pd.DataFrame()

    @output
    @render.download(
        filename=lambda: os.path.basename(
            summary_file() or "Summary.xlsx"
        )
    )
    def download_summary():
        path = summary_file()
        return path if path and os.path.exists(path) else None

    @output
    @render.download(
        filename=lambda: os.path.basename(
            full_summary_file() or "Full_Summary.xlsx"
        )
    )
    def download_full_summary():
        path = full_summary_file()
        return path if path and os.path.exists(path) else None


# ---------------- APP ----------------
app = App(app_ui, server)

# ---------------- APP ----------------
app = App(app_ui, server)
