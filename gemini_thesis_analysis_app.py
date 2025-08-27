import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import json
import io

st.set_page_config(layout="wide", page_title="ابزار تحلیل پایان‌نامه")

st.title("💡 ابزار تحلیل نوآوری پایان‌نامه‌ها با جمینای")
st.markdown("""
این ابزار به شما کمک می‌کند تا پایان‌نامه‌ها را بر اساس معیارهای نوآوری تحلیل و رتبه‌بندی کنید.
فایل اکسل حاوی عنوان و چکیده پایان‌نامه‌ها را آپلود کنید و API Key جمینای را وارد نمایید.
""")

# Input for Gemini API Key
api_key = st.text_input("🔑 Gemini API Key", type="password", help="کلید API خود را از Google AI Studio دریافت کنید.")

if not api_key:
    st.info("لطفاً برای شروع، Gemini API Key خود را وارد کنید.")
    st.stop()

# Configure and test the API key
try:
    genai.configure(api_key=api_key)
    model_options = [m.name for m in genai.list_models() if "generateContent" in m.supported_generative_methods]
    st.success("API Key با موفقیت تنظیم شد!")
except Exception as e:
    st.error(f"خطا در تنظیم API Key: {e}. لطفاً از صحت کلید اطمینان حاصل کنید.")
    st.stop()

uploaded_file = st.file_uploader("📂 فایل اکسل خود را آپلود کنید", type=["xlsx"], help="فایل اکسل شما باید شامل ستون‌های 'عنوان' و 'چکیده' باشد.")

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        st.success("فایل با موفقیت بارگذاری شد!")

        if 'عنوان' not in df.columns or 'چکیده' not in df.columns:
            st.error("فایل اکسل باید شامل ستون‌های 'عنوان' و 'چکیده' باشد.")
            st.stop()
        else:
            st.write("پیش‌نمایش فایل آپلود شده:")
            st.dataframe(df.head())

    except Exception as e:
        st.error(f"خطا در خواندن فایل اکسل: {e}. لطفاً از فرمت صحیح فایل اطمینان حاصل کنید.")
        st.stop()
    
    st.markdown("---")
    st.header("⚙️ تحلیل پایان‌نامه‌ها")

    selected_model = st.selectbox("🤖 مدل جمینای را انتخاب کنید:", model_options, index=model_options.index("gemini-pro") if "gemini-pro" in model_options else 0)

    # Initialize the model
    model = genai.GenerativeModel(selected_model)

    # Define evaluation criteria based on the image provided
    criteria = """
    معیارهای ارزیابی نوآوری (بر اساس تصویر):
    1.  **حوزه علمی پایان‌نامه**: آیا به حوزه‌هایی است که بیشترین ارجاع به پشتوانه‌ها را دارند؟ (مثلاً: داروسازی، مهندسی، علوم زیستی، مواد، پزشکی و...)
        * نمره: 1 تا 3
    2.  **استفاده از فناوری یا نوآوری خاص**: آیا چکیده به تکنولوژی نو، مدل فنی، محصول، الگوریتم، فرآیند، یا متدولوژی جدید اشاره دارد؟
        * نمره: 1 تا 3
    3.  **حل مسئله صنعتی اجتماعی مشخص**: آیا در چکیده به یک نیاز یا مسئله کاربردی خاص اشاره شده؟
        * نمره: 1 تا 3
    4.  **قابلیت تجاری‌سازی**: آیا پایان‌نامه به نتایجی ختم شده که قابل توسعه به محصول، نرم‌افزار، دستگاه یا راهکار باشد؟
        * نمره: 1 تا 3
    5.  **همکاری با صنعت/نهاد غیردانشگاهی**: آیا چکیده نشان می‌دهد با یک نهاد صنعتی یا سازمانی همکاری شده؟
        * نمره: 1 یا 0
    """

    st.write("لطفاً منتظر بمانید تا تحلیل پایان‌نامه‌ها انجام شود...")

    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()

    results = []
    for index, row in df.iterrows():
        title = row['عنوان']
        abstract = row['چکیده']

        prompt = f"""
        با توجه به معیارهای زیر و عنوان و چکیده پایان‌نامه، این پایان‌نامه را ارزیابی کرده و یک امتیاز کلی بین 0 تا 10 بدهید.
        امتیازات جزئی را برای هر معیار نیز ذکر کنید. فرمت خروجی باید به صورت JSON باشد.

        **عنوان پایان‌نامه:** {title}
        **چکیده پایان‌نامه:** {abstract}

        **{criteria}**

        **مثال فرمت خروجی JSON:**
        {{
            "عنوان": "عنوان پایان‌نامه",
            "تحلیل_کلی": "متن تحلیل کلی...",
            "امتیازات_جزئی": {{
                "حوزه_علمی_پایان_نامه": 2,
                "استفاده_از_فناوری_یا_نوآوری_خاص": 3,
                "حل_مسئله_صنعتی_اجتماعی_مشخص": 2,
                "قابلیت_تجاری_سازی": 3,
                "همکاری_با_صنعت_نهاد_غیردانشگاهی": 1
            }},
            "امتیاز_کلی": 8
        }}
        """
        
        try:
            response = model.generate_content(prompt)
            analysis = json.loads(response.text)
            results.append(analysis)
        except Exception as e:
            st.warning(f"خطا در تحلیل پایان‌نامه '{title}': {e}. این مورد نادیده گرفته شد.")
            results.append({
                "عنوان": title,
                "تحلیل_کلی": "خطا در تحلیل",
                "امتیازات_جزئی": {},
                "امتیاز_کلی": 0
            })

        # Update progress bar
        progress = (index + 1) / len(df)
        progress_bar.progress(progress)
        status_text.text(f"در حال تحلیل: {index + 1}/{len(df)} پایان‌نامه")

    st.success("تحلیل پایان‌نامه‌ها به پایان رسید!")
    
    # Convert results to DataFrame for display and download
    output_data = []
    for res in results:
        row_data = {
            "عنوان": res.get("عنوان", "N/A"),
            "تحلیل_کلی": res.get("تحلیل_کلی", "N/A"),
            "امتیاز_کلی": res.get("امتیاز_کلی", "N/A"),
        }
        # Add detailed scores if available
        detailed_scores = res.get("امتیازات_جزئی", {})
        row_data.update(detailed_scores)
        output_data.append(row_data)

    output_df = pd.DataFrame(output_data)

    st.header("📊 نتایج تحلیل")
    st.dataframe(output_df)

    # Download button
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        output_df.to_excel(writer, index=False, sheet_name='نتایج رتبه‌بندی')
    
    st.download_button(
        label="📥 دانلود نتایج به صورت فایل اکسل",
        data=buffer,
        file_name="innovation_ranking_results.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.markdown("---")
    # Reset button
    if st.button("🔄 بازنشانی", help="فرم را برای شروع مجدد پاک می‌کند."):
        st.experimental_rerun()
