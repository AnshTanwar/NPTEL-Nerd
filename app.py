import os
import streamlit as st
import google.generativeai as genai
import tempfile
import time


genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

def upload_to_gemini(file):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(file.getvalue())
        tmp_file_path = tmp_file.name

    try:
        uploaded_file = genai.upload_file(tmp_file_path, mime_type="application/pdf")
        alert = st.success(f"Uploaded file: {uploaded_file.name}")
        time.sleep(2)
        alert.empty()
        return uploaded_file
    finally:
        os.unlink(tmp_file_path)

def cleanup_files():
    if "active_files" in st.session_state:
        for file in st.session_state.active_files:
            genai.delete_file(file.name)
            alert = st.success(f"Deleted file: {file.name}")
            time.sleep(1)
            alert.empty()
        st.session_state.clear()
        alert = st.success("All uploaded files have been deleted.")
        time.sleep(2)
        alert.empty()
    st.session_state.show_form = True
    st.rerun()


st.title("Your NPTEL Assignment Saviour")

if "show_form" not in st.session_state:
    st.session_state.show_form = True
if "active_files" not in st.session_state:
    st.session_state.active_files = []

if st.session_state.show_form:
    with st.form("my-form", clear_on_submit=True):
        files = st.file_uploader("Upload files", accept_multiple_files=True, type="pdf")
        submitted = st.form_submit_button("Submit")

    if submitted and files is not None:
        st.session_state.active_files = []
        for file in files:
            with st.spinner(f"Uploading and processing file: {file.name}..."):
                gemini_file = upload_to_gemini(file)
                st.session_state.active_files.append(gemini_file)
        st.session_state.show_form = False 
        st.rerun() 

sys_prpt = """Please Cite the page or paragraph or anywhere you found the answer to the question. 
Your response should be clear, concise, and directly grounded in the information from the documents and your contextual knowledge.
You may use your own knowledge incase you fail to find an answer in the documents or your context but please acknowledge it in your response.
"""

if st.session_state.active_files:
    generation_config = {
        "temperature": 0.3,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 8192,
    }
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config,
    )

    if "chat_session" not in st.session_state:
        st.session_state.chat_session = model.start_chat(history=[])

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if not st.session_state.messages:
        prompt = "What is the title of the document(s)?"
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        response = model.generate_content([*st.session_state.active_files, prompt+sys_prpt])
        st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})

    if prompt := st.chat_input("Ask your questions from the assignment!"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        response = model.generate_content([*st.session_state.active_files, prompt+sys_prpt])
        st.markdown(response.text)
        st.session_state.messages.append({"role": "assistant", "content": response.text})

    if st.button("Cleanup Files"):
        cleanup_files()

else:
    st.info("Please upload this week's lecture material in a PDF format")
