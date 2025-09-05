# app.py - Simple Addition Calculator (Streamlit)

import streamlit as st

st.title("Simple Addition Calculator")

a = st.number_input("Enter first number", value=0.0, step=1.0, format="%.5f")
b = st.number_input("Enter second number", value=0.0, step=1.0, format="%.5f")

if st.button("Calculate sum"):
    result = a + b
    st.success(f"The sum is: {result}")

    # prepare text file content and provide download
    result_text = f"First number: {a}\nSecond number: {b}\nSum: {result}\n"
    st.download_button(
        label="Download Result",
        data=result_text,
        file_name="sum_result.txt",
        mime="text/plain",
    )
