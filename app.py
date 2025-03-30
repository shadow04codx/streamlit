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

# Set page configuration at the very beginning
st.set_page_config(page_title="AI Job Assistant", layout="wide")

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Sidebar Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Select a Feature", ["Resume Analyzer", "Cold Email Generator"])

# Function to Get Gemini AI Response
def get_gemini_response(input_text, pdf_content, prompt):
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content([input_text, pdf_content[0], prompt])
    return response.text

# Function to Extract Text from PDF Resume
def extract_text_from_pdf(uploaded_file):
    with fitz.open(stream=uploaded_file.read(), filetype="pdf") as pdf_doc:
        text = ""
        for page in pdf_doc:
            text += page.get_text("text") + "\n"
    return text.strip()

# Function to Extract Resume Image and Encode
def input_pdf_setup(uploaded_file):
    if uploaded_file is not None:
        with fitz.open(stream=uploaded_file.read(), filetype="pdf") as pdf_doc:
            first_page = pdf_doc[0].get_pixmap()
            img_bytes = first_page.tobytes("png")
            encoded_img = base64.b64encode(img_bytes).decode()
            return Image.open(io.BytesIO(img_bytes)), encoded_img
    else:
        raise FileNotFoundError("No file uploaded")

# Improved Extract Match Percentage
def extract_match_percentage(response_text):
    match = re.search(r"Match\s*Percentage[:\s]*([\d]+)%", response_text, re.IGNORECASE)
    if match:
        return int(match.group(1))

    # Additional checks to catch different formats
    numbers = re.findall(r'\b\d+\b', response_text)
    for num in numbers:
        num = int(num)
        if 50 <= num <= 100:  # Avoid extremely low incorrect values
            return num

    return 50  # Default minimum threshold if AI response is unclear

# Convert Match Percentage to Words
def match_percentage_to_words(match_percentage):
    if match_percentage >= 80:
        return "*Excellent Match* ✅"
    elif match_percentage >= 60:
        return "*Strong Match* 👍"
    elif match_percentage >= 40:
        return "*Good Match* ⚡"
    elif match_percentage >= 20:
        return "*Weak Match* ⚠"
    else:
        return "*Poor Match* ❌"

# Display Pie Chart
def display_pie_chart(match_percentage):
    labels = ['Match', 'Not Match']
    sizes = [match_percentage, 100 - match_percentage]
    colors = ['#4CAF50', '#FF5733']
    explode = (0.1, 0)

    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors, startangle=140, explode=explode)
    ax.axis('equal')
    st.pyplot(fig)

# Resume Analyzer Feature
if page == "Resume Analyzer":
    st.markdown("<h1 style='text-align: center;'>Technical ATS Resume Expert</h1>", unsafe_allow_html=True)

    input_text = st.text_area("Job Description: ")
    uploaded_file = st.file_uploader("Upload your resume (PDF)...", type=["pdf"])

    if uploaded_file:
        st.success("✅ PDF Uploaded Successfully!")

    # Buttons
    submit1 = st.button("Analyze Resume", key="analyze_resume")
    submit2 = st.button("How Can I Improve My Skills?", key="improve_skills")
    submit3 = st.button("Match Resume with Job Description", key="match_resume")

    # Prompts
    input_prompt1 = """Analyze the resume and job description to provide feedback..."""
    input_prompt2 = """Suggest career improvements based on resume analysis..."""
    input_prompt3 = """
    You are an advanced AI-based ATS scanner. Evaluate the resume against the job description 
    and provide a *clear match percentage* between *0% to 100%*. 
    
    *Output Format Example:*
    - Match Percentage: XX%
    - Missing Keywords: [List missing skills/tools]
    - Final Thoughts: Summary of strengths, weaknesses, and a recommendation.
    
    Ensure the evaluation is *concise, relevant, and data-driven*.
    """

    # Actions
    if submit1 and uploaded_file:
        pdf_image, pdf_base64 = input_pdf_setup(uploaded_file)
        response = get_gemini_response(input_text, [{"mime_type": "image/png", "data": pdf_base64}], input_prompt1)
        st.subheader("📌 Analysis")
        st.write(response)

    elif submit2 and uploaded_file:
        pdf_image, pdf_base64 = input_pdf_setup(uploaded_file)
        response = get_gemini_response(input_text, [{"mime_type": "image/png", "data": pdf_base64}], input_prompt2)
        st.subheader("📌 Improvement Suggestions")
        st.write(response)

    elif submit3 and uploaded_file:
        pdf_image, pdf_base64 = input_pdf_setup(uploaded_file)
        response = get_gemini_response(input_text, [{"mime_type": "image/png", "data": pdf_base64}], input_prompt3)
        match_percentage = extract_match_percentage(response)

        st.image(pdf_image, caption="Resume First Page", width=400)
        st.subheader(f"📌 Match Percentage: *{match_percentage}%*")

        display_pie_chart(match_percentage)

        st.markdown(f"<h3 style='text-align: center;'>{match_percentage_to_words(match_percentage)}</h3>", unsafe_allow_html=True)

        st.subheader("📌 Detailed Analysis")
        st.write(response)

    elif (submit1 or submit2 or submit3) and not uploaded_file:
        st.error("❌ Please upload your resume!")

# Cold Email Generator Feature with Resume Extraction
elif page == "Cold Email Generator":
    st.markdown("<h1 style='text-align: center;'>📧 AI Cold Email Generator</h1>", unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Upload your resume (PDF) for auto-extraction...", type=["pdf"])

    if uploaded_file:
        st.success("✅ Resume Uploaded Successfully!")
        extracted_text = extract_text_from_pdf(uploaded_file)

        st.text_area("Extracted Resume Details:", value=extracted_text, height=200, disabled=True)

    job_description = st.text_area("Enter Job Description:", height=200)
    linkedin = st.text_input("Enter Your LinkedIn Profile (Optional):")
    tone = st.radio("Select Email Tone:", ["Formal", "Casual"], index=0)

    # Function to Generate Cold Email Using Extracted Resume Data
    def get_cold_email(job_description, resume_text, linkedin, tone):
        prompt = f"""
        Write a professional cold email for a job opportunity based on the provided resume details and job description.

        *LinkedIn Profile (if provided)*: {linkedin}
        *Email Tone*: {tone}

        *Extracted Resume Details:*
        {resume_text}

        *Job Description:*
        {job_description}

        Generate a complete email with proper formatting.
        """

        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text

    generate_email = st.button("Generate Cold Email", key="generate_email")

    if generate_email:
        if uploaded_file and job_description.strip():
            cold_email = get_cold_email(job_description, extracted_text, linkedin, tone)
            st.subheader("Generated Cold Email:")
            st.write(cold_email)
        else:
            st.warning("Please upload your resume and enter a job description!")
