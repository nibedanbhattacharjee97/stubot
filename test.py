import streamlit as st
import base64

# Set the page config for wider display
st.set_page_config(layout="wide")

# Function to load and encode the background image
def add_bg_from_local(image_file):
    with open(image_file, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()

    # Add custom CSS
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpg;base64,{encoded_string}");
            background-size: cover;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# Call the function to set the background image
add_bg_from_local('Actual.jpg')  # Replace with your image file

# Your app content goes here
st.title("Welcome to the Streamlit App")
st.write("This is an app with a background image.")
