from src.output.i_output_writer import IOutputWriter
from src.models.exam_schedule import ExamSchedule
from src.models.exam_period import ExamPeriod
from src.models.course import Course
from src.output.export_formatters.schedule_export_formatter import ExportFormatterFactory


class ScheduleReportWriter(IOutputWriter):
    """
    Writes exam scheduling results to a UTF-8 encoded text file.

    The output contains:
    - Selected programs header
    - Total number of valid complete schedules
    - All schedule assignments, sorted by period and date
    """

    def write(
        self,
        schedules: list[ExamSchedule],
        metadata: dict[ExamPeriod, dict],
        programs: list[str],
        output_path: str,
    ) -> None:
        lines = self._buildReport(schedules, programs)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    # ------------------------------------------------------------------
    # Report builder
    # ------------------------------------------------------------------

    def _buildReport(
        self,
        schedules: list[ExamSchedule],
        programs: list[str],
    ) -> list[str]:
        lines: list[str] = []
        sep = "=" * 60

        lines.append(sep)
        lines.append("           EXAM SCHEDULE GENERATOR - RESULTS")
        lines.append(sep)
        lines.append("")
        lines.append(f"Selected Programs : {', '.join(programs)}")
        lines.append("")

        total = len(schedules)
        lines.append(sep)
        lines.append(f"TOTAL COMPLETE SCHEDULES : {total:,}")
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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _formatSchedule(self, schedule: ExamSchedule) -> str:
        parts = []
        for period, course, exam_date in schedule.sortByDate():
            parts.append(
                f"[{period.semester}-{period.moed}] "
                f"{course.name} ({course.course_id}) | "
                f"{course.instructor}: {exam_date.strftime('%d-%m-%Y')}"
            )
        return " | ".join(parts)

    def _groupByPeriod(self, schedules: list[ExamSchedule]) -> dict:
        groups: dict[tuple, list[ExamSchedule]] = {}
        for sched in schedules:
            key = (sched.semester, sched.moed)
            groups.setdefault(key, []).append(sched)
        return groups
