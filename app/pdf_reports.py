"""
PDF Report Generation Module - Optimized

This module handles the generation of various PDF reports for the estimates system.
Currently supports:
- Bill of Materials (BOM) reports with category breakdown
- Professional pie charts for cost visualization
- Side-by-side chart and table layouts
- Butech branding and color schemes

Optimized for code reuse and maintainability.
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
# CONSTANTS AND CONFIGURATION
# ============================================================================

class ButechTheme:
    """Centralized Butech color scheme and branding constants"""
    PRIMARY_RED = colors.Color(0.8, 0.2, 0.2)
    LIGHT_RED = colors.Color(0.98, 0.9, 0.9)
    DARK_RED = colors.Color(0.6, 0.1, 0.1)
    GRAY = colors.Color(0.95, 0.95, 0.95)
    WHITE = colors.white
    BLACK = colors.black


class PageDimensions:
    """Page layout dimensions"""
    PORTRAIT_MARGIN_SIDE = 0.6 * inch
    PORTRAIT_MARGIN_TOP = 0.4 * inch
    PORTRAIT_WIDTH = 7.3 * inch
    PORTRAIT_HEIGHT = 10.4 * inch
    
    LANDSCAPE_MARGIN_SIDE = 0.7 * inch
    LANDSCAPE_MARGIN_TOP = 0.3 * inch
    LANDSCAPE_WIDTH = 9.6 * inch
    LANDSCAPE_HEIGHT = 7.4 * inch


# ============================================================================
# CENTRALIZED STYLES
# ============================================================================

class PDFStyles:
    """Centralized style definitions for all PDF elements"""
    
    def __init__(self):
        self.base_styles = getSampleStyleSheet()
        self._create_custom_styles()
    
    def _create_custom_styles(self):
        """Create all custom styles used throughout the PDF"""
        
        # Title styles
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.base_styles['Heading1'],
            fontSize=24,
            textColor=ButechTheme.PRIMARY_RED,
            alignment=1  # Center alignment
        )
        
        # Section title styles
        self.section_title_style = ParagraphStyle(
            'SectionTitle',
            parent=self.base_styles['Heading3'],
            fontSize=16,
            textColor=ButechTheme.PRIMARY_RED,
            spaceAfter=15,
            alignment=1
        )
        
        self.subsection_title_style = ParagraphStyle(
            'SubsectionTitle',
            parent=self.base_styles['Heading3'],
            fontSize=14,
            textColor=ButechTheme.PRIMARY_RED,
            spaceAfter=10
        )
        
        # Table header style (universal for all tables)
        self.table_header_style = ParagraphStyle(
            'TableHeaderStyle',
            parent=self.base_styles['Normal'],
            fontSize=11,
            leading=12,
            fontName='Helvetica-Bold',
            textColor=ButechTheme.WHITE,
            wordWrap='LTR',
            alignment=1  # Center alignment
        )
        
        # Different sized header styles for different tables
        self.small_header_style = ParagraphStyle(
            'SmallHeaderStyle',
            parent=self.table_header_style,
            fontSize=10,
            leading=11
        )
        
        self.large_header_style = ParagraphStyle(
            'LargeHeaderStyle',
            parent=self.table_header_style,
            fontSize=12,
            leading=14
        )
        
        # Cell content styles
        self.table_cell_style = ParagraphStyle(
            'TableCellStyle',
            parent=self.base_styles['Normal'],
            fontSize=8,
            leading=10,
            wordWrap='LTR'
        )
        
        # Info paragraph style
        self.info_style = self.base_styles['Normal']
        
        # Summary style
        self.summary_style = ParagraphStyle(
            'Summary', 
            parent=self.base_styles['Normal'], 
            fontSize=10
        )
        
        # Preliminary stamp style
        self.preliminary_stamp_style = ParagraphStyle(
            'PreliminaryStamp',
            parent=self.base_styles['Normal'],
            fontSize=14,
            fontName='Helvetica-Bold',
            textColor=ButechTheme.PRIMARY_RED,
            alignment=1,  # Center alignment
            spaceBefore=10,
            spaceAfter=10
        )


class TableStyler:
    """Centralized table styling functionality"""
    
    @staticmethod
    def get_base_table_style():
        """Base table style that all tables inherit"""
        return TableStyle([
            # Universal header styling
            ('BACKGROUND', (0, 0), (-1, 0), ButechTheme.PRIMARY_RED),
            ('TEXTCOLOR', (0, 0), (-1, 0), ButechTheme.WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            
            # Universal borders
            ('GRID', (0, 0), (-1, -1), 1, ButechTheme.BLACK),
            ('LINEWIDTH', (0, 0), (-1, -1), 0.5),
            
            # Header padding
            ('TOPPADDING', (0, 0), (-1, 0), 6),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ])
    
    @staticmethod
    def apply_alternating_rows(table, row_count, start_row=1, end_offset=0):
        """Apply alternating row colors to any table"""
        for i in range(start_row, row_count - end_offset):
            if i % 2 == 1:  # Odd rows - white
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, i), (-1, i), ButechTheme.WHITE)
                ]))
            else:  # Even rows - light gray/red
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, i), (-1, i), ButechTheme.GRAY)
                ]))
    
    @staticmethod
    def style_bom_table(table, row_count):
        """Apply specific styling for BOM table"""
        base_style = TableStyler.get_base_table_style()
        
        # Add BOM-specific styling
        bom_specific = TableStyle([
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('ALIGN', (1, 1), (3, -2), 'LEFT'),  # Part number, description, manufacturer left-aligned
            ('ALIGN', (4, 1), (-1, -2), 'CENTER'),  # Qty, UOM, prices centered
            ('ALIGN', (6, 1), (-1, -2), 'RIGHT'),   # Prices right-aligned
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 8),
            ('TOPPADDING', (0, 1), (-1, -2), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -2), 8),
            
            # Total row styling
            ('BACKGROUND', (0, -1), (-1, -1), ButechTheme.LIGHT_RED),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 11),
            ('ALIGN', (0, -1), (-1, -1), 'RIGHT'),
            ('TOPPADDING', (0, -1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 10),
        ])
        
        table.setStyle(base_style)
        table.setStyle(bom_specific)
        TableStyler.apply_alternating_rows(table, row_count, start_row=1, end_offset=1)
    
    @staticmethod
    def style_summary_table(table, row_count):
        """Apply specific styling for summary table"""
        base_style = TableStyler.get_base_table_style()
        
        summary_specific = TableStyle([
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 1), (-1, -3), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -3), 11),
            ('TOPPADDING', (0, 1), (-1, -3), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -3), 6),
            
            # Separator line
            ('LINEABOVE', (0, -2), (-1, -2), 2, ButechTheme.PRIMARY_RED),
            ('TOPPADDING', (0, -2), (-1, -2), 2),
            ('BOTTOMPADDING', (0, -2), (-1, -2), 2),
            
            # Combined total row
            ('BACKGROUND', (0, -1), (-1, -1), ButechTheme.DARK_RED),
            ('TEXTCOLOR', (0, -1), (-1, -1), ButechTheme.WHITE),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 12),
            ('TOPPADDING', (0, -1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 8),
            ('GRID', (0, -1), (-1, -1), 1, ButechTheme.BLACK),
        ])
        
        table.setStyle(base_style)
        table.setStyle(summary_specific)
        TableStyler.apply_alternating_rows(table, row_count, start_row=1, end_offset=2)
    
    @staticmethod
    def style_category_table(table, row_count):
        """Apply specific styling for category breakdown table"""
        base_style = TableStyler.get_base_table_style()
        
        category_specific = TableStyle([
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Center color indicators
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ])
        
        table.setStyle(base_style)
        table.setStyle(category_specific)
        TableStyler.apply_alternating_rows(table, row_count)
    
    @staticmethod
    def style_category_table_with_descriptions(table, row_count):
        """Apply specific styling for category breakdown table with descriptions"""
        base_style = TableStyler.get_base_table_style()
        
        category_specific = TableStyle([
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),  # Cost and percentage right-aligned
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Center color indicators
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),    # Description left-aligned
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),   # Top alignment for text wrapping
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ])
        
        table.setStyle(base_style)
        table.setStyle(category_specific)
        TableStyler.apply_alternating_rows(table, row_count)
    
    @staticmethod
    def style_labor_table(table, row_count):
        """Apply specific styling for labor costs table"""
        base_style = TableStyler.get_base_table_style()
        
        labor_specific = TableStyle([
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 1), (0, -2), 'LEFT'),  # Labor type left-aligned
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 9),
            ('TOPPADDING', (0, 1), (-1, -2), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -2), 4),
            
            # Total row
            ('BACKGROUND', (0, -1), (-1, -1), ButechTheme.LIGHT_RED),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 10),
            ('ALIGN', (0, -1), (-1, -1), 'RIGHT'),
            ('TOPPADDING', (0, -1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 6),
        ])
        
        table.setStyle(base_style)
        table.setStyle(labor_specific)
        TableStyler.apply_alternating_rows(table, row_count, start_row=1, end_offset=1)


# ============================================================================
# CHART UTILITIES
# ============================================================================

class ChartGenerator:
    """Centralized chart generation functionality"""
    
    CHART_COLORS = [
        rl_colors.Color(0.2, 0.4, 0.8),    # Butech blue
        rl_colors.Color(0.8, 0.4, 0.2),    # Orange
        rl_colors.Color(0.2, 0.8, 0.4),    # Green
        rl_colors.Color(0.8, 0.2, 0.4),    # Red
        rl_colors.Color(0.4, 0.2, 0.8),    # Purple
        rl_colors.Color(0.8, 0.8, 0.2),    # Yellow
        rl_colors.Color(0.2, 0.8, 0.8),    # Cyan
        rl_colors.Color(0.8, 0.2, 0.8),    # Magenta
        rl_colors.Color(0.4, 0.8, 0.2),    # Light green
        rl_colors.Color(0.8, 0.4, 0.8),    # Light purple
    ]
    
    @classmethod
    def create_pie_chart(cls, sorted_categories, total_value, width=320, height=320):
        """Create a pie chart for category breakdown with labels"""
        drawing = Drawing(width, height)
        
        # Create pie chart
        pie = Pie()
        pie.x = 35
        pie.y = 35
        pie.width = width - 70
        pie.height = height - 70
        
        # Prepare data and labels
        pie_data = []
        pie_labels = []
        
        for category, value in sorted_categories:
            pie_data.append(value)
            percentage = (value / total_value) * 100 if total_value > 0 else 0
            # Add category name with percentage
            pie_labels.append(f"{category}\n{percentage:.1f}%")
        
        pie.data = pie_data
        pie.labels = None  # Remove labels to eliminate leader lines
        
        # Assign colors to slices
        for i in range(len(pie_data)):
            pie.slices[i].fillColor = cls.CHART_COLORS[i % len(cls.CHART_COLORS)]
            pie.slices[i].strokeColor = rl_colors.white
            pie.slices[i].strokeWidth = 2
        
        drawing.add(pie)
        return drawing
    
    @classmethod
    def create_color_indicator(cls, color_index):
        """Create a color indicator rectangle for category tables"""
        color_indicator = Drawing(15, 15)
        rect = Rect(2, 2, 11, 11)
        rect.fillColor = cls.CHART_COLORS[color_index % len(cls.CHART_COLORS)]
        rect.strokeColor = colors.black
        rect.strokeWidth = 0.5
        color_indicator.add(rect)
        return color_indicator


# ============================================================================
# TABLE BUILDERS
# ============================================================================

class TableBuilder:
    """Centralized table building functionality"""
    
    def __init__(self, styles: PDFStyles):
        self.styles = styles
    
    def create_header_paragraphs(self, headers, style=None):
        """Convert header strings to Paragraph objects with consistent styling"""
        if style is None:
            style = self.styles.table_header_style
        return [Paragraph(header, style) for header in headers]
    
    def build_bom_table(self, bom_data):
        """Build the main BOM table"""
        # Create headers
        headers = ['#', 'Part Number', 'Description', 'Manufacturer', 'Qty', 'UOM', 'Unit Price', 'Total Price']
        table_data = [self.create_header_paragraphs(headers)]
        
        # Add data rows
        total_value = 0
        for i, item in enumerate(bom_data, 1):
            unit_price = float(item['unit_price'])
            total_quantity = float(item['total_quantity'])
            total_price = total_quantity * unit_price
            total_value += total_price
            
            # Create wrapped paragraphs for text fields
            part_number_para = Paragraph(item['part_number'] or 'N/A', self.styles.table_cell_style)
            description_para = Paragraph(item['component_name'] or item['description'] or 'N/A', self.styles.table_cell_style)
            manufacturer_para = Paragraph(item['manufacturer'] or 'N/A', self.styles.table_cell_style)
            
            table_data.append([
                str(i),
                part_number_para,
                description_para,
                manufacturer_para,
                str(int(total_quantity)),
                item['unit_of_measure'] or 'EA',
                f"${unit_price:,.2f}",
                f"${total_price:,.2f}"
            ])
        
        # Add total row
        table_data.append(['', '', '', '', '', '', 'TOTAL:', f"${total_value:,.2f}"])
        
        # Create table with optimized column widths
        table = Table(table_data, colWidths=[0.3*inch, 0.9*inch, 2.6*inch, 1.2*inch, 0.4*inch, 0.4*inch, 0.7*inch, 0.8*inch], 
                     repeatRows=1)
        
        TableStyler.style_bom_table(table, len(table_data))
        return table
    
    def build_summary_table(self, estimate, total_purchased_components):
        """Build the project cost summary table"""
        # Get totals
        engineering_hours = float(estimate.total_engineering_hours or 0)
        panel_shop_hours_cost = float(estimate.total_panel_shop_cost or 0)
        combined_total = total_purchased_components + panel_shop_hours_cost
        
        # Create table data
        headers = ['Cost Category', 'Amount']
        table_data = [self.create_header_paragraphs(headers, self.styles.large_header_style)]
        
        table_data.extend([
            ['Total Purchased Components', f"${total_purchased_components:,.2f}"],
            [f'Engineering Hours Total ({engineering_hours:.1f} hrs)', f"${float(estimate.total_engineering_cost or 0):,.2f}"],
            [f'Panel Shop Hours Cost ({float(estimate.total_panel_shop_hours or 0):.1f} hrs)', f"${panel_shop_hours_cost:,.2f}"],
            ['', ''],  # Separator
            ['Combined Total (Components + Panel Shop)', f"${combined_total:,.2f}"]
        ])
        
        table = Table(table_data, colWidths=[4.5*inch, 2.0*inch])
        TableStyler.style_summary_table(table, len(table_data))
        return table
    
    def build_category_table(self, sorted_categories, total_value, colWidths):
        """Build category breakdown table with color indicators"""
        headers = ['', 'Category', 'Total Cost', 'Percentage']
        table_data = [self.create_header_paragraphs(headers, self.styles.small_header_style)]
        
        for i, (category, total) in enumerate(sorted_categories):
            percentage = (total / total_value) * 100
            color_indicator = ChartGenerator.create_color_indicator(i)
            
            table_data.append([
                color_indicator,
                category,
                f"${total:,.2f}",
                f"{percentage:.1f}%"
            ])
        
        table = Table(table_data, colWidths=colWidths)
        TableStyler.style_category_table(table, len(table_data))
        return table
    
    def build_category_table_with_descriptions(self, sorted_categories, total_value, category_descriptions, colWidths):
        """Build category breakdown table with color indicators and descriptions"""
        headers = ['', 'Category', 'Description', 'Total Cost', 'Percentage']
        table_data = [self.create_header_paragraphs(headers, self.styles.small_header_style)]
        
        for i, (category, total) in enumerate(sorted_categories):
            percentage = (total / total_value) * 100
            color_indicator = ChartGenerator.create_color_indicator(i)
            
            # Get description with text wrapping
            description = category_descriptions.get(category, 'No description available')
            if not description or description.strip() == '' or description == 'None':
                description = 'No description available'
            description_para = Paragraph(description, self.styles.table_cell_style)
            
            table_data.append([
                color_indicator,
                category,
                description_para,
                f"${total:,.2f}",
                f"{percentage:.1f}%"
            ])
        
        table = Table(table_data, colWidths=colWidths)
        TableStyler.style_category_table_with_descriptions(table, len(table_data))
        return table
    
    def build_labor_table(self, estimate):
        """Build labor costs table"""
        headers = ['Labor Type', 'Hours', 'Rate', 'Total Cost']
        table_data = [self.create_header_paragraphs(headers, self.styles.small_header_style)]
        
        total_labor_cost = 0
        
        # Add labor rows if they have costs
        labor_types = [
            ('Engineering', estimate.total_engineering_hours, estimate.total_engineering_cost),
            ('Panel Shop', estimate.total_panel_shop_hours, estimate.total_panel_shop_cost),
            ('Machine Assembly', estimate.total_machine_assembly_hours, estimate.total_machine_assembly_cost)
        ]
        
        for labor_type, hours, cost in labor_types:
            hours = float(hours or 0)
            cost = float(cost or 0)
            if cost > 0:
                rate = cost / hours if hours > 0 else 0
                table_data.append([
                    labor_type,
                    f"{hours:.1f}",
                    f"${rate:,.2f}/hr",
                    f"${cost:,.2f}"
                ])
                total_labor_cost += cost
        
        # Add total row
        table_data.append(['', '', 'TOTAL LABOR:', f"${total_labor_cost:,.2f}"])
        
        table = Table(table_data, colWidths=[2.0*inch, 1.0*inch, 1.3*inch, 1.5*inch])
        TableStyler.style_labor_table(table, len(table_data))
        return table


# ============================================================================
# MAIN PDF GENERATION
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
    
    # Initialize components
    styles = PDFStyles()
    table_builder = TableBuilder(styles)
    
    # Create PDF with multiple page templates
    buffer = BytesIO()
    
    # Page templates
    portrait_frame = Frame(
        PageDimensions.PORTRAIT_MARGIN_SIDE, 
        PageDimensions.PORTRAIT_MARGIN_TOP,
        PageDimensions.PORTRAIT_WIDTH, 
        PageDimensions.PORTRAIT_HEIGHT, 
        id='portrait'
    )
    portrait_template = PageTemplate(id='portrait', frames=[portrait_frame], pagesize=A4)
    
    landscape_frame = Frame(
        PageDimensions.LANDSCAPE_MARGIN_SIDE, 
        PageDimensions.LANDSCAPE_MARGIN_TOP,
        PageDimensions.LANDSCAPE_WIDTH, 
        PageDimensions.LANDSCAPE_HEIGHT, 
        id='landscape'
    )
    landscape_template = PageTemplate(id='landscape', frames=[landscape_frame], pagesize=landscape(A4))
    
    # Create document
    doc = BaseDocTemplate(buffer, pagesize=A4)
    doc.addPageTemplates([portrait_template, landscape_template])
    
    # Build content
    story = []
    
    # Add header with logo and title
    _add_header_section(story, styles)
    
    # Add project information
    _add_project_info(story, styles, estimate)
    
    # Add comprehensive totals summary
    total_value = sum(float(item['unit_price']) * float(item['total_quantity']) for item in bom_data)
    summary_table = table_builder.build_summary_table(estimate, total_value)
    story.append(Paragraph("Project Cost Summary", styles.section_title_style))
    story.append(Spacer(1, 15))
    story.append(summary_table)
    story.append(Spacer(1, 20))
    
    # Create main BOM table
    bom_table = table_builder.build_bom_table(bom_data)
    story.append(bom_table)
    
    # Add labor costs section
    _add_labor_costs_section(story, styles, estimate, table_builder)
    
    # Add category breakdown on landscape page
    _add_category_breakdown(story, styles, bom_data, table_builder, estimate)
    
    # Add summary with comprehensive total including labor
    category_count = len(set(item.get('category', 'Uncategorized') for item in bom_data))
    engineering_cost = float(estimate.total_engineering_cost or 0)
    panel_shop_cost = float(estimate.total_panel_shop_cost or 0)
    comprehensive_total = total_value + engineering_cost + panel_shop_cost
    
    story.append(Paragraph(
        f"<b>Summary:</b> {len(bom_data)} unique parts, {category_count} categories, Total value: ${comprehensive_total:,.2f}", 
        styles.summary_style
    ))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer


def _add_header_section(story, styles):
    """Add header section with logo and title"""
    logo_path = os.path.join('app', 'static', 'images', 'stacked_rgb_300dpi.jpg')
    
    try:
        if os.path.exists(logo_path):
            logo = Image(logo_path, width=2*inch, height=1*inch)
            title_para = Paragraph("Bill of Materials", styles.title_style)
            
            header_table = Table([[logo, title_para]], colWidths=[2.2*inch, 4.8*inch])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ]))
            story.append(header_table)
            story.append(Spacer(1, 12))
        else:
            story.append(Paragraph("Bill of Materials", styles.title_style))
    except Exception:
        story.append(Paragraph("Bill of Materials", styles.title_style))
    
    # Add preliminary stamp
    story.append(Paragraph("PRELIMINARY AND ESTIMATE ONLY", styles.preliminary_stamp_style))


def _add_project_info(story, styles, estimate):
    """Add project information section"""
    story.append(Paragraph(f"<b>Project:</b> {estimate.project.project_name}", styles.info_style))
    story.append(Paragraph(f"<b>Estimate:</b> {estimate.estimate_name}", styles.info_style))
    story.append(Paragraph(f"<b>Estimate #:</b> {estimate.estimate_number}", styles.info_style))
    story.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles.info_style))
    story.append(Spacer(1, 12))


def _add_labor_costs_section(story, styles, estimate, table_builder):
    """Add labor costs section"""
    # Check if we have any labor costs to display
    panel_shop_cost = float(estimate.total_panel_shop_cost or 0)
    engineering_cost = float(estimate.total_engineering_cost or 0)
    machine_assembly_cost = float(estimate.total_machine_assembly_cost or 0)
    
    if panel_shop_cost > 0 or engineering_cost > 0 or machine_assembly_cost > 0:
        story.append(Spacer(1, 20))
        story.append(Paragraph("Labor Costs", styles.subsection_title_style))
        
        labor_table = table_builder.build_labor_table(estimate)
        story.append(labor_table)
        story.append(Spacer(1, 15))


def _add_category_breakdown(story, styles, bom_data, table_builder, estimate):
    """Add category cost breakdown section with pie chart and table on landscape page"""
    from app.models import PartCategory
    
    # Calculate category totals (materials only)
    category_totals = {}
    total_materials_value = 0
    
    for item in bom_data:
        category = _categorize_item(item)
        item_total_price = float(item['unit_price']) * float(item['total_quantity'])
        total_materials_value += item_total_price
        
        if category not in category_totals:
            category_totals[category] = 0
        category_totals[category] += item_total_price
    
    # Add labor costs to the breakdown
    engineering_cost = float(estimate.total_engineering_cost or 0)
    panel_shop_cost = float(estimate.total_panel_shop_cost or 0)
    
    if engineering_cost > 0:
        category_totals['Engineering Labor'] = engineering_cost
    
    if panel_shop_cost > 0:
        category_totals['Panel Shop Labor'] = panel_shop_cost
    
    # Calculate total value including labor
    total_value = total_materials_value + engineering_cost + panel_shop_cost
    
    # Fetch category descriptions from database
    category_descriptions = {}
    try:
        categories = PartCategory.query.all()
        for cat in categories:
            category_descriptions[cat.name] = cat.description or ''
    except Exception as e:
        print(f"Warning: Could not fetch category descriptions: {e}")
        category_descriptions = {}
    
    # Add descriptions for labor categories
    category_descriptions['Engineering Labor'] = 'Engineering design and programming labor costs'
    category_descriptions['Panel Shop Labor'] = 'Panel fabrication and wiring labor costs'
    
    if category_totals:
        # Switch to landscape for category breakdown
        story.append(NextPageTemplate('landscape'))
        story.append(PageBreak())
        
        story.append(Paragraph("Cost Breakdown by Category", styles.section_title_style))
        
        # Sort categories by value
        sorted_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
        
        # Create layout with table on left, logo and pie chart on right
        category_table = table_builder.build_category_table_with_descriptions(
            sorted_categories, total_value, category_descriptions,
            colWidths=[0.3*inch, 1.8*inch, 1.5*inch, 1.0*inch, 0.7*inch]
        )
        
        # Create right side with logo and pie chart
        right_side_content = _create_right_side_with_logo_and_chart(sorted_categories, total_value)
        
        layout_table = Table([[category_table, right_side_content]], colWidths=[5.5*inch, 3.5*inch])
        layout_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        story.append(layout_table)
        
        # Switch back to portrait
        story.append(NextPageTemplate('portrait'))


def _create_right_side_with_logo_and_chart(sorted_categories, total_value):
    """Create right side content with logo at top and centered pie chart"""
    from reportlab.platypus import KeepTogether
    
    # Create logo
    logo_path = os.path.join('app', 'static', 'images', 'stacked_rgb_300dpi.jpg')
    logo = None
    
    try:
        if os.path.exists(logo_path):
            # Smaller logo for top right - maintain 2:1 aspect ratio
            logo = Image(logo_path, width=1.2*inch, height=0.6*inch)
    except Exception:
        pass
    
    # Create pie chart centered on right half
    pie_chart = ChartGenerator.create_pie_chart(sorted_categories, total_value, width=280, height=280)
    
    # Create layout table for right side
    if logo:
        # Logo at top, spacer, then centered pie chart
        right_content = Table([
            [logo],
            [Spacer(1, 20)],
            [pie_chart]
        ])
        right_content.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'RIGHT'),    # Logo right-aligned
            ('ALIGN', (0, 2), (0, 2), 'CENTER'),   # Pie chart centered
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
    else:
        # Just centered pie chart if no logo
        right_content = Table([[pie_chart]])
        right_content.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
        ]))
    
    return right_content


def _categorize_item(item):
    """Categorize an item using the category from the parts database"""
    # Use the category directly from the parts database
    category = item.get('category', '')
    
    # Only fallback to 'Uncategorized' if no category is provided
    if not category or category.strip() == '':
        return 'Uncategorized'
    
    return category.strip()


def get_bom_filename(estimate):
    """Generate a standardized filename for BOM PDF"""
    safe_name = estimate.estimate_name.replace(" ", "_").replace("/", "_")
    return f"BOM_{estimate.estimate_number}_{safe_name}.pdf"