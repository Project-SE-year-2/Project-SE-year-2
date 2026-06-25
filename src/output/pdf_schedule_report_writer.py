from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Preformatted, SimpleDocTemplate, Spacer

from src.models.exam_period import ExamPeriod
from src.models.exam_schedule import ExamSchedule
from src.output.i_output_writer import IOutputWriter
from src.output.export_formatters.schedule_export_formatter import ExportFormatterFactory


class PdfScheduleReportWriter(IOutputWriter):
    """Writes exam scheduling results to a PDF file."""

    def write(
        self,
        schedules: list[ExamSchedule],
        metadata: dict[ExamPeriod, dict],
        programs: list[str],
        output_path: str,
    ) -> None:
        """Create a PDF report for the given schedules."""
        lines = self._build_report_lines(schedules, programs)

        doc = SimpleDocTemplate(output_path, pagesize=A4)
        styles = getSampleStyleSheet()

        story = [
            Preformatted("\n".join(lines), styles["Code"]),
            Spacer(1, 12),
        ]

        doc.build(story)

    def _build_report_lines(
        self,
        schedules: list[ExamSchedule],
        programs: list[str],
    ) -> list[str]:
        """Build report lines using the same formatter logic as the text export."""
        lines: list[str] = []
        sep = "=" * 60

        lines.append(sep)
        lines.append("           EXAM SCHEDULE GENERATOR - RESULTS")
        lines.append(sep)
        lines.append("")
        lines.append(f"Selected Programs : {', '.join(programs)}")
        lines.append("")

        lines.append(sep)
        lines.append(f"TOTAL COMPLETE SCHEDULES : {len(schedules):,}")
        lines.append(sep)
        lines.append("")

        if schedules:
            lines.append(
                "--- Complete Exam Schedules "
                "(sorted: FALL Aleph -> FALL Bet -> SPRI) ---"
            )
            lines.append("")

            div = "-" * 60
            for idx, sched in enumerate(schedules, start=1):
                formatter = ExportFormatterFactory.create(sched)
                lines.extend(formatter.format_schedule(sched, idx, div))

        lines.append(sep)
        lines.append("END OF REPORT")
        lines.append(sep)

        return lines
