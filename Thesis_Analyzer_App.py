import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
from time import sleep

# --- Page Configuration ---
# تنظیمات اولیه صفحه شامل عنوان، آیکون و طرح‌بندی
st.set_page_config(
    page_title="تحلیلگر پایان‌نامه داروسازی",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Functions ---

def create_prompt(title, abstract):
    """
    این تابع یک دستور (prompt) دقیق برای مدل هوش مصنوعی ایجاد می‌کند.
    """
    return f"""
        شما یک متخصص نخبه در زمینه علوم دارویی، توسعه کسب‌وکار و انتقال فناوری هستید.
        وظیفه شما تحلیل عنوان و چکیده پایان‌نامه زیر از رشته داروسازی است.
        آن را بر اساس سه معیار اصلی با دقت ارزیابی کنید:
        1.  **پتانسیل تجاری‌سازی (Commercialization Potential):** آیا این ایده می‌تواند به یک محصول، سرویس یا پتنت سودآور تبدیل شود؟ بازار هدف آن چیست؟
        2.  **سطح نوآوری (Innovation Level):** آیا این تحقیق یک رویکرد جدید، روش نوین یا کشف بدیع را ارائه می‌دهد؟ در مقایسه با دانش موجود چقدر نوآورانه است؟
        3.  **پتانسیل ارزش‌آفرینی (Value Creation Potential):** این تحقیق چه مشکلی را حل می‌کند؟ چه ارزشی برای بیماران، صنعت داروسازی یا جامعه علمی ایجاد می‌کند؟

        برای هر معیار یک امتیاز از ۱ تا ۱۰ بدهید. سپس یک تحلیل کلی و مختصر (حداکثر ۲-۳ جمله) ارائه دهید.
        خروجی را **دقیقا** با فرمت زیر و فقط به زبان فارسی ارائه دهید:

        نوآوری: [امتیاز]/10
        تجاری‌سازی: [امتیاز]/10
        ارزش‌آفرینی: [امتیاز]/10
        تحلیل کلی: [خلاصه تحلیل شما در اینجا]

        ---
        **عنوان پایان‌نامه:** {title}

        **چکیده پایان‌نامه:** {abstract}
        ---
    """

def parse_response(text):
    """
    این تابع پاسخ ساختاریافته مدل هوش مصنوعی را تجزیه کرده و امتیازها و خلاصه را استخراج می‌کند.
    """
    data = {
        "نوآوری": "N/A",
        "تجاری‌سازی": "N/A",
        "ارزش‌آفرینی": "N/A",
        "تحلیل کلی": "خطا در پردازش پاسخ مدل."
    }
    try:
        lines = text.strip().split('\n')
        for line in lines:
            if "نوآوری:" in line:
                data["نوآوری"] = line.split(':')[1].strip().split('/')[0]
            elif "تجاری‌سازی:" in line:
                data["تجاری‌سازی"] = line.split(':')[1].strip().split('/')[0]
            elif "ارزش‌آفرینی:" in line:
                data["ارزش‌آفرینی"] = line.split(':')[1].strip().split('/')[0]
            elif "تحلیل کلی:" in line:
                data["تحلیل کلی"] = line.split(':', 1)[1].strip()
    except Exception:
        # در صورت بروز خطا در تجزیه، از پیام پیش‌فرض استفاده می‌شود.
        pass
    return data

def to_excel(df):
    """
    یک DataFrame را به فایل اکسل در حافظه (in-memory) تبدیل می‌کند.
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='تحلیل_پایان‌نامه‌ها')
        # تنظیم خودکار عرض ستون‌ها برای خوانایی بهتر
        for column in df:
            column_length = max(df[column].astype(str).map(len).max(), len(column)) + 2
            col_idx = df.columns.get_loc(column)
            writer.sheets['تحلیل_پایان‌نامه‌ها'].set_column(col_idx, col_idx, column_length)
    processed_data = output.getvalue()
    return processed_data


# --- Streamlit App UI ---

st.title("🧪 تحلیلگر هوشمند پتانسیل پایان‌نامه‌های داروسازی")
st.markdown("این ابزار با استفاده از هوش مصنوعی Gemini، پتانسیل **تجاری‌سازی**، **نوآوری** و **ارزش‌آفرینی** پایان‌نامه‌ها را بر اساس عنوان و چکیده تحلیل می‌کند.")

# نوار کناری برای دریافت ورودی‌ها
st.sidebar.header("تنظیمات")

# 1. ورودی کلید API
# نکته: مدل gemini-2.0-flash وجود ندارد. از آخرین مدل flash یعنی gemini-1.5-flash-latest استفاده می‌کنیم.
api_key = st.sidebar.text_input("🔑 کلید API گوگل Gemini خود را وارد کنید:", type="password", help="کلید API شما محرمانه باقی می‌ماند و فقط برای این جلسه استفاده می‌شود.")

if not api_key:
    st.warning("لطفاً برای شروع تحلیل، کلید API گوگل Gemini خود را در نوار کناری وارد کنید.")
    st.stop()

try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
except Exception as e:
    st.error(f"❌ خطا در تنظیم کلید API: لطفاً از معتبر بودن کلید خود اطمینان حاصل کنید.")
    st.stop()

# 2. بارگذاری فایل
uploaded_file = st.file_uploader("📂 فایل اکسل حاوی عناوین و چکیده‌ها را بارگذاری کنید", type=["xlsx"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        st.success("✅ فایل با موفقیت بارگذاری شد. لطفا ستون‌ها را مشخص کنید.")
        st.dataframe(df.head())

        st.sidebar.header("انتخاب ستون‌ها")
        columns = df.columns.tolist()

        # 3. انتخاب ستون‌ها
        title_col = st.sidebar.selectbox("ستون حاوی **عنوان** را انتخاب کنید:", columns, index=0)
        abstract_col = st.sidebar.selectbox("ستون حاوی **چکیده** را انتخاب کنید:", columns, index=1 if len(columns) > 1 else 0)

        if st.button("🚀 شروع تحلیل", type="primary"):
            if title_col == abstract_col:
                st.error("ستون عنوان و چکیده نمی‌توانند یکسان باشند.")
            else:
                with st.spinner("در حال تحلیل... این فرآیند ممکن است بسته به تعداد ردیف‌ها زمان‌بر باشد."):
                    progress_bar = st.progress(0, text="شروع فرآیند تحلیل...")
                    total_rows = len(df)
                    results = []

                    for i, row in df.iterrows():
                        title = str(row.get(title_col, ''))
                        abstract = str(row.get(abstract_col, ''))

                        if not title or not abstract:
                            results.append({
                                "نوآوری": "N/A", "تجاری‌سازی": "N/A",
                                "ارزش‌آفرینی": "N/A", "تحلیل کلی": "عنوان یا چکیده موجود نیست."
                            })
                        else:
                            prompt = create_prompt(title, abstract)
                            try:
                                response = model.generate_content(prompt)
                                parsed_data = parse_response(response.text)
                                results.append(parsed_data)
                            except Exception as e:
                                st.error(f"خطا در ردیف {i+1}: {e}")
                                results.append({
                                    "نوآوری": "خطا", "تجاری‌سازی": "خطا",
                                    "ارزش‌آفرینی": "خطا", "تحلیل کلی": str(e)
                                })
                        
                        # یک تأخیر کوتاه برای جلوگیری از رسیدن به محدودیت‌های API
                        sleep(1) 
                        progress_bar.progress((i + 1) / total_rows, text=f"در حال پردازش ردیف {i+1} از {total_rows}")
                
                st.success("🎉 تحلیل با موفقیت انجام شد!")

                # ایجاد DataFrame از نتایج و الحاق آن به DataFrame اصلی
                results_df = pd.DataFrame(results)
                
                # تغییر نام ستون‌ها برای وضوح بیشتر
                results_df.rename(columns={
                    "نوآوری": "امتیاز نوآوری",
                    "تجاری‌سازی": "امتیاز تجاری‌سازی",
                    "ارزش‌آفرینی": "امتیاز ارزش‌آفرینی",
                    "تحلیل کلی": "خلاصه تحلیل هوش مصنوعی"
                }, inplace=True)
                
                final_df = pd.concat([df, results_df], axis=1)

                st.dataframe(final_df)

                # 4. دکمه دانلود
                excel_data = to_excel(final_df)
                st.download_button(
                    label="📥 دانلود فایل اکسل نتایج",
                    data=excel_data,
                    file_name="تحلیل_پایان‌نامه‌ها.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    except Exception as e:
        st.error(f"خطا در خواندن فایل اکسل: {e}")
