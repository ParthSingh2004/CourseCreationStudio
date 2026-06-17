from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from models.schemas import GeneratedCourse
import os
from config import Config
from typing import Optional

def build_quiz_pdf(course: GeneratedCourse) -> Optional[str]:
    if not course.content or not course.content.quizzes:
        return None
        
    output_path = os.path.join(Config.PDF_OUTPUT_DIR, f"{course.course_id}_quiz.pdf")
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    story.append(Paragraph(f"Quiz: {course.outline.title}", styles['Title']))
    story.append(Spacer(1, 12))
        
    answer_key = []
    q_num = 1
    for quiz in course.content.quizzes:
        story.append(Paragraph(f"Module {quiz.module_index} Quiz", styles['Heading2']))
        for q in quiz.questions:
            story.append(Paragraph(f"{q_num}. {q.question}", styles['Heading3']))
            for i, opt in enumerate(q.options):
                story.append(Paragraph(f"{chr(65+i)}. {opt}", styles['Normal']))
            story.append(Spacer(1, 12))
            
            answer_key.append(f"Q{q_num}: {chr(65+q.correct_index)} - {q.explanation}")
            q_num += 1
            
    story.append(PageBreak())
    story.append(Paragraph("Answer Key", styles['Heading1']))
    for ans in answer_key:
        story.append(Paragraph(ans, styles['Normal']))
        story.append(Spacer(1, 6))
        
    doc.build(story)
    return output_path

def build_summary_pdf(course: GeneratedCourse) -> Optional[str]:
    if not course.content or not course.content.lessons:
        return None
        
    output_path = os.path.join(Config.PDF_OUTPUT_DIR, f"{course.course_id}_summary.pdf")
    doc = SimpleDocTemplate(output_path, pagesize=letter, leftMargin=0.75*inch, rightMargin=0.75*inch)
    styles = getSampleStyleSheet()

    # Custom style for the essay body text
    essay_style = ParagraphStyle(
        'EssayBody',
        parent=styles['Normal'],
        fontSize=10.5,
        leading=16,          # line height
        spaceAfter=8,
        textColor=HexColor('#334155'),
        leftIndent=0,
    )

    # Custom style for the essay section label
    essay_label_style = ParagraphStyle(
        'EssayLabel',
        parent=styles['Heading3'],
        fontSize=10,
        textColor=HexColor('#1E5EF3'),
        spaceBefore=10,
        spaceAfter=4,
    )

    story = []
    
    story.append(Paragraph(f"Course Summary: {course.outline.title}", styles['Title']))
    story.append(Spacer(1, 12))
        
    for module in course.outline.modules:
        story.append(Paragraph(f"Module {module.index}: {module.title}", styles['Heading1']))
        story.append(Spacer(1, 8))
        
        lessons = [l for l in course.content.lessons if l.module_index == module.index]
        for lesson in lessons:
            story.append(Paragraph(f"Lesson {lesson.lesson_index}: {lesson.title}", styles['Heading2']))

            # Key Takeaways bullets
            story.append(Paragraph("Key Takeaways:", styles['Heading3']))
            for tk in lesson.key_takeaways:
                story.append(Paragraph(f"• {tk}", styles['Normal']))
            story.append(Spacer(1, 10))

            # Lesson Essay — only if present (new courses)
            if lesson.lesson_essay and lesson.lesson_essay.strip():
                story.append(Paragraph("Deep Dive:", essay_label_style))
                # Split on newlines so multi-paragraph essays render as separate paragraphs
                for para in lesson.lesson_essay.split('\n'):
                    if para.strip():
                        story.append(Paragraph(para.strip(), essay_style))
                story.append(Spacer(1, 6))

            # Thin divider between lessons
            story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor('#e2e8f0'), spaceAfter=10))
            
        fc_deck = next((fc for fc in course.content.flashcards if fc.module_index == module.index), None)
        if fc_deck and fc_deck.cards:
            story.append(Paragraph("Flashcards:", styles['Heading3']))
            for card in fc_deck.cards:
                story.append(Paragraph(f"<b>F:</b> {card.front}", styles['Normal']))
                story.append(Paragraph(f"<b>B:</b> {card.back}", styles['Normal']))
                story.append(Spacer(1, 6))
        
        story.append(PageBreak())
        
    doc.build(story)
    return output_path

