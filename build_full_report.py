#!/usr/bin/env python3
"""
Comprehensive Project Report Generator for:
Enterprise AWS Organizations & Landing Zone Architecture
Project: A Taste of Your Own Medicine: Design and Architect Infrastructure for Ecipient Technologies
# Author: Lead Enterprise Cloud Architect
# Output: AWS_Organizations_Infrastructure_Design_Ecipient_Technologies.pdf
"""

import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak, HRFlowable, Preformatted
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and print total page numbers:
    'Page X of Y' along with header and footer bars.
    """
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            # Suppress running header/footer on title cover page
            return

        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#4A5568"))

        # Header
        self.drawString(40, 755, "Ecipient Technologies | AWS Organizations Enterprise Architecture & Governance")
        self.drawRightString(letter[0] - 40, 755, "Enterprise AWS Organizations & Landing Zone Architecture")
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.6)
        self.line(40, 747, letter[0] - 40, 747)

        # Footer
        self.line(40, 42, letter[0] - 40, 42)
        self.drawString(40, 30, "Lead AWS Cloud Solutions Architect | Confidential & Proprietary")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 40, 30, page_str)
        self.restoreState()


