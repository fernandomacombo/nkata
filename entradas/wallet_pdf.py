"""Private A4 statement; no external resources, no uploaded content."""
from io import BytesIO
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, LongTable

WINE = colors.HexColor("#7d2638")
INK = colors.HexColor("#32272c")
MUTED = colors.HexColor("#74696d")
PALE = colors.HexColor("#f5eef0")
KINDS = {"ALL":"Todos", "RECARGA":"Recarga", "BONUS":"Bónus", "CONSUMO":"Consumo", "ESTORNO":"Estorno", "AJUSTE":"Ajuste"}
MAPUTO = ZoneInfo("Africa/Maputo")


def stamp(value):
    return value.astimezone(MAPUTO).strftime("%d/%m/%Y %H:%M") if value else "Desde o início"


def number(value, signed=False):
    return format(value, "+,d" if signed else ",d").replace(",", " ")


def render_statement_pdf(data, *, kind, member_id):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=38, rightMargin=38,
        topMargin=62, bottomMargin=50, title="NKATA - Extrato de créditos", author="NKATA")
    normal = ParagraphStyle("normal", fontName="Helvetica", fontSize=9, leading=13, textColor=INK)
    small = ParagraphStyle("small", parent=normal, fontSize=8, leading=11, textColor=MUTED)
    header = ParagraphStyle("header", parent=normal, fontName="Helvetica-Bold", fontSize=19, leading=24, textColor=WINE)
    section = ParagraphStyle("section", parent=normal, fontName="Helvetica-Bold", fontSize=11, leading=15, textColor=WINE)
    th = ParagraphStyle("th", parent=small, fontName="Helvetica-Bold", textColor=colors.white)
    def p(value, style=normal):
        return Paragraph(escape("".join(ch if ord(ch)>=32 else " " for ch in str(value))), style)
    story = [p("Extrato de créditos", header), Spacer(1, 6),
        p(f"Conta de membro #{member_id} | Emitido em {stamp(data['as_of'])} (Maputo, UTC+2)", small),
        p(f"Período: {stamp(data['from'])} a {stamp(data['as_of'])}", small),
        p(f"Filtro de movimentos: {KINDS[kind]}", small), Spacer(1, 15)]
    s = data["summary"]
    metrics = [
        ["Saldo actual", "Créditos de recargas", "Bónus recebidos"],
        [number(data["balance"]), number(s["recharged"]), number(s["bonus"])],
        ["Saídas de créditos", "Estornos", "Ajustes líquidos"],
        [number(s["spent"]), number(s["refunded"]), number(s["adjustments"], True)],
    ]
    table = Table(metrics, colWidths=[doc.width/3]*3)
    table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),PALE),("TEXTCOLOR",(0,0),(-1,-1),WINE),
        ("FONTNAME",(0,0),(-1,-1),"Helvetica"),("FONTNAME",(0,1),(-1,1),"Helvetica-Bold"),
        ("FONTNAME",(0,3),(-1,3),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),10),
        ("FONTSIZE",(0,1),(-1,1),16),("FONTSIZE",(0,3),(-1,3),16),
        ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8)]))
    story += [table, Spacer(1,8)]
    if s.get("simulated_recharged"):
        story += [p(f"Recargas simuladas: {number(s['simulated_recharged'])} créditos. Sem dinheiro real.", section), Spacer(1,5)]
    story += [p("Saldo actual à data de emissão. Os totais abrangem todos os movimentos do período; o filtro aplica-se apenas ao extrato abaixo. Valores em créditos, não em meticais.",small),Spacer(1,15)]
    story += [p("Consumo por funcionalidade",section),Spacer(1,4)]
    for row in data["breakdown"]:
        if row["credits"]:
            story.append(p(f"{row['label']}: {number(row['credits'])} créditos"))
    if not any(row["credits"] for row in data["breakdown"]):
        story.append(p("Sem consumo de créditos no período.",small))
    story += [Spacer(1,12),p(f"Movimentos ({len(data['results'])})",section),Spacer(1,5)]
    rows = [[p(x,th) for x in ("Data / ID","Operação","Créditos","Saldo após")]]
    for row in data["results"]:
        rows.append([p(f"{stamp(row['criado_em'])} / #{row['id']}",small),
            p(f"{KINDS.get(row['tipo'],row['tipo'])}: {row['motivo']}"),
            p(number(row["quantidade"],True)),p(number(row["saldo_apos"]))])
    if len(rows)>1:
        ledger = LongTable(rows, colWidths=[112,doc.width-248,68,68], repeatRows=1, hAlign="LEFT")
        ledger.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),WINE),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,PALE]),
            ("VALIGN",(0,0),(-1,-1),"TOP"),("TOPPADDING",(0,0),(-1,-1),7),
            ("BOTTOMPADDING",(0,0),(-1,-1),7),("LINEBELOW",(0,0),(-1,0),.5,WINE)]))
        story.append(ledger)
    else:
        story.append(p("Nenhum movimento corresponde ao filtro seleccionado."))
    def page(canvas, doc):
        canvas.saveState()
        w,h=A4
        canvas.setFillColor(WINE);canvas.rect(0,h-43,w,43,fill=1,stroke=0)
        canvas.setFont("Helvetica-Bold",15);canvas.setFillColor(colors.white);canvas.drawString(38,h-27,"NKATA")
        canvas.setFont("Helvetica",8);canvas.drawRightString(w-38,h-27,"CARTEIRA | EXTRATO PRIVADO")
        canvas.setFillColor(MUTED);canvas.setFont("Helvetica",8)
        canvas.drawString(38,28,"Documento informativo - não é factura nem comprovativo de pagamento.")
        canvas.drawRightString(w-38,28,f"Página {doc.page}")
        canvas.restoreState()
    doc.build(story,onFirstPage=page,onLaterPages=page)
    return buffer.getvalue()
