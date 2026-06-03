import re
from io import BytesIO
import logging

import pdfplumber


logger = logging.getLogger(__name__)


KNOWN_SKILLS = {
    "python",
    "django",
    "django rest framework",
    "react",
    "javascript",
    "typescript",
    "html",
    "css",
    "tailwind",
    "sql",
    "postgresql",
    "sqlite",
    "git",
    "docker",
    "aws",
    "machine learning",
    "nlp",
    "spacy",
    "pandas",
    "numpy",
    "rest api",
}

TARGET_AI_SKILLS = {
    "python",
    "machine learning",
    "nlp",
    "sql",
    "django",
    "react",
    "rest api",
    "git",
}


def analyze_resume_file(uploaded_file):
    text = extract_pdf_text(uploaded_file)
    skills = extract_skills(text)
    education = extract_section_lines(text, ("education", "academic"))
    projects = extract_section_lines(text, ("project", "projects"))
    experience = extract_section_lines(text, ("experience", "work history", "employment"))
    missing_skills = sorted(TARGET_AI_SKILLS - set(skills))
    detected_sections = []
    if education:
        detected_sections.append("Education")
    if experience:
        detected_sections.append("Experience")
    if projects:
        detected_sections.append("Projects")
    missing_sections = [section for section in ("Education", "Experience", "Projects") if section not in detected_sections]
    score_parts = calculate_score_breakdown(skills, detected_sections)

    return {
        "filename": uploaded_file.name,
        "extracted_text": text[:20000],
        "skills": skills,
        "found_skills": skills,
        "education": education,
        "projects": projects,
        "experience": experience,
        "missing_skills": missing_skills,
        "detected_sections": detected_sections,
        "missing_sections": missing_sections,
        "skills_score": score_parts["skills_score"],
        "sections_score": score_parts["sections_score"],
        "score_explanation": build_score_explanation(score_parts, detected_sections, missing_sections),
        "suggestions": build_suggestions(skills, education, projects, experience, missing_skills),
        "interview_questions": build_interview_questions(skills, projects),
        "score": score_parts["score"],
    }


def extract_pdf_text(uploaded_file):
    data = uploaded_file.read()
    text = extract_pdf_text_with_pdfplumber(data)
    if len(text.strip()) >= 100:
        return text

    logger.warning(
        "PDF text extraction returned %s characters for %s; using OCR fallback.",
        len(text.strip()),
        getattr(uploaded_file, "name", "uploaded resume"),
    )
    ocr_text = extract_pdf_text_with_ocr(data)
    return ocr_text or text


def extract_pdf_text_with_pdfplumber(data):
    try:
        with pdfplumber.open(BytesIO(data)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        return "\n".join(pages).strip()
    except Exception as exc:
        logger.warning("PDF text extraction with pdfplumber failed: %s", exc)
        return ""


def extract_pdf_text_with_ocr(data):
    try:
        import pytesseract
        from pdf2image import convert_from_bytes
    except ImportError as exc:
        logger.warning("OCR fallback was triggered but pytesseract/pdf2image is not installed: %s", exc)
        return ""

    try:
        images = convert_from_bytes(data)
        pages = [pytesseract.image_to_string(image) for image in images]
        return "\n".join(pages).strip()
    except Exception as exc:
        logger.warning("OCR fallback failed: %s", exc)
        return ""


def extract_skills(text):
    lowered = text.lower()
    found = [skill for skill in KNOWN_SKILLS if re.search(rf"\b{re.escape(skill)}\b", lowered)]
    return sorted(found)


def extract_section_lines(text, headings):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    matches = []
    capture = False
    for line in lines:
        lowered = line.lower()
        if any(heading in lowered for heading in headings):
            capture = True
            matches.append(line)
            continue
        if capture and re.match(r"^[A-Z][A-Za-z ]{2,30}$", line) and len(matches) >= 2:
            break
        if capture and len(matches) < 6:
            matches.append(line)
    return matches[:6]


def calculate_score_breakdown(skills, detected_sections):
    skills_score = min(len(skills) * 6, 60)
    sections_score = round((len(detected_sections) / 3) * 40)
    return {
        "skills_score": skills_score,
        "sections_score": sections_score,
        "score": min(skills_score + sections_score, 100),
    }


def build_score_explanation(score_parts, detected_sections, missing_sections):
    detected = ", ".join(detected_sections) or "none"
    missing = ", ".join(missing_sections) or "none"
    return (
        f"Score = skills {score_parts['skills_score']}/60 plus sections {score_parts['sections_score']}/40. "
        f"Detected sections: {detected}. Missing sections: {missing}."
    )


def build_suggestions(skills, education, projects, experience, missing_skills):
    suggestions = []
    if missing_skills:
        suggestions.append("Add proof of core AI/full-stack skills: " + ", ".join(missing_skills[:5]) + ".")
    if not projects:
        suggestions.append("Add 2-3 measurable projects with tech stack, problem, impact, and links.")
    if not experience:
        suggestions.append("Add internship, freelance, open-source, or project experience with measurable outcomes.")
    if not education:
        suggestions.append("Add education, certifications, or relevant coursework.")
    if len(skills) < 6:
        suggestions.append("Create a compact skills section grouped by language, backend, frontend, data, and tools.")
    return suggestions or ["Resume has a solid base. Improve impact by adding metrics and project outcomes."]


def build_interview_questions(skills, projects):
    questions = [
        "Walk me through the strongest project on your resume.",
        "How would you design a secure JWT authentication flow?",
        "How do you debug a production API failure?",
    ]
    if "django" in skills:
        questions.append("How do Django serializers, views, and permissions work together?")
    if "react" in skills:
        questions.append("How do you manage state and API errors in a React app?")
    if projects:
        questions.append("What tradeoff did you make in your most recent project and why?")
    return questions[:8]
