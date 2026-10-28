"""
منطق خالص آزمون برج هانوی (Tower of Hanoi)
==============================================
- پشتیبانی از N دیسک (۳، ۴، ۵)
- بدون وابستگی به UI
- compute_toh_evidence: جمع‌بندی شواهد در سطح کل آزمون

نسخه: 2.0.0 — پشتیبانی چندسطحی + شواهد ۴گانه
"""
import time
from dataclasses import dataclass


@dataclass
class ToHMove:
    trial_id: int
    move_number: int
    timestamp_ms: int
    disk_moved: int
    source_peg: str
    target_peg: str
    is_valid: bool
    reaction_time_ms: int = 0


class ToHLogic:
    """
    مدیریت وضعیت برج هانوی N دیسکی.
    - start: A = [N, ..., 1] (پایین به بالا)
    - goal:  C = [N, ..., 1]
    - MIN_MOVES = 2^N - 1
    """
    MAX_ATTEMPTS = 3

    def __init__(self, num_disks: int = 3, trial_id: int = 1):
        self.num_disks = max(3, min(5, num_disks))
        self.MIN_MOVES = (2 ** self.num_disks) - 1
        self.trial_id = trial_id
        self.reset()

    # ----------------------------------------------------------
    def reset(self):
        """بازنشانی به وضعیت شروع."""
        self.pegs: dict = {
            "A": list(range(self.num_disks, 0, -1)),
            "B": [],
            "C": [],
        }
        self.moves: list[ToHMove] = []
        self.invalid_attempts: int = 0
        self.is_solved: bool = False
        self.start_time_ms: int = int(time.time() * 1000)
        self.first_move_time_ms: int = 0
        self.last_move_time_ms: int = 0
        self.attempt_number: int = 1

    # ----------------------------------------------------------
    def get_top_disk(self, peg: str) -> int | None:
        p = self.pegs.get(peg)
        if not p:
            return None
        return p[-1]

    # ----------------------------------------------------------
    def is_valid_move(
        self, source: str, target: str
    ) -> tuple[bool, str]:
        if source not in self.pegs or target not in self.pegs:
            return False, "میله‌ی نامعتبر"
        if source == target:
            return False, "مبدأ و مقصد یکی هستند"

        src_top = self.get_top_disk(source)
        if src_top is None:
            return False, "میله‌ی مبدأ خالی است"

        dst_top = self.get_top_disk(target)
        if dst_top is not None and src_top > dst_top:
            return (
                False,
                "دیسک بزرگ‌تر روی دیسک کوچک‌تر قرار نمی‌گیرد",
            )
        return True, ""

    # ----------------------------------------------------------
    def try_move(
        self, source: str, target: str
    ) -> tuple[bool, str]:
        if self.is_solved:
            return False, "آزمون حل شده است"

        now_ms = int(time.time() * 1000)
        is_valid, err = self.is_valid_move(source, target)

        rt = (
            now_ms - self.last_move_time_ms
            if self.moves
            else now_ms - self.start_time_ms
        )

        if not is_valid:
            self.invalid_attempts += 1
            self.moves.append(ToHMove(
                trial_id=self.trial_id,
                move_number=len(self.moves) + 1,
                timestamp_ms=now_ms,
                disk_moved=self.get_top_disk(source) or 0,
                source_peg=source,
                target_peg=target,
                is_valid=False,
                reaction_time_ms=rt,
            ))
            return False, err

        disk = self.pegs[source].pop()
        self.pegs[target].append(disk)

        if self.first_move_time_ms == 0:
            self.first_move_time_ms = now_ms
        self.last_move_time_ms = now_ms

        self.moves.append(ToHMove(
            trial_id=self.trial_id,
            move_number=len(self.valid_move_count()),
            timestamp_ms=now_ms,
            disk_moved=disk,
            source_peg=source,
            target_peg=target,
            is_valid=True,
            reaction_time_ms=rt,
        ))

        goal = list(range(self.num_disks, 0, -1))
        if self.pegs["C"] == goal:
            self.is_solved = True

        return True, ""

    # ----------------------------------------------------------
    def valid_move_count(self) -> list:
        return [m for m in self.moves if m.is_valid]

    # ----------------------------------------------------------
    def get_metrics(self) -> dict:
        valid_moves = len(self.valid_move_count())
        now_ms = int(time.time() * 1000)

        if self.first_move_time_ms > 0:
            planning_ms = (
                self.first_move_time_ms - self.start_time_ms
            )
        else:
            planning_ms = now_ms - self.start_time_ms

        if self.first_move_time_ms > 0:
            end_ms = (
                self.last_move_time_ms
                if self.is_solved
                else now_ms
            )
            execution_ms = end_ms - self.first_move_time_ms
        else:
            execution_ms = 0

        efficiency = (
            self.MIN_MOVES / valid_moves
            if valid_moves > 0
            else 0.0
        )

        return {
            "num_disks": self.num_disks,
            "min_moves": self.MIN_MOVES,
            "solved": self.is_solved,
            "valid_moves": valid_moves,
            "invalid_attempts": self.invalid_attempts,
            "efficiency": round(min(1.0, efficiency), 3),
            "planning_time_ms": planning_ms,
            "execution_time_ms": execution_ms,
            "total_time_ms": now_ms - self.start_time_ms,
            "attempt_number": self.attempt_number,
        }

    # ----------------------------------------------------------
    def serialize_moves(self) -> list[dict]:
        return [
            {
                "trial_id": m.trial_id,
                "move_number": m.move_number,
                "timestamp_ms": m.timestamp_ms,
                "disk_moved": m.disk_moved,
                "source_peg": m.source_peg,
                "target_peg": m.target_peg,
                "is_valid": m.is_valid,
                "reaction_time_ms": m.reaction_time_ms,
            }
            for m in self.moves
        ]


# ============================================================
# محاسبه‌ی شواهد (۴ شاخص درخواستی)
# ============================================================
def compute_toh_evidence(all_levels_results: list) -> list:
    """
    جمع‌بندی شواهد بر اساس نتایج همه‌ی سطوح.

    Args:
        all_levels_results: لیست دیکشنری‌ها، هر کدام یکی از
            سطوح با کلیدهای: num_disks, solved, valid_moves,
            invalid_attempts, efficiency, planning_time_ms,
            execution_time_ms, total_time_ms

    Returns:
        لیست شواهد با ۵ آیتم:
        ۱. کارآمدی حرکات (تعداد حرکات)
        ۲. کیفیت زمان‌بندی
        ۳. نرخ موفقیت
        ۴. پرهیز از نقض قواعد
        ۵. بالاترین سطح (bonus)
    """
    if not all_levels_results:
        return []

    levels_attempted = len(all_levels_results)
    levels_solved = sum(
        1 for r in all_levels_results if r.get("solved")
    )
    highest_solved = max(
        (
            r.get("num_disks", 0)
            for r in all_levels_results
            if r.get("solved")
        ),
        default=0,
    )

    total_moves = sum(
        r.get("valid_moves", 0) for r in all_levels_results
    )
    total_invalid = sum(
        r.get("invalid_attempts", 0)
        for r in all_levels_results
    )
    total_planning = sum(
        r.get("planning_time_ms", 0)
        for r in all_levels_results
    )
    total_execution = sum(
        r.get("execution_time_ms", 0)
        for r in all_levels_results
    )

    # ---- ۱. کارآمدی حرکات ----
    solved_effs = [
        r.get("efficiency", 0.0)
        for r in all_levels_results
        if r.get("solved")
    ]
    moves_score = (
        sum(solved_effs) / len(solved_effs)
        if solved_effs
        else 0.0
    )

    # ---- ۲. کیفیت زمان‌بندی (planning + execution) ----
    avg_planning_ms = total_planning / levels_attempted
    if 2000 <= avg_planning_ms <= 15000:
        planning_score = 1.0
    elif 1000 <= avg_planning_ms <= 30000:
        planning_score = 0.7
    elif avg_planning_ms < 1000:
        planning_score = 0.3
    else:
        planning_score = 0.4

    avg_moves = (
        total_moves / levels_attempted
        if levels_attempted
        else 0
    )
    avg_execution_ms = total_execution / levels_attempted
    ms_per_move = avg_execution_ms / max(1, avg_moves)
    if 500 <= ms_per_move <= 3000:
        execution_score = 1.0
    elif ms_per_move <= 5000:
        execution_score = 0.6
    elif ms_per_move <= 8000:
        execution_score = 0.3
    else:
        execution_score = 0.1

    time_score = (
        planning_score * 0.4 + execution_score * 0.6
    )

    # ---- ۳. نرخ موفقیت ----
    success_rate = levels_solved / levels_attempted

    # ---- ۴. پرهیز از نقض قواعد ----
    violations_score = max(0.0, 1.0 - (total_invalid / 20.0))

    # ---- ۵. بالاترین سطح (bonus) ----
    highest_level_score = min(1.0, highest_solved / 5.0)

    return [
        {
            "key": "E_TOH_moves_efficiency",
            "value": round(moves_score, 3),
            "weight": 0.25,
            "description": "کارآمدی حرکات (تعداد حرکات)",
        },
        {
            "key": "E_TOH_time_quality",
            "value": round(time_score, 3),
            "weight": 0.20,
            "description": "کیفیت زمان‌بندی (برنامه‌ریزی + اجرا)",
        },
        {
            "key": "E_TOH_success_rate",
            "value": round(success_rate, 3),
            "weight": 0.30,
            "description": "نرخ موفقیت در سطوح",
        },
        {
            "key": "E_TOH_violations_quality",
            "value": round(violations_score, 3),
            "weight": 0.15,
            "description": "پرهیز از نقض قواعد",
        },
        {
            "key": "E_TOH_highest_level",
            "value": round(highest_level_score, 3),
            "weight": 0.10,
            "description": "بالاترین سطح حل‌شده",
        },
    ]