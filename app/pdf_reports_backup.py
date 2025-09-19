"""
PDF Report Generation Module

This module handles the generation of various PDF reports for the estimates system.
Currently supports:
- Bill of Materials (BOM) reports with category breakdown
- Professional pie charts for cost visualization
- Side-by-side chart and table layouts
- Butech branding and color schemes
"""

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, PageTemplate, Frame, NextPageTemplate, BaseDocTemplate
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import Image
from io import BytesIO
from datetime import datetime
import os


def generate_bom_pdf(estimate, bom_data):
    """
    Generate a professional Bill of Materials PDF report.
    
    Args:
        estimate: The estimate object containing project and estimate details
        bom_data: List of dictionaries containing BOM item data with keys:
                 - part_number, component_name, description, manufacturer
                 - unit_price, total_quantity, unit_of_measure, category
    
    Returns:
        BytesIO: PDF buffer ready for download
    """
    
    # Sort by total price (most expensive first)
    bom_data.sort(key=lambda x: x['unit_price'] * x['total_quantity'], reverse=True)
    
    # Create PDF with multiple page templates (portrait and landscape)
    buffer = BytesIO()
    
    # Portrait template for main content - increased side margins, decreased top margin
    portrait_frame = Frame(0.6*inch, 0.4*inch, 7.3*inch, 10.4*inch, id='portrait')
    portrait_template = PageTemplate(id='portrait', frames=[portrait_frame], pagesize=A4)
    
    # Landscape template for category breakdown - increased side margins, decreased top margin
    landscape_frame = Frame(0.7*inch, 0.3*inch, 9.6*inch, 7.4*inch, id='landscape')
    landscape_template = PageTemplate(id='landscape', frames=[landscape_frame], pagesize=landscape(A4))
    
    # Use BaseDocTemplate for multiple page templates
    doc = BaseDocTemplate(buffer, pagesize=A4)
    doc.addPageTemplates([portrait_template, landscape_template])
    
    # Build PDF content
    story = []
    styles = getSampleStyleSheet()
    
    # Add header with logo and title
    _add_header_section(story, styles)
    
    # Add project information
    _add_project_info(story, styles, estimate)
    
    # Add comprehensive totals summary
    total_value = sum(float(item['unit_price']) * float(item['total_quantity']) for item in bom_data)
    _add_comprehensive_totals_summary(story, styles, estimate, total_value)
    
    # Create main BOM table
    table = _create_bom_table(bom_data, styles)
    story.append(table)
    
    # Add labor costs section
    _add_labor_costs_section(story, styles, estimate)
    
    # Add category breakdown
    _add_category_breakdown(story, styles, bom_data)
    
    # Add summary
    total_value = sum(float(item['unit_price']) * float(item['total_quantity']) for item in bom_data)
    category_count = len(set(item.get('category', 'Uncategorized') for item in bom_data))
    _add_summary(story, styles, len(bom_data), category_count, total_value)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    
    return buffer


def _add_header_section(story, styles):
    """Add header section with logo and title"""
    logo_path = os.path.join('app', 'static', 'images', 'stacked_rgb_300dpi.jpg')
    
    try:
        if os.path.exists(logo_path):
            # Create logo image with proper aspect ratio
            # Butech logo is approximately 2:1 ratio (width:height)
            logo_width = 2*inch
            logo_height = 1*inch  # Maintain proper aspect ratio
            logo = Image(logo_path, width=logo_width, height=logo_height)
            
            # Create title paragraph
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.Color(0.8, 0.2, 0.2),  # Butech red
                alignment=1  # Center alignment
            )
            title_para = Paragraph("Bill of Materials", title_style)
            
            # Create header table - portrait optimized with proper logo spacing
            header_table = Table([[logo, title_para]], colWidths=[2.2*inch, 4.8*inch])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),    # Logo left
                ('ALIGN', (1, 0), (1, 0), 'CENTER'),  # Title center
            ]))
            story.append(header_table)
            story.append(Spacer(1, 12))
        else:
            # Fallback if logo not found
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                textColor=colors.Color(0.8, 0.2, 0.2)  # Butech red
            )
            story.append(Paragraph("Bill of Materials", title_style))
    except Exception as e:
        # Fallback if image processing fails
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.Color(0.2, 0.4, 0.8)  # Butech blue
        )
        story.append(Paragraph("Bill of Materials", title_style))


def _add_project_info(story, styles, estimate):
    """Add project information section"""
    info_style = styles['Normal']
    story.append(Paragraph(f"<b>Project:</b> {estimate.project.project_name}", info_style))
    story.append(Paragraph(f"<b>Estimate:</b> {estimate.estimate_name}", info_style))
    story.append(Paragraph(f"<b>Estimate #:</b> {estimate.estimate_number}", info_style))
    story.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", info_style))
    story.append(Spacer(1, 12))


def _create_bom_table(bom_data, styles):
    """Create the main BOM table with all items"""
    # Create paragraph style for table cells
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        wordWrap='LTR'
    )
    
    # Create paragraph style for table headers
    header_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontSize=11,
        leading=12,
        fontName='Helvetica-Bold',
        textColor=colors.white,  # White text for headers
        wordWrap='LTR',
        alignment=1  # Center alignment
    )
    
    # Create table data with text wrapping for descriptions and headers
    # Create wrapped paragraphs for all headers to ensure white text
    table_data = [[
        Paragraph('#', header_style),
        Paragraph('Part Number', header_style),
        Paragraph('Description', header_style),
        Paragraph('Manufacturer', header_style),
        Paragraph('Qty', header_style),
        Paragraph('UOM', header_style),
        Paragraph('Unit Price', header_style),
        Paragraph('Total Price', header_style)
    ]]
    
    total_value = 0
    for i, item in enumerate(bom_data, 1):
        # Convert to float to avoid Decimal/float mixing issues
        unit_price = float(item['unit_price'])
        total_quantity = float(item['total_quantity'])
        total_price = total_quantity * unit_price
        total_value += total_price
        
        # Create wrapped paragraphs for longer text fields
        part_number_text = item['part_number'] or 'N/A'
        part_number_para = Paragraph(part_number_text, cell_style)
        
        description_text = item['component_name'] or item['description'] or 'N/A'
        description_para = Paragraph(description_text, cell_style)
        
        manufacturer_text = item['manufacturer'] or 'N/A'
        manufacturer_para = Paragraph(manufacturer_text, cell_style)
        
        table_data.append([
            str(i),
            part_number_para,  # Use paragraph for text wrapping
            description_para,  # Use paragraph for text wrapping
            manufacturer_para,  # Use paragraph for text wrapping
            str(int(total_quantity)),
            item['unit_of_measure'] or 'EA',
            f"${unit_price:,.2f}",
            f"${total_price:,.2f}"
        ])
    
    # Add total row
    table_data.append(['', '', '', '', '', '', 'TOTAL:', f"${total_value:,.2f}"])
    
    # Create table with portrait-optimized column widths (adjusted for increased margins)
    table = Table(table_data, colWidths=[0.3*inch, 0.9*inch, 2.6*inch, 1.2*inch, 0.4*inch, 0.4*inch, 0.7*inch, 0.8*inch], 
                 repeatRows=1)  # Repeat header row on each page
    
    # Apply styling
    _apply_table_styling(table, len(table_data))
    
    return table


def _apply_table_styling(table, row_count):
    """Apply professional styling to the BOM table"""
    # Define Butech color scheme - red header like logo
    butech_red = colors.Color(0.8, 0.2, 0.2)  # Red to match logo
    butech_light_red = colors.Color(0.98, 0.9, 0.9)  # Light red for alternating rows
    butech_gray = colors.Color(0.95, 0.95, 0.95)
    
    # Table styling with Butech colors and improved text wrapping support
    table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), butech_red),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -2), 'LEFT'),  # Part number left-aligned
        ('ALIGN', (2, 1), (2, -2), 'LEFT'),  # Description left-aligned
        ('ALIGN', (3, 1), (3, -2), 'LEFT'),  # Manufacturer left-aligned
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Top alignment for wrapped text
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        
        # Data rows with alternating colors
        ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -2), 8),
        ('ALIGN', (4, 1), (-1, -2), 'CENTER'),  # Qty, UOM, prices centered
        ('ALIGN', (6, 1), (-1, -2), 'RIGHT'),   # Prices right-aligned
        ('TOPPADDING', (0, 1), (-1, -2), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -2), 8),
        
        # Total row
        ('BACKGROUND', (0, -1), (-1, -1), butech_light_red),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 11),
        ('ALIGN', (0, -1), (-1, -1), 'RIGHT'),
        ('TOPPADDING', (0, -1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 10),
        
        # Borders
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('LINEWIDTH', (0, 0), (-1, -1), 0.5)
    ]))
    
    # Apply alternating row colors manually (since ROWBACKGROUNDS doesn't always work as expected)
    for i in range(1, row_count - 1):  # Skip header (0) and total row (-1)
        if i % 2 == 1:  # Odd rows (1, 3, 5, ...) - white
            table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), colors.white)]))
        else:  # Even rows (2, 4, 6, ...) - light gray
            table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), butech_gray)]))


def _add_category_breakdown(story, styles, bom_data):
    """Add category cost breakdown section with pie chart and table on landscape page"""
    # Switch to landscape template for this page only
    story.append(NextPageTemplate('landscape'))
    story.append(PageBreak())
    
    # Calculate category totals
    category_totals = {}
    total_value = 0
    
    for item in bom_data:
        # Get category from the item
        category = item.get('category', 'Uncategorized') or 'Uncategorized'
        
        # If no category, try to categorize by manufacturer
        if category == 'Uncategorized':
            manufacturer = item.get('manufacturer', 'Unknown')
            if 'Allen-Bradley' in manufacturer:
                category = 'Control Components'
            elif 'Phoenix Contact' in manufacturer or 'PHOENIX CONTACT' in manufacturer:
                category = 'Power & Communication'
            elif 'nVent Hoffman' in manufacturer:
                category = 'Enclosures & Hardware'
            elif 'Littelfuse' in manufacturer:
                category = 'Protection Devices'
            elif manufacturer == 'N/A' or manufacturer == '_':
                category = 'Miscellaneous'
            else:
                category = 'Other Components'
        
        item_total_price = float(item['unit_price']) * float(item['total_quantity'])
        total_value += item_total_price
        
        if category not in category_totals:
            category_totals[category] = 0
        category_totals[category] += item_total_price
    
    # Create category breakdown section
    if category_totals:
        # Define colors - red header like logo
        butech_red = colors.Color(0.8, 0.2, 0.2)  # Red to match logo
        butech_light_red = colors.Color(0.98, 0.9, 0.9)  # Light red for alternating rows
        
        # Compact title for landscape
        chart_title = ParagraphStyle('ChartTitle', parent=styles['Heading2'], fontSize=16, spaceAfter=15, alignment=1)
        story.append(Paragraph("Cost Breakdown by Category", chart_title))
        
        # Sort categories by value (largest first)
        sorted_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
        
        # Create side-by-side layout for landscape (table left, chart right)
        category_table = _create_category_table_landscape(sorted_categories, total_value, butech_red, butech_light_red)
        pie_chart = _create_pie_chart_landscape(sorted_categories, total_value)
        
        # Create layout table for side-by-side positioning (adjusted for increased margins)
        layout_table = Table([[category_table, pie_chart]], colWidths=[4.2*inch, 4.8*inch])
        layout_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        story.append(layout_table)
        
        # Switch back to portrait template for any subsequent pages
        story.append(NextPageTemplate('portrait'))


def _create_pie_chart_without_legend(sorted_categories, total_value):
    """Create a pie chart for category breakdown without legend"""
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.lib import colors as rl_colors
    
    # Create drawing - larger since no legend needed
    drawing = Drawing(350, 350)
    
    # Create pie chart - centered and larger
    pie = Pie()
    pie.x = 50
    pie.y = 50
    pie.width = 250
    pie.height = 250
    
    # Prepare data
    pie_data = []
    
    for category, value in sorted_categories:
        pie_data.append(value)
    
    pie.data = pie_data
    # Don't show labels on the pie chart itself since we have the table
    pie.labels = None
    
    # Define a color palette with professional colors
    chart_colors = [
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
    
    # Assign colors to slices
    for i in range(len(pie_data)):
        pie.slices[i].fillColor = chart_colors[i % len(chart_colors)]
        pie.slices[i].strokeColor = rl_colors.white
        pie.slices[i].strokeWidth = 2
    
    # Add chart to drawing
    drawing.add(pie)
    
    return drawing


def _create_pie_chart(sorted_categories, total_value):
    """Create a pie chart for category breakdown (legacy function with legend)"""
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics.charts.legends import Legend
    from reportlab.lib import colors as rl_colors
    
    # Create drawing
    drawing = Drawing(280, 280)
    
    # Create pie chart
    pie = Pie()
    pie.x = 40
    pie.y = 40
    pie.width = 200
    pie.height = 200
    
    # Prepare data
    pie_data = []
    pie_labels = []
    
    for category, value in sorted_categories:
        pie_data.append(value)
        percentage = (value / total_value) * 100
        pie_labels.append(f"{category}\n${value:,.0f} ({percentage:.1f}%)")
    
    pie.data = pie_data
    pie.labels = [label.split('\n')[0] for label in pie_labels]  # Just category names for the chart
    
    # Define a color palette with professional colors
    chart_colors = [
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
    
    # Assign colors to slices
    for i in range(len(pie_data)):
        pie.slices[i].fillColor = chart_colors[i % len(chart_colors)]
        pie.slices[i].strokeColor = rl_colors.white
        pie.slices[i].strokeWidth = 1
    
    # Add chart to drawing
    drawing.add(pie)
    
    # Create legend
    legend = Legend()
    legend.x = 10
    legend.y = 250
    legend.dx = 8
    legend.dy = 8
    legend.fontName = 'Helvetica'
    legend.fontSize = 8
    legend.boxAnchor = 'nw'
    legend.columnMaximum = 10
    legend.strokeWidth = 1
    legend.strokeColor = rl_colors.black
    legend.deltax = 75
    legend.deltay = 10
    legend.autoXPadding = 5
    legend.yGap = 0
    legend.dxTextSpace = 5
    legend.alignment = 'right'
    legend.dividerLines = 1|2|4
    legend.dividerOffsY = 4.5
    legend.subCols.rpad = 30
    
    # Set legend data
    legend.colorNamePairs = [(chart_colors[i % len(chart_colors)], pie_labels[i]) for i in range(len(pie_data))]
    
    # Add legend to drawing
    drawing.add(legend)
    
    return drawing


def _create_pie_chart_landscape(sorted_categories, total_value):
    """Create a pie chart optimized for landscape layout"""
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.lib import colors as rl_colors
    
    # Create drawing - optimized for landscape
    drawing = Drawing(320, 320)
    
    # Create pie chart - larger for landscape
    pie = Pie()
    pie.x = 35
    pie.y = 35
    pie.width = 250
    pie.height = 250
    
    # Prepare data
    pie_data = []
    
    for category, value in sorted_categories:
        pie_data.append(value)
    
    pie.data = pie_data
    # Don't show labels on the pie chart itself since we have the table
    pie.labels = None
    
    # Define a color palette with professional colors
    chart_colors = [
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
    
    # Assign colors to slices
    for i in range(len(pie_data)):
        pie.slices[i].fillColor = chart_colors[i % len(chart_colors)]
        pie.slices[i].strokeColor = rl_colors.white
        pie.slices[i].strokeWidth = 2
    
    # Add chart to drawing
    drawing.add(pie)
    
    return drawing


def _create_category_table_landscape(sorted_categories, total_value, butech_red, butech_light_red):
    """Create the category breakdown table optimized for landscape layout"""
    from reportlab.graphics.shapes import Drawing, Rect
    from reportlab.lib import colors as rl_colors
    
    # Define the same color palette as the pie chart
    chart_colors = [
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
    
    # Create category breakdown table with color indicators - landscape optimized
    # Create header style for category table
    from reportlab.lib.styles import getSampleStyleSheet
    sample_styles = getSampleStyleSheet()
    category_header_style = ParagraphStyle(
        'CategoryHeaderStyle',
        parent=sample_styles['Normal'],
        fontSize=10,
        leading=11,
        fontName='Helvetica-Bold',
        textColor=colors.white,  # White text for headers
        wordWrap='LTR',
        alignment=1  # Center alignment
    )
    
    # Create wrapped headers
    category_header = Paragraph('Category', category_header_style)
    total_cost_header = Paragraph('Total Cost', category_header_style)
    percentage_header = Paragraph('Percentage', category_header_style)
    
    category_table_data = [['', category_header, total_cost_header, percentage_header]]
    
    for i, (category, total) in enumerate(sorted_categories):
        percentage = (total / total_value) * 100
        
        # Create color indicator
        color_indicator = Drawing(15, 15)
        rect = Rect(2, 2, 11, 11)
        rect.fillColor = chart_colors[i % len(chart_colors)]
        rect.strokeColor = colors.black
        rect.strokeWidth = 0.5
        color_indicator.add(rect)
        
        category_table_data.append([
            color_indicator,
            category,
            f"${total:,.2f}",
            f"{percentage:.1f}%"
        ])
    
    # Create category table with landscape-optimized column widths (fixed header alignment)
    category_table = Table(category_table_data, colWidths=[0.3*inch, 2.0*inch, 1.3*inch, 0.9*inch])
    category_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), butech_red),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Center color indicators
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 4),
        
        # Data rows
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        
        # Borders
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('LINEWIDTH', (0, 0), (-1, -1), 0.5)
    ]))
    
    # Apply alternating row colors to category table
    for i in range(1, len(category_table_data)):
        if i % 2 == 1:  # Odd rows - white
            category_table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), colors.white)]))
        else:  # Even rows - light blue
            category_table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), butech_light_red)]))
    
    return category_table


def _create_pie_chart_portrait(sorted_categories, total_value):
    """Create a pie chart optimized for portrait layout"""
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.lib import colors as rl_colors
    
    # Create drawing - optimized for portrait
    drawing = Drawing(300, 300)
    
    # Create pie chart - centered
    pie = Pie()
    pie.x = 50
    pie.y = 50
    pie.width = 200
    pie.height = 200
    
    # Prepare data
    pie_data = []
    
    for category, value in sorted_categories:
        pie_data.append(value)
    
    pie.data = pie_data
    # Don't show labels on the pie chart itself since we have the table
    pie.labels = None
    
    # Define a color palette with professional colors
    chart_colors = [
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
    
    # Assign colors to slices
    for i in range(len(pie_data)):
        pie.slices[i].fillColor = chart_colors[i % len(chart_colors)]
        pie.slices[i].strokeColor = rl_colors.white
        pie.slices[i].strokeWidth = 2
    
    # Add chart to drawing
    drawing.add(pie)
    
    return drawing


def _create_category_table_portrait(sorted_categories, total_value, butech_red, butech_light_red):
    """Create the category breakdown table optimized for portrait layout"""
    from reportlab.graphics.shapes import Drawing, Rect
    from reportlab.lib import colors as rl_colors
    
    # Define the same color palette as the pie chart
    chart_colors = [
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
    
    # Create category breakdown table with color indicators - portrait optimized
    # Create header style for category table
    from reportlab.lib.styles import getSampleStyleSheet
    sample_styles = getSampleStyleSheet()
    category_header_style = ParagraphStyle(
        'CategoryHeaderStyle',
        parent=sample_styles['Normal'],
        fontSize=11,
        leading=12,
        fontName='Helvetica-Bold',
        wordWrap='LTR',
        alignment=1  # Center alignment
    )
    
    # Create wrapped headers
    category_header = Paragraph('Category', category_header_style)
    total_cost_header = Paragraph('Total Cost', category_header_style)
    percentage_header = Paragraph('Percentage', category_header_style)
    
    category_table_data = [['', category_header, total_cost_header, percentage_header]]
    
    for i, (category, total) in enumerate(sorted_categories):
        percentage = (total / total_value) * 100
        
        # Create color indicator
        color_indicator = Drawing(15, 15)
        rect = Rect(2, 2, 11, 11)
        rect.fillColor = chart_colors[i % len(chart_colors)]
        rect.strokeColor = colors.black
        rect.strokeWidth = 0.5
        color_indicator.add(rect)
        
        category_table_data.append([
            color_indicator,
            category,
            f"${total:,.2f}",
            f"{percentage:.1f}%"
        ])
    
    # Create category table with portrait-optimized column widths
    category_table = Table(category_table_data, colWidths=[0.3*inch, 3.5*inch, 1.5*inch, 1.0*inch])
    category_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), butech_red),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Center color indicators
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        
        # Data rows
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        
        # Borders
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('LINEWIDTH', (0, 0), (-1, -1), 0.5)
    ]))
    
    # Apply alternating row colors to category table
    for i in range(1, len(category_table_data)):
        if i % 2 == 1:  # Odd rows - white
            category_table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), colors.white)]))
        else:  # Even rows - light blue
            category_table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), butech_light_red)]))
    
    return category_table


def _create_category_table(sorted_categories, total_value, butech_red, butech_light_red):
    """Create the category breakdown table with color indicators"""
    from reportlab.graphics.shapes import Drawing, Rect
    from reportlab.lib import colors as rl_colors
    
    # Define the same color palette as the pie chart
    chart_colors = [
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
    
    # Create category breakdown table with color indicators
    # Create header style for category table
    from reportlab.lib.styles import getSampleStyleSheet
    sample_styles = getSampleStyleSheet()
    category_header_style = ParagraphStyle(
        'CategoryHeaderStyle',
        parent=sample_styles['Normal'],
        fontSize=10,
        leading=11,
        fontName='Helvetica-Bold',
        textColor=colors.white,  # White text for headers
        wordWrap='LTR',
        alignment=1  # Center alignment
    )
    
    # Create wrapped headers
    category_header = Paragraph('Category', category_header_style)
    total_cost_header = Paragraph('Total Cost', category_header_style)
    percentage_header = Paragraph('Percentage', category_header_style)
    
    category_table_data = [['', category_header, total_cost_header, percentage_header]]
    
    for i, (category, total) in enumerate(sorted_categories):
        percentage = (total / total_value) * 100
        
        # Create color indicator
        color_indicator = Drawing(15, 15)
        rect = Rect(2, 2, 11, 11)
        rect.fillColor = chart_colors[i % len(chart_colors)]
        rect.strokeColor = colors.black
        rect.strokeWidth = 0.5
        color_indicator.add(rect)
        
        category_table_data.append([
            color_indicator,
            category,
            f"${total:,.2f}",
            f"{percentage:.1f}%"
        ])
    
    # Create category table with adjusted column widths
    category_table = Table(category_table_data, colWidths=[0.3*inch, 2.2*inch, 1.2*inch, 0.8*inch])
    category_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), butech_red),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Center color indicators
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        
        # Data rows
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        
        # Borders
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('LINEWIDTH', (0, 0), (-1, -1), 0.5)
    ]))
    
    # Apply alternating row colors to category table
    for i in range(1, len(category_table_data)):
        if i % 2 == 1:  # Odd rows - white
            category_table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), colors.white)]))
        else:  # Even rows - light blue
            category_table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), butech_light_red)]))
    
    return category_table


def _add_comprehensive_totals_summary(story, styles, estimate, total_purchased_components):
    """Add comprehensive totals summary at the top of the report"""
    story.append(Spacer(1, 15))
    
    # Get all the required totals
    engineering_hours = float(estimate.total_engineering_hours or 0)
    panel_shop_hours_cost = float(estimate.total_panel_shop_cost or 0)
    combined_total = total_purchased_components + panel_shop_hours_cost
    
    # Create summary title
    summary_title_style = ParagraphStyle(
        'SummaryTitle',
        parent=styles['Heading3'],
        fontSize=16,
        textColor=colors.Color(0.8, 0.2, 0.2),  # Butech red
        spaceAfter=15,
        alignment=1  # Center alignment
    )
    story.append(Paragraph("Project Cost Summary", summary_title_style))
    
    # Create summary table
    summary_table_data = []
    
    # Create header style for summary table
    summary_header_style = ParagraphStyle(
        'SummaryHeaderStyle',
        parent=styles['Normal'],
        fontSize=12,
        leading=14,
        fontName='Helvetica-Bold',
        textColor=colors.white,  # White text for headers
        wordWrap='LTR',
        alignment=1  # Center alignment
    )
    
    # Create data style for summary table
    summary_data_style = ParagraphStyle(
        'SummaryDataStyle',
        parent=styles['Normal'],
        fontSize=11,
        leading=13,
        fontName='Helvetica',
        alignment=2  # Right alignment for numbers
    )
    
    # Create wrapped headers
    summary_table_data = [[
        Paragraph('Cost Category', summary_header_style),
        Paragraph('Amount', summary_header_style)
    ]]
    
    # Add the requested totals
    summary_table_data.append([
        'Total Purchased Components',
        f"${total_purchased_components:,.2f}"
    ])
    
    summary_table_data.append([
        f'Engineering Hours Total ({engineering_hours:.1f} hrs)',
        f"${float(estimate.total_engineering_cost or 0):,.2f}"
    ])
    
    summary_table_data.append([
        f'Panel Shop Hours Cost ({float(estimate.total_panel_shop_hours or 0):.1f} hrs)',
        f"${panel_shop_hours_cost:,.2f}"
    ])
    
    # Add separator line
    summary_table_data.append(['', ''])
    
    # Add combined total (purchased components + panel shop hours cost)
    summary_table_data.append([
        'Combined Total (Components + Panel Shop)',
        f"${combined_total:,.2f}"
    ])
    
    # Create table with appropriate column widths
    summary_table = Table(summary_table_data, colWidths=[4.5*inch, 2.0*inch])
    
    # Apply styling
    butech_red = colors.Color(0.8, 0.2, 0.2)
    butech_light_red = colors.Color(0.98, 0.9, 0.9)
    butech_dark_red = colors.Color(0.6, 0.1, 0.1)
    
    summary_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), butech_red),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        
        # Data rows
        ('FONTNAME', (0, 1), (-1, -3), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -3), 11),
        ('TOPPADDING', (0, 1), (-1, -3), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -3), 6),
        
        # Separator row (empty row)
        ('LINEABOVE', (0, -2), (-1, -2), 2, butech_red),
        ('TOPPADDING', (0, -2), (-1, -2), 2),
        ('BOTTOMPADDING', (0, -2), (-1, -2), 2),
        
        # Combined total row (highlighted)
        ('BACKGROUND', (0, -1), (-1, -1), butech_dark_red),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
        ('TOPPADDING', (0, -1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 8),
        
        # Borders
        ('GRID', (0, 0), (-1, -3), 1, colors.black),
        ('GRID', (0, -1), (-1, -1), 1, colors.black),
        ('LINEWIDTH', (0, 0), (-1, -1), 0.5)
    ]))
    
    # Apply alternating row colors for data rows (excluding header, separator, and total)
    for i in range(1, len(summary_table_data) - 2):  # Skip header, separator, and total
        if i % 2 == 1:  # Odd rows - white
            summary_table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), colors.white)]))
        else:  # Even rows - light red
            summary_table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), butech_light_red)]))
    
    story.append(summary_table)
    story.append(Spacer(1, 20))


def _add_labor_costs_section(story, styles, estimate):
    """Add labor costs section showing panel shop hours and other labor costs"""
    # Only add this section if there are actual labor costs
    panel_shop_hours = float(estimate.total_panel_shop_hours or 0)
    panel_shop_cost = float(estimate.total_panel_shop_cost or 0)
    engineering_hours = float(estimate.total_engineering_hours or 0)
    engineering_cost = float(estimate.total_engineering_cost or 0)
    machine_assembly_hours = float(estimate.total_machine_assembly_hours or 0)
    machine_assembly_cost = float(estimate.total_machine_assembly_cost or 0)
    
    # Check if we have any labor costs to display
    if panel_shop_cost > 0 or engineering_cost > 0 or machine_assembly_cost > 0:
        story.append(Spacer(1, 20))
        
        # Labor costs title
        labor_title_style = ParagraphStyle(
            'LaborTitle',
            parent=styles['Heading3'],
            fontSize=14,
            textColor=colors.Color(0.8, 0.2, 0.2),  # Butech red
            spaceAfter=10
        )
        story.append(Paragraph("Labor Costs", labor_title_style))
        
        # Create labor costs table
        labor_table_data = [['Labor Type', 'Hours', 'Rate', 'Total Cost']]
        
        # Create header style for labor table
        labor_header_style = ParagraphStyle(
            'LaborHeaderStyle',
            parent=styles['Normal'],
            fontSize=10,
            leading=11,
            fontName='Helvetica-Bold',
            textColor=colors.white,  # White text for headers
            wordWrap='LTR',
            alignment=1  # Center alignment
        )
        
        # Create wrapped headers
        labor_table_data = [[
            Paragraph('Labor Type', labor_header_style),
            Paragraph('Hours', labor_header_style),
            Paragraph('Rate', labor_header_style),
            Paragraph('Total Cost', labor_header_style)
        ]]
        
        total_labor_cost = 0
        
        # Engineering hours
        if engineering_cost > 0:
            eng_rate = engineering_cost / engineering_hours if engineering_hours > 0 else 0
            labor_table_data.append([
                'Engineering',
                f"{engineering_hours:.1f}",
                f"${eng_rate:,.2f}/hr",
                f"${engineering_cost:,.2f}"
            ])
            total_labor_cost += engineering_cost
        
        # Panel shop hours
        if panel_shop_cost > 0:
            panel_rate = panel_shop_cost / panel_shop_hours if panel_shop_hours > 0 else 0
            labor_table_data.append([
                'Panel Shop',
                f"{panel_shop_hours:.1f}",
                f"${panel_rate:,.2f}/hr",
                f"${panel_shop_cost:,.2f}"
            ])
            total_labor_cost += panel_shop_cost
        
        # Machine assembly hours
        if machine_assembly_cost > 0:
            machine_rate = machine_assembly_cost / machine_assembly_hours if machine_assembly_hours > 0 else 0
            labor_table_data.append([
                'Machine Assembly',
                f"{machine_assembly_hours:.1f}",
                f"${machine_rate:,.2f}/hr",
                f"${machine_assembly_cost:,.2f}"
            ])
            total_labor_cost += machine_assembly_cost
        
        # Add total row
        labor_table_data.append(['', '', 'TOTAL LABOR:', f"${total_labor_cost:,.2f}"])
        
        # Create table with appropriate column widths
        labor_table = Table(labor_table_data, colWidths=[2.0*inch, 1.0*inch, 1.3*inch, 1.5*inch])
        
        # Apply styling
        butech_red = colors.Color(0.8, 0.2, 0.2)
        butech_light_red = colors.Color(0.98, 0.9, 0.9)
        
        labor_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), butech_red),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (0, 1), (0, -2), 'LEFT'),  # Labor type left-aligned
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 4),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 9),
            ('TOPPADDING', (0, 1), (-1, -2), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -2), 4),
            
            # Total row
            ('BACKGROUND', (0, -1), (-1, -1), butech_light_red),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 10),
            ('ALIGN', (0, -1), (-1, -1), 'RIGHT'),
            ('TOPPADDING', (0, -1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 6),
            
            # Borders
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('LINEWIDTH', (0, 0), (-1, -1), 0.5)
        ]))
        
        # Apply alternating row colors
        for i in range(1, len(labor_table_data) - 1):  # Skip header and total
            if i % 2 == 1:  # Odd rows - white
                labor_table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), colors.white)]))
            else:  # Even rows - light red
                labor_table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), butech_light_red)]))
        
        story.append(labor_table)
        story.append(Spacer(1, 15))


def _add_summary(story, styles, part_count, category_count, total_value):
    """Add summary section"""
    summary_style = ParagraphStyle('Summary', parent=styles['Normal'], fontSize=10)
    story.append(Paragraph(
        f"<b>Summary:</b> {part_count} unique parts, {category_count} categories, Total value: ${total_value:,.2f}", 
        summary_style
    ))


def get_bom_filename(estimate):
    """Generate a standardized filename for BOM PDF"""
    safe_name = estimate.estimate_name.replace(" ", "_").replace("/", "_")
    return f"BOM_{estimate.estimate_number}_{safe_name}.pdf"