"""
PDF Report Generation Module - Ultra Clean & Organized

This module handles the generation of professional PDF reports for the estimates system.
Features:
- Bill of Materials (BOM) reports with category breakdown
- Professional pie charts for cost visualization
- Butech branding and color schemes
- Modular, DRY (Don't Repeat Yourself) architecture

Optimized for maximum code reuse and maintainability.
"""

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (
    Table, TableStyle, Paragraph, Spacer, PageBreak, 
    PageTemplate, Frame, NextPageTemplate, BaseDocTemplate, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.piecharts import Pie
from reportlab.lib import colors as rl_colors
from io import BytesIO
from datetime import datetime
import os


# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

class Config:
    """Centralized configuration for PDF generation"""
    
    # Color scheme
    PRIMARY_RED = colors.Color(0.8, 0.2, 0.2)
    LIGHT_RED = colors.Color(0.98, 0.9, 0.9)
    DARK_RED = colors.Color(0.6, 0.1, 0.1)
    GRAY = colors.Color(0.95, 0.95, 0.95)
    WHITE = colors.white
    BLACK = colors.black
    
    # Page dimensions
    PAGE_MARGINS = {
        'portrait': {'side': 0.6 * inch, 'top': 0.4 * inch, 'width': 7.3 * inch, 'height': 10.4 * inch},
        'landscape': {'side': 0.7 * inch, 'top': 0.3 * inch, 'width': 9.6 * inch, 'height': 7.4 * inch}
    }
    
    # Table column widths
    TABLE_WIDTHS = {
        'bom': [0.3*inch, 0.9*inch, 2.6*inch, 1.2*inch, 0.4*inch, 0.4*inch, 0.7*inch, 0.8*inch],
        'summary': [4.5*inch, 2.0*inch],
        'category': [0.3*inch, 1.8*inch, 1.5*inch, 1.0*inch, 0.7*inch],
        'labor': [2.0*inch, 1.0*inch, 1.3*inch, 1.5*inch]
    }
    
    # Chart colors
    CHART_COLORS = [
        rl_colors.Color(0.2, 0.4, 0.8), rl_colors.Color(0.8, 0.4, 0.2), rl_colors.Color(0.2, 0.8, 0.4),
        rl_colors.Color(0.8, 0.2, 0.4), rl_colors.Color(0.4, 0.2, 0.8), rl_colors.Color(0.8, 0.8, 0.2),
        rl_colors.Color(0.2, 0.8, 0.8), rl_colors.Color(0.8, 0.2, 0.8), rl_colors.Color(0.4, 0.8, 0.2),
        rl_colors.Color(0.8, 0.4, 0.8)
    ]
    
    # Logo dimensions (maintain 2:1 aspect ratio)
    LOGO_MAIN = {'width': 2*inch, 'height': 1*inch}
    LOGO_SMALL = {'width': 1.2*inch, 'height': 0.6*inch}


# ============================================================================
# STYLE FACTORY
# ============================================================================

class StyleFactory:
    """Factory for creating consistent PDF styles"""
    
    def __init__(self):
        self.base_styles = getSampleStyleSheet()
    
    def create_style(self, name, parent_name='Normal', **kwargs):
        """Create a style with default Butech settings"""
        defaults = {
            'textColor': Config.PRIMARY_RED if 'title' in name.lower() else colors.black,
            'fontName': 'Helvetica-Bold' if 'header' in name.lower() or 'title' in name.lower() else 'Helvetica'
        }
        defaults.update(kwargs)
        return ParagraphStyle(name, parent=self.base_styles[parent_name], **defaults)
    
    def get_styles(self):
        """Get all predefined styles"""
        return {
            'title': self.create_style('Title', fontSize=24, alignment=1),
            'section_title': self.create_style('SectionTitle', fontSize=16, spaceAfter=15, alignment=1),
            'subsection_title': self.create_style('SubsectionTitle', fontSize=14, spaceAfter=10),
            'table_header': self.create_style('TableHeader', fontSize=11, leading=12, textColor=Config.WHITE, wordWrap='LTR', alignment=1),
            'table_header_small': self.create_style('TableHeaderSmall', fontSize=10, leading=11, textColor=Config.WHITE, wordWrap='LTR', alignment=1),
            'table_header_large': self.create_style('TableHeaderLarge', fontSize=12, leading=14, textColor=Config.WHITE, wordWrap='LTR', alignment=1),
            'table_cell': self.create_style('TableCell', fontSize=8, leading=10, wordWrap='LTR'),
            'preliminary_stamp': self.create_style('PreliminaryStamp', fontSize=14, fontName='Helvetica-Bold', alignment=1, spaceBefore=10, spaceAfter=10),
            'summary': self.create_style('Summary', fontSize=10),
            'info': self.base_styles['Normal']
        }


# ============================================================================
# TABLE STYLING ENGINE
# ============================================================================

class TableStyleEngine:
    """Unified table styling with inheritance and composition"""
    
    @staticmethod
    def get_base_style():
        """Base style inherited by all tables"""
        return TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), Config.PRIMARY_RED),
            ('TEXTCOLOR', (0, 0), (-1, 0), Config.WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, Config.BLACK),
            ('LINEWIDTH', (0, 0), (-1, -1), 0.5),
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ])
    
    @staticmethod
    def apply_alternating_rows(table, row_count, start_row=1, end_offset=0):
        """Apply alternating row colors to any table"""
        for i in range(start_row, row_count - end_offset):
            bg_color = Config.WHITE if i % 2 == 1 else Config.GRAY
            table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), bg_color)]))
    
    @classmethod
    def create_styled_table(cls, table_data, col_widths, table_type='default', **style_overrides):
        """Create a table with predefined styling based on type"""
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        base_style = cls.get_base_style()
        
        # Apply base style
        table.setStyle(base_style)
        
        # Apply type-specific styles
        type_styles = cls._get_type_styles().get(table_type, {})
        if type_styles:
            table.setStyle(TableStyle(type_styles))
        
        # Apply custom overrides
        if style_overrides:
            table.setStyle(TableStyle(list(style_overrides.items())))
        
        # Apply alternating rows
        cls.apply_alternating_rows(table, len(table_data))
        
        return table
    
    @staticmethod
    def _get_type_styles():
        """Get predefined styles for different table types"""
        return {
            'bom': [
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('ALIGN', (1, 1), (3, -2), 'LEFT'),
                ('ALIGN', (4, 1), (-1, -2), 'CENTER'),
                ('ALIGN', (6, 1), (-1, -2), 'RIGHT'),
                ('FONTSIZE', (0, 1), (-1, -2), 8),
                ('BACKGROUND', (0, -1), (-1, -1), Config.LIGHT_RED),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('ALIGN', (0, -1), (-1, -1), 'RIGHT'),
            ],
            'summary': [
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('LINEABOVE', (0, -2), (-1, -2), 2, Config.PRIMARY_RED),
                ('BACKGROUND', (0, -1), (-1, -1), Config.DARK_RED),
                ('TEXTCOLOR', (0, -1), (-1, -1), Config.WHITE),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ],
            'category': [
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ],
            'labor': [
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('ALIGN', (0, 1), (0, -2), 'LEFT'),
                ('BACKGROUND', (0, -1), (-1, -1), Config.LIGHT_RED),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('ALIGN', (0, -1), (-1, -1), 'RIGHT'),
            ]
        }


# ============================================================================
# CONTENT GENERATORS
# ============================================================================

class ContentGenerator:
    """Generates specific content sections for PDFs"""
    
    def __init__(self, styles):
        self.styles = styles
    
    def create_header_paragraphs(self, headers, style_name='table_header'):
        """Convert strings to styled Paragraph objects"""
        style = self.styles[style_name]
        return [Paragraph(str(header), style) for header in headers]
    
    def create_wrapped_text(self, text, style_name='table_cell'):
        """Create wrapped text paragraph"""
        if not text or str(text).strip() == '' or str(text) == 'None':
            text = 'No description available'
        return Paragraph(str(text), self.styles[style_name])
    
    def format_currency(self, value):
        """Format currency with commas"""
        return f"${float(value):,.2f}"
    
    def calculate_percentage(self, part, total):
        """Calculate percentage with proper formatting"""
        return f"{(part / total * 100):.1f}%" if total > 0 else "0.0%"


class ChartFactory:
    """Factory for creating charts and visual elements"""
    
    @staticmethod
    def create_pie_chart(categories_data, total_value, size=(320, 320)):
        """Create a clean pie chart without labels"""
        drawing = Drawing(*size)
        pie = Pie()
        pie.x = 35
        pie.y = 35
        pie.width = size[0] - 70
        pie.height = size[1] - 70
        
        pie.data = [value for _, value in categories_data]
        pie.labels = None  # Clean chart without labels
        
        # Apply colors
        for i, _ in enumerate(pie.data):
            color_index = i % len(Config.CHART_COLORS)
            pie.slices[i].fillColor = Config.CHART_COLORS[color_index]
            pie.slices[i].strokeColor = rl_colors.white
            pie.slices[i].strokeWidth = 2
        
        drawing.add(pie)
        return drawing
    
    @staticmethod
    def create_color_indicator(color_index):
        """Create color indicator for tables"""
        indicator = Drawing(15, 15)
        rect = Rect(2, 2, 11, 11)
        rect.fillColor = Config.CHART_COLORS[color_index % len(Config.CHART_COLORS)]
        rect.strokeColor = Config.BLACK
        rect.strokeWidth = 0.5
        indicator.add(rect)
        return indicator


# ============================================================================
# TABLE BUILDERS
# ============================================================================

class TableBuilder:
    """High-level table building with business logic"""
    
    def __init__(self, content_gen, style_engine):
        self.content = content_gen
        self.style_engine = style_engine
    
    def build_bom_table(self, bom_data):
        """Build main BOM table"""
        headers = ['#', 'Part Number', 'Description', 'Manufacturer', 'Qty', 'UOM', 'Unit Price', 'Total Price']
        table_data = [self.content.create_header_paragraphs(headers)]
        
        total_value = 0
        for i, item in enumerate(bom_data, 1):
            unit_price = float(item['unit_price'])
            total_quantity = float(item['total_quantity'])
            total_price = total_quantity * unit_price
            total_value += total_price
            
            table_data.append([
                str(i),
                self.content.create_wrapped_text(item['part_number'] or 'N/A'),
                self.content.create_wrapped_text(item['component_name'] or item['description'] or 'N/A'),
                self.content.create_wrapped_text(item['manufacturer'] or 'N/A'),
                str(int(total_quantity)),
                item['unit_of_measure'] or 'EA',
                self.content.format_currency(unit_price),
                self.content.format_currency(total_price)
            ])
        
        # Add total row
        table_data.append(['', '', '', '', '', '', 'TOTAL:', self.content.format_currency(total_value)])
        
        return self.style_engine.create_styled_table(table_data, Config.TABLE_WIDTHS['bom'], 'bom')
    
    def build_summary_table(self, estimate, total_purchased_components):
        """Build project cost summary table"""
        headers = ['Cost Category', 'Amount']
        table_data = [self.content.create_header_paragraphs(headers, 'table_header_large')]
        
        # Calculate costs
        engineering_hours = float(estimate.total_engineering_hours or 0)
        engineering_cost = float(estimate.total_engineering_cost or 0)
        panel_shop_hours = float(estimate.total_panel_shop_hours or 0)
        panel_shop_cost = float(estimate.total_panel_shop_cost or 0)
        combined_total = total_purchased_components + panel_shop_cost
        
        # Add data rows
        table_data.extend([
            ['Total Purchased Components', self.content.format_currency(total_purchased_components)],
            [f'Engineering Hours Total ({engineering_hours:.1f} hrs)', self.content.format_currency(engineering_cost)],
            [f'Panel Shop Hours Cost ({panel_shop_hours:.1f} hrs)', self.content.format_currency(panel_shop_cost)],
            ['', ''],  # Separator
            ['Combined Total (Components + Panel Shop)', self.content.format_currency(combined_total)]
        ])
        
        return self.style_engine.create_styled_table(table_data, Config.TABLE_WIDTHS['summary'], 'summary')
    
    def build_category_table(self, categories_data, total_value, descriptions):
        """Build category breakdown table with descriptions"""
        headers = ['', 'Category', 'Description', 'Total Cost', 'Percentage']
        table_data = [self.content.create_header_paragraphs(headers, 'table_header_small')]
        
        for i, (category, total) in enumerate(categories_data):
            description = descriptions.get(category, '')
            table_data.append([
                ChartFactory.create_color_indicator(i),
                category,
                self.content.create_wrapped_text(description),
                self.content.format_currency(total),
                self.content.calculate_percentage(total, total_value)
            ])
        
        return self.style_engine.create_styled_table(table_data, Config.TABLE_WIDTHS['category'], 'category')
    
    def build_labor_table(self, estimate):
        """Build labor costs table"""
        headers = ['Labor Type', 'Hours', 'Rate', 'Total Cost']
        table_data = [self.content.create_header_paragraphs(headers, 'table_header_small')]
        
        labor_data = [
            ('Engineering', estimate.total_engineering_hours, estimate.total_engineering_cost),
            ('Panel Shop', estimate.total_panel_shop_hours, estimate.total_panel_shop_cost),
            ('Machine Assembly', estimate.total_machine_assembly_hours, estimate.total_machine_assembly_cost)
        ]
        
        total_labor_cost = 0
        for labor_type, hours, cost in labor_data:
            hours = float(hours or 0)
            cost = float(cost or 0)
            if cost > 0:
                rate = cost / hours if hours > 0 else 0
                table_data.append([
                    labor_type,
                    f"{hours:.1f}",
                    f"${rate:,.2f}/hr",
                    self.content.format_currency(cost)
                ])
                total_labor_cost += cost
        
        table_data.append(['', '', 'TOTAL LABOR:', self.content.format_currency(total_labor_cost)])
        
        return self.style_engine.create_styled_table(table_data, Config.TABLE_WIDTHS['labor'], 'labor')


# ============================================================================
# DOCUMENT ASSEMBLY
# ============================================================================

class DocumentAssembler:
    """Assembles complete PDF documents"""
    
    def __init__(self):
        self.style_factory = StyleFactory()
        self.styles = self.style_factory.get_styles()
        self.content_gen = ContentGenerator(self.styles)
        self.style_engine = TableStyleEngine()
        self.table_builder = TableBuilder(self.content_gen, self.style_engine)
    
    def create_document_templates(self, buffer):
        """Create document with page templates"""
        portrait_margins = Config.PAGE_MARGINS['portrait']
        landscape_margins = Config.PAGE_MARGINS['landscape']
        
        portrait_frame = Frame(
            portrait_margins['side'], portrait_margins['top'],
            portrait_margins['width'], portrait_margins['height'], id='portrait'
        )
        landscape_frame = Frame(
            landscape_margins['side'], landscape_margins['top'],
            landscape_margins['width'], landscape_margins['height'], id='landscape'
        )
        
        doc = BaseDocTemplate(buffer, pagesize=A4)
        doc.addPageTemplates([
            PageTemplate(id='portrait', frames=[portrait_frame], pagesize=A4),
            PageTemplate(id='landscape', frames=[landscape_frame], pagesize=landscape(A4))
        ])
        
        return doc
    
    def add_header_section(self, story):
        """Add header with logo and title"""
        logo_path = os.path.join('app', 'static', 'images', 'stacked_rgb_300dpi.jpg')
        
        try:
            if os.path.exists(logo_path):
                logo = Image(logo_path, **Config.LOGO_MAIN)
                title = Paragraph("Bill of Materials", self.styles['title'])
                
                header_table = Table([[logo, title]], colWidths=[2.2*inch, 4.8*inch])
                header_table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                    ('ALIGN', (1, 0), (1, 0), 'CENTER'),
                ]))
                story.append(header_table)
                story.append(Spacer(1, 12))
            else:
                story.append(Paragraph("Bill of Materials", self.styles['title']))
        except Exception:
            story.append(Paragraph("Bill of Materials", self.styles['title']))
        
        # Add preliminary stamp
        story.append(Paragraph("PRELIMINARY AND ESTIMATE ONLY", self.styles['preliminary_stamp']))
    
    def add_project_info(self, story, estimate):
        """Add project information section"""
        info_style = self.styles['info']
        story.extend([
            Paragraph(f"<b>Project:</b> {estimate.project.project_name}", info_style),
            Paragraph(f"<b>Estimate:</b> {estimate.estimate_name}", info_style),
            Paragraph(f"<b>Estimate #:</b> {estimate.estimate_number}", info_style),
            Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", info_style),
            Spacer(1, 12)
        ])
    
    def add_category_breakdown(self, story, bom_data, estimate):
        """Add category breakdown with pie chart"""
        from app.models import PartCategory
        
        # Calculate category totals and get descriptions
        category_totals, total_value, descriptions = self._process_categories(bom_data, estimate)
        
        if not category_totals:
            return
        
        # Switch to landscape
        story.extend([NextPageTemplate('landscape'), PageBreak()])
        story.append(Paragraph("Cost Breakdown by Category", self.styles['section_title']))
        
        # Create content
        sorted_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
        category_table = self.table_builder.build_category_table(sorted_categories, total_value, descriptions)
        pie_chart = ChartFactory.create_pie_chart(sorted_categories, total_value)
        
        # Create layout
        layout = Table([[category_table, self._create_chart_with_logo(pie_chart)]], colWidths=[5.5*inch, 3.5*inch])
        layout.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        story.append(layout)
        story.append(NextPageTemplate('portrait'))
    
    def _process_categories(self, bom_data, estimate):
        """Process category data and get descriptions from database"""
        from app.models import PartCategory
        
        category_totals = {}
        total_value = 0
        
        # Process BOM categories
        for item in bom_data:
            category = item.get('category', '').strip() or 'Uncategorized'
            item_total = float(item['unit_price']) * float(item['total_quantity'])
            total_value += item_total
            category_totals[category] = category_totals.get(category, 0) + item_total
        
        # Add labor costs
        engineering_cost = float(estimate.total_engineering_cost or 0)
        panel_shop_cost = float(estimate.total_panel_shop_cost or 0)
        
        if engineering_cost > 0:
            category_totals['Engineering Labor'] = engineering_cost
            total_value += engineering_cost
        
        if panel_shop_cost > 0:
            category_totals['Panel Shop Labor'] = panel_shop_cost
            total_value += panel_shop_cost
        
        # Get descriptions from database
        descriptions = {
            'Engineering Labor': 'Engineering design and programming labor costs',
            'Panel Shop Labor': 'Panel fabrication and wiring labor costs'
        }
        
        try:
            categories = PartCategory.query.all()
            descriptions.update({cat.name: cat.description or '' for cat in categories})
        except Exception:
            pass  # Graceful fallback
        
        return category_totals, total_value, descriptions
    
    def _create_chart_with_logo(self, pie_chart):
        """Create right side content with logo and chart"""
        logo_path = os.path.join('app', 'static', 'images', 'stacked_rgb_300dpi.jpg')
        
        try:
            if os.path.exists(logo_path):
                logo = Image(logo_path, **Config.LOGO_SMALL)
                content = Table([[logo], [Spacer(1, 20)], [pie_chart]])
                content.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (0, 0), 'RIGHT'),
                    ('ALIGN', (0, 2), (0, 2), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                return content
        except Exception:
            pass
        
        # Fallback: just the chart
        content = Table([[pie_chart]])
        content.setStyle(TableStyle([('ALIGN', (0, 0), (0, 0), 'CENTER')]))
        return content


# ============================================================================
# MAIN API
# ============================================================================

def generate_bom_pdf(estimate, bom_data):
    """
    Generate a professional Bill of Materials PDF report.
    
    Args:
        estimate: The estimate object containing project and estimate details
        bom_data: List of dictionaries containing BOM item data
    
    Returns:
        BytesIO: PDF buffer ready for download
    """
    # Sort by total price (most expensive first)
    bom_data.sort(key=lambda x: x['unit_price'] * x['total_quantity'], reverse=True)
    
    # Initialize document assembler
    assembler = DocumentAssembler()
    
    # Create PDF document
    buffer = BytesIO()
    doc = assembler.create_document_templates(buffer)
    
    # Build content
    story = []
    
    # Add sections
    assembler.add_header_section(story)
    assembler.add_project_info(story, estimate)
    
    # Add comprehensive totals summary
    total_materials_value = sum(float(item['unit_price']) * float(item['total_quantity']) for item in bom_data)
    summary_table = assembler.table_builder.build_summary_table(estimate, total_materials_value)
    story.extend([
        Paragraph("Project Cost Summary", assembler.styles['section_title']),
        Spacer(1, 15),
        summary_table,
        Spacer(1, 20)
    ])
    
    # Add main BOM table
    bom_table = assembler.table_builder.build_bom_table(bom_data)
    story.append(bom_table)
    
    # Add labor costs section if applicable
    labor_costs = [
        float(estimate.total_panel_shop_cost or 0),
        float(estimate.total_engineering_cost or 0),
        float(estimate.total_machine_assembly_cost or 0)
    ]
    
    if any(cost > 0 for cost in labor_costs):
        story.extend([
            Spacer(1, 20),
            Paragraph("Labor Costs", assembler.styles['subsection_title']),
            assembler.table_builder.build_labor_table(estimate),
            Spacer(1, 15)
        ])
    
    # Add category breakdown
    assembler.add_category_breakdown(story, bom_data, estimate)
    
    # Add summary
    engineering_cost = float(estimate.total_engineering_cost or 0)
    panel_shop_cost = float(estimate.total_panel_shop_cost or 0)
    comprehensive_total = total_materials_value + engineering_cost + panel_shop_cost
    category_count = len(set(item.get('category', 'Uncategorized') for item in bom_data))
    
    story.append(Paragraph(
        f"<b>Summary:</b> {len(bom_data)} unique parts, {category_count} categories, Total value: ${comprehensive_total:,.2f}", 
        assembler.styles['summary']
    ))
    
    # Build and return PDF
    doc.build(story)
    buffer.seek(0)
    return buffer


def get_bom_filename(estimate):
    """Generate a standardized filename for BOM PDF"""
    safe_name = estimate.estimate_name.replace(" ", "_").replace("/", "_")
    return f"BOM_{estimate.estimate_number}_{safe_name}.pdf"