from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas


def _fmt_brl(value):
    return f'R$ {float(value):,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def build_report_pdf(summary: dict, title: str) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 2 * cm
    y = height - margin
    line_height = 0.55 * cm

    def ensure_space(lines=1):
        nonlocal y
        if y - (lines * line_height) < margin:
            pdf.showPage()
            y = height - margin

    def write_line(text, size=11, bold=False, gap=1):
        nonlocal y
        ensure_space(gap)
        font = 'Helvetica-Bold' if bold else 'Helvetica'
        pdf.setFont(font, size)
        pdf.drawString(margin, y, str(text)[:100])
        y -= line_height * gap

    def write_section(label):
        nonlocal y
        y -= 0.2 * cm
        write_line(label, size=13, bold=True, gap=1.2)

    write_line('ONG+', size=10, bold=True)
    write_line(title, size=16, bold=True, gap=1.4)

    ong = summary.get('ong', {})
    write_line(f"Organização: {ong.get('name', '—')}")
    if summary.get('cnpj') or ong.get('cnpj'):
        write_line(f"CNPJ: {summary.get('cnpj') or ong.get('cnpj')}")
    write_line(f"Período: {summary.get('period', '—')}")
    write_line(f"Score de confiança: {summary.get('score', 0)}/100")
    write_line(f"Gerado em: {summary.get('generatedAt', '—')[:10]}")

    finance = summary.get('finance')
    if finance:
        write_section('Resumo Financeiro')
        write_line(f"Total de entradas: {_fmt_brl(finance.get('totalIncome', 0))}")
        write_line(f"Total distribuído: {_fmt_brl(finance.get('totalDistributed', 0))}")

    donors = summary.get('donors')
    if donors:
        write_section('Doadores')
        write_line(f"Doações concluídas: {donors.get('donationCount', 0)}")
        write_line(f"Doadores únicos: {donors.get('uniqueDonors', 0)}")
        write_line(f"Valor total: {_fmt_brl(donors.get('totalAmount', 0))}")

    campaigns = summary.get('campaigns')
    if campaigns:
        write_section('Campanhas')
        write_line(f"Campanhas ativas: {campaigns.get('activeCount', 0)}")
        write_line(f"Total arrecadado: {_fmt_brl(campaigns.get('totalRaised', 0))}")

    write_section('Observações')
    write_line(
        'Relatório gerado automaticamente com dados registrados na plataforma ONG+.',
        size=10,
    )
    write_line('Documento válido para fins de prestação de contas interna.', size=10)

    pdf.save()
    return buffer.getvalue()
