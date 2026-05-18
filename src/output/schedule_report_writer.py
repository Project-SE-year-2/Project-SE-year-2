from src.models.exam_schedule import ExamSchedule
from src.models.exam_period import ExamPeriod
from src.models.course import Course


class ScheduleReportWriter:
    """
    Writes the complete exam scheduling results to a UTF-8 text file
    (requirement: output is a text file encoded in UTF-8).

    The full list of all valid complete schedules is written to the file.
    A brief summary is printed to the console so the user knows what happened.
    """

    def write(
        self,
        schedules: list[ExamSchedule],
        metadata: dict[ExamPeriod, dict],
        programs: list[str],
        output_path: str,
    ) -> None:
        # Write full report to UTF-8 text file
        lines = self._buildReport(schedules, metadata, programs)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        # Print brief console summary only
        self._printSummary(metadata, schedules, output_path)

    # ------------------------------------------------------------------
    # Full report (written to file)
    # ------------------------------------------------------------------

    def _buildReport(
        self,
        schedules: list[ExamSchedule],
        metadata: dict[ExamPeriod, dict],
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

        # Per-period summary
        lines.append("--- Period Summary ---")
        lines.append("")
        for period, info in metadata.items():
            courses: list[Course] = info["courses"]
            n_days: int = info["available_days"]
            n_c: int = len(courses)
            theoretical: int = info["theoretical_count"]
            valid: int = info["valid_count"]

            lines.append(
                f"Period : {period.semester} - {period.moed}  "
                f"({period.start_date.strftime('%d-%m-%Y')} to "
                f"{period.end_date.strftime('%d-%m-%Y')})"
            )
            lines.append(f"  Available Days : {n_days}")
            lines.append(
                "  Courses        : "
                + (", ".join(f"{c.name} [{c.course_id}]" for c in courses) if courses else "none")
            )
            if n_c > 0:
                lines.append(
                    f"  Theoretical    : C({n_days}, {n_c}) x {n_c} = {theoretical:,}"
                )
                lines.append(f"  Valid          : {valid:,}")
            else:
                lines.append("  No exam courses in this period.")
            lines.append("")

        total = len(schedules)
        lines.append(sep)
        lines.append(f"TOTAL COMPLETE SCHEDULES : {total:,}")
        lines.append(sep)
        lines.append("")

        # Full schedule list
        if schedules:
            lines.append(
                "--- Complete Exam Schedules "
                "(sorted: FALL Aleph -> FALL Bet -> SPRI) ---"
            )
            lines.append("")
            for idx, sched in enumerate(schedules, start=1):
                sorted_items = sched.sortByDate()  # (period, course, date)

                # 2.3.1 — which exams are included (deduplicated by course_id)
                seen: set[str] = set()
                unique_courses = []
                for item in sorted_items:
                    if len(item) == 3:
                         _, c, _ = item
                    else:
                         c, _ = item

                    if c.course_id not in seen:
                        seen.add(c.course_id)
                        unique_courses.append(c)
                exam_names = ", ".join(
                    f"{c.name} ({c.course_id})" for c in unique_courses
                )
                lines.append(f"  Schedule #{idx}  |  Exams: {exam_names}")

                # 2.3.2 — for each exam: date and instructor name
                # 2.3.3 — already sorted FALL Aleph -> FALL Bet -> SPRI
                for item in sorted_items:
                    if len(item) == 3:
                        period, course, exam_date = item
                        period_text = f"[{period.semester} - {period.moed}]"
                    else:
                        course, exam_date = item
                        period_text = f"[{sched.semester} - {sched.moed}]"

                    lines.append(
                        f"    {period_text}  "
                        f"{course.name} ({course.course_id}) | "
                        f"{course.instructor} : "
                        f"{exam_date.strftime('%d-%m-%Y')}"
                    )
                lines.append("")

        lines.append(sep)
        lines.append("END OF REPORT")
        lines.append(sep)
        return lines

    # ------------------------------------------------------------------
    # Console summary (printed to stdout)
    # ------------------------------------------------------------------

    def _printSummary(
        self,
        metadata: dict[ExamPeriod, dict],
        schedules: list[ExamSchedule],
        output_path: str,
    ) -> None:
        sep = "-" * 60
        print(sep)
        print("  EXAM SCHEDULE GENERATOR - SUMMARY")
        print(sep)
        for period, info in metadata.items():
            n_c = len(info["courses"])
            if n_c == 0:
                continue
            print(
                f"  {period.semester} - {period.moed}: "
                f"{info['valid_count']:,} valid schedules  "
                f"[C({info['available_days']}, {n_c}) x {n_c} = {info['theoretical_count']:,}]"
            )
        print(sep)
        print(f"  TOTAL COMPLETE SCHEDULES : {len(schedules):,}")
        print(sep)
        print(f"  Full report written to: {output_path}")
        print(sep)

    # ------------------------------------------------------------------
    # Helpers (used by other components)
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
