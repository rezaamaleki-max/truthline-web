"""
مکانیک تخته وابستگی (SPA-01) — نسخه‌ی وب
======================================================
- بازیکن کارت‌ها را بین «زنجیره» و «لازم نیست» جابه‌جا می‌کند
- زنجیره: ترتیب اقدامات
- لازم نیست: کارت‌های غیرمرتبط (distractor)
- ✅ نسخه 2.0: منطقه‌ی «لازم نیست» به پایین منتقل شد (طبق بازخورد)

نسخه: 2.0.0
"""
import random
import time
from nicegui import ui

from web_app.config import TEST_MODE


DEPENDENCY_CSS_HTML = """
<style>
.dep-card {
    background-color: #1A2A4A;
    border: 2px solid #4FC3F7;
    border-radius: 10px;
    padding: 12px 16px;
    margin: 6px 0;
    cursor: grab;
    user-select: none;
    transition: border-color 0.15s, background-color 0.15s;
}
.dep-card:hover {
    border-color: #FFFFFF;
    background-color: #2B4A6F;
}
.dep-card:active { cursor: grabbing; }
.dep-card .dep-title {
    font-size: 14px;
    font-weight: bold;
    color: #FFFFFF;
}
.dep-card .dep-brief {
    font-size: 11px;
    color: #90A4AE;
    margin-top: 4px;
}
.dep-card.sortable-ghost {
    opacity: 0.35;
    border-style: dashed;
    background-color: #0B1D3A;
}
.sortable-container {
    min-height: 80px;
    padding: 8px;
    border: 1px dashed #2B4A6F;
    border-radius: 10px;
    background-color: rgba(11, 29, 58, 0.3);
}
/* ✅ نسخه 2.0: منطقه‌ی trash به‌صورت افقی و کوتاه در پایین */
.trash-container {
    min-height: 70px;
    padding: 8px;
    border: 2px dashed #D32F2F;
    border-radius: 10px;
    background-color: rgba(211, 47, 47, 0.05);
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: flex-start;
}
.trash-container-empty::after {
    content: "کارتی که در زنجیره لازم نیست را اینجا بکشید";
    color: #666666;
    font-size: 11px;
    display: block;
    text-align: center;
    padding: 14px;
    width: 100%;
}
</style>
"""


def _lcs_length(a: list, b: list) -> int:
    n, m = len(a), len(b)
    if n == 0 or m == 0:
        return 0
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n):
        for j in range(m):
            if a[i] == b[j]:
                dp[i + 1][j + 1] = dp[i][j] + 1
            else:
                dp[i + 1][j + 1] = max(
                    dp[i][j + 1], dp[i + 1][j]
                )
    return dp[n][m]


def _calc_sequence_score(
    user_order: list, correct_order: list, distractor_ids: list
) -> float:
    filtered = [aid for aid in user_order if aid in correct_order]
    lcs = _lcs_length(filtered, correct_order)
    base = (lcs / len(correct_order)) if correct_order else 0.0
    distractor_in_seq = sum(
        1 for aid in user_order if aid in distractor_ids
    )
    penalty_factor = max(0.0, 1.0 - 0.30 * distractor_in_seq)
    return max(0.0, base * penalty_factor)


def _calc_planning_time_score(t_ms: int) -> float:
    if 5000 <= t_ms <= 30000:
        return 1.0
    if t_ms < 5000:
        return 0.4
    if t_ms <= 60000:
        return 0.6
    return 0.3


async def render_dependency_board(scenario: dict, on_complete):
    cfg = scenario.get("dependency_config", {})
    actions = cfg.get("actions", [])
    correct_order = cfg.get("correct_order", [])

    action_map = {a["id"]: a for a in actions}

    distractor_ids = [
        a["id"] for a in actions if a.get("is_distractor", False)
    ]
    main_ids = [
        a["id"] for a in actions if a["id"] not in distractor_ids
    ]
    distractor_only_ids = [
        a["id"] for a in actions if a["id"] in distractor_ids
    ]

    shuffled_ids = list(main_ids) + list(distractor_only_ids)
    random.shuffle(shuffled_ids)

    state = {"start_time": time.time(), "submitted": False}

    ui.label("🔗 زنجیره‌ی اقدامات").classes(
        'text-xl font-bold text-cyan-400 w-full text-right'
    )

    # ---- راهنما ----
    with ui.element('div').classes(
        'w-full p-3 rounded border-2 border-orange-500 '
        'bg-orange-900/20 my-2'
    ):
        ui.label("💡 راهنما").classes(
            'text-sm font-bold text-orange-400 mb-1 w-full text-right'
        )
        ui.label(
            "• کارت‌ها را با ماوس بکشید و در ترتیب صحیح "
            "در زنجیره بچینید."
        ).classes('text-xs text-gray-300 w-full text-right')
        ui.label(
            "• ممکن است برخی کارت‌ها در این زنجیره جا نداشته "
            "باشند — به توضیحات هر کارت دقت کنید و آن‌ها را "
            "به کادر «لازم نیست» (پایین) بکشید."
        ).classes('text-xs text-gray-300 w-full text-right')
        ui.label(
            "• سپس روی «ثبت ترتیب» کلیک کنید."
        ).classes('text-xs text-gray-300 w-full text-right')

    # ============================================================
    # ✅ نسخه 2.0: چیدمان عمودی — زنجیره بالا، «لازم نیست» پایین
    # ============================================================
    with ui.column().classes('w-full gap-3'):
        # بخش بالا: زنجیره‌ی اقدامات
        with ui.column().classes('w-full gap-1'):
            ui.label("📋 زنجیره‌ی اقدامات").classes(
                'text-sm font-bold text-cyan-400 w-full text-right'
            )
            with ui.column().classes(
                'w-full gap-2 sortable-container'
            ).props('data-spa01-sequence') as seq_container:
                for aid in shuffled_ids:
                    action = action_map.get(
                        aid, {"id": aid, "name": aid}
                    )
                    name_fa = action.get("name") or aid
                    icon = action.get("icon", "")
                    brief = action.get("brief", "")

                    with ui.element('div').classes(
                        'dep-card'
                    ).props(f'data-id={aid}'):
                        ui.html(
                            f'<span class="dep-id-x" '
                            f'style="display:none">{aid}</span>'
                        )
                        with ui.column().classes('gap-0'):
                            with ui.row().classes(
                                'items-center gap-2 no-wrap'
                            ):
                                if icon:
                                    ui.label(icon).classes(
                                        'text-lg flex-shrink-0'
                                    )
                                ui.label(name_fa).classes(
                                    'dep-title'
                                )
                            if brief:
                                ui.label(brief).classes(
                                    'dep-brief'
                                )

        # ✅ بخش پایین: لازم نیست (نسخه 2.0)
        with ui.column().classes('w-full gap-1'):
            ui.label("🗑 لازم نیست").classes(
                'text-sm font-bold text-orange-400 '
                'w-full text-right'
            )
            ui.label(
                "کارت‌هایی که در این زنجیره نقشی ندارند را "
                "اینجا رها کنید."
            ).classes(
                'text-xs text-gray-500 w-full text-right '
                'italic mb-1'
            )
            with ui.column().classes(
                'w-full gap-2 trash-container '
                'trash-container-empty'
            ).props('data-spa01-trash'):
                pass

    # ============================================================
    # SortableJS init
    # ============================================================
    await ui.run_javascript(
        """
        (async () => {
            if (typeof Sortable === 'undefined') {
                await new Promise((resolve, reject) => {
                    const script = document.createElement('script');
                    script.src = 'https://cdn.jsdelivr.net/npm/sortablejs@1.15.0/Sortable.min.js';
                    script.onload = () => resolve();
                    script.onerror = () => reject(
                        new Error('SortableJS load failed')
                    );
                    document.head.appendChild(script);
                });
                console.log('[SPA-01] SortableJS loaded');
            }

            if (window._spa01_seq_sortable) {
                try { window._spa01_seq_sortable.destroy(); } catch(e) {}
                window._spa01_seq_sortable = null;
            }
            if (window._spa01_trash_sortable) {
                try { window._spa01_trash_sortable.destroy(); } catch(e) {}
                window._spa01_trash_sortable = null;
            }

            await new Promise(r => setTimeout(r, 200));

            const seqContainer = document.querySelector(
                '[data-spa01-sequence]'
            );
            const trashContainer = document.querySelector(
                '[data-spa01-trash]'
            );

            if (!seqContainer || !trashContainer) {
                console.error('[SPA-01] containers not found');
                return;
            }

            const updateOrder = () => {
                const cards = seqContainer.querySelectorAll('.dep-card');
                const ids = [];
                cards.forEach(el => {
                    let id = el.getAttribute('data-id');
                    if (!id || id === 'null') {
                        const span = el.querySelector('.dep-id-x');
                        if (span) id = span.textContent.trim();
                    }
                    if (id && id !== 'null') ids.push(id);
                });
                window._spa01_order = ids;
                console.log('[SPA-01] order =', JSON.stringify(ids));
            };

            updateOrder();

            window._spa01_seq_sortable = new Sortable(
                seqContainer, {
                    group: 'spa01', animation: 120,
                    ghostClass: 'sortable-ghost',
                    onEnd: updateOrder,
                }
            );

            window._spa01_trash_sortable = new Sortable(
                trashContainer, {
                    group: 'spa01', animation: 120,
                    ghostClass: 'sortable-ghost',
                    onEnd: updateOrder,
                }
            );

            console.log(
                '[SPA-01] init OK, initial order:',
                window._spa01_order
            );
        })();
        """,
        timeout=15,
    )

    submit_btn = ui.button("✓ ثبت ترتیب").classes(
        'w-full py-3 text-lg font-bold '
        'bg-green-600 hover:bg-green-500 mt-3'
    )

    async def _on_submit():
        if state["submitted"]:
            return
        state["submitted"] = True
        submit_btn.disable()

        ordered_ids = await ui.run_javascript(
            "return window._spa01_order || [];",
            timeout=5,
        )

        if not isinstance(ordered_ids, list) or not ordered_ids:
            print("[SPA-01] JS var empty — trying DOM fallback")
            ordered_ids = await ui.run_javascript(
                """
                const container = document.querySelector(
                    '[data-spa01-sequence]'
                );
                if (!container) return [];
                const cards = container.querySelectorAll('.dep-card');
                const ids = [];
                cards.forEach(el => {
                    let id = el.getAttribute('data-id');
                    if (!id || id === 'null') {
                        const span = el.querySelector('.dep-id-x');
                        if (span) id = span.textContent.trim();
                    }
                    if (id && id !== 'null') ids.push(id);
                });
                return ids;
                """,
                timeout=5,
            )

        if isinstance(ordered_ids, list):
            ordered_ids = [
                x for x in ordered_ids
                if x and x != 'null'
            ]
        else:
            ordered_ids = []

        if not ordered_ids:
            print("!" * 60)
            print("!!! CRITICAL: SPA-01 order is empty!")
            print("!" * 60)
            ui.notify(
                'خطای فنی در ثبت ترتیب — نمره‌ی صفر ثبت می‌شود.',
                type='negative', position='top', timeout=8000,
            )

        seq_score = _calc_sequence_score(
            ordered_ids, correct_order, distractor_ids
        )
        planning_ms = int(
            (time.time() - state["start_time"]) * 1000
        )

        distractor_in_seq = [
            aid for aid in ordered_ids if aid in distractor_ids
        ]

        print("=" * 60)
        print("[SPA-01] نتیجه‌ی نهایی:")
        print(
            f"  ترتیب بازیکن ({len(ordered_ids)}): {ordered_ids}"
        )
        print(
            f"  ترتیب صحیح ({len(correct_order)}):  {correct_order}"
        )
        print(f"  distractorهای در زنجیره: {distractor_in_seq}")
        print(f"  sequence_score: {seq_score:.3f}")
        print(f"  planning_ms: {planning_ms}")
        print("=" * 60)

        result = {
            "sequence": ordered_ids,
            "correct_order": correct_order,
            "sequence_score": round(seq_score, 3),
            "planning_time_ms": planning_ms,
            "planning_score": _calc_planning_time_score(
                planning_ms
            ),
            "efficiency_score": round(seq_score, 3),
            "total_time_ms": planning_ms,
            "distractor_ids": distractor_ids,
            "distractor_used": distractor_in_seq,
            "distractor_count": len(distractor_in_seq),
        }

        if on_complete:
            await on_complete(result)

    submit_btn.on_click(_on_submit)

