import streamlit as st
import os
import base64
import io
import re
import fitz  # PyMuPDF
import matplotlib.pyplot as plt
from PIL import Image
from dotenv import load_dotenv
import google.generativeai as genai

# ---------------------------
# 🌐 App Setup
# ---------------------------
st.set_page_config(page_title="AI Job Assistant", layout="wide")
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# ---------------------------
# 🔧 Utility Functions
# ---------------------------
@st.cache_data
def extract_text_from_pdf(uploaded_file):
    """Extract plain text from uploaded PDF resume."""
    with fitz.open(stream=uploaded_file.read(), filetype="pdf") as pdf_doc:
        text = ""
        for page in pdf_doc:
            text += page.get_text("text") + "\n"
    return text.strip()


def input_pdf_setup(uploaded_file):
    """Convert first page of PDF into image and Base64 encoding."""
    if uploaded_file is None:
        raise FileNotFoundError("No file uploaded")
    with fitz.open(stream=uploaded_file.read(), filetype="pdf") as pdf_doc:
        first_page = pdf_doc[0].get_pixmap()
        img_bytes = first_page.tobytes("png")
        encoded_img = base64.b64encode(img_bytes).decode()
        return Image.open(io.BytesIO(img_bytes)), encoded_img


def get_gemini_response(prompt, job_desc="", pdf_content=None):
    """Generate response from Gemini AI model."""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        inputs = [job_desc, pdf_content] if pdf_content else [job_desc]
        inputs.append(prompt)
        response = model.generate_content(inputs)
        return response.text
    except Exception as e:
        return f"⚠️ Error fetching response: {str(e)}"


def extract_match_percentage(response_text):
    """Extract numeric match percentage from AI response."""
    match = re.search(r"Match\s*Percentage[:\s]*([\d]+)%", response_text, re.IGNORECASE)
    if match:
        return int(match.group(1))

    numbers = re.findall(r'\b\d+\b', response_text)
    for num in numbers:
        num = int(num)
        if 50 <= num <= 100:
            return num
    return 50  # Default fallback


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
    labels = ['Match', 'Not Match']
    sizes = [match_percentage, 100 - match_percentage]
    colors = ['#4CAF50', '#FF5733']
    explode = (0.1, 0)

    fig, ax = plt.subplots()
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, autopct='%1.1f%%',
        colors=colors, startangle=140, explode=explode, textprops={'color': "w"}
    )
    ax.axis('equal')
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

    if uploaded_file:
        st.success("✅ Resume Uploaded Successfully!")

    st.divider()

    # Action Buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        analyze_btn = st.button("🔍 Analyze Resume")
    with col2:
        improve_btn = st.button("📈 Improve Skills")
    with col3:
        match_btn = st.button("⚡ Match with Job")

    # Prompts
    prompts = {
        "analyze": "Analyze the resume and job description to provide detailed, actionable feedback.",
        "improve": "Suggest concrete skill improvements and certifications to strengthen this resume.",
        "match": """
        You are an advanced AI-based ATS scanner. Evaluate the resume against the job description 
        and provide a *clear match percentage* between *0% to 100%*. 
        Format:
        - Match Percentage: XX%
        - Missing Keywords: [List missing skills/tools]
        - Final Thoughts: Summary of strengths, weaknesses, and recommendation.
        """
    }

    if uploaded_file:
        pdf_image, pdf_base64 = input_pdf_setup(uploaded_file)

        if analyze_btn:
            with st.spinner("Analyzing resume..."):
                response = get_gemini_response(prompts["analyze"], job_desc, {"mime_type": "image/png", "data": pdf_base64})
            st.subheader("📊 Analysis")
            st.write(response)

        elif improve_btn:
            with st.spinner("Generating improvement suggestions..."):
                response = get_gemini_response(prompts["improve"], job_desc, {"mime_type": "image/png", "data": pdf_base64})
            st.subheader("📈 Improvement Suggestions")
            st.write(response)

        elif match_btn:
            with st.spinner("Matching resume with job description..."):
                response = get_gemini_response(prompts["match"], job_desc, {"mime_type": "image/png", "data": pdf_base64})

            match_percentage = extract_match_percentage(response)
            st.image(pdf_image, caption="Resume First Page", width=400)
            st.subheader(f"📌 Match Percentage: *{match_percentage}%*")
            display_pie_chart(match_percentage)
            st.markdown(f"<h3 style='text-align: center;'>{match_percentage_to_words(match_percentage)}</h3>", unsafe_allow_html=True)

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

    uploaded_file = st.file_uploader("📂 Upload your resume (PDF) for auto-extraction...", type=["pdf"])
    extracted_text = ""

    if uploaded_file:
        st.success("✅ Resume Uploaded Successfully!")
        extracted_text = extract_text_from_pdf(uploaded_file)
        st.text_area("📑 Extracted Resume Details:", value=extracted_text, height=200, disabled=True)

    job_description = st.text_area("📌 Enter Job Description:", height=150)
    linkedin = st.text_input("🔗 Enter Your LinkedIn Profile (Optional):")
    tone = st.radio("🎯 Select Email Tone:", ["Formal", "Casual"], index=0)

    def get_cold_email(job_description, resume_text, linkedin, tone):
        prompt = f"""
        Write a professional cold email for a job opportunity based on the resume and job description.

        LinkedIn: {linkedin if linkedin else 'Not Provided'}
        Tone: {tone}

        Resume Details:
        {resume_text}

        Job Description:
        {job_description}
        """
        return get_gemini_response(prompt)

    if st.button("✉️ Generate Cold Email"):
        if uploaded_file and job_description.strip():
            with st.spinner("Generating cold email..."):
                cold_email = get_cold_email(job_description, extracted_text, linkedin, tone)
            st.subheader("📨 Generated Cold Email:")
            st.write(cold_email)

            # Download Option
            st.download_button("⬇️ Download Email", cold_email, file_name="cold_email.txt")
        else:
            st.warning("⚠️ Please upload your resume and enter a job description!")
