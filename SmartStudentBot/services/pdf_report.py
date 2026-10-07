# services/pdf_report.py
# تولید کارنامه رسمی شبیه‌ساز ISEE Parificato در قالب PDF با استانداردهای دانشگاهی ایتالیا

import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

def generate_isee_pdf(result, inputs, user_name: str = "Studente") -> io.BytesIO:
    """
    تولید فایل PDF شیک و رسمی برای نتایج محاسبه ISEE Parificato
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # استایل‌های سفارشی
    title_style = ParagraphStyle(
        name='TitleStyle',
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#0B2545')
    )
    
    subtitle_style = ParagraphStyle(
        name='SubTitleStyle',
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#134074')
    )
    
    badge_style = ParagraphStyle(
        name='BadgeStyle',
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#006400') if result.status == 'full' else colors.HexColor('#8B4500')
    )
    
    normal_style = ParagraphStyle(
        name='NormalCustom',
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1D2D44')
    )
    
    bold_style = ParagraphStyle(
        name='BoldCustom',
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#0B2545')
    )
    
    story = []
    
    # ۱. سربرگ گزارش
    story.append(Paragraph("UNIVERSITÀ DEGLI STUDI DI PERUGIA", title_style))
    story.append(Paragraph("ADiSU Umbria - Simulazione ISEE Parificato (A.A. 2025/2026)", subtitle_style))
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#134074'), spaceAfter=15))
    
    # ۲. اطلاعات کلی متقاضی
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    info_data = [
        [
            Paragraph(f"<b>Candidato:</b> {user_name}", normal_style),
            Paragraph(f"<b>Data Simulazione:</b> {date_str}", normal_style)
        ],
        [
            Paragraph("<b>Tipo Attestazione:</b> ISEE Parificato Studenti Non-UE", normal_style),
            Paragraph(f"<b>Tasso Cambio EUR/IRR:</b> {inputs.eur_rate:,} Toman", normal_style)
        ]
    ]
    info_table = Table(info_data, colWidths=[270, 240])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#EEF4F8')),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#D0DBE5')),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 20))
    
    # ۳. کادر نتیجه نهایی ISEE
    status_label = "Idoneo Borsa Piena + Alloggio (Full Scholarship)" if result.status == 'full' else (
        "Idoneo Borsa Parziale (Partial Scholarship)" if result.status == 'partial' else (
            "Riduzione Tasse Universitarie (Fee Reduction)" if result.status == 'reduced' else "Non Idoneo Borsa DSU"
        )
    )
    
    result_data = [
        [Paragraph(f"VALORE ISEE CALCOLATO: <b>{result.isee:,.2f} €</b>", title_style)],
        [Paragraph(f"ESITO: <b>{status_label}</b>", badge_style)]
    ]
    result_table = Table(result_data, colWidths=[510])
    result_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#E8F5E9') if result.status == 'full' else colors.HexColor('#FFF8E1')),
        ('BORDER', (0, 0), (-1, -1), 1.5, colors.HexColor('#4CAF50') if result.status == 'full' else colors.HexColor('#FFA000')),
        ('PADDING', (0, 0), (-1, -1), 12),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(result_table)
    story.append(Spacer(1, 25))
    
    # ۴. جدول ریز محاسبات و معافیت‌ها
    story.append(Paragraph("<b>Dettagli del Calcolo Economico (Breakdown)</b>", bold_style))
    story.append(Spacer(1, 8))
    
    breakdown_data = [
        [Paragraph("Parametro Economico", bold_style), Paragraph("Valore Dichiarato", bold_style), Paragraph("Deduzione / Franchigia", bold_style), Paragraph("Valore Netto", bold_style)],
        [
            Paragraph("Reddito Complessivo (ISR)", normal_style),
            Paragraph(f"{inputs.income:,.0f} €", normal_style),
            Paragraph(f"-{result.rent_deduction:,.0f} € (Locazione)", normal_style),
            Paragraph(f"{result.adjusted_income:,.0f} €", bold_style)
        ],
        [
            Paragraph("Patrimonio Immobiliare", normal_style),
            Paragraph(f"{inputs.property_value:,.0f} €", normal_style),
            Paragraph(f"-{result.home_exemption:,.0f} € (Prima Casa)", normal_style),
            Paragraph(f"{result.adjusted_property:,.0f} €", bold_style)
        ],
        [
            Paragraph("Patrimonio Mobiliare (Conti/Titoli)", normal_style),
            Paragraph(f"{inputs.financial_assets:,.0f} €", normal_style),
            Paragraph(f"-{result.financial_exemption:,.0f} € (Franchigia)", normal_style),
            Paragraph(f"{result.adjusted_financial:,.0f} €", bold_style)
        ],
        [
            Paragraph("Debiti Dichiarati", normal_style),
            Paragraph(f"{inputs.total_debts:,.0f} €", normal_style),
            Paragraph(f"-{result.debt_deduction:,.0f} € (Detrazione)", normal_style),
            Paragraph(f"-{result.debt_deduction:,.0f} €", bold_style)
        ],
        [
            Paragraph("Patrimonio Netto Totale (ISP)", bold_style),
            Paragraph("-", normal_style),
            Paragraph("-", normal_style),
            Paragraph(f"{result.total_patrimony:,.0f} €", bold_style)
        ],
        [
            Paragraph("Indicatore Situazione Economica (ISE = ISR + 20% ISP)", bold_style),
            Paragraph("-", normal_style),
            Paragraph("-", normal_style),
            Paragraph(f"{result.ise:,.0f} €", bold_style)
        ],
        [
            Paragraph(f"Parametro Scala di Equivalenza ({inputs.members} componenti)", bold_style),
            Paragraph("-", normal_style),
            Paragraph("-", normal_style),
            Paragraph(f"{result.scale:.2f}", bold_style)
        ]
    ]
    
    breakdown_table = Table(breakdown_data, colWidths=[180, 110, 130, 90])
    breakdown_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#134074')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#B0C4DE')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#FFFFFF'), colors.HexColor('#F8FAFC')]),
    ]))
    story.append(breakdown_table)
    story.append(Spacer(1, 20))
    
    # ۵. آستانه‌های بورسیه ADiSU Umbria
    story.append(Paragraph("<b>Soglie Borsa di Studio ADiSU Umbria 2025/2026:</b>", bold_style))
    story.append(Paragraph("• <b>Limite Borsa Piena + Alloggio:</b> 25.500 €", normal_style))
    story.append(Paragraph("• <b>Limite Borsa Parziale:</b> 36.000 €", normal_style))
    story.append(Paragraph("• <b>Limite Riduzione Tasse:</b> 50.000 €", normal_style))
    story.append(Spacer(1, 15))
    
    # ۶. سلب مسئولیت حقوقی
    disclaimer_text = (
        "<b>Avviso Legale / Disclaimer:</b> Il presente documento costituisce una simulazione non ufficiale "
        "basata sui parametri DPCM 159/2013 e sui dati autodichiarati dal candidato. "
        "L'attestazione ufficiale ISEE Parificato deve essere rilasciata esclusivamente da un CAF convenzionato in Italia."
    )
    story.append(Paragraph(disclaimer_text, ParagraphStyle(name='Disclaimer', fontName='Helvetica-Oblique', fontSize=8, leading=11, textColor=colors.HexColor('#666666'))))
    
    doc.build(story)
    buffer.seek(0)
    return buffer
