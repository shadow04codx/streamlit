# app.py
import streamlit as st
import base64
import io
import re
import fitz  # PyMuPDF
import matplotlib.pyplot as plt
from PIL import Image
import requests

# ---------------------------
# 🌐 App Setup
# ---------------------------
st.set_page_config(page_title="AI Job Assistant", layout="wide")

# OpenRouter settings (load from Streamlit secrets)
OPENROUTER_API_KEY = st.secrets["OPENROUTER_API_KEY"]
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ---------------------------
# 🔧 Utility Functions
# ---------------------------
@st.cache_data
def extract_text_from_pdf(uploaded_file):
    """Extract plain text from uploaded PDF resume."""
    with fitz.open(stream=uploaded_file.read(), filetype="pdf") as pdf_doc:
        return "\n".join(page.get_text("text") for page in pdf_doc).strip()


def input_pdf_setup(uploaded_file):
    """Convert first page of PDF into image and Base64 encoding."""
    if uploaded_file is None:
        raise FileNotFoundError("No file uploaded")
    with fitz.open(stream=uploaded_file.read(), filetype="pdf") as pdf_doc:
        first_page = pdf_doc[0].get_pixmap()
        img_bytes = first_page.tobytes("png")
        encoded_img = base64.b64encode(img_bytes).decode()
        return Image.open(io.BytesIO(img_bytes)), encoded_img


def get_openrouter_response(prompt, job_desc="", resume_text=""):
    """Send prompt to OpenRouter API and return response text."""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "anthropic/claude-3.5-sonnet",  # Change to gpt-4, llama, mistral, etc.
        "messages": [
            {"role": "system", "content": "You are an expert ATS resume analyzer and career coach."},
            {"role": "user", "content": f"Job Description:\n{job_desc}\n\nResume:\n{resume_text}\n\nTask:\n{prompt}"}
        ],
    }

    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ Error: {str(e)}"


def extract_match_percentage(response_text):
    """Extract numeric match percentage from AI response."""
    match = re.search(r"Match\s*Percentage[:\s]*([\d]+)%", response_text, re.IGNORECASE)
    if match:
        return int(match.group(1))

    numbers = [int(num) for num in re.findall(r'\b\d+\b', response_text)]
    for num in numbers:
        if 50 <= num <= 100:
            return num
    return 50


def match_percentage_to_words(match_percentage):
    """Convert match percentage into qualitative feedback."""
    if match_percentage >= 80:
        return "*Excellent Match* ✅"
    elif match_percentage >= 60:
        return "*Strong Match* 👍"
    elif match_percentage >= 40:
        return "*Good Match* ⚡"
    elif match_percentage >= 20:
        return "*Weak Match* ⚠"
    return "*Poor Match* ❌"


def display_pie_chart(match_percentage):
    """Display pie chart for resume-job match percentage."""
    labels = ["Match", "Not Match"]
    sizes = [match_percentage, 100 - match_percentage]
    colors = ["#4CAF50", "#FF5733"]
    explode = (0.1, 0)

    fig, ax = plt.subplots()
    ax.pie(
        sizes,
        labels=labels,
        autopct="%1.1f%%",
        colors=colors,
        startangle=140,
        explode=explode,
        textprops={"color": "w"},
    )
    ax.axis("equal")
    st.pyplot(fig)

# ---------------------------
# 📌 Sidebar Navigation
# ---------------------------
st.sidebar.title("Navigation")
page = st.sidebar.radio("Select a Feature", ["Resume Analyzer", "Cold Email Generator"])

# ---------------------------
# 📄 Resume Analyzer
# ---------------------------
if page == "Resume Analyzer":
    st.markdown("<h1 style='text-align: center;'>📝 Technical ATS Resume Expert</h1>", unsafe_allow_html=True)

    job_desc = st.text_area("📌 Paste Job Description: ")
    uploaded_file = st.file_uploader("📂 Upload your resume (PDF)...", type=["pdf"])

    resume_text = ""
    pdf_image = None
    if uploaded_file:
        st.success("✅ Resume Uploaded Successfully!")
        resume_text = extract_text_from_pdf(uploaded_file)
        pdf_image, _ = input_pdf_setup(uploaded_file)

    st.divider()

    col1, col2, col3 = st.columns(3)
    analyze_btn = col1.button("🔍 Analyze Resume")
    improve_btn = col2.button("📈 Improve Skills")
    match_btn = col3.button("⚡ Match with Job")

    prompts = {
        "analyze": "Analyze the resume and job description. Provide detailed, actionable feedback.",
        "improve": "Suggest concrete skill improvements and certifications.",
        "match": """
        Evaluate the resume against the job description.
        Output format:
        - Match Percentage: XX%
        - Missing Keywords: [List missing skills/tools]
        - Final Thoughts: Summary of strengths, weaknesses, recommendation.
        """,
    }

    if uploaded_file:
        if analyze_btn:
            with st.spinner("Analyzing resume..."):
                response = get_openrouter_response(prompts["analyze"], job_desc, resume_text)
            st.subheader("📊 Analysis")
            st.write(response)

        elif improve_btn:
            with st.spinner("Generating improvement suggestions..."):
                response = get_openrouter_response(prompts["improve"], job_desc, resume_text)
            st.subheader("📈 Improvement Suggestions")
            st.write(response)

        elif match_btn:
            with st.spinner("Matching resume with job description..."):
                response = get_openrouter_response(prompts["match"], job_desc, resume_text)
            match_percentage = extract_match_percentage(response)

            if pdf_image:
                st.image(pdf_image, caption="Resume First Page", width=400)

            st.subheader(f"📌 Match Percentage: *{match_percentage}%*")
            display_pie_chart(match_percentage)
            st.markdown(
                f"<h3 style='text-align: center;'>{match_percentage_to_words(match_percentage)}</h3>",
                unsafe_allow_html=True,
            )

            st.subheader("📑 Detailed Analysis")
            st.write(response)
    else:
        if analyze_btn or improve_btn or match_btn:
            st.error("❌ Please upload your resume!")

# ---------------------------
# 📧 Cold Email Generator
# ---------------------------
elif page == "Cold Email Generator":
    st.markdown("<h1 style='text-align: center;'>📧 AI Cold Email Generator</h1>", unsafe_allow_html=True)

    uploaded_file = st.file_uploader("📂 Upload your resume (PDF)...", type=["pdf"])
    extracted_text = ""

    if uploaded_file:
        st.success("✅ Resume Uploaded Successfully!")
        extracted_text = extract_text_from_pdf(uploaded_file)
        st.text_area("📑 Extracted Resume Details:", value=extracted_text, height=200, disabled=True)

    job_description = st.text_area("📌 Enter Job Description:", height=150)
    linkedin = st.text_input("🔗 Enter Your LinkedIn Profile (Optional):")
    tone = st.radio("🎯 Select Email Tone:", ["Formal", "Casual"], index=0)

    if st.button("✉️ Generate Cold Email"):
        if uploaded_file and job_description.strip():
            with st.spinner("Generating cold email..."):
                prompt = f"""
                Write a professional cold email for a job opportunity.

                LinkedIn: {linkedin if linkedin else "Not Provided"}
                Tone: {tone}

                Resume:
                {extracted_text}

                Job Description:
                {job_description}
                """
                cold_email = get_openrouter_response(prompt, job_description, extracted_text)

            st.subheader("📨 Generated Cold Email:")
            st.write(cold_email)
            st.download_button("⬇️ Download Email", cold_email, file_name="cold_email.txt")
        else:
            st.warning("⚠️ Please upload your resume and enter a job description!")
