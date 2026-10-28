from nicegui import ui, app, run
from web_app.report.pdf_generator import generate_pdf_report
from web_app.config import PAGE_CSS

@ui.page('/download-report')
async def download_report_page():
    participant_id = app.storage.user.get('participant_id')
    if not participant_id:
        ui.navigate.to('/')
        return
        
    ui.query('body').style(PAGE_CSS)
    with ui.column().classes('w-full items-center justify-center mt-20'):
        ui.label("در حال ساخت گزارش...").classes('text-xl text-cyan-400')
        ui.spinner(size='lg', color='cyan')
        
        try:
            path = await run.io_bound(generate_pdf_report, participant_id)
            
            # ✅ بررسی اینکه خروجی None نباشد
            if path:
                ui.notify("✓ گزارش آماده شد.", type='positive')
                ui.download(path, filename=f"Truthline_Report_{participant_id}.pdf")
            else:
                ui.notify("خطا در تولید فایل گزارش.", type='negative')
                
        except Exception as e:
            ui.notify(f"خطا در تولید گزارش: {e}", type='negative')