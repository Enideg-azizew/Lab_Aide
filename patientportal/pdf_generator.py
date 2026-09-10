from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from datetime import datetime

class PDFReportGenerator:
    """Generate PDF reports for patient lab results."""
    
    def __init__(self, patient, results, include_ai_summary=True):
        self.patient = patient
        self.results = results
        self.include_ai_summary = include_ai_summary
        self.styles = getSampleStyleSheet()
        self.buffer = BytesIO()
        self.doc = SimpleDocTemplate(
            self.buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
        )
        self.story = []
        
    def generate(self):
        """Generate the complete PDF report."""
        self._add_header()
        self._add_patient_info()
        self._add_results_table()
        if self.include_ai_summary:
            self._add_ai_summary()
        self._add_footer()
        
        self.doc.build(self.story)
        self.buffer.seek(0)
        return self.buffer
    
    def _add_header(self):
        """Add report header."""
        header_style = ParagraphStyle(
            'Header',
            parent=self.styles['Title'],
            fontSize=18,
            alignment=1,  # Center
            spaceAfter=12,
        )
        self.story.append(Paragraph("Laboratory Results Report", header_style))
        self.story.append(Spacer(1, 0.2*inch))
        
        # Date
        date_style = ParagraphStyle(
            'Date',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=1,
            textColor=colors.grey,
        )
        self.story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", date_style))
        self.story.append(Spacer(1, 0.3*inch))
        
    def _add_patient_info(self):
        """Add patient information."""
        # Patient-entered text is escaped before going into Paragraph(),
        # since Paragraph interprets a small HTML-like markup subset - an
        # unescaped '<' or '&' in a name could otherwise break rendering.
        info_style = self.styles['Normal']
        self.story.append(Paragraph(f"<b>Patient ID:</b> {escape(self.patient.patient_id)}", info_style))
        self.story.append(Paragraph(f"<b>Name:</b> {escape(self.patient.name)}", info_style))
        if self.patient.date_of_birth:
            self.story.append(Paragraph(f"<b>Date of Birth:</b> {self.patient.date_of_birth.strftime('%Y-%m-%d')}", info_style))
        self.story.append(Spacer(1, 0.2*inch))
        
    def _add_results_table(self):
        """Add results table."""
        self.story.append(Paragraph("Test Results", self.styles['Heading2']))
        self.story.append(Spacer(1, 0.1*inch))
        
        # Table headers
        data = [['Test Name', 'Result', 'Unit', 'Normal Range', 'Status']]
        
        for result in self.results:
            status = result.get('status', 'Normal')
            if status == 'Critical':
                status = '⚠ CRITICAL'
            elif status == 'Abnormal':
                status = '⚠ Abnormal'
            
            # Note: these are plain Table cell strings, not Paragraph
            # flowables, so reportlab draws them literally rather than
            # parsing markup - no escaping needed here (unlike the
            # Paragraph() calls elsewhere in this file).
            data.append([
                str(result['test_name']),
                str(result['result']),
                str(result['unit']),
                str(result['normal_range']),
                status,
            ])
        
        # Create table
        table = Table(data, colWidths=[2*inch, 1*inch, 0.8*inch, 1.5*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#ecf0f1')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdc3c7')),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        
        # Color rows based on status
        for i in range(1, len(data)):
            if 'CRITICAL' in data[i][4]:
                table.setStyle([('BACKGROUND', (0, i), (-1, i), colors.HexColor('#ffcccc'))])
            elif 'Abnormal' in data[i][4]:
                table.setStyle([('BACKGROUND', (0, i), (-1, i), colors.HexColor('#ffebcc'))])
        
        self.story.append(table)
        self.story.append(Spacer(1, 0.3*inch))
        
    def _add_ai_summary(self):
        """Add a plain-language summary of this result set.

        Named "AI-Generated Summary" previously, but no AI is actually
        involved - this is a simple rule-based count. Renamed to avoid
        overstating what it is; swap in a real generator here later if
        one is built (see the commented-out AISummaryGenerator in views.py).
        """
        self.story.append(Paragraph("Summary", self.styles['Heading2']))
        self.story.append(Spacer(1, 0.1*inch))

        summary_style = ParagraphStyle(
            'Summary',
            parent=self.styles['Normal'],
            fontSize=10,
            leftIndent=20,
            rightIndent=20,
            spaceAfter=10,
        )

        critical_results = [r for r in self.results if r.get('is_critical', False)]
        abnormal_results = [r for r in self.results if r.get('is_abnormal', False) and not r.get('is_critical', False)]

        patient_name = escape(self.patient.name)
        if critical_results or abnormal_results:
            parts = []
            if critical_results:
                parts.append(f"{len(critical_results)} critical")
            if abnormal_results:
                parts.append(f"{len(abnormal_results)} abnormal")
            summary_text = (
                f"Patient {patient_name} has " + " and ".join(parts) + " result(s) in this report. "
                "Please consult with your healthcare provider for interpretation."
            )
        else:
            summary_text = f"All results for {patient_name} in this report are within normal ranges."

        self.story.append(Paragraph(summary_text, summary_style))
        self.story.append(Spacer(1, 0.2*inch))
        
    def _add_footer(self):
        """Add footer with disclaimer."""
        footer_style = ParagraphStyle(
            'Footer',
            parent=self.styles['Normal'],
            fontSize=8,
            alignment=1,
            textColor=colors.grey,
        )
        self.story.append(Spacer(1, 0.5*inch))
        self.story.append(Paragraph(
            "This report is for informational purposes only. "
            "Please consult with your healthcare provider for proper interpretation and medical advice.",
            footer_style
        ))
