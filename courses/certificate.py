"""
Professional Certificate Generation for Course Completion.
Generates high-quality PDF certificates with Navy Blue & Metallic Gold design.
Features: RADOKI logo support, instructor signatures, CEO signature block.
"""

from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import os


class CertificateGenerator:
    """Generate professional certificate PDFs with Navy & Gold design."""
    
    def __init__(self):
        self.pagesize = landscape(A4)
        self.width, self.height = self.pagesize
        # Professional color scheme
        self.navy_blue = colors.HexColor('#001F3F')      # Deep Navy Blue
        self.gold = colors.HexColor('#D4AF37')           # Metallic Gold
        self.cream = colors.HexColor('#FFF8DC')          # Cream background
        self.dark_text = colors.HexColor('#2C2C2C')      # Dark gray text
        
    def generate_certificate(self, student_name, course_name, completion_date, 
                           instructor_name, start_date=None, ceo_name="Raymond Dominic", 
                           logo_path=None, issue_number=None):
        """
        Generate a professional certificate PDF with Navy Blue & Gold design.
        
        Args:
            student_name (str): Full name of the student
            course_name (str): Name of the course
            completion_date (datetime): Date course was completed
            instructor_name (str): Name of the instructor
            start_date (datetime): Optional course start date
            ceo_name (str): Name of CEO for signature (default: Raymond Dominic)
            logo_path (str): Optional path to RADOKI logo image
            issue_number (str): Optional certificate number
            
        Returns:
            BytesIO: PDF file in memory
        """
        pdf_buffer = BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=landscape(A4))
        width, height = landscape(A4)
        
        # Set background color (cream)
        c.setFillColor(self.cream)
        c.rect(0, 0, width, height, fill=1, stroke=0)
        
        # ============ BORDER DESIGN ============
        # Outer border - Navy Blue (thick)
        margin_outer = 0.5 * inch
        c.setLineWidth(4)
        c.setStrokeColor(self.navy_blue)
        c.rect(margin_outer, margin_outer, width - 2*margin_outer, height - 2*margin_outer, stroke=1, fill=0)
        
        # Inner border - Gold (thin)
        margin_inner = margin_outer + 0.2 * inch
        c.setLineWidth(1.5)
        c.setStrokeColor(self.gold)
        c.rect(margin_inner, margin_inner, width - 2*margin_inner, height - 2*margin_inner, stroke=1, fill=0)
        
        # Logo removed from template
        
        # ============ TITLE (DISTRIBUTED VERTICALLY) ============
        # Title positioned at upper-middle with breathing room
        title_x = width / 2
        title_y = height - margin_inner - 0.75 * inch
        
        c.setFont("Courier-Bold", 48)
        c.setFillColor(self.navy_blue)
        c.drawCentredString(title_x, title_y, "Certificate")
        
        c.setFont("Courier-Bold", 28)
        c.setFillColor(self.gold)
        c.drawCentredString(title_x, title_y - 0.5*inch, "of Completion")
        
        # ============ INTRODUCTORY TEXT WITH SPACING ============
        intro_y = title_y - 1.25 * inch
        c.setFont("Helvetica", 13)
        c.setFillColor(self.dark_text)
        c.drawCentredString(title_x, intro_y, "This is to certify that")
        
        # ============ RECIPIENT NAME WITH PROPER SPACING ============
        name_y = intro_y - 0.65 * inch
        c.setFont("Courier-BoldOblique", 40)
        c.setFillColor(self.navy_blue)
        c.drawCentredString(title_x, name_y, student_name)
        
        # Underline for name
        name_underline_y = name_y - 0.2 * inch
        underline_width = 4.0 * inch
        c.setLineWidth(2.5)
        c.setStrokeColor(self.gold)
        c.line(title_x - underline_width/2, name_underline_y, title_x + underline_width/2, name_underline_y)
        
        # ============ ACHIEVEMENT TEXT WITH BALANCED SPACING ============
        achievement_y = name_y - 0.85 * inch
        line_height = 0.25 * inch
        
        c.setFont("Helvetica", 13)
        c.setFillColor(self.dark_text)
        c.drawCentredString(title_x, achievement_y, "has successfully completed the")
        
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(self.navy_blue)
        c.drawCentredString(title_x, achievement_y - line_height, course_name)
        
        c.setFont("Helvetica", 12)
        c.setFillColor(self.dark_text)
        c.drawCentredString(title_x, achievement_y - line_height * 1.8, "Course")
        
        # ============ COURSE DATES - CONSISTENT FORMAT WITH SPACING ============
        dates_y = achievement_y - line_height * 2.5
        c.setFont("Helvetica", 12)
        c.setFillColor(self.dark_text)
        
        # Format dates consistently - handle both datetime and string formats
        def format_date(date_obj):
            if isinstance(date_obj, datetime):
                return date_obj.strftime("%d %B %Y")
            else:
                # Try to parse string dates
                date_str = str(date_obj).strip()
                try:
                    # Handle ISO format (YYYY-MM-DD)
                    if '-' in date_str and len(date_str) == 10:
                        parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
                        return parsed_date.strftime("%d %B %Y")
                except:
                    pass
                return date_str
        
        if start_date:
            start_date_str = format_date(start_date)
        else:
            start_date_str = "[START DATE]"
        
        completion_date_str = format_date(completion_date)
        
        c.drawCentredString(title_x, dates_y, "Course Period:")
        c.drawCentredString(title_x, dates_y - line_height * 0.8, f"{start_date_str} to {completion_date_str}")
        
        # ============ COMPETENCY STATEMENT WITH SPACING ============
        competency_y = dates_y - line_height * 2.0
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(self.navy_blue)
        c.drawCentredString(title_x, competency_y, "has successfully demonstrated proficiency in the theoretical")
        c.drawCentredString(title_x, competency_y - line_height * 0.75, f"knowledge and practical application of {course_name.lower()} principles.")
        
        # ============ SIGNATURE BLOCKS SECTION ============
        sig_top_y = competency_y - line_height * 2.0
        
        # Separator line before signatures
        sep_line_y = sig_top_y - 0.15 * inch
        c.setLineWidth(1)
        c.setStrokeColor(self.gold)
        c.line(margin_inner + 0.5*inch, sep_line_y, width - margin_inner - 0.5*inch, sep_line_y)
        
        # Signature line details - spread across width
        line_length = 1.6 * inch
        line_y = sig_top_y - 0.65 * inch
        sig_name_y = line_y - 0.3 * inch
        sig_title_y = sig_name_y - 0.25 * inch
        
        # Left signature - Instructor
        left_sig_x = width * 0.25
        c.setLineWidth(1.5)
        c.setStrokeColor(self.navy_blue)
        c.line(left_sig_x - line_length/2, line_y, left_sig_x + line_length/2, line_y)
        
        c.setFont("Helvetica", 11)
        c.setFillColor(self.dark_text)
        c.drawCentredString(left_sig_x, sig_name_y, instructor_name)
        
        c.setFont("Helvetica", 10)
        c.setFillColor(self.dark_text)
        c.drawCentredString(left_sig_x, sig_title_y, "Instructor Signature")
        
        # Right signature - CEO
        right_sig_x = width * 0.75
        c.setLineWidth(1.5)
        c.setStrokeColor(self.navy_blue)
        c.line(right_sig_x - line_length/2, line_y, right_sig_x + line_length/2, line_y)
        
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(self.navy_blue)
        c.drawCentredString(right_sig_x, sig_name_y, ceo_name)
        
        c.setFont("Helvetica", 10)
        c.setFillColor(self.dark_text)
        c.drawCentredString(right_sig_x, sig_title_y, "CEO RADOKI Statistics Solutions")
        
        # ============ FOOTER ============
        footer_y = margin_inner + 0.2 * inch
        
        c.showPage()
        c.save()
        
        pdf_buffer.seek(0)
        return pdf_buffer
    
    def generate_simple_certificate(self, student_name, course_name, completion_date, 
                                   instructor_name, start_date=None, logo_path=None):
        """
        Alias to generate_certificate for backwards compatibility.
        """
        return self.generate_certificate(
            student_name=student_name,
            course_name=course_name,
            completion_date=completion_date,
            instructor_name=instructor_name,
            start_date=start_date,
            logo_path=logo_path
        )


def generate_certificate_pdf(enrollment):
    """
    Convenience function to generate certificate for an enrollment.
    Automatically pulls course info and logo from project folder.
    
    Args:
        enrollment: Enrollment object with student, course, and completion info
        
    Returns:
        BytesIO: PDF file in memory
    """
    generator = CertificateGenerator()
    
    # Try to find RADOKI logo in static/images folder
    logo_path = None
    possible_paths = [
        os.path.join(os.path.dirname(__file__), '../static/images/radoki_logo.png'),
        os.path.join(os.path.dirname(__file__), '../static/images/logo.png'),
        os.path.join(os.path.dirname(__file__), '../media/logo.png'),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            logo_path = path
            break
    
    return generator.generate_simple_certificate(
        student_name=enrollment.student.get_full_name() or enrollment.student.username,
        course_name=enrollment.course.title,
        completion_date=enrollment.completed_at,
        instructor_name=enrollment.course.instructor.get_full_name() or enrollment.course.instructor.username,
        start_date=enrollment.course.start_date,
        logo_path=logo_path
    )
